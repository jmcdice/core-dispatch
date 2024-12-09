#!/usr/bin/env python3

import asyncio
import logging
from src.agent_framework.audio.receiver import AudioReceiverAgent, AudioConfig

logging.basicConfig(level=logging.DEBUG)

async def main():
    # Simple callback that prints transcription
    async def on_transcription(text):
        print(f"Transcription: {text}")

    config = AudioConfig(
        sample_rate=44100,
        channels=1,
        device_index=0,  # Adjust if needed, '0' often default input device
        audio_threshold=0.005,
        silence_threshold=1.0,
        min_duration=0.5,
        max_duration=5.0,
        pre_roll=0.5,
        post_roll=0.5,
        queue_size=10,
        project_id="dummy-project",
        transcription_service_type="mock",
        api_key=None
    )

    agent = AudioReceiverAgent(config=config, on_transcription=on_transcription, debug_mode=True)

    # Lifecycle: initialize, start
    await agent.initialize()
    await agent.start()

    # Let it run for 10 seconds, then stop
    await asyncio.sleep(10)
    await agent.stop()
    await agent.cleanup()

asyncio.run(main())

