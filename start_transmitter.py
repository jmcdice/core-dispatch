#!/usr/bin/env python3

import asyncio
import logging
import os
import argparse
from pathlib import Path
from core_dispatch.agent_framework.audio.transmitter import AudioTransmitterAgent, AudioTransmitterConfig
from core_dispatch.launch_control.config.settings import (
    TX_SAMPLE_RATE,
    TX_CHANNELS,
    TX_AUDIO_DEVICE_INDEX,
    AUDIO_DEVICE,
    OPENAI_API_KEY,
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
    DEFAULT_VOICE
)

# Suppress debug logs from specific libraries
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Ensure necessary directories exist
os.makedirs(TTS_AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
os.makedirs(PROCESSED_TRANSCRIPTIONS_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(TX_LOG_FILE),
        logging.StreamHandler()
    ]
)

def get_personas_from_profile(profile_name: str) -> list:
    """Retrieve persona files from a given profile directory."""
    profiles_dir = Path("src/core_dispatch/personas")
    profile_path = profiles_dir / profile_name

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{profile_name}' does not exist in {profiles_dir}")

    if profile_path.is_dir():
        # Directory containing multiple persona files
        #return [f.stem for f in profile_path.glob("*.json")]
        return [file.stem for file in profile_path.glob("*.json") if file.is_file()]

    else:
        raise ValueError(f"Profile '{profile_name}' is not a valid directory.")

async def main():
    """Main entry point for starting the audio transmitter service."""
    # Retrieve profile argument
    parser = argparse.ArgumentParser(description="Start the audio transmitter")
    parser.add_argument("--profile", type=str, required=True, help="Profile or profile set to load")
    args = parser.parse_args()

    profile = args.profile

    # Get personas from the profile
    try:
        personas = get_personas_from_profile(profile)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Create configuration for the transmitter
    config = AudioTransmitterConfig(
        sample_rate=TX_SAMPLE_RATE,
        channels=TX_CHANNELS,
        device_index=TX_AUDIO_DEVICE_INDEX,
        audio_device=AUDIO_DEVICE,
        api_key=OPENAI_API_KEY,
        processed_files_json=PROCESSED_FILES_JSON,
        tts_audio_dir=TTS_AUDIO_DIR,
        context_expiration=CONTEXT_EXPIRATION,
        response_queue_max_size=RESPONSE_QUEUE_MAX_SIZE,
        conversation_history_limit=CONVERSATION_HISTORY_LIMIT,
        tx_log_file=TX_LOG_FILE,
        log_format=LOG_FORMAT,
        transcriptions_dir=TRANSCRIPTIONS_DIR,
        processed_transcriptions_dir=PROCESSED_TRANSCRIPTIONS_DIR,
        transcriptions_log_file=TRANSCRIPTIONS_LOG_FILE,
        tts_provider=TTS_PROVIDER,
        unrealspeech_api_key=UNREALSPEECH_API_KEY,
        default_voice=DEFAULT_VOICE
    )

    agent = AudioTransmitterAgent(
        config=config,
        debug_mode=True,
        persona_names=personas,
        profile_name=profile
    )
    

    try:
        # Start the transmitter
        await agent.initialize()
        await agent.start()

        print("Audio transmitter is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        print("\nStopping audio transmitter...")
    finally:
        await agent.stop()
        print("Audio transmitter stopped. Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived exit signal. Cleaning up...")

