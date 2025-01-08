#!/usr/bin/env python3

import asyncio
import logging
import os
from pathlib import Path
from src.agent_framework.audio.receiver import AudioReceiverAgent, AudioConfig
from launch_control.config.settings import (
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
    GOOGLE_CLOUD_PROJECT,
    LOGS_DIR
)

# Ensure necessary directories exist
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logging
log_file = LOGS_DIR / "core_dispatch.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

async def main():
    """Main entry point for starting the audio receiver service."""
    
    async def on_transcription(text):
        """Callback for handling transcription results."""
        # print(f"Transcription: {text}")

    # Configure audio receiver using settings
    config = AudioConfig(
        sample_rate=SAMPLE_RATE,
        channels=CHANNELS,
        device_index=AUDIO_DEVICE_INDEX,
        audio_threshold=AUDIO_THRESHOLD,
        silence_threshold=SILENCE_THRESHOLD,
        min_duration=MIN_RECORDING_DURATION,
        max_duration=MAX_RECORDING_DURATION,
        pre_roll=PRE_ROLL_DURATION,
        post_roll=POST_ROLL_DURATION,
        queue_size=10,
        project_id=GOOGLE_CLOUD_PROJECT,
        transcription_service_type=TRANSCRIPTION_SERVICE_TYPE,
        api_key=OPENAI_API_KEY
    )

    # Initialize the AudioReceiverAgent
    agent = AudioReceiverAgent(config=config, on_transcription=on_transcription, debug_mode=True)

    try:
        # Initialize and start the agent
        await agent.initialize()
        await agent.start()

        # Keep the agent running indefinitely
        print("Audio receiver is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass
    finally:
        # print("\nStopping audio receiver...")
        await agent.stop()
        await agent.cleanup()
        # print("Audio receiver stopped. Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived exit signal. Cleaning up...")

