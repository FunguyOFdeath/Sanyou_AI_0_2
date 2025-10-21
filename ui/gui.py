# ui/gui.py
from __future__ import annotations

import os
import sys
import subprocess
from typing import Optional

import numpy as np
import sounddevice as sd
from PyQt5 import QtCore, QtGui, QtWidgets

from core import WhisperRecognizer, ConfigManager, list_input_devices
from ui.i18n import I18N, tr


class GuiBridge(QtCore.QObject):
    text_sig = QtCore.pyqtSignal(str)
    info_sig = QtCore.pyqtSignal(str)
    status_sig = QtCore.pyqtSignal(str)


class SettingsDialog(QtWidgets.QDialog):
    TEST_SECONDS = 2.0

    def __init__(self, parent, cfg: ConfigManager, recognizer: WhisperRecognizer, on_apply):
        super().__init__(parent)
        self.cfg = cfg
        self.recognizer = recognizer
        self.on_apply = on_apply
        self.setModal(True)
        self.resize(600, 560)

        # язык интерфейса уже установлен снаружи; используем tr()
        self.setWindowTitle(tr("settings.title"))

        root = QtWidgets.QVBoxLayout(self)

        # --- Микрофон и вход ---
        box = QtWidgets.QGroupBox(tr("settings.group.mic"))
        gl = QtWidgets.QGridLayout(box)

        self.devices = list_input_devices()
        self.dev_combo = QtWidgets.QComboBox()
        names = [f"[{d['index']}] {d['name']}  (ch={d['channels']}, sr={int(d['sr'])})" for d in self.devices]
        self.dev_combo.addItems(names)
        cur_idx = self.cfg.device_index
        if cur_idx is not None:
            i = next((k for k, dv in enumerate(self.devices) if dv["index"] == cur_idx), -1)
            if i >= 0:
                self.dev_combo.setCurrentIndex(i)
        gl.addWidget(QtWidgets.QLabel(tr("settings.device")), 0, 0)
        gl.addWidget(self.dev_combo, 0, 1, 1, 2)

        self.gain_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.gain_slider.setRange(-200, 200)
        self.gain_slider.setValue(int(float(self.cfg.gain_db) * 10))
        self.gain_label = QtWidgets.QLabel(f"{self.cfg.gain_db:.1f} dB")
        self.gain_slider.valueChanged.connect(lambda v: self.gain_label.setText(f"{v/10.0:.1f} dB"))
        gl.addWidget(QtWidgets.QLabel(tr("settings.gain")), 1, 0)
        gl.addWidget(self.gain_slider, 1, 1)
        gl.addWidget(self.gain_label, 1, 2)

        self.nr_chk = QtWidgets.QCheckBox(tr("settings.nr"))
        self.nr_chk.setChecked(bool(self.cfg.noise_reduction))
        gl.addWidget(self.nr_chk, 2, 0, 1, 3)

        root.addWidget(box)

        # --- Модель Whisper ---
        mbox = QtWidgets.QGroupBox(tr("settings.group.model"))
        ml = QtWidgets.QGridLayout(mbox)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.addItems(["small", "medium", "large"])
        cur_model = self.cfg.model_name if self.cfg.model_name in {"small", "medium", "large"} else "small"
        self.model_combo.setCurrentIndex({"small": 0, "medium": 1, "large": 2}[cur_model])
        self.model_combo.setToolTip(tr("settings.model.tip"))
        ml.addWidget(QtWidgets.QLabel(tr("settings.model.size")), 0, 0)
        ml.addWidget(self.model_combo, 0, 1)

        root.addWidget(mbox)

        # --- Режим языков ---
        lbox = QtWidgets.QGroupBox(tr("settings.group.lang"))
        ll = QtWidgets.QGridLayout(lbox)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([
            tr("settings.mode.standard"),
            tr("settings.mode.priority"),
            tr("settings.mode.exclusive"),
        ])
        m_idx = {"standard": 0, "priority": 1, "exclusive": 2}.get(self.cfg.lang_mode, 0)
        self.mode_combo.setCurrentIndex(m_idx)
        ll.addWidget(QtWidgets.QLabel(tr("settings.mode")), 0, 0)
        ll.addWidget(self.mode_combo, 0, 1, 1, 2)

        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(["ru", "en", "zh"])
        lang = self.cfg.chosen_lang if self.cfg.chosen_lang in {"ru", "en", "zh"} else "ru"
        self.lang_combo.setCurrentIndex({"ru": 0, "en": 1, "zh": 2}[lang])
        ll.addWidget(QtWidgets.QLabel(tr("settings.chosen_lang")), 1, 0)
        ll.addWidget(self.lang_combo, 1, 1)

        self.mode_combo.currentIndexChanged.connect(self._update_lang_visibility)
        self._update_lang_visibility()
        root.addWidget(lbox)

        # --- Интерфейс (язык UI) ---
        uibox = QtWidgets.QGroupBox(tr("settings.group.ui"))
        ul = QtWidgets.QGridLayout(uibox)
        self.ui_lang_combo = QtWidgets.QComboBox()
        # показываем самоназвания
        self.ui_lang_combo.addItems(["Русский (ru)", "English (en)", "中文 (zh)"])
        ui_map = {"ru": 0, "en": 1, "zh": 2}
        self.ui_lang_combo.setCurrentIndex(ui_map.get(self.cfg.ui_language, 0))
        ul.addWidget(QtWidgets.QLabel(tr("settings.ui_lang")), 0, 0)
        ul.addWidget(self.ui_lang_combo, 0, 1)
        root.addWidget(uibox)

        # --- Тест микрофона ---
        tbox = QtWidgets.QGroupBox(tr("settings.group.test"))
        tl = QtWidgets.QGridLayout(tbox)

        self.test_btn = QtWidgets.QPushButton(tr("settings.test.start"))
        self.test_btn.clicked.connect(self._start_test)
        tl.addWidget(self.test_btn, 0, 0, 1, 1)

        self.play_btn = QtWidgets.QPushButton(tr("settings.test.play"))
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_test)
        tl.addWidget(self.play_btn, 0, 1, 1, 1)

        self.vu = QtWidgets.QProgressBar()
        self.vu.setRange(0, 100)
        self.vu.setValue(0)
        tl.addWidget(QtWidgets.QLabel(tr("settings.level")), 1, 0)
        tl.addWidget(self.vu, 1, 1)

        self.db_label = QtWidgets.QLabel(tr("settings.dbfs"))
        tl.addWidget(self.db_label, 1, 2)

        self.lang_label = QtWidgets.QLabel(tr("settings.lang.detected"))
        f = self.lang_label.font(); f.setBold(True); self.lang_label.setFont(f)
        tl.addWidget(self.lang_label, 2, 0, 1, 3)

        root.addWidget(tbox)

        # --- Кнопки ---
        btns = QtWidgets.QHBoxLayout()
        self.apply_btn = QtWidgets.QPushButton(tr("settings.apply"))
        self.apply_btn.setStyleSheet("background:#2E7D32; color:white; font-weight:bold;")
        self.apply_btn.clicked.connect(self._apply)
        btns.addWidget(self.apply_btn)

        self.cancel_btn = QtWidgets.QPushButton(tr("settings.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

        # состояния теста
        self._test_stream: Optional[sd.InputStream] = None
        self._test_running = False
        self._test_buf: list[np.ndarray] = []
        self._test_sr = int(self.cfg.sample_rate)
        self._last_test_audio: Optional[np.ndarray] = None

    def _update_lang_visibility(self):
        need = (self.mode_combo.currentIndex() in (1, 2))
        self.lang_combo.setEnabled(need)

    def _apply(self):
        # девайс
        new_dev = None
        idx = self.dev_combo.currentIndex()
        if 0 <= idx < len(self.devices):
            new_dev = int(self.devices[idx]["index"])
        # аудио
        new_gain = self.gain_slider.value() / 10.0
        new_nr = self.nr_chk.isChecked()
        # режим
        mode = {0: "standard", 1: "priority", 2: "exclusive"}[self.mode_combo.currentIndex()]
        chosen = self.lang_combo.currentText()
        # модель
        model_name = self.model_combo.currentText()
        # язык интерфейса
        ui_idx = self.ui_lang_combo.currentIndex()
        ui_lang = {0: "ru", 1: "en", 2: "zh"}[ui_idx]

        self.on_apply(new_dev, new_gain, new_nr, mode, chosen, model_name, ui_lang)
        self.accept()

    def _start_test(self):
        if self._test_running:
            return
        self._test_running = True
        self.test_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.lang_label.setText(tr("settings.lang.detected"))
        self._test_buf.clear()
        self._last_test_audio = None

        dev_idx = None
        i = self.dev_combo.currentIndex()
        if 0 <= i < len(self.devices):
            dev_idx = int(self.devices[i]["index"])

        frames_to_read = int(self._test_sr * self.TEST_SECONDS)
        collected = {"n": 0}
        gain_lin = 10.0 ** ((self.gain_slider.value() / 10.0) / 20.0)

        def _cb(indata, frames, time_info, status):
            x = indata.reshape(-1).astype(np.float32)
            if gain_lin != 1.0:
                x = np.clip(x * gain_lin, -1.0, 1.0)
            rms = float(np.sqrt(np.mean(x * x)) + 1e-9)
            db = 20.0 * np.log10(rms)
            vu = max(0.0, min(100.0, (db + 60.0) * (100.0 / 60.0)))
            QtCore.QMetaObject.invokeMethod(self.vu, "setValue", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, int(vu)))
            self.db_label.setText(f"{db:.1f} dBFS")

            self._test_buf.append(x.copy())
            collected["n"] += frames
            if collected["n"] >= frames_to_read:
                QtCore.QTimer.singleShot(0, self._stop_test)

        try:
            self._test_stream = sd.InputStream(
                device=dev_idx, samplerate=self._test_sr, channels=1,
                dtype="float32", blocksize=int(self._test_sr * 0.2), callback=_cb
            )
            self._test_stream.start()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr("settings.title"), tr("settings.test.err").format(e))
            self._test_running = False
            self.test_btn.setEnabled(True)
            self.play_btn.setEnabled(False)

    def _stop_test(self):
        if self._test_stream is not None:
            try:
                self._test_stream.stop()
                self._test_stream.close()
            except Exception:
                pass
        self._test_stream = None
        self._test_running = False
        self.test_btn.setEnabled(True)

        try:
            if not self._test_buf:
                self.lang_label.setText(tr("settings.lang.detected"))
                self.play_btn.setEnabled(False)
                return

            audio = np.concatenate(self._test_buf).astype(np.float32)
            self._last_test_audio = audio
            self.play_btn.setEnabled(True)

            lang, conf = self.recognizer.detect_language_from_audio(audio, self._test_sr)
            label = {"ru": "RU", "en": "EN", "zh": "ZH"}.get(lang, lang.upper())
            self.lang_label.setText(f"{tr('settings.lang.detected')[:-1]} {label} ({conf:.2f})")
        except Exception:
            self.lang_label.setText(tr("settings.lang.detected"))
            self.play_btn.setEnabled(False)
        finally:
            self._test_buf.clear()

    def _play_test(self):
        if self._last_test_audio is None or len(self._last_test_audio) == 0:
            QtWidgets.QMessageBox.information(self, tr("settings.title"), tr("settings.play.no"))
            return
        try:
            sd.stop()
            sd.play(self._last_test_audio, samplerate=self._test_sr, blocking=False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr("settings.title"), tr("settings.play.err").format(e))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()
        I18N.set_lang(self.cfg.ui_language)

        self.setWindowTitle(tr("app.title"))
        self.resize(980, 740)

        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        # Заголовок
        self.title_lbl = QtWidgets.QLabel(tr("main.header"))
        f = self.title_lbl.font(); f.setPointSize(13); f.setBold(True); self.title_lbl.setFont(f)
        vbox.addWidget(self.title_lbl)

        # Строка режима/языка
        info_row = QtWidgets.QHBoxLayout(); info_row.setSpacing(12)
        self.mode_text_lbl = QtWidgets.QLabel(tr("main.mode"))
        self.mode_value_lbl = QtWidgets.QLabel("—"); self.mode_value_lbl.setStyleSheet("font-weight:bold;")
        self.lang_text_lbl = QtWidgets.QLabel(tr("main.lang"))
        self.lang_value_lbl = QtWidgets.QLabel("—"); self.lang_value_lbl.setStyleSheet("font-weight:bold;")
        info_row.addWidget(self.mode_text_lbl); info_row.addWidget(self.mode_value_lbl)
        info_row.addWidget(self.lang_text_lbl); info_row.addWidget(self.lang_value_lbl); info_row.addStretch(1)
        vbox.addLayout(info_row)

        # Вывод
        self.out = QtWidgets.QPlainTextEdit(); self.out.setReadOnly(True)
        self.out.setStyleSheet("background:#121212; color:#E6E6E6; font-family:Consolas; font-size:11pt;")
        vbox.addWidget(self.out, 1)

        # Кнопки
        bar = QtWidgets.QHBoxLayout(); vbox.addLayout(bar)
        self.btn_start = QtWidgets.QPushButton(tr("main.btn.start"))
        self.btn_start.setStyleSheet("background:#2E7D32; color:white; font-weight:bold;")
        self.btn_start.clicked.connect(self.on_start); bar.addWidget(self.btn_start)

        self.btn_toggle = QtWidgets.QPushButton(tr("main.btn.stop_stream"))
        self.btn_toggle.setStyleSheet("background:#C62828; color:white; font-weight:bold;")
        self.btn_toggle.setEnabled(False); self.btn_toggle.clicked.connect(self.on_toggle); bar.addWidget(self.btn_toggle)

        self.btn_openlog = QtWidgets.QPushButton(tr("main.btn.open_log"))
        self.btn_openlog.setEnabled(False); self.btn_openlog.clicked.connect(self.on_open_log); bar.addWidget(self.btn_openlog)

        self.btn_settings = QtWidgets.QPushButton(tr("main.btn.settings"))
        self.btn_settings.clicked.connect(self.on_settings); bar.addWidget(self.btn_settings)

        self.btn_exit = QtWidgets.QPushButton(tr("main.btn.exit"))
        self.btn_exit.clicked.connect(self.on_exit); bar.addWidget(self.btn_exit)

        self.status_dot = QtWidgets.QLabel("●"); self.status_dot.setStyleSheet("color:#9E9E9E; font-size:14pt;")
        self.statusBar().addPermanentWidget(self.status_dot)
        self.statusBar().showMessage(tr("status.ready"))

        # мост сигналов
        self.bridge = GuiBridge()
        self.bridge.text_sig.connect(self._append)
        self.bridge.info_sig.connect(self._append)
        self.bridge.status_sig.connect(self._set_status)

        # распознаватель
        self.recognizer = WhisperRecognizer(
            on_text=lambda s: self.bridge.text_sig.emit(s),
            on_info=lambda s: self.bridge.info_sig.emit(s),
            on_status=lambda s: self.bridge.status_sig.emit(s),
            config=self.cfg
        )

        self._append(f"[i] Log: {self.recognizer.log_path}")
        self._append(self._format_cfg_line())
        self._refresh_mode_lang_strip()

    def _format_cfg_line(self) -> str:
        di = self.cfg.device_index
        return (f"[cfg] device_index={di if di is not None else 'default'}, "
                f"gain_db={self.cfg.gain_db:.1f}, "
                f"NR={'on' if self.cfg.noise_reduction else 'off'}, "
                f"mode={self.cfg.lang_mode}, "
                f"chosen={self.cfg.chosen_lang}, "
                f"model={self.cfg.model_name}, "
                f"ui={self.cfg.ui_language}")

    def _refresh_mode_lang_strip(self):
        mode_map = {
            "standard": tr("mode.standard"),
            "priority": tr("mode.priority"),
            "exclusive": tr("mode.exclusive"),
        }
        mode_txt = mode_map.get(self.cfg.lang_mode, self.cfg.lang_mode)
        lang_txt = "— (ru/en/zh)" if self.cfg.lang_mode == "standard" else self.cfg.chosen_lang.upper()

        self.mode_value_lbl.setText(mode_txt)
        self.lang_value_lbl.setText(lang_txt)
        self.mode_value_lbl.setToolTip(tr("tip.mode"))
        self.lang_value_lbl.setToolTip(tr("tip.lang"))

    @QtCore.pyqtSlot(str)
    def _append(self, text: str):
        self.out.appendPlainText(text)
        self.out.verticalScrollBar().setValue(self.out.verticalScrollBar().maximum())

    @QtCore.pyqtSlot(str)
    def _set_status(self, status: str):
        if status == "loading":
            self.status_dot.setStyleSheet("color:#FBC02D; font-size:14pt;")
            self.statusBar().showMessage(tr("status.loading"))
            self.btn_start.setEnabled(False); self.btn_toggle.setEnabled(False)
        elif status == "running":
            self.status_dot.setStyleSheet("color:#2E7D32; font-size:14pt;")
            self.statusBar().showMessage(tr("status.listening"))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setText(tr("main.btn.stop_stream"))
            self.btn_toggle.setStyleSheet("background:#C62828; color:white; font-weight:bold;")
            self.btn_openlog.setEnabled(True); self.btn_start.setEnabled(False)
        elif status == "paused":
            self.status_dot.setStyleSheet("color:#FBC02D; font-size:14pt;")
            self.statusBar().showMessage(tr("status.paused"))
            self.btn_toggle.setEnabled(True)
            self.btn_toggle.setText(tr("main.btn.resume_stream"))
            self.btn_toggle.setStyleSheet("background:#1565C0; color:white; font-weight:bold;")
            self.btn_openlog.setEnabled(True)
        else:
            self.status_dot.setStyleSheet("color:#C62828; font-size:14pt;")
            self.statusBar().showMessage(tr("status.stopped"))
            self.btn_toggle.setEnabled(False)
            self.btn_toggle.setText(tr("main.btn.stop_stream"))
            self.btn_toggle.setStyleSheet("background:#C62828; color:white; font-weight:bold;")
            self.btn_start.setEnabled(True)

    # кнопки
    def on_start(self):
        self._append("🧠 Start recognition…")
        self.btn_start.setEnabled(False); self.btn_toggle.setEnabled(False)
        QtCore.QTimer.singleShot(0, self.recognizer.start)

    def on_toggle(self):
        if not self.recognizer.is_running:
            QtWidgets.QMessageBox.information(self, tr("app.title"), tr("main.msg.not_started"))
            return
        if self.recognizer.is_paused:
            self.recognizer.resume()
        else:
            self.recognizer.pause()

    def on_open_log(self):
        path = str(self.recognizer.log_path)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr("app.title"), tr("main.msg.openlog.error").format(e))

    def on_settings(self):
        def _apply(new_dev, new_gain, new_nr, mode, chosen, model_name, ui_lang):
            # применяем к распознавателю и конфигу
            self.recognizer.apply_new_settings(new_dev, new_gain, new_nr, mode, chosen, model_name)
            self.cfg.ui_language = ui_lang
            I18N.set_lang(ui_lang)

            # обновляем тексты UI
            self._apply_locale()

            self._append(tr("main.cfg.applied").format(self._format_cfg_line()))
            self._refresh_mode_lang_strip()
            if self.recognizer.is_running:
                self._append(tr("main.cfg.restart"))
                self.recognizer.stop()
                QtCore.QTimer.singleShot(350, self.recognizer.start)

        dlg = SettingsDialog(self, self.cfg, self.recognizer, _apply)
        dlg.exec_()

    def _apply_locale(self):
        # заголовки/подписи/кнопки/статусы
        self.setWindowTitle(tr("app.title"))
        self.title_lbl.setText(tr("main.header"))
        self.mode_text_lbl.setText(tr("main.mode"))
        self.lang_text_lbl.setText(tr("main.lang"))
        self.btn_start.setText(tr("main.btn.start"))
        # состояние кнопки паузы меняем по статусу
        if self.recognizer.is_running and not self.recognizer.is_paused:
            self.btn_toggle.setText(tr("main.btn.stop_stream"))
        elif self.recognizer.is_paused:
            self.btn_toggle.setText(tr("main.btn.resume_stream"))
        else:
            self.btn_toggle.setText(tr("main.btn.stop_stream"))
        self.btn_openlog.setText(tr("main.btn.open_log"))
        self.btn_settings.setText(tr("main.btn.settings"))
        self.btn_exit.setText(tr("main.btn.exit"))
        # статусбар (не трогаем, если уже что-то показывает)
        if not self.statusBar().currentMessage():
            self.statusBar().showMessage(tr("status.ready"))
        # подписи режимов/языков
        self._refresh_mode_lang_strip()

    def on_exit(self):
        try:
            self.recognizer.stop()
        finally:
            self.close()


def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
