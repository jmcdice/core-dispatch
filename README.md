# Core Dispatch

Core Dispatch is an **AI-driven radio communication system** that blends classic handheld two-way radios with modern AI services. By integrating speech-to-text (STT) and text-to-speech (TTS) technologies with AI-based personas, Core Dispatch can **listen**, **transcribe**, and **respond** to radio transmissions in real time.

---

## Features

- **Real-Time Transcription**  
  - Leverages OpenAI Whisper, Google Chirp, or a mock service.
  
- **AI Integration**  
  - System prompts and persona JSON files shape AI responses (currently gpt-4).
  
- **Multi-Persona Support**  
  - Dispatch, Fire Analyst, Logistics, The Dude, Warehouse Worker, or any custom persona.
  
- **Tool Calls**  
  - AI can call custom tools (e.g., inventory lookups) for real data.
  
- **TTS Output**  
  - Plays synthesized speech over the TX radio using OpenAI TTS or UnrealSpeech.
  
- **Modular Architecture**  
  - Extend with new personas, STT/TTS providers, or specialized logic.

---

## Hardware Requirements

- **Raspberry Pi (4 or 5)**  
  - probably any Linux system and sound card
- **Three handheld two-way radios**  
  1. Receive (RX)  
  2. Transmit (TX)  
  3. Operator radio  
- **USB Sound Card**  
- **Audio Cables**  
- **VOX Mode** enabled on the TX radio

For an example wiring diagram and more details, see the [Developer Guide](./docs/DEV_GUIDE.md#2-hardware--equipment-setup).

---

## Quick Setup

1. **Clone the Repo**  
   ```bash
   git clone https://github.com/jmcdice/core-dispatch.git
   cd core-dispatch
   ```

2. **Create a Virtual Environment**  
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**  
   ```bash
   pip install -e .
   ```

4. **Configure Environment Variables**  
   - In `env.sh` or `.env`, set:
     ```bash
     export OPENAI_API_KEY="sk-xxxx"
     export TTS_PROVIDER="openai"          # or "unrealspeech"
     export TRANSCRIPTION_SERVICE_TYPE="openai-whisper"
     export AUDIO_DEVICE="plughw:1,0"      # Adjust to match your sound card
     ```
   - See `settings.py` for additional config options.

5. **Start the Receiver**  
   ```bash
   core-dispatch receiver
   ```
   - Continuously listens for audio on the RX radio input.

6. **Start the Transmitter**  
   ```bash
   core-dispatch transmitter --profile the_dude
   ```
   - Chooses a persona profile (`the_dude`, `warehouse_worker`, `emg_response`, etc.).  
   - Transcribes text → GPT → TTS → plays audio over TX radio.

---

## Usage Example

1. Speak over your **operator radio** with an activation phrase, e.g.:
   > “Hey Dude, what’s your favorite beverage?”

2. The system:
   - **Receives** audio  
   - **Transcribes** to text  
   - **Detects** the phrase “Hey Dude” → Activates “the_dude” persona  
   - **Generates** a GPT-4 response  
   - **Synthesizes** speech  
   - **Plays** that audio through the TX radio

3. Listen for The Dude’s laid-back reply over the airwaves.

---

## Persona System

- **JSON-Based**: Each persona (e.g., `the_dude.json`, `warehouse_worker.json`) defines a prompt, optional voice settings, and activation phrases.  
- **Multi-Persona**: With the `emg_response` profile, you can have “dispatch,” “fire_analyst,” and “logistics” roles in one session.

---

## Tool Calls

- **`tool_inventory_lookup.py`**: Shows how GPT can request inventory data by outputting lines like `TOOL_CALL InventoryLookupTool: lookup organic almond milk`.  
- Extend or replace this with real-world lookups (database queries, APIs, etc.).

---

## Logs & Conversation

- **`conversation_log.txt`**: Records user transmissions and AI persona responses for review.  
- **`src/core_dispatch/logs/`**: Holds additional logs (`core_dispatch.log`, `transcriptions.log`, etc.).

---

## Demo

We’ve included a [demo script](./demo/demo.md) to showcase multiple scenarios. For a live show-and-tell:

1. **tmux** session with **Receiver** on top, **Transmitter** on bottom.  
2. **Tail** the `conversation_log.txt` in another terminal.  
3. **Speak** your lines and watch the logs flow in real time.

---

## Contributing

1. **Fork** the repo  
2. **Create** a feature branch  
3. **Commit** your changes  
4. **Open** a pull request  

Please follow coding style guidelines and provide docstrings for new classes or methods.

---

## Further Documentation

For a more in-depth look at code structure, class responsibilities, and customization tips, check out our **[Developer Guide](./docs/DEV_GUIDE.md)**.

Feel free to open issues or discussions if you have questions, suggestions, or feature requests!

---

