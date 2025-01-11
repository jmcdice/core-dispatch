# src/core_dispatch/agent_framework/audio/transmitter.py

import os
import sys
import shutil
import json
import time
import logging
from logging.handlers import WatchedFileHandler
import threading
from datetime import datetime, timedelta
import queue
import argparse
import warnings
import subprocess
import random
import requests
from dataclasses import dataclass
from typing import Optional, Dict

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Local imports
import core_dispatch.agent_framework.core.base_agent as base_agent
from core_dispatch.agent_framework.core.base_agent import BaseAgent

# TTS services (NEW)
from core_dispatch.agent_framework.utils.tts_service import (
    OpenAITTSService,
    UnrealSpeechTTSService
)

# Use your own path to settings
from core_dispatch.launch_control.config.settings import (
    OPENAI_API_KEY,
    TX_SAMPLE_RATE,
    TX_CHANNELS,
    TX_AUDIO_DEVICE_INDEX,
    AUDIO_DEVICE,
    PROCESSED_FILES_JSON,
    TTS_AUDIO_DIR,
    CONTEXT_EXPIRATION,
    RESPONSE_QUEUE_MAX_SIZE,
    CONVERSATION_HISTORY_LIMIT,
    TX_LOG_FILE,
    LOG_FORMAT,
    TRANSCRIPTIONS_DIR,
    PROCESSED_TRANSCRIPTIONS_DIR,
    TRANSCRIPTIONS_LOG_FILE,
    TTS_PROVIDER,
    UNREALSPEECH_API_KEY,
    DEFAULT_VOICE,
    VOICE_MAPPING
)

LOCK_FILE = '/tmp/tx_rx_lock'

CONVERSATION_LOG_FILE = "conversation_log.txt"


@dataclass
class AudioTransmitterConfig:
    """Configuration for the AudioTransmitterAgent."""
    sample_rate: int = TX_SAMPLE_RATE
    channels: int = TX_CHANNELS
    device_index: int = TX_AUDIO_DEVICE_INDEX
    audio_device: str = AUDIO_DEVICE
    api_key: str = OPENAI_API_KEY
    processed_files_json: str = PROCESSED_FILES_JSON
    tts_audio_dir: str = TTS_AUDIO_DIR
    context_expiration: timedelta = CONTEXT_EXPIRATION
    response_queue_max_size: int = RESPONSE_QUEUE_MAX_SIZE
    conversation_history_limit: int = CONVERSATION_HISTORY_LIMIT
    tx_log_file: str = TX_LOG_FILE
    log_format: str = LOG_FORMAT
    transcriptions_dir: str = TRANSCRIPTIONS_DIR
    processed_transcriptions_dir: str = PROCESSED_TRANSCRIPTIONS_DIR
    transcriptions_log_file: str = TRANSCRIPTIONS_LOG_FILE
    tts_provider: str = TTS_PROVIDER
    unrealspeech_api_key: Optional[str] = UNREALSPEECH_API_KEY
    default_voice: Dict[str, str] = None  # e.g., {"openai": "some_voice_id"}


