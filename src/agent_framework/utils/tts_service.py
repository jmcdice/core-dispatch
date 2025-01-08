# src/agent_framework/utils/tts_service.py

import os
import logging
import subprocess
import requests
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BaseTTSService:
    """Base abstract TTS service."""
    def synthesize_text(self, text: str, voice: str, debug_mode: bool = False) -> Optional[str]:
        raise NotImplementedError


class OpenAITTSService(BaseTTSService):
    """
    Hypothetical TTS from 'TTSOpenAI'.
    If you have a specialized TTSOpenAI client object, pass it in the constructor
    or instantiate it here. In your original code, it was `client.audio.speech.create(...)`.
    """
    def __init__(self, client, tts_audio_dir: str):
        self.client = client
        self.tts_audio_dir = tts_audio_dir

    def synthesize_text(self, text: str, voice: str, debug_mode: bool = False) -> Optional[str]:
        temp_audio_file = 'temp_response.wav'
        try:
            # Original: response = client.audio.speech.create(model='tts-1', voice=provider_voice, ...)
            response = self.client.audio.speech.create(
                model='tts-1',
                voice=voice,
                input=text,
                response_format='wav'
            )
            response.stream_to_file(temp_audio_file)

            if debug_mode:
                os.makedirs(self.tts_audio_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                debug_audio_file = os.path.join(self.tts_audio_dir, f'response_{timestamp}.wav')
                os.rename(temp_audio_file, debug_audio_file)
                logger.info(f"Saved TTS audio to {debug_audio_file}")
                return debug_audio_file

            return temp_audio_file

        except Exception as e:
            logger.error(f"OpenAITTSService error: {e}")
            return None


class UnrealSpeechTTSService(BaseTTSService):
    """
    Integrates with UnrealSpeech at https://api.v7.unrealspeech.com/stream
    """
    def __init__(self, api_key: str, tts_audio_dir: str):
        self.api_key = api_key
        self.tts_audio_dir = tts_audio_dir

    def synthesize_text(self, text: str, voice: str, debug_mode: bool = False) -> Optional[str]:
        if not self.api_key:
            logger.error("UnrealSpeech API key is not set. Please provide it.")
            return None

        temp_audio_file = 'temp_response.wav'
        url = 'https://api.v7.unrealspeech.com/stream'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        data = {
            'Text': text,
            'VoiceId': voice,
            'Bitrate': '192k',
            'Speed': '0',
            'Pitch': '1',
            'Codec': 'libmp3lame'
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                temp_mp3_file = 'temp_response.mp3'
                with open(temp_mp3_file, 'wb') as f:
                    f.write(response.content)
                # Convert MP3 to WAV
                command = ['ffmpeg', '-y', '-i', temp_mp3_file, temp_audio_file]
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.remove(temp_mp3_file)

                if debug_mode:
                    os.makedirs(self.tts_audio_dir, exist_ok=True)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    debug_audio_file = os.path.join(self.tts_audio_dir, f"response_{timestamp}.wav")
                    os.rename(temp_audio_file, debug_audio_file)
                    logger.info(f"Saved TTS audio to {debug_audio_file}")
                    return debug_audio_file

                return temp_audio_file

            else:
                logger.error(f"UnrealSpeech request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"UnrealSpeechTTSService error: {e}")
            return None

