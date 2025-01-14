# Core Dispatch – Developer Guide

This document explains how to set up and develop for **Core Dispatch**, an AI-driven radio communication system that leverages GPT-based personas on a Raspberry Pi + handheld two-way radios.

---

## 1. Introduction

Core Dispatch provides a framework that:

- **Listens** to incoming audio via a handheld transceiver (receiver).
- **Transcribes** the audio using STT (Whisper, Google Chirp, or a mock service).
- **Determines** which AI persona should respond (e.g., “The Dude,” “Warehouse Worker,” or an emergency response role).
- **Generates** the persona’s text response via GPT-4.
- **Optionally calls tools** (like an Inventory Lookup) to incorporate real-world data.
- **Converts** the final AI text to speech using TTS (OpenAI or UnrealSpeech).
- **Transmits** the resulting audio back over the radio (transmitter).

---

## 2. Hardware & Equipment Setup

### 2.1 Required Equipment

1. **Raspberry Pi** (Pi 4 or Pi 5 recommended; 1GB RAM or more).
2. **Three handheld two-way radios** (or Baofeng UV5R, etc.):  
   - One for receiving (RX).  
   - One for transmitting (TX) via VOX mode.  
   - One for the operator to speak from.
3. **USB Sound Card** for capturing RX audio.
4. **Audio Cables** to connect the Pi’s audio out to the TX radio, and the RX radio’s audio out to the Pi’s microphone in.

### 2.2 Wiring Diagram

```none
[RX Radio] --> [USB Sound Card Mic In] --> [Raspberry Pi]
[Raspberry Pi Headphone Out] --> [TX Radio Mic In]
```

Ensure VOX is enabled on your TX radio so it automatically keys up when audio is played.

---

