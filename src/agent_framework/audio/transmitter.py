# src/agent_framework/audio/transmitter.py

import asyncio
import logging
from dataclasses import dataclass
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, Any

from agent_framework.core.base_agent import BaseAgent
from agent_framework.utils.tts_service import MockTTSService

@dataclass
class TransmitterConfig:
    sample_rate: int = 44100
    channels: int = 1
    device_index: Optional[int] = None  # None for default output device
    queue_size: int = 100

class AudioTransmitterAgent(BaseAgent):
    def __init__(
        self,
        config: TransmitterConfig,
    ):
        super().__init__()
        self.config = config
        self.tts_service = MockTTSService()
        self.terminate_flag = asyncio.Event()
        self.text_queue = asyncio.Queue(maxsize=config.queue_size)
        self.loop = None

    async def initialize(self):
        self.logger.info("AudioTransmitterAgent initialized.")

    async def start(self):
        self.loop = asyncio.get_running_loop()
        asyncio.create_task(self._process_text_queue())
        self.logger.info("AudioTransmitterAgent started.")

    async def stop(self):
        self.terminate_flag.set()
        self.logger.info("AudioTransmitterAgent stopped.")

    async def _process_text_queue(self):
        while not self.terminate_flag.is_set():
            try:
                text = await self.text_queue.get()
                # Synthesize audio
                audio_data = await self.tts_service.synthesize(text, sample_rate=self.config.sample_rate)
                # Play audio_data
                await self._play_audio(audio_data)
            except Exception as e:
                self.logger.error(f"Error in transmitter: {e}")

    async def send_text(self, text: str):
        """Public method to enqueue text for transmission."""
        if not self.text_queue.full():
            await self.text_queue.put(text)
        else:
            self.logger.warning("Text queue is full, dropping message.")

    async def _play_audio(self, audio_data: np.ndarray):
        """Play the synthesized audio out the sound device."""
        try:
            self.logger.debug("Playing audio through transmitter...")
            def callback(outdata, frames, time, status):
                if status:
                    self.logger.warning(f"Transmitter output stream status: {status}")
                # Copy audio_data into outdata until we run out
                length = min(len(audio_data), frames)
                outdata[:length, 0] = audio_data[:length]
                # If shorter than 'frames', pad with silence
                if length < frames:
                    outdata[length:] = 0
            # Use a blocking mode to play audio once
            with sd.OutputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                device=self.config.device_index,
                dtype='float32',
                callback=None,  # we'll write data manually
            ) as stream:
                # Write audio_data in chunks
                block_size = 1024
                idx = 0
                while idx < len(audio_data):
                    end_idx = min(idx+block_size, len(audio_data))
                    block = audio_data[idx:end_idx]
                    stream.write(block.reshape(-1, 1))
                    idx = end_idx
            self.logger.debug("Audio playback completed.")
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")


