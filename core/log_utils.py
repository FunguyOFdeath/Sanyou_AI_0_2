# core/log_utils.py
from __future__ import annotations
from datetime import datetime
from pathlib import Path

class LogFile:
    def __init__(self, base_dir: Path) -> None:
        base_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = base_dir / f"log_{ts}.txt"
        self._write(f"===== Sanyou AI log {ts} =====")

    def write(self, line: str) -> None:
        self._write(line)

    def _write(self, line: str) -> None:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(f"[{ts}] {line}\n")
        except Exception:
            pass
