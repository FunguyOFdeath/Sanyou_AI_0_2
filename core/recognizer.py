# core/recognizer.py
from __future__ import annotations

import os
import gc
import queue
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Tuple

# 🚫 принудительно отключаем CUDA и гасим конфликт OpenMP
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch
import whisper

from .config import ConfigManager
from .log_utils import LogFile
from .audio import list_input_devices, open_input_stream, apply_gain, denoise_wiener
from .vad import EnergyVAD


# ограничим потоки BLAS
try:
    torch.set_num_threads(max(1, min(os.cpu_count() or 2, 4)))
except Exception:
    pass


class WhisperRecognizer:
    """
    Непрерывное офлайн-распознавание (Whisper) для {ru,en,zh}.
    Оптимизации:
      • модель грузится в фоновом потоке (статус 'loading');
      • очереди ограничены (без утечки RAM);
      • VAD/NR/усиление — на лету;
      • режимы стандарт/приоритет/исключительный;
      • аккуратная остановка потоков.
    GUI использует:
      - start(), pause(), resume(), stop()
      - apply_new_settings(...)
      - detect_language_from_audio(audio, sr)
      - свойства: is_running, is_paused, log_path
      - события: on_text(str), on_info(str), on_status(str)
    """

    def __init__(
        self,
        on_text: Callable[[str], None],
        on_info: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        config: Optional[ConfigManager] = None,
        frame_ms: int = 200,
    ) -> None:
        self.on_text = on_text
        self.on_info = on_info or (lambda s: None)
        self.on_status = on_status or (lambda s: None)

        self.cfg = config or ConfigManager()
        self.sr = int(self.cfg.sample_rate)
        self.frame = int(self.sr * frame_ms / 1000.0)

        base = Path(__file__).resolve().parents[1]
        logs_dir = base / "logs"
        self.log = LogFile(logs_dir)
        self.log_path = self.log.path

        self._emit_info(f"[INFO] PyTorch {torch.__version__} | CUDA: {torch.cuda.is_available()}")
        self._emit_info(f"[INFO] Model: {self.cfg.model_name} | SR: {self.sr} | Device: CPU")

        # модель lazy: загрузим в фоне на start()
        self.model: Optional[whisper.Whisper] = None
        self._loading = False

        # рабочие объекты
        self._audio_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=12)
        self._stream_thread: Optional[threading.Thread] = None
        self._proc_thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

        # vad
        self.vad = EnergyVAD(sr=self.sr)

        # состояния
        self.is_running = False
        self.is_paused = False

        # языки
        self._allowed = {"ru", "en", "zh"}
        self._last_lang: Optional[str] = None

    # ---------- публичный API ----------
    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._stop_evt.clear()

        if self.model is None and not self._loading:
            self._loading = True
            self._emit_status("loading")
            t = threading.Thread(target=self._load_model_bg, daemon=True)
            t.start()

        # поток чтения микрофона
        self._stream_thread = threading.Thread(target=self._mic_loop, daemon=True)
        self._stream_thread.start()

        # поток обработки
        self._proc_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._proc_thread.start()

    def pause(self) -> None:
        if not self.is_running:
            return
        self.is_paused = True
        self._emit_status("paused")
        self._emit_info("⏸ Пауза")

    def resume(self) -> None:
        if not self.is_running:
            return
        self.is_paused = False
        if self.model is not None:
            self._emit_status("running")
        else:
            self._emit_status("loading")
        self._emit_info("▶ Возобновлено")

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        self.is_paused = False
        self._stop_evt.set()
        # освободим очередь
        try:
            while not self._audio_q.empty():
                self._audio_q.get_nowait()
        except Exception:
            pass
        # дождёмся
        for th in (self._stream_thread, self._proc_thread):
            try:
                if th and th.is_alive():
                    th.join(timeout=1.5)
            except Exception:
                pass
        self._emit_status("stopped")
        self._emit_info("🛑 Остановлено")

    def apply_new_settings(
        self,
        device_index: Optional[int],
        gain_db: float,
        noise_reduction: bool,
        lang_mode: Optional[str] = None,
        chosen_lang: Optional[str] = None,
        model_name: Optional[str] = None,   # ← добавлено
    ) -> None:
        # микрофон / обработка
        self.cfg.device_index = device_index
        self.cfg.gain_db = gain_db
        self.cfg.noise_reduction = noise_reduction
        # языки
        if lang_mode is not None:
            self.cfg.lang_mode = lang_mode
        if chosen_lang is not None:
            self.cfg.chosen_lang = chosen_lang
        # модель
        if model_name and model_name != self.cfg.model_name:
            old = self.cfg.model_name
            self.cfg.model_name = model_name
            # освобождаем старую модель и принудительно перезагрузим на старте
            try:
                self.model = None
                gc.collect()
            except Exception:
                pass
            self._emit_info(f"[INFO] Модель изменена: {old} → {self.cfg.model_name}. Будет загружена при запуске.")

    # для теста в настройках
    def detect_language_from_audio(self, audio: np.ndarray, sr: int) -> Tuple[str, float]:
        x = self._resample_if_needed(audio, sr)
        x = whisper.pad_or_trim(x.astype(np.float32))
        if self.cfg.noise_reduction:
            x = denoise_wiener(x)
        mel = whisper.log_mel_spectrogram(x)
        if self.model is None:
            # временную модель загрузим синхронно (малую) только для детектора языка
            tmp_model = whisper.load_model("tiny", device="cpu")
            _, probs = tmp_model.detect_language(mel)
        else:
            _, probs = self.model.detect_language(mel)
        filt = {k: v for k, v in probs.items() if k in self._allowed}
        if not filt:
            return ("en", 0.0)
        lang = max(filt, key=filt.get)
        return (lang, float(filt[lang]))

    # ---------- внутреннее ----------
    def _load_model_bg(self):
        try:
            self._emit_info(f"[INFO] Loading Whisper model '{self.cfg.model_name}'...")
            self.model = whisper.load_model(self.cfg.model_name, device="cpu")
            if not self.is_paused and self.is_running:
                self._emit_status("running")
            self._emit_info("[INFO] Model ready.")
        except Exception as e:
            self._emit_info(f"[ERROR] Model load failed: {e}")
        finally:
            self._loading = False

    def _mic_loop(self):
        """Чтение аудио → очередь."""
        def _cb(indata, frames, time_info, status):
            if self._stop_evt.is_set():
                return
            if status:
                self._emit_info(f"[AUDIO] {status}")
            if not self.is_running or self.is_paused:
                return
            x = indata.reshape(-1).astype(np.float32)
            x = apply_gain(x, self.cfg.gain_db)
            try:
                self._audio_q.put_nowait(x)
            except queue.Full:
                pass

        try:
            stream = open_input_stream(
                callback=_cb,
                samplerate=self.sr,
                device_index=self.cfg.device_index,
                blocksize=self.frame,
                channels=1,
            )
            with stream:
                while self.is_running and not self._stop_evt.is_set():
                    import time
                    time.sleep(0.05)
        except Exception as e:
            self._emit_info(f"[ERROR] Audio stream: {e}")
            self.stop()

    def _process_loop(self):
        self.vad.reset()
        while self.is_running and not self._stop_evt.is_set():
            try:
                x = self._audio_q.get(timeout=0.3)
            except queue.Empty:
                continue

            if self.is_paused:
                self.vad.reset()
                continue

            utt = self.vad.feed(x)
            if utt is None:
                continue

            if self.model is None:
                self._emit_info("… (model loading)")
                continue

            y = whisper.pad_or_trim(utt.astype(np.float32))
            if self.cfg.noise_reduction:
                y = denoise_wiener(y)

            mode = self.cfg.lang_mode
            if mode == "exclusive":
                lang = self.cfg.chosen_lang if self.cfg.chosen_lang in self._allowed else "ru"
                text = self._asr(y, lang)
            elif mode == "priority":
                primary = self.cfg.chosen_lang if self.cfg.chosen_lang in self._allowed else "ru"
                text = self._asr(y, primary)
                if len(text.strip()) < 2:
                    lang = self._best_lang(y, exclude={primary})
                    text = self._asr(y, lang)
                else:
                    lang = primary
            else:
                lang = self._best_lang(y)
                if self._last_lang and lang != self._last_lang:
                    lang2 = self._best_lang(y, force=True)
                    lang = lang2
                self._last_lang = lang
                text = self._asr(y, lang)

            if text:
                line = f"[{lang.upper()}] {text.strip()}"
                self._emit_text(line)
                self.log.write(line)
                self._emit_info(line)

    # --- helpers ---
    def _best_lang(self, audio: np.ndarray, exclude: Optional[set] = None, force: bool = False) -> str:
        mel = whisper.log_mel_spectrogram(audio)
        _, probs = self.model.detect_language(mel)  # type: ignore[union-attr]
        filt: Dict[str, float] = {k: float(v) for k, v in probs.items() if k in self._allowed}
        if exclude:
            for k in list(filt.keys()):
                if k in exclude:
                    filt.pop(k, None)
        if not filt:
            return self._last_lang or "en"
        lang = max(filt, key=filt.get)
        if not force and self._last_lang and lang != self._last_lang:
            if filt.get(lang, 0.0) < 0.50:
                return self._last_lang
        return lang

    def _asr(self, audio: np.ndarray, lang: str) -> str:
        res = self.model.transcribe(  # type: ignore[union-attr]
            audio,
            language=lang,
            task="transcribe",
            fp16=False,
            temperature=0.0,
            best_of=5,
            beam_size=5,
            condition_on_previous_text=False,
            no_speech_threshold=0.3,
        )
        return (res.get("text") or "").strip()

    def _resample_if_needed(self, x: np.ndarray, sr: int) -> np.ndarray:
        if sr == self.sr:
            return x.astype(np.float32)
        ratio = self.sr / float(sr)
        n = int(len(x) * ratio)
        idx = (np.arange(n) / ratio).astype(np.float32)
        idx = np.clip(idx, 0, len(x) - 1)
        return x[idx.astype(np.int32)].astype(np.float32)

    # --- emitters ---
    def _emit_text(self, s: str):
        try: self.on_text(s)
        except Exception: pass

    def _emit_info(self, s: str):
        try: self.on_info(s)
        except Exception: pass

    def _emit_status(self, s: str):
        try: self.on_status(s)
        except Exception: pass
