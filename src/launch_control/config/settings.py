# src/launch_control/config/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Audio settings
SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', 44100))
CHANNELS = int(os.getenv('CHANNELS', 1))
AUDIO_DEVICE_INDEX = int(os.getenv('AUDIO_DEVICE_INDEX', 1))
AUDIO_THRESHOLD = float(os.getenv('AUDIO_THRESHOLD', 0.005))
SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', 1.0))
MIN_RECORDING_DURATION = float(os.getenv('MIN_RECORDING_DURATION', 0.5))
MAX_RECORDING_DURATION = float(os.getenv('MAX_RECORDING_DURATION', 30.0))
PRE_ROLL_DURATION = float(os.getenv('PRE_ROLL_DURATION', 0.5))
POST_ROLL_DURATION = float(os.getenv('POST_ROLL_DURATION', 0.5))

# Transcription service config
TRANSCRIPTION_SERVICE_TYPE = os.getenv('TRANSCRIPTION_SERVICE_TYPE', 'google-chirp')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Gemini / Other API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Logging
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
LOG_FILE = LOGS_DIR / "core_dispatch.log"

# Project Paths
TRANSCRIPTIONS_DIR = os.getenv('TRANSCRIPTIONS_DIR', 'data/transcriptions')
AUDIO_DIR = os.getenv('AUDIO_DIR', 'data/audio')

# Google Cloud
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

