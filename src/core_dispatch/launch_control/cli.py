import asyncio
import logging
import os
import sys
from pathlib import Path

import click

from core_dispatch.agent_framework.audio.receiver import AudioReceiverAgent, AudioConfig
from core_dispatch.agent_framework.audio.transmitter import AudioTransmitterAgent, AudioTransmitterConfig
from core_dispatch.launch_control.config.settings import (
    LOGS_DIR,
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
    TX_SAMPLE_RATE,
    TX_CHANNELS,
    TX_AUDIO_DEVICE_INDEX,
    AUDIO_DEVICE,
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
    DEFAULT_VOICE,
)


@click.group()
def cli():
    """
    Core Dispatch CLI
    
    Use this tool to start receiver or transmitter services.
    """
    pass

@cli.command()
@click.option('--debug', is_flag=True, default=False, help='Enable debug logging')
def receiver(debug):  # pragma: no cover
    """Start the audio receiver service."""
    # Suppress verbose logs from underlying libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = LOGS_DIR / "core_dispatch.log"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    def on_transcription(text: str):  # noqa: U100
        # Default no-op handler; override by passing a custom callback
        pass

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

    agent = AudioReceiverAgent(config=config, on_transcription=on_transcription, debug_mode=debug)

    async def run():
        await agent.initialize()
        await agent.start()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await agent.stop()
            await agent.cleanup()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nReceived exit signal. Cleaning up...")

def get_personas_from_profile(profile_name: str) -> list:
    """
    Retrieve persona file stems from a given profile directory.
    """
    pkg_dir = Path(__file__).resolve().parent.parent  # points to src/core_dispatch
    profiles_dir = pkg_dir / "personas"
    profile_path = profiles_dir / profile_name
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{profile_name}' does not exist in {profiles_dir}")
    if profile_path.is_dir():
        return [file.stem for file in profile_path.glob("*.json") if file.is_file()]
    else:
        raise ValueError(f"Profile '{profile_name}' is not a valid directory.")

@cli.command()
@click.option('--profile', required=True, help="Profile or profile set to load")
@click.option('--debug', is_flag=True, default=False, help='Enable debug logging')
def transmitter(profile, debug):  # pragma: no cover
    """Start the audio transmitter service."""
    # Suppress verbose logs from underlying libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Ensure necessary directories exist
    os.makedirs(TTS_AUDIO_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
    os.makedirs(PROCESSED_TRANSCRIPTIONS_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(TX_LOG_FILE),
            logging.StreamHandler()
        ]
    )

    try:
        personas = get_personas_from_profile(profile)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

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
        debug_mode=debug,
        persona_names=personas,
        profile_name=profile
    )

    async def run():
        await agent.initialize()
        await agent.start()
        click.echo("Audio transmitter is running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await agent.stop()
            click.echo("Audio transmitter stopped. Goodbye!")

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nReceived exit signal. Cleaning up...")
