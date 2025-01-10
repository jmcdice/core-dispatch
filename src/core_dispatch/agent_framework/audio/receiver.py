# src/core_dispatch/agent_framework/audio/receiver.py

import json
import asyncio
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable, Any

from core_dispatch.agent_framework.core.base_agent import BaseAgent
from core_dispatch.agent_framework.audio.transcription import (
    TranscriptionConfig,
    TranscriptionResult,
    create_transcription_service,
    TranscriptionService
)

LOCK_FILE = '/tmp/tx_rx_lock'

# Import settings from core_dispatch.launch_control.config
from core_dispatch.launch_control.config.settings import (
    SAMPLE_RATE,
    CHANNELS,
    AUDIO_DEVICE_INDEX,
    AUDIO_THRESHOLD,
    SILENCE_THRESHOLD,
    MIN_RECORDING_DURATION,
    MAX_RECORDING_DURATION,
    PRE_ROLL_DURATION,
    POST_ROLL_DURATION,
    TRANSCRIPTION_SERVICE_TYPE,
    OPENAI_API_KEY,
    GOOGLE_CLOUD_PROJECT
)


@dataclass
class AudioConfig:
    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    device_index: int = AUDIO_DEVICE_INDEX
    audio_threshold: float = AUDIO_THRESHOLD
    silence_threshold: float = SILENCE_THRESHOLD
    min_duration: float = MIN_RECORDING_DURATION
    max_duration: float = MAX_RECORDING_DURATION
    pre_roll: float = PRE_ROLL_DURATION
    post_roll: float = POST_ROLL_DURATION
    queue_size: int = 100
    project_id: str = GOOGLE_CLOUD_PROJECT if GOOGLE_CLOUD_PROJECT else ""
    transcription_service_type: str = TRANSCRIPTION_SERVICE_TYPE
    api_key: Optional[str] = OPENAI_API_KEY


