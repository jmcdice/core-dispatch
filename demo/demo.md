
# Core Dispatch – AI-Driven Radio Communication System

### By Joey

- AI personas on handheld radios + Raspberry Pi
- Chat AI (gpt-4) for conversation & tool use
- Real-time STT + TTS + radio integration

---
# What is Core Dispatch?

- AI service(s) that bridge classic handheld radios and modern AI systems.
- Listens for incoming transmissions, transcribes via Whisper/Chirp.
- Generates persona-specific responses (e.g., "The Dude").
- Converts AI response to speech, transmits back over radio (VOX).
- Modular: easy to add new personas, TTS, STT, and tools.

---
# Why Did I Build This?

- Curiosity: merging old-school radio comms with cutting-edge AI
- Just exploring new frontiers in voice + GPT integration 
- MVP approach:
  - Baofeng radios are cheap and widely used.
  - Raspberry Pi is a flexible, low-cost platform.
- Potential use-cases:
  - Any organizationt that uses radio's for work.
  - Construction sites
  - Any facilities 
  - Warehouse/inventory Q&A (tools)
  - Emergency dispatch 
  - Space: Launch control, ISS, moon base
  - AI buddy to chat with “The Dude” or a "Professor", whatever. 

---
# Hardware Setup & Cost

- Raspberry Pi (4/5) ≈ $80–$90
- 3x Baofeng radios ≈ $70 total
  - 1 radio for Rx
  - 1 radio for Tx
  - 1 radio for the operator
- USB sound card, audio cables ≈ $10–$15
- ~ $200 total on Amazon
- Licensing note:
  - In the US, use FRS channels if no ham license
  - Always follow local regulations

---
# System Overview

- **AudioReceiverAgent** 
  - VAD-based listening, transcribes speech → text
- **Transcription Service** 
  - Whisper / Google Chirp
- **AudioTransmitterAgent** 
  - Chooses persona
  - Generates GPT-based response
  - Converts to TTS
  - Plays audio via VOX
- **Persona System** 
  - JSON-based config (the_dude.json, warehouse_worker.json, etc.)
- **Tool Use** 
  - Persona can call external tools (inventory lookups, etc.)

---
# Conversation Flow Through Core Dispatch

1. **User speaks over radio** → Pi hears on RX radio
2. **Receiver Agent** detects audio, sends to STT (Whisper/Chirp)
3. **Transcribed text** gets queued or stored
4. **AudioTransmitterAgent** picks persona based on activation phrase (hey dude)
5. **GPT-4** generates response (prompts + context)
6. **Response** is parsed for any tool calls
   - Inventory lookups, etc. 
7. **TTS service** (OpenAI or UnrealSpeech) synthesizes speech
8. **VOX** triggers TX radio to broadcast final audio

---
# Tools & Persona Access

- There are persona files which describe an AI persona.
- Each persona can call different tools.
- Example: Warehouse Worker persona → InventoryLookupTool
  - Tool code in `tool_inventory_lookup.py`
  - Wait for "TOOL_RESPONSE" before final user-facing answer
- Results in a two-pass conversation flow:
  - Pass #1: Gather data/output from the tool
  - Pass #2: GPT finalizes the user-facing output

---
# Demo Part 1: The Dude

### Profile: the_dude

Interact:
   - "Hey Dude, you got your ears on?"
   - "Wanna go bowling?"
   - "How do you make a White Russian?"

---

# Demo Part 2: Warehouse Worker

### Profile: warehouse_worker

Interact:
   - "Warehouse, do we have organic almond milk?"
   - "Warehouse, do we have signature coffee?"
   - "Warehouse, do we have paddle boards?"
Observe:
   - AI performs 'TOOL_CALL InventoryLookupTool: lookup <item>'
   - Responds with quantity & aisle

---
# Demo Part 3: Emergency Response

### Profile: emg_response (Advanced: multiple personas interact with multiple issues)

- Personas: dispatch, fire_analyst, logistics

Interact:
   - "Dispatch, this is unit 33. There's a fast-moving fire near Sunset Blvd. Over."
   - "Fire Analyst, this is unit 33. What's the spread rate for the Sunset Fire? Over."
   - "Logistics, unit 33 - do we have water tankers for the Sunset fire? Over."

   - "Dispatch, this is Unit 11. We have a group of looters near 5th Avenue 
      breaking into stores."
   - "Dispatch, Unit 11 again. The looters have dispersed. Situation is under 
      control at 5th Avenue. Over."

   - "Dispatch, this is incident command, provide a summary of the last 30 minutes. Over."

---
# Recap & Q&A

- We covered:
  - Project hardware
  - System architecture & conversation flow
  - Three demo personas: The Dude, Warehouse, Emergency Response
- Total cost ≈ $200 for Pi + radios + cables
- Source code on GitHub (link here)
  - Next up: SaaS Dashboard
- Questions? Suggestions?
  - Boulder AI Meetup
  - Contact info: https://jmcdice.github.io