class AudioTransmitterAgent(BaseAgent):
    """
    A transmitter that:
      1. Watches for new transcriptions in TRANSCRIPTIONS_DIR
      2. Determines if (and which) persona should respond
      3. Generates the AI response
      4. Converts AI response to audio (TTS)
      5. Plays/“transmits” the audio
      6. Moves processed transcriptions and handles cleanup
    """
    def __init__(self, config: AudioTransmitterConfig, debug_mode: bool = False,
                 persona_names=None, profile_name=None, load_all_personas=False):
        super().__init__()
        self.config = config
        self.debug_mode = debug_mode
        self.profile_name = profile_name  # Store profile name
    
        # Lazy import of OpenAI so we can handle missing dependencies
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.api_key)
        except ImportError:
            self.logger.error("Failed to import openai. Please install it.")
            self.client = None

        # Setup logging
        self._initialize_logging()

        # Additional attributes
        self.terminate_flag = threading.Event()
        self.response_queue = queue.Queue(maxsize=self.config.response_queue_max_size)
        self.conversation_history = []
        self.personas = {}
        self.activation_phrases_set = set()
        self.active_persona = None
        self.last_interaction_time = None
        self.CONVERSATION_TIMEOUT = timedelta(minutes=5)  # adjustable
        self.assistant_responses = []
        self.load_personas_on_init = load_all_personas
        self.persona_names = persona_names if persona_names else []

        # TTS service (NEW)
        self.tts_service = None
        self._init_tts_service()

        # Threads
        self.generator_thread = None
        self.transmitter_thread = None

        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            self.logger.info("Removed stale lock file on startup.")

        # Load personas
        if self.load_personas_on_init:
            self._load_all_personas()
        else:
            for name in self.persona_names:
                self.logger.info(f"Loading persona '{name}'.")
                p_data = self._load_persona(name)
                if p_data:
                    self.personas[name] = p_data

        if not self.personas:
            self.logger.error("No personas loaded. The transmitter won't respond to anything.")

        loaded_list = ', '.join(self.personas.keys()) if self.personas else "None"
        self.logger.info(f"Transmitter ready with personas: {loaded_list}")


    def _initialize_logging(self):
        """Initialize file-based logging for transmitter and transcriptions."""
        logging.basicConfig(
            filename=self.config.tx_log_file,
            format=self.config.log_format,
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

        # Separate logger for transcriptions
        self.transcription_logger = logging.getLogger('transcriptions')
        self.transcription_logger.setLevel(logging.INFO)
        transcription_handler = WatchedFileHandler(self.config.transcriptions_log_file)
        transcription_handler.setLevel(logging.INFO)
        transcription_formatter = logging.Formatter('%(asctime)s | %(processName)s | assistant | %(message)s')
        transcription_handler.setFormatter(transcription_formatter)
        self.transcription_logger.addHandler(transcription_handler)

    def _init_tts_service(self):
        """
        Configure the TTS service class based on self.config.tts_provider.
        This is where we unify logic so `_text_to_speech` can just call self.tts_service.synthesize_text().
        """
        provider = self.config.tts_provider.lower()
        self.logger.info(f"Initializing TTS service: {provider}")

        if provider == 'openai':
            if not self.client:
                self.logger.error("OpenAI TTS selected, but 'self.client' is None (import error?).")
                return
            # We pass the openai client plus the directory for debug audio
            self.tts_service = OpenAITTSService(self.client, self.config.tts_audio_dir)

        elif provider == 'unrealspeech':
            if not self.config.unrealspeech_api_key:
                self.logger.error("UnrealSpeech TTS selected but no API key provided.")
                return
            self.tts_service = UnrealSpeechTTSService(
                api_key=self.config.unrealspeech_api_key,
                tts_audio_dir=self.config.tts_audio_dir
            )
        else:
            self.logger.error(f"Unknown TTS provider: {provider}")

    async def initialize(self):
        """Async init, for parity with the receiver agent."""
        self.logger.info("AudioTransmitterAgent initialized (async).")

    async def start(self):
        """Start the transmitter threads."""
        self.logger.info("Starting AudioTransmitterAgent threads...")
        self.generator_thread = threading.Thread(target=self._generate_response, daemon=True)
        self.transmitter_thread = threading.Thread(target=self._transmit_responses, daemon=True)
        self.generator_thread.start()
        self.transmitter_thread.start()

    async def stop(self):
        """Signal threads to stop and wait for them to join."""
        self.logger.info("Stopping AudioTransmitterAgent...")
        self.terminate_flag.set()
        if self.generator_thread:
            self.generator_thread.join()
        if self.transmitter_thread:
            self.transmitter_thread.join()
        self.logger.info("AudioTransmitterAgent stopped.")

    def _generate_response(self):
        """Continuously polls for new transcription files, decides if/how to respond, and enqueues responses."""
        while not self.terminate_flag.is_set():
            new_transcriptions = self._load_new_transcriptions()
            for timestamp, transcription, tool_response, filename in new_transcriptions:
                filepath = os.path.join(self.config.transcriptions_dir, filename)
                self.logger.info(f"New transcription: {transcription[:60]}...")

                responding_persona = self._should_respond(transcription)
                if responding_persona:
                    self.logger.info(f"Transcription handled by persona '{responding_persona}'.")
                    persona_data = self.personas[responding_persona]
                    # Provider-specific voice
                    voice = persona_data['voices'].get(
                        self.config.tts_provider,
                        self.config.default_voice  # Use the default voice string directly
                    )
                    
                    # Update conversation history
                    self._update_conversation_history(timestamp, transcription, tool_response)
                    # Build messages for ChatGPT
                    messages = self._prepare_chat_messages(persona_data)

                    response_text = self._generate_chat_completion(messages, responding_persona, timestamp)
                    if response_text:
                        # Enqueue the response for TTS & playback
                        self.response_queue.put({'text': response_text, 'voice': voice})
                        self._log_conversation(transcription, response_text, responding_persona)

                else:
                    self.logger.info("No active persona or ignoring message.")

                # Move file to processed
                self._move_processed_file(filepath, filename)

            # time.sleep(1)  # avoid tight loop

    def _transmit_responses(self):
        """Continuously pulls responses from queue, runs TTS, and plays the audio."""
        while not self.terminate_flag.is_set():
            try:
                response_item = self.response_queue.get(timeout=1)
                if response_item:
                    response_text = response_item['text']
                    voice = response_item['voice']
                    # self.logger.debug(f"Transmitting response: {response_text}")
                    audio_file = self._text_to_speech(response_text, voice)
                    if audio_file:
                        self._play_audio(audio_file)
                    else:
                        self.logger.error("Failed to convert text to speech.")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in transmit_responses: {e}")

    def _should_respond(self, transcription: str) -> Optional[str]:
        """Decide whether to respond based on activation phrases, persona timeouts, etc."""
        transcription_lower = transcription.lower()

        # Don’t respond if the message is exactly the same as a known assistant response
        for resp in self.assistant_responses:
            if transcription.strip() == resp.strip():
                self.logger.info("Ignoring transcription that matches our own recent response.")
                return None

        # Check for explicit activation
        for persona_name, persona_data in self.personas.items():
            for phrase in persona_data['activation_phrases']:
                if phrase.lower() in transcription_lower:
                    self.active_persona = persona_name
                    self.last_interaction_time = datetime.now()
                    self.logger.info(f"Activated persona '{self.active_persona}' via activation phrase.")
                    return self.active_persona

        # If we already have an active persona, check conversation timeout
        if self.active_persona:
            if datetime.now() - self.last_interaction_time <= self.CONVERSATION_TIMEOUT:
                self.last_interaction_time = datetime.now()
                return self.active_persona
            else:
                self.logger.info("Conversation timed out. No active persona.")
                self.active_persona = None

        # If no active persona, but we only have one loaded, just use it
        if not self.active_persona and len(self.personas) == 1:
            self.active_persona = next(iter(self.personas))
            self.last_interaction_time = datetime.now()
            self.logger.info(f"No activation phrase needed; defaulting to persona '{self.active_persona}'.")
            return self.active_persona
        elif not self.active_persona and len(self.personas) > 1:
            # If multiple are loaded, pick randomly
            self.active_persona = random.choice(list(self.personas.keys()))
            self.last_interaction_time = datetime.now()
            self.logger.info(f"No activation phrase detected; randomly selected persona '{self.active_persona}'.")
            return self.active_persona

        return None

    def _load_persona(self, persona_name: str):
        """Load a single persona from the specified profile."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        personas_dir = os.path.join(project_root, 'personas', self.profile_name)  # Add self.profile_name to the path
        persona_file = os.path.join(personas_dir, f"{persona_name}.json")  # Construct full path to persona file
    
        if not os.path.exists(persona_file):
            self.logger.error(f"Persona file '{persona_file}' does not exist.")
            return {}
    
        try:
            with open(persona_file, 'r') as f:
                data = json.load(f)
            prompt = data.get('prompt', '')
            voices = data.get('voices', {})
            activation_phrases = data.get('activation_phrases', [])
    
            # Check for duplicate activation phrases
            for phrase in activation_phrases:
                if phrase.lower() in self.activation_phrases_set:
                    self.logger.error(f"Duplicate activation phrase '{phrase}' in persona '{persona_name}'.")
                    continue
                self.activation_phrases_set.add(phrase.lower())
    
            return {
                'prompt': prompt,
                'voices': voices,
                'activation_phrases': activation_phrases
            }
        except Exception as e:
            self.logger.error(f"Error loading persona '{persona_name}': {e}")
            return {}
    
    def _load_all_personas(self):
        """Scan the profiles folder and load all profiles."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        profiles_dir = os.path.join(project_root, 'profiles')
        profile_dirs = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    
        for profile in profile_dirs:
            persona_file = os.path.join(profiles_dir, profile, f"{profile}.json")
            if os.path.exists(persona_file):
                p_data = self._load_persona(profile)
                if p_data:
                    self.personas[profile] = p_data
    
    def _load_new_transcriptions(self):
        """Return list of (timestamp, transcription, tool_response, filename) for new JSON files."""
        results = []
        try:
            files = sorted(os.listdir(self.config.transcriptions_dir))
            for filename in files:
                if filename.endswith('.json'):
                    filepath = os.path.join(self.config.transcriptions_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        transcription = data['transcription']
                        tool_response = data.get('tool_response')
                        results.append((timestamp, transcription, tool_response, filename))
        except Exception as e:
            self.logger.error(f"Error loading transcriptions: {e}")
        return results

    def _move_processed_file(self, filepath: str, filename: str):
        """Move the processed JSON file to the processed folder."""
        processed_filepath = os.path.join(self.config.processed_transcriptions_dir, filename)
        try:
            shutil.move(filepath, processed_filepath)
            self.logger.info(f"Moved file {filename} to {processed_filepath}")
        except Exception as e:
            self.logger.error(f"Error moving file {filename}: {e}")

    def _update_conversation_history(self, timestamp, transcription, tool_response=None):
        """Append user & tool responses to conversation history, trim old messages."""
        self.conversation_history.append({
            'timestamp': timestamp,
            'role': 'user',
            'content': transcription
        })
        if tool_response:
            self.conversation_history.append({
                'timestamp': timestamp,
                'role': 'assistant',
                'content': tool_response
            })

        # Expire old messages
        now = datetime.now(tz=timestamp.tzinfo)
        cutoff_time = now - self.config.context_expiration
        self.conversation_history = [m for m in self.conversation_history if m['timestamp'] >= cutoff_time]

        # Limit total conversation length
        if len(self.conversation_history) > self.config.conversation_history_limit:
            self.conversation_history = self.conversation_history[-self.config.conversation_history_limit:]

    def _prepare_chat_messages(self, persona_data):
        """Build messages array for ChatGPT completion."""
        system_prompt = persona_data['prompt'].format(military_time=self._get_military_time())
        messages = [{'role': 'system', 'content': system_prompt}]

        for msg in self.conversation_history:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        return messages

    def _generate_chat_completion(self, messages, responding_persona, original_ts):
        """Calls OpenAI or ChatGPT to generate a response from the persona prompt + conversation history."""
        if not self.client:
            self.logger.error("OpenAI client is not available.")
            return None
        try:
            completion = self.client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=messages
            )
            response_text = completion.choices[0].message.content.strip()
            # self.logger.info(f"Generated response: {response_text[:60]} ...")
            self.transcription_logger.info(f"{responding_persona} | {response_text}")

            # Add as assistant message in conversation
            self.conversation_history.append({
                'timestamp': datetime.now(tz=original_ts.tzinfo),
                'role': 'assistant',
                'content': response_text
            })
            # Store for "self-response" checks
            self.assistant_responses.append(response_text)
            if len(self.assistant_responses) > 10:
                self.assistant_responses = self.assistant_responses[-10:]
            return response_text
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return None

    def _text_to_speech(self, text: str, voice_id: Optional[str]):
        """
        Convert text to speech using self.tts_service.
        Return a WAV file path or None on failure.
        """
        if not text:
            return None
        if not self.tts_service:
            self.logger.error("No TTS service configured!")
            return None

        # Synthesize text (this calls OpenAITTSService or UnrealSpeechTTSService)
        wav_path = self.tts_service.synthesize_text(text, voice_id, debug_mode=self.debug_mode)
        return wav_path

    def _play_audio(self, audio_file: str):
        """Lock the receiver, play the audio, then unlock. Optionally remove the file if not debug."""
        self.logger.info(f"Playing audio: {audio_file} on device: {self.config.audio_device}")
        self._create_lock()
        try:
            _, ext = os.path.splitext(audio_file)
            ext = ext.lower()
            if ext == '.wav':
                player = ['aplay', '-D', self.config.audio_device, audio_file]
            elif ext == '.mp3':
                player = ['mpg123', '-a', self.config.audio_device, audio_file]
            else:
                self.logger.error(f"Unsupported audio format: {ext}")
                return
            subprocess.run(player, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.info("Audio playback completed.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error playing audio: {e}")
        finally:
            time.sleep(1)
            self._remove_lock()
            if not self.debug_mode and os.path.exists(audio_file):
                os.remove(audio_file)
                self.logger.info(f"Removed temporary audio file: {audio_file}")

    def _log_conversation(self, transcription, response, persona_name):
        """Log the conversation to a single file, including the persona name."""
        with open(CONVERSATION_LOG_FILE, "a") as f:
            f.write(f"User: {transcription}\n")
            f.write(f"{persona_name}: {response}\n")
            f.write("-" * 40 + "\n")
    

    def _create_lock(self):
        """Create a lock file to signal the receiver to pause."""
        with open(LOCK_FILE, 'w') as f:
            f.write('locked')

    def _remove_lock(self):
        """Remove the lock file to signal the receiver to resume after a small delay."""
        if os.path.exists(LOCK_FILE):
            time.sleep(1)  # Delay to allow the playback to fully finish
            os.remove(LOCK_FILE)
            # self.logger.info("Lock file removed. Receiver can resume.")
    
    def _get_military_time(self):
        return datetime.now().strftime('%H:%M')

