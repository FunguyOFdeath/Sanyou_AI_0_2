# core/config.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigManager:
    DEFAULTS: Dict[str, Any] = {
        "device_index": None,        # int | None
        "gain_db": 0.0,              # -20..+20
        "noise_reduction": True,     # Wiener
        "model_name": "small",       # small | medium | large
        "sample_rate": 16000,
        "lang_mode": "standard",     # standard | priority | exclusive
        "chosen_lang": "ru",         # ru | en | zh
        "ui_language": "ru",         # ru | en | zh  <-- добавлено
    }

    def __init__(self, path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[1]
        self.path = path or (base / "config.json")
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}
        for k, v in self.DEFAULTS.items():
            self.data.setdefault(k, v)
        self.save()

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # properties
    @property
    def device_index(self): return self.data.get("device_index")
    @device_index.setter
    def device_index(self, v): self.data["device_index"] = v; self.save()

    @property
    def gain_db(self) -> float: return float(self.data.get("gain_db", 0.0))
    @gain_db.setter
    def gain_db(self, v: float): self.data["gain_db"] = float(v); self.save()

    @property
    def noise_reduction(self) -> bool: return bool(self.data.get("noise_reduction", True))
    @noise_reduction.setter
    def noise_reduction(self, v: bool): self.data["noise_reduction"] = bool(v); self.save()

    @property
    def model_name(self) -> str: return str(self.data.get("model_name", "small"))
    @model_name.setter
    def model_name(self, v: str): self.data["model_name"] = str(v); self.save()

    @property
    def sample_rate(self) -> int: return int(self.data.get("sample_rate", 16000))

    @property
    def lang_mode(self) -> str: return str(self.data.get("lang_mode", "standard"))
    @lang_mode.setter
    def lang_mode(self, v: str): self.data["lang_mode"] = v; self.save()

    @property
    def chosen_lang(self) -> str: return str(self.data.get("chosen_lang", "ru"))
    @chosen_lang.setter
    def chosen_lang(self, v: str): self.data["chosen_lang"] = v; self.save()

    @property
    def ui_language(self) -> str: return str(self.data.get("ui_language", "ru"))
    @ui_language.setter
    def ui_language(self, v: str): self.data["ui_language"] = v; self.save()
