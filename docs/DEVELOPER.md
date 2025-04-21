<!--
  Core Dispatch Developer Documentation
  Auto-generated developer overview
-->

# Core Dispatch – Developer Documentation

## 1. Project Overview
Core Dispatch is a modular, AI‑driven radio‑dispatch system that:
- Listens to a handheld radio (RX) via a USB sound card
- Transcribes incoming speech (OpenAI Whisper, Google Chirp, or mock)
- Selects one of several “personas” to respond (e.g. The Dude, Warehouse Worker, EMG roles)
- Generates the persona’s reply via GPT‑4 (with optional tool calls)
- Synthesizes speech (OpenAI TTS or UnrealSpeech)
- Transmits the audio back over the TX radio in VOX mode

Its agent‑based architecture makes it easy to swap out STT/TTS providers, add new personas or tools, and run entirely within Python on a Raspberry Pi (or any Linux box with a sound card).

---

## 2. Installation & Setup

### 2.1 Prerequisites
- Python 3.8+
- A Linux device (Raspberry Pi 4/5 recommended)
- USB sound card & audio cabling to your radios
- VOX‑capable handheld two‑way radios (RX & TX)

### 2.2 Clone & Install
```bash
git clone https://github.com/…/core‑dispatch.git
cd core‑dispatch
python -m venv .venv
source .venv/bin/activate
pip install -e .       # or `pip install -r requirements.txt`
```

### 2.3 Configuration
Copy or create an `env.sh` or `.env` file and set (see `src/core_dispatch/launch_control/config/settings.py` for all options):
```bash
export OPENAI_API_KEY="sk-…"
export TRANSCRIPTION_SERVICE_TYPE="openai-whisper"   # or "google-chirp", "mock"
export TTS_PROVIDER="openai"                         # or "unrealspeech"
export UNREALSPEECH_API_KEY="…"
# Audio device indices—list with `sounddevice.query_devices()`
export AUDIO_DEVICE_INDEX=1       # for receiver
export TX_AUDIO_DEVICE_INDEX=2    # for transmitter
```

---

## 3. Directory Layout
```text
.
├── README.md
├── pyproject.toml        # defines `core-dispatch` CLI entrypoint
├── start_receiver.py     # legacy scripts; prefer `core-dispatch receiver`
├── start_transmitter.py
├── src/
│   └── core_dispatch/
│       ├── agent_framework/
│       │   ├── audio/
│       │   │   ├── receiver.py
│       │   │   ├── transcription.py
│       │   │   └── transmitter.py
│       │   ├── core/
│       │   │   └── base_agent.py
│       │   ├── tools/
│       │   │   └── tool_inventory_lookup.py
│       │   └── utils/
│       │       └── tts_service.py
│       ├── launch_control/
│       │   ├── cli.py     # `core-dispatch` CLI
│       │   └── config/
│       │       └── settings.py
│       └── personas/      # JSON‑defined persona profiles
│
├── docs/
│   └── DEV_GUIDE.md      # existing developer guide
│
└── tests/
    ├── test_receiver.py
    └── test_transmitter.py
```

---

## 4. CLI Usage

The project installs a console script:
```bash
core-dispatch receiver [--debug]
core-dispatch transmitter --profile <profile_name> [--debug]
```

- **receiver**: Launches `AudioReceiverAgent` to capture & transcribe radio audio.
- **transmitter**: Launches `AudioTransmitterAgent`, loads one “profile” (a directory under `src/core_dispatch/personas/`), watches for new transcriptions, invokes GPT & TTS, and plays back the audio.

---

## 5. Core Components

### 5.1 agent_framework/audio/receiver.py
- `AudioReceiverAgent`: records microphone input, chops it on silence thresholds, and emits WAV blobs to a transcription service.

### 5.2 agent_framework/audio/transcription.py
- Abstract `TranscriptionService`
- `OpenAIWhisperService`, `GoogleChirpService`, `MockTranscriptionService`

### 5.3 agent_framework/audio/transmitter.py
- `AudioTransmitterAgent`:
  - Monitors transcription JSON files
  - Matches activation phrases to select a persona
  - Feeds transcript + conversation history to GPT-4
  - Parses `SAY:` and `TOOL_CALL:` lines
  - Invokes tools via `tool_inventory_lookup.py` or custom ones
  - Sends the final reply through a TTS service and plays it on the TX radio

### 5.4 agent_framework/tools/tool_inventory_lookup.py
- Example “tool” illustrating how the AI can request structured data during a session.

### 5.5 agent_framework/utils/tts_service.py
- Abstract `BaseTTSService`
- `OpenAITTSService`, `UnrealSpeechTTSService`

### 5.6 core_dispatch/core/base_agent.py
- Defines the async lifecycle (`initialize()`, `start()`, `stop()`, `cleanup()`) for all agents.

### 5.7 launch_control/config/settings.py
- Centralizes all environment/configuration variables (sample rates, directories, thresholds, API keys, log paths, etc.)

---

## 6. Persona System
Each persona lives in its own subfolder under `personas/`. A JSON file must include:
```json
{
  "prompt":     "System prompt to shape style and role",
  "activation_phrases": ["Hey Dude", "Dude"],
  "voices":     {
    "openai":     "alloy",
    "unrealspeech": "Liv"
  }
}
```
- **prompt**: The “system” instructions for GPT
- **activation_phrases**: Phrases that trigger this persona
- **voices**: TTS voice IDs per provider

To run multiple personas in one session, point `--profile emg_response` (which contains several JSONs like `dispatch.json`, `fire_analyst.json`, `logistics.json`).

---

## 7. Running & Testing

### 7.1 Run the Demo
There’s a demo script in `demo/run.sh` and `docs/demo.md` showing a tmux setup with receiver/transmitter + log tail.

### 7.2 Automated Tests
```bash
pytest   # runs tests in test_receiver.py & test_transmitter.py
```

---

## 8. Extending Core Dispatch

1. **New STT or TTS**
   - Add a new subclass of `TranscriptionService` or `BaseTTSService`.
   - Wire it into `settings.py` & update the CLI.

2. **Custom Tools**
   - Drop a Python module in `agent_framework/tools/`
   - Expose it in your persona JSON with instructions for GPT to call it.

3. **New Personas**
   - Create a folder under `src/core_dispatch/personas/`
   - Add `<name>.json` with prompt, activation phrases, voices.

---

## 9. Troubleshooting

- **No audio detected**: verify your `AUDIO_DEVICE_INDEX` / USB sound card ID.
- **VOX not keying TX**: check radio VOX sensitivity & Pi volume out.
- **GPT/TTS errors**: confirm API keys & network access.
- **Feedback loop**: ensure the built‑in lock files prevent the receiver from hearing its own TX.

---

## 10. Contributing & Style

- Follow the existing async‑agent pattern and naming conventions.
- Add docstrings for all new classes & methods.
- Run `black` and `flake8` via `pre-commit`.
- Open pull requests against `main`; include tests for new behavior.

---

That should give any new developer a clear path into the codebase, show how to configure/run the system, and explain where to hook in new functionality. Let me know if you’d like more detail on any specific component!