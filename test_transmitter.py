#!/usr/bin/env python3

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

# If your repo is structured differently, adjust imports accordingly
from agent_framework.audio.transmitter import AudioTransmitterAgent, AudioTransmitterConfig

logging.basicConfig(level=logging.DEBUG)

async def main():
    # 1) Set up working directories
    project_root = Path(__file__).parent.parent  # Adjust if needed
    transcriptions_dir = project_root / "transcriptions_test"
    processed_dir = project_root / "transcriptions_processed_test"
    tts_audio_dir = project_root / "tts_audio_test"

    # Ensure these directories exist
    transcriptions_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    tts_audio_dir.mkdir(parents=True, exist_ok=True)

    # 2) Build transmitter config
    config = AudioTransmitterConfig(
        sample_rate=44100,
        channels=1,
        device_index=0,                 # Usually 0 is default out, adjust if needed
        audio_device="default",         # On Linux, you might use 'default' or 'plughw:0,0'
        api_key=os.environ.get("OPENAI_API_KEY", ""),  # Make sure you have your key set in env or replace with a real key
        processed_files_json=str(project_root / "processed_files.json"),
        voice_name="test_voice",
        tts_audio_dir=str(tts_audio_dir),
        response_queue_max_size=5,
        conversation_history_limit=10,
        tx_log_file=str(project_root / "transmitter.log"),
        log_format="%(asctime)s %(levelname)s %(message)s",
        transcriptions_dir=str(transcriptions_dir),
        processed_transcriptions_dir=str(processed_dir),
        transcriptions_log_file=str(project_root / "transcriptions.log"),
        tts_provider="openai",          # or "unrealspeech", etc.
        unrealspeech_api_key=os.environ.get("UNREALSPEECH_API_KEY", ""),  # If using UnrealSpeech
        default_voice={"openai": "some_openai_voice_id"},  # Replace with your valid voice ID if needed
    )

    # 3) Create a transmitter agent with a single persona that has an activation phrase
    # For this test, the persona can be loaded from disk, or we can replicate the structure inline
    # but we’ll do a minimal approach: we’ll rely on the file-based loading or just define persona_names
    agent = AudioTransmitterAgent(
        config=config,
        debug_mode=True,            # Debug mode saves TTS .wav files in tts_audio_dir
        persona_names=["test_persona"], 
        load_all_personas=False
    )

    # 4) Initialize and start
    await agent.initialize()
    await agent.start()

    # 5) Drop a test transcription file into transcriptions_dir
    # The transcription text must contain the activation phrase, e.g. "hey transmitter" or whatever your persona has
    timestamp_str = datetime.now().isoformat()
    test_json = {
        "timestamp": timestamp_str,
        "transcription": "Hey transmitter, how's it going today?",
        "tool_response": None
    }
    test_file_path = transcriptions_dir / "test_transcription.json"
    test_file_path.write_text(str(test_json))

    print(f"Dropped a test transcription file at: {test_file_path}")

    # 6) Wait a bit for the transmitter to notice and respond
    # The transmitter’s loop checks every second, so 5-10 seconds is usually enough
    print("Waiting 10 seconds for transmitter to pick up the transcription...")
    await asyncio.sleep(10)

    # 7) Stop transmitter
    print("Stopping transmitter now...")
    await agent.stop()
    await agent.cleanup()
    print("Transmitter test complete.")

# If running as a script:
if __name__ == "__main__":
    asyncio.run(main())

