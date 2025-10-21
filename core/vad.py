# core/vad.py
from __future__ import annotations
import numpy as np

class EnergyVAD:
    """Простой VAD по среднему модулю. Гистерезис + таймауты."""
    def __init__(
        self,
        sr: int,
        energy_thresh: float = 0.015,
        min_utt_ms: int = 900,
        max_utt_ms: int = 6000,
        silence_ms: int = 450,
    ) -> None:
        self.sr = sr
        self.th = energy_thresh
        self.min_utt = int(sr * min_utt_ms / 1000.0)
        self.max_utt = int(sr * max_utt_ms / 1000.0)
        self.silence_need = int(sr * silence_ms / 1000.0)
        self.reset()

    def reset(self) -> None:
        self.buf = np.zeros(0, dtype=np.float32)
        self.silence_run = 0
        self.in_speech = False

    def feed(self, frame: np.ndarray):
        """Принимает 1D float32, возвращает готовый utterance|None."""
        f = frame.reshape(-1)
        self.buf = np.concatenate((self.buf, f))
        energy = float(np.mean(np.abs(f)))
        voice = energy >= self.th

        if voice:
            self.in_speech = True
            self.silence_run = 0
        else:
            self.silence_run += len(f)

        # слишком длинно — отрежем
        if self.in_speech and len(self.buf) >= self.max_utt:
            utt = self.buf.copy()
            self.reset()
            return utt

        # пауза завершила реплику
        if self.in_speech and self.silence_run >= self.silence_need:
            if len(self.buf) >= self.min_utt:
                utt = self.buf.copy()
                self.reset()
                return utt
            self.reset()

        return None