class AudioReceiverAgent(BaseAgent):
    """Agent responsible for receiving audio and providing transcriptions."""

    def __init__(
        self,
        config: AudioConfig,
        on_transcription: Callable[[str], Any],
        debug_mode: bool = False
    ):
        super().__init__()
        self.config = config
        self.on_transcription = on_transcription
        self.debug_mode = debug_mode

        self.audio_queue = asyncio.Queue(maxsize=config.queue_size)
        self.terminate_flag = asyncio.Event()
        self.loop = None

        transcription_config = TranscriptionConfig(
            sample_rate=config.sample_rate,
            language="en-US",
            debug_mode=debug_mode,
            project_id=config.project_id,
            api_key=config.api_key
        )
        self.transcription_service: TranscriptionService = create_transcription_service(
            config.transcription_service_type,
            transcription_config
        )

        self.pre_roll_buffer = []
        self.recording = False
        self.audio_frames = []
        self.silence_counter = 0.0
        self.recording_duration = 0.0
        self.stream = None

    async def initialize(self):
        """Initialize the transcription service and test audio input."""
        await self.transcription_service.initialize()
        # Test audio input levels before starting
        await self._test_audio_input()
        self.logger.info("AudioReceiverAgent initialized.")

    async def start(self):
        """Start the audio reception and transcription process."""
        self.loop = asyncio.get_running_loop()

        # Start processing task
        asyncio.create_task(self._process_audio_queue())

        # Start audio stream
        try:
            self.stream = sd.InputStream(
                device=self.config.device_index,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            self.logger.info("AudioReceiverAgent stream started.")
        except Exception as e:
            self.logger.error(f"Error starting audio receiver: {e}")
            raise

    async def stop(self):
        """Stop the audio reception and transcription."""
        self.terminate_flag.set()
        if self.stream:
            self.stream.stop()
            self.stream.close()
        await self.transcription_service.cleanup()
        self.logger.info("AudioReceiverAgent stopped.")

    async def _process_audio_queue(self):
        """Process audio from the queue and transcribe."""
        while not self.terminate_flag.is_set():
            try:
                audio_data = await self.audio_queue.get()
                if audio_data is not None:
                    await self._transcribe_audio(audio_data)
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        """Handle incoming audio data."""
        if os.path.exists(LOCK_FILE):
            # self.logger.info("Lock file detected. Pausing audio processing.")
            return None, sd.CallbackFlags()

        if status:
            self.logger.warning(f"Audio stream status: {status}")

        rms = np.sqrt(np.mean(np.square(indata)))

        # Update pre-roll buffer
        self.pre_roll_buffer.append(indata.copy())
        pre_roll_frames = int(self.config.pre_roll * self.config.sample_rate / frames)
        if len(self.pre_roll_buffer) > pre_roll_frames:
            self.pre_roll_buffer.pop(0)

        if not self.recording and rms > self.config.audio_threshold:
            self._start_recording()

        if self.recording:
            self._handle_recording(indata, rms, frames)

    def _start_recording(self):
        """Start a new recording."""
        self.recording = True
        self.audio_frames = self.pre_roll_buffer.copy()
        self.silence_counter = 0.0
        self.recording_duration = 0.0
        self.logger.debug("Started recording")

    def _handle_recording(self, indata, rms, frames):
        """Handle ongoing recording state."""
        self.audio_frames.append(indata.copy())
        frame_duration = frames / self.config.sample_rate
        self.recording_duration += frame_duration

        if rms <= self.config.audio_threshold:
            self.silence_counter += frame_duration
        else:
            self.silence_counter = 0.0

        if self._should_stop_recording():
            self._stop_recording()

    def _should_stop_recording(self) -> bool:
        """Determine if recording should stop."""
        return (
            (self.silence_counter >= self.config.silence_threshold or
             self.recording_duration >= self.config.max_duration) and
            self.recording_duration >= self.config.min_duration
        )

    def _stop_recording(self):
        """Stop recording and queue audio for processing."""
        self.recording = False
        audio_data = np.concatenate(self.audio_frames)
        try:
            if self.loop and not self.audio_queue.full():
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.audio_queue.put(audio_data))
                )
                self.logger.debug("Queued audio for processing")
            else:
                self.logger.warning("Audio queue full or loop not set, dropping audio frame")
        except RuntimeError as e:
            self.logger.error(f"Failed to enqueue audio data: {e}")
        self.audio_frames = []

    async def _transcribe_audio(self, audio_data):
        """Transcribe audio and save JSON output."""
        try:
            result: Optional[TranscriptionResult] = await self.transcription_service.transcribe(audio_data)
            if result and result.text:
                # Filter out unwanted transcriptions
                ignored_transcriptions = {".", ". . .", "you"}
                if result.text.strip() in ignored_transcriptions:
                    self.logger.info(f"Ignored transcription: '{result.text.strip()}'")
                    return  # Skip processing
    
                self.logger.debug(f"Transcribed: {result.text}")
    
                # Save audio for debugging if enabled
                audio_path = None
                if self.debug_mode:
                    audio_path = self._save_debug_data(audio_data, result.text)
    
                # Save JSON output with optional audio path
                self._save_json_output(transcription=result.text, audio_path=audio_path)
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
    
    async def _test_audio_input(self):
        """Test audio input configuration to ensure levels are okay."""
        duration = 2
        self.logger.info(f"Testing audio input for {duration} seconds...")
    
        # Record audio for the test duration
        recording = sd.rec(
            int(duration * self.config.sample_rate),
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            device=self.config.device_index,
            dtype='float32'
        )
        sd.wait()
    
        # Calculate RMS level of the recording
        rms = np.sqrt(np.mean(np.square(recording)))
    
        self.logger.info(f"Current RMS level: {rms:.6f}")
        self.logger.info(f"Audio threshold: {self.config.audio_threshold:.6f}")
    
        # Compare RMS to audio_threshold dynamically
        if rms < self.config.audio_threshold:
            self.logger.warning(f"RMS level ({rms:.6f}) is below the threshold ({self.config.audio_threshold:.6f}).")
        else:
            self.logger.info("Audio input test passed.")
    
    def _save_json_output(self, transcription: str, audio_path: Optional[str]):
        """Save transcription results as a JSON file to the queue directory."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        queue_dir = "dispatch_queue" # Queue directory for JSON files
        os.makedirs(queue_dir, exist_ok=True)  # Ensure the directory exists
    
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "transcription": transcription,
        }
    
        # Include audio_file only if audio_path is provided
        if audio_path:
            json_data["audio_file"] = audio_path
    
        json_path = os.path.join(queue_dir, f"transcription_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)
            f.write('\n')

        self.logger.debug(f"Saved transcription JSON to {json_path}")

    def _save_debug_data(self, audio_data, transcription: str) -> str:
        """Save debug audio and transcription files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = "debug/audio"
        os.makedirs(debug_dir, exist_ok=True)
    
        # Save audio file
        audio_path = os.path.join(debug_dir, f"audio_{timestamp}.wav")
        sf.write(audio_path, audio_data, self.config.sample_rate)
    
        # Save transcription text
        trans_path = os.path.join(debug_dir, f"trans_{timestamp}.txt")
        with open(trans_path, 'w') as f:
            f.write(transcription)
    
        self.logger.debug(f"Debug files saved: {audio_path}, {trans_path}")
        return audio_path  # Return the audio path
    
