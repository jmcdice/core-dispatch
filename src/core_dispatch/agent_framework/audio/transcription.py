# src/core_dispatch/agent_framework/audio/transcription.py

from abc import ABC, abstractmethod
import io
from typing import Optional
from dataclasses import dataclass
import soundfile as sf
import logging

from openai import OpenAI
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from core_dispatch.launch_control.config.settings import (
    TRANSCRIPTION_SERVICE_TYPE,
    OPENAI_API_KEY,
    GOOGLE_CLOUD_PROJECT
)

@dataclass
class TranscriptionConfig:
    sample_rate: int
    language: str = "en-US"
    debug_mode: bool = False
    project_id: Optional[str] = None
    api_key: Optional[str] = None

@dataclass
class TranscriptionResult:
    text: str
    confidence: float = 1.0
    language: str = "en-US"
    metadata: dict = None

class TranscriptionService(ABC):
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def transcribe(self, audio_data) -> Optional[TranscriptionResult]:
        pass

    async def cleanup(self) -> None:
        pass

    def _prepare_audio(self, audio_data) -> io.BytesIO:
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, self.config.sample_rate, format='WAV', subtype='PCM_16')
        audio_buffer.seek(0)
        return audio_buffer

class GoogleChirpService(TranscriptionService):
    async def initialize(self) -> None:
        if not self.config.project_id:
            raise ValueError("project_id must be set for GoogleChirpService")
        self.client = SpeechClient(
            client_options=ClientOptions(
                api_endpoint="us-central1-speech.googleapis.com",
            )
        )

    async def transcribe(self, audio_data) -> Optional[TranscriptionResult]:
        try:
            audio_content = self._prepare_audio(audio_data).read()

            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=[self.config.language],
                model="chirp",
            )

            request = cloud_speech.RecognizeRequest(
                recognizer=f"projects/{self.config.project_id}/locations/us-central1/recognizers/_",
                config=config,
                content=audio_content,
            )

            self.logger.debug("Sending audio to Google Chirp...")
            response = self.client.recognize(request=request)

            if response.results:
                result = response.results[0].alternatives[0]
                return TranscriptionResult(
                    text=result.transcript.strip(),
                    confidence=result.confidence,
                    language=self.config.language
                )

            return None

        except Exception as e:
            self.logger.error(f"Google Chirp transcription error: {e}")
            return None

class OpenAIWhisperService(TranscriptionService):
    async def initialize(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key must be set for OpenAIWhisperService")
        self.client = OpenAI(api_key=self.config.api_key)

    async def transcribe(self, audio_data) -> Optional[TranscriptionResult]:
        try:
            audio_buffer = self._prepare_audio(audio_data)
            # Set a filename with a supported extension
            audio_buffer.name = 'audio.wav'

            self.logger.debug("Sending audio to Whisper...")
            response = self.client.audio.transcriptions.create(
                file=audio_buffer,
                model="whisper-1",
                language=self.config.language.split('-')[0]
            )

            return TranscriptionResult(
                text=response.text.strip(),
                language=self.config.language
            )

        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            return None

class MockTranscriptionService(TranscriptionService):
    async def initialize(self):
        pass

    async def transcribe(self, audio_data) -> Optional[TranscriptionResult]:
        return TranscriptionResult(text="[mock transcription]")

def create_transcription_service(service_type: str, config: TranscriptionConfig) -> TranscriptionService:
    services = {
        'google-chirp': GoogleChirpService,
        'openai-whisper': OpenAIWhisperService
    }

    if service_type not in services:
        # If unknown or not set, use mock service
        return MockTranscriptionService(config)

    return services[service_type](config)
