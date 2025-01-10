# src/core_dispatch/launch_control/config/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env if present
load_dotenv()

# Project Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Logging
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
LOG_FILE = LOGS_DIR / "core_dispatch.log"  # Global log file
TX_LOG_FILE = LOGS_DIR / os.getenv('TX_LOG_FILE', 'tx_log.log')  # Transmitter-specific log file

# TTS provider (e.g., 'openai', 'unrealspeech')
TTS_PROVIDER = os.getenv('TTS_PROVIDER', 'openai')  # Default to 'openai'

# Processed transcriptions
PROCESSED_TRANSCRIPTIONS_DIR = DATA_DIR / os.getenv('PROCESSED_TRANSCRIPTIONS_DIR', 'processed_transcriptions')
PROCESSED_TRANSCRIPTIONS_DIR.mkdir(exist_ok=True)
# Processed files JSON
PROCESSED_FILES_JSON = Path(os.getenv('PROCESSED_FILES_JSON', DATA_DIR / "processed_files.json"))
# Transcriptions log file
TRANSCRIPTIONS_LOG_FILE = LOGS_DIR / os.getenv('TRANSCRIPTIONS_LOG_FILE', 'transcriptions.log')

# Audio directories
TRANSCRIPTIONS_DIR = Path(os.getenv('TRANSCRIPTIONS_DIR', DATA_DIR / "transcriptions"))
AUDIO_DIR = Path(os.getenv('AUDIO_DIR', DATA_DIR / "audio"))
TTS_AUDIO_DIR = Path(os.getenv('TTS_AUDIO_DIR', DATA_DIR / "tts_audio"))

# Ensure directories exist
TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Audio settings
SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', 44100))
CHANNELS = int(os.getenv('CHANNELS', 1))
AUDIO_DEVICE_INDEX = int(os.getenv('AUDIO_DEVICE_INDEX', 1))
AUDIO_THRESHOLD = float(os.getenv('AUDIO_THRESHOLD', 0.001))
SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', 1.0))
MIN_RECORDING_DURATION = float(os.getenv('MIN_RECORDING_DURATION', 0.5))
MAX_RECORDING_DURATION = float(os.getenv('MAX_RECORDING_DURATION', 30.0))
PRE_ROLL_DURATION = float(os.getenv('PRE_ROLL_DURATION', 0.5))
POST_ROLL_DURATION = float(os.getenv('POST_ROLL_DURATION', 0.5))

# Transmitter-specific audio settings
TX_SAMPLE_RATE = int(os.getenv('TX_SAMPLE_RATE', 44100))
TX_CHANNELS = int(os.getenv('TX_CHANNELS', 1))
TX_AUDIO_DEVICE_INDEX = int(os.getenv('TX_AUDIO_DEVICE_INDEX', 1))
AUDIO_DEVICE = os.getenv('AUDIO_DEVICE', 'default')

# Conversation settings
CONTEXT_EXPIRATION = timedelta(minutes=int(os.getenv('CONTEXT_EXPIRATION', 5)))  # Default: 5 minutes
RESPONSE_QUEUE_MAX_SIZE = int(os.getenv('RESPONSE_QUEUE_MAX_SIZE', 10))  # Default: 10
CONVERSATION_HISTORY_LIMIT = int(os.getenv('CONVERSATION_HISTORY_LIMIT', 20))  # Default: 20

# Transcription service config
TRANSCRIPTION_SERVICE_TYPE = os.getenv('TRANSCRIPTION_SERVICE_TYPE', 'google-chirp')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# UnrealSpeech API Key
UNREALSPEECH_API_KEY = os.getenv('UNREALSPEECH_API_KEY')
# Default TTS voice
DEFAULT_VOICE = os.getenv('DEFAULT_VOICE', 'onyx')

# Voice mappings for personas or configurations
VOICE_MAPPING = {
    "openai": "onyx",
    "unrealspeech": "scarlett",
}



# Gemini / Other API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Cloud
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

