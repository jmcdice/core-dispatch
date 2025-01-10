#!/usr/bin/env python3

import asyncio
import logging
import os
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

async def main():
    """Main entry point for starting the audio transmitter service."""
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

    # Initialize the transmitter agent
    agent = AudioTransmitterAgent(
        config=config,
        debug_mode=True,
        persona_names=["the_dude"]  # Specify the persona(s) to load
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

