# core/audio.py
from __future__ import annotations
from typing import List, Optional, Tuple, Callable
import numpy as np
import sounddevice as sd
from scipy.signal import wiener


def list_input_devices() -> List[dict]:
    out: List[dict] = []
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0:
                out.append({
                    "index": idx,
                    "name": dev.get("name", f"Device {idx}"),
                    "hostapi": dev.get("hostapi"),
                    "sr": dev.get("default_samplerate"),
                    "channels": dev.get("max_input_channels"),
                })
    except Exception:
        pass
    return out


def open_input_stream(
    callback: Callable,
    samplerate: int,
    device_index: Optional[int],
    blocksize: int,
    channels: int = 1,
):
    """Фабрика безопасного ввода."""
    return sd.InputStream(
        device=device_index,
        samplerate=samplerate,
        channels=channels,
        dtype="float32",
        blocksize=blocksize,
        callback=callback,
    )


def apply_gain(x: np.ndarray, gain_db: float) -> np.ndarray:
    if not gain_db:
        return x
    g = 10.0 ** (float(gain_db) / 20.0)
    return np.clip(x * g, -1.0, 1.0).astype(np.float32)


def denoise_wiener(x: np.ndarray, mysize: int = 29) -> np.ndarray:
    try:
        y = wiener(x, mysize=mysize)
        return np.clip(y, -1.0, 1.0).astype(np.float32)
    except Exception:
        return x
