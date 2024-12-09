#!/usr/bin/env python3
# test_full_loop.py

import asyncio
import logging

from src.agent_framework.audio.receiver import AudioReceiverAgent, AudioConfig
from src.agent_framework.audio.transmitter import AudioTransmitterAgent, TransmitterConfig

logging.basicConfig(level=logging.DEBUG)

async def main():
    # Define a callback that sends text to the transmitter
    transmitter_config = TransmitterConfig()  # Rely on settings.py defaults

    transmitter = AudioTransmitterAgent(config=transmitter_config)

    async def on_transcription(text: str):
        print(f"Transcription: {text}")
        # Send a response to transmitter
        await transmitter.send_text("Received your message.")

    # Rely on defaults from AudioConfig which uses settings.py for configuration
    receiver_config = AudioConfig()

    receiver = AudioReceiverAgent(
        config=receiver_config,
        on_transcription=on_transcription,
        debug_mode=True
    )

    # Initialize and start agents
    await receiver.initialize()
    await transmitter.initialize()

    await receiver.start()
    await transmitter.start()

    # Let it run for 20 seconds
    await asyncio.sleep(20)

    # Stop agents
    await receiver.stop()
    await transmitter.stop()

    await receiver.cleanup()
    # transmitter currently doesn't need special cleanup, but could be implemented if needed

asyncio.run(main())
