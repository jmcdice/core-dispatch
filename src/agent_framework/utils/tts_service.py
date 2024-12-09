# src/agent_framework/utils/tts_service.py

import numpy as np
import asyncio

class TTSService:
    """Abstract TTS interface. In the future, implement real TTS providers here."""
    async def synthesize(self, text: str, sample_rate: int = 44100) -> np.ndarray:
        raise NotImplementedError

class MockTTSService(TTSService):
    """Mock TTS that returns a short beep indicating we got some text."""
    async def synthesize(self, text: str, sample_rate: int = 44100) -> np.ndarray:
        duration = 1.0  # 1 second tone
        frequency = 440.0  # A4 note
        t = np.linspace(0, duration, int(sample_rate*duration), endpoint=False)
        audio = 0.1*np.sin(2*np.pi*frequency*t).astype(np.float32)
        return audio