## 3. Software Setup

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/YOUR_USER/core-dispatch.git
   cd core-dispatch
   ```
2. **Create and Activate a Virtual Environment**  
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
4. **Set Environment Variables** (in `env.sh` or similar)  
   ```bash
   export OPENAI_API_KEY="sk-xxxx"
   export TRANSCRIPTION_SERVICE_TYPE="openai-whisper"  # or "google-chirp"
   export TTS_PROVIDER="openai"                       # or "unrealspeech"
   export AUDIO_DEVICE="plughw:1,0"
   ```
   Adjust `AUDIO_DEVICE` to match your sound card. You can check device IDs with:
   ```bash
   python -c "import sounddevice; print(sounddevice.query_devices())"
   ```

---

## 4. Directory Structure

Below is the **simplified** tree:

```none
core-dispatch/
├── conversation_log.txt
├── demo/
│   ├── demo.md
│   └── run.sh
├── dispatch_queue/
├── docs/
│   ├── demo.md
│   ├── reciever.md
│   └── start_demo.sh
├── env.sh
├── pyproject.toml
├── README.md
├── src/
│   └── core_dispatch/
│       ├── agent_framework/
│       │   ├── audio/
│       │   │   ├── __init__.py
│       │   │   ├── receiver.py
│       │   │   ├── transcription.py
│       │   │   └── transmitter.py
│       │   ├── core/
│       │   │   ├── base_agent.py
│       │   │   └── __init__.py
│       │   ├── __init__.py
│       │   ├── tools/
│       │   │   └── tool_inventory_lookup.py
│       │   └── utils/
│       │       ├── __init__.py
│       │       └── tts_service.py
│       ├── launch_control/
│       │   └── config/
│       │       └── settings.py
│       ├── logs/
│       │   ├── core_dispatch.log
│       │   ├── transcriptions.log
│       │   └── tx_log.log
│       └── personas/
│           ├── emg_response/
│           │   ├── dispatch.json
│           │   ├── fire_analyst.json
│           │   └── logistics.json
│           ├── the_dude/
│           │   └── the_dude.json
│           └── warehouse_worker/
│               └── warehouse_worker.json
├── src.sh
├── start_reciever.py
├── start_transmitter.py
├── test_full_loop.py
└── test_receiver.py
```

### Key Folders

- **`agent_framework/audio/`**: Audio-related agents (`receiver.py`, `transmitter.py`, etc.).  
- **`agent_framework/core/`**: Base agent classes and shared logic.  
- **`agent_framework/tools/`**: Additional tools (e.g., inventory lookups).  
- **`agent_framework/utils/`**: Utility modules (TTS services, etc.).  
- **`launch_control/config/`**: Holds `settings.py` (env variables, config).  
- **`personas/`**: JSON files defining persona prompts, voices, activation phrases.

---

## 5. Classes & Responsibilities

This section describes the major classes and their methods. (For the sake of brevity, we won’t include every method signature—just the highlights.)

### 5.1 Base Classes

**`BaseAgent`** (`agent_framework/core/base_agent.py`)  
- An abstract class that all agents inherit from.  
- Provides async lifecycle methods: `initialize()`, `start()`, `stop()`, `cleanup()`.

### 5.2 Receiver Side

**`AudioReceiverAgent`** (`agent_framework/audio/receiver.py`)  
- Continuously listens to the audio input (via `sounddevice`).  
- Uses a **TranscriptionService** to convert audio to text.  
- Saves the transcription to JSON in `TRANSCRIPTIONS_DIR`.  
- Main methods:
  - `initialize()`: Prepare the audio stream and logging.  
  - `start()`: Start capturing audio.  
  - `stop()`: Cleanly stop capturing audio.  

### 5.3 Transcription Services

(`agent_framework/audio/transcription.py`)  
- `TranscriptionService`: An abstract base for STT.  
- Implementations:
  - **`OpenAIWhisperService`**  
  - **`GoogleChirpService`**  
  - **`MockTranscriptionService`** (for testing)  

### 5.4 Transmitter Side

**`AudioTransmitterAgent`** (`agent_framework/audio/transmitter.py`)  
- Monitors transcribed messages in `TRANSCRIPTIONS_DIR`.  
- Chooses which persona to respond based on activation phrases.  
- Calls GPT-4 to generate a response.  
- Optionally handles multi-pass logic (e.g., `SAY:` lines or `TOOL_CALL:` lines).  
- Converts final text to audio via **TTS** and plays it out to the TX radio.  
- Main methods:
  - `start()`: Launches threads to watch for new transcriptions and handle responses.  
  - `_generate_response()`: The “brains” that reads transcription files, calls GPT-4, and enqueues final text.  
  - `_transmit_responses()`: Dequeues final text, calls TTS, and plays the audio.  
  - `_play_audio(...)`: Actually plays WAV/MP3 using `aplay` or `mpg123`.  
  - `_invoke_tool(...)`: If the AI output has a tool call (e.g. inventory lookup).  

### 5.5 TTS Services

(`agent_framework/utils/tts_service.py`)  
- **`BaseTTSService`**: Abstract base for TTS.  
- **`OpenAITTSService`** and **`UnrealSpeechTTSService`**: Concrete classes that contact external APIs to generate audio from text.

### 5.6 Tools

(`agent_framework/tools/tool_inventory_lookup.py`)  
- **`InventoryLookupTool`**: Example tool that checks an in-memory dictionary for stock quantities, aisles, or if items are discontinued.  
- In your persona config (`warehouse_worker.json`), the GPT-4 prompt instructs the AI how to call this tool.

---

## 6. Persona System

Each persona is defined by a **JSON** file in `src/core_dispatch/personas/`. For example:

```jsonc
{
  "prompt": "You are The Dude ...",
  "voices": {
    "openai": "echo",
    "unrealspeech": "Liv"
  },
  "activation_phrases": ["Hey Dude", "Dude"]
}
```

- **`prompt`**: The “system” style prompt that shapes the AI’s personality.  
- **`voices`**: Which TTS voice to use for this persona.  
- **`activation_phrases`**: If the user says one of these phrases, the transmitter knows to switch to this persona.

---

## 7. Running the Project

1. **Start the Receiver**  
   ```bash
   python start_reciever.py
   ```
   - This launches the `AudioReceiverAgent`.  
   - It writes transcription files to `src/core_dispatch/data/transcriptions/` (or as configured).

2. **Start the Transmitter**  
   ```bash
   python start_transmitter.py --profile the_dude
   ```
   - This launches the `AudioTransmitterAgent` with a specified persona folder (`the_dude` or `warehouse_worker`, etc.).  
   - Monitors the same transcriptions folder for new JSON files.  

3. **Speak Over Your Operator Radio**  
   - The receiver picks it up, transcribes to text.  
   - The transmitter sees the text, triggers the correct persona, calls GPT-4 + TTS, and broadcasts back.

---

## 8. Customizing & Extending

1. **Add/Modify Personas**  
   - Create a new folder in `personas/` (e.g., `my_new_persona`) with a JSON file.  
   - Update your prompts and voice settings.

2. **Add Tools**  
   - Create a new Python file under `agent_framework/tools/`.  
   - Implement your tool logic (e.g., DB calls, external APIs).  
   - Update your persona JSON to instruct the AI how to call that tool.

3. **Switch STT or TTS Providers**  
   - In `.env` or `settings.py`, change `TRANSCRIPTION_SERVICE_TYPE` to `"mock"` or `"google-chirp"`.  
   - For TTS, change `TTS_PROVIDER` to `"unrealspeech"` or another supported service.

4. **Logging**  
   - Logs are written to `src/core_dispatch/logs/` by default.  
   - The conversation logs go to `conversation_log.txt`.

---

## 9. Troubleshooting

- **Receiver Not Detecting Audio**  
  - Check your sound card index in `settings.py` or `.env` (e.g., `AUDIO_DEVICE_INDEX`).  
  - Make sure VOX or volume levels on the radio are set appropriately.

- **Transmitter Not Keying**  
  - Ensure VOX is enabled on your TX radio.  
  - If volume out of the Pi is too low, VOX might not trigger.

- **GPT-4 or TTS Errors**  
  - Confirm `OPENAI_API_KEY` or `UNREALSPEECH_API_KEY` are valid.  
  - Check that the voice ID you’re using is supported by your TTS provider.

- **Feedback Loop**  
  - If the system starts transcribing its own output, ensure the lock file logic is functioning (`_create_lock()` / `_remove_lock()`) and the receiver honors that lock.

---

## 10. Further Reading & Next Steps

- **Multi-Persona Setup**: The `emg_response` profile loads three JSON files (`dispatch.json`, `fire_analyst.json`, `logistics.json`) so the transmitter can switch roles in a single session.  
- **Advanced TTS**: Investigate caching TTS results or adding custom voice fonts if your provider supports it.  
- **Hardware Alternatives**: Instead of a Pi, any small Linux system with a headphone/mic jack could work similarly.

---

## 11. Conclusion

Core Dispatch is a modular, extensible system for AI-driven radio communications. With its agent-based architecture, you can easily:

- Swap in new STT/TTS providers  
- Add specialized personas  
- Integrate custom tools for real data queries  

We hope this guide helps you dive deeper into the codebase and build your own AI radio experience.

