# ui/i18n.py
from __future__ import annotations
from typing import Dict, Any

class I18N:
    _lang = "ru"

    _STRINGS: Dict[str, Dict[str, str]] = {
        # ==== Общие ====
        "app.title": {
            "ru": "🧠 СаньЮ（三友）AI",
            "en": "🧠 Sanyou AI",
            "zh": "🧠 三友 AI",
        },
        "status.ready": {"ru": "готово", "en": "ready", "zh": "就绪"},
        "status.loading": {"ru": "загрузка модели…", "en": "loading model…", "zh": "正在加载模型…"},
        "status.listening": {"ru": "слушаю…", "en": "listening…", "zh": "正在监听…"},
        "status.paused": {"ru": "пауза", "en": "paused", "zh": "已暂停"},
        "status.stopped": {"ru": "остановлено", "en": "stopped", "zh": "已停止"},

        # ==== Главное окно ====
        "main.header": {
            "ru": "🧠 СаньЮ（三友）AI",
            "en": "🧠 Sanyou AI",
            "zh": "🧠 三友 AI",
        },
        "main.mode": {"ru": "Режим:", "en": "Mode:", "zh": "模式："},
        "main.lang": {"ru": " | Язык:", "en": " | Language:", "zh": " | 语言："},
        "main.btn.start": {"ru": "▶ Запустить", "en": "▶ Start", "zh": "▶ 启动"},
        "main.btn.stop_stream": {"ru": "⏸ Остановить поток", "en": "⏸ Stop stream", "zh": "⏸ 停止流"},
        "main.btn.resume_stream": {"ru": "▶ Возобновить поток", "en": "▶ Resume stream", "zh": "▶ 恢复流"},
        "main.btn.open_log": {"ru": "📂 Открыть лог", "en": "📂 Open log", "zh": "📂 打开日志"},
        "main.btn.settings": {"ru": "⚙ Настройки", "en": "⚙ Settings", "zh": "⚙ 设置"},
        "main.btn.exit": {"ru": "🚪 Выйти", "en": "🚪 Exit", "zh": "🚪 退出"},
        "main.msg.not_started": {
            "ru": "Поток ещё не запущен.",
            "en": "Stream is not started yet.",
            "zh": "音频流尚未启动。",
        },
        "main.msg.openlog.error": {
            "ru": "Не удалось открыть лог-файл:\n{}",
            "en": "Failed to open log file:\n{}",
            "zh": "无法打开日志文件：\n{}",
        },
        "main.cfg.applied": {
            "ru": "[cfg] Применены новые настройки: {}",
            "en": "[cfg] Settings applied: {}",
            "zh": "[cfg] 已应用新设置：{}",
        },
        "main.cfg.restart": {
            "ru": "↻ Перезапуск потока для применения настроек…",
            "en": "↻ Restarting stream to apply settings…",
            "zh": "↻ 正在重启音频流以应用设置…",
        },

        # ==== Подпись режимов ====
        "mode.standard": {"ru": "Стандартный (все)", "en": "Standard (all)", "zh": "标准（全部）"},
        "mode.priority": {"ru": "Приоритетный", "en": "Priority", "zh": "优先"},
        "mode.exclusive": {"ru": "Исключительный", "en": "Exclusive", "zh": "单一"},

        # ==== Подсказки ====
        "tip.mode": {
            "ru": "Режим определения языка. В стандартном — все три языка. В приоритетном — сначала выбранный, затем остальные. В исключительном — только выбранный.",
            "en": "Language detection mode. Standard: all three languages. Priority: try chosen first, then others. Exclusive: only the chosen one.",
            "zh": "语言识别模式。标准：三种语言均启用。优先：先尝试所选语言，再尝试其他。单一：仅使用所选语言。",
        },
        "tip.lang": {
            "ru": "Выбранный язык (для приоритетного/исключительного режимов)",
            "en": "Selected language (for priority/exclusive modes)",
            "zh": "所选语言（用于优先/单一模式）",
        },

        # ==== Настройки ====
        "settings.title": {"ru": "⚙ Настройки", "en": "⚙ Settings", "zh": "⚙ 设置"},
        "settings.group.mic": {"ru": "Микрофон и вход", "en": "Microphone & Input", "zh": "麦克风与输入"},
        "settings.device": {"ru": "Устройство ввода:", "en": "Input device:", "zh": "输入设备："},
        "settings.gain": {"ru": "Усиление (дБ):", "en": "Gain (dB):", "zh": "增益（dB）："},
        "settings.nr": {"ru": "Включить шумоподавление (Wiener)", "en": "Enable noise reduction (Wiener)", "zh": "启用降噪（Wiener）"},

        "settings.group.model": {"ru": "Модель распознавания", "en": "Recognition model", "zh": "识别模型"},
        "settings.model.size": {"ru": "Размер модели:", "en": "Model size:", "zh": "模型大小："},
        "settings.model.tip": {
            "ru": "Выбор размера модели Whisper:\n• small — быстрее, ~1–2 ГБ ОЗУ\n• medium — выше качество, ~3–4 ГБ ОЗУ\n• large — максимум качества, может требовать 8–12+ ГБ ОЗУ",
            "en": "Choose Whisper model size:\n• small — faster, ~1–2 GB RAM\n• medium — better quality, ~3–4 GB RAM\n• large — best quality, may need 8–12+ GB RAM",
            "zh": "选择Whisper模型大小：\n• small — 更快，约1–2 GB内存\n• medium — 更高质量，约3–4 GB内存\n• large — 最高质量，可能需要8–12+ GB内存",
        },

        "settings.group.lang": {"ru": "Режим языков", "en": "Language mode", "zh": "语言模式"},
        "settings.mode": {"ru": "Режим:", "en": "Mode:", "zh": "模式："},
        "settings.mode.standard": {"ru": "standard (все 3 языка)", "en": "standard (all 3 languages)", "zh": "standard（3种语言）"},
        "settings.mode.priority": {"ru": "priority (с приоритетом)", "en": "priority (prefer chosen)", "zh": "priority（优先所选）"},
        "settings.mode.exclusive": {"ru": "exclusive (один язык)", "en": "exclusive (single language)", "zh": "exclusive（仅一个）"},
        "settings.chosen_lang": {"ru": "Выбранный язык:", "en": "Chosen language:", "zh": "选择语言："},

        "settings.group.ui": {"ru": "Интерфейс", "en": "Interface", "zh": "界面"},
        "settings.ui_lang": {"ru": "Язык интерфейса:", "en": "UI language:", "zh": "界面语言："},

        "settings.group.test": {"ru": "Тест микрофона", "en": "Microphone test", "zh": "麦克风测试"},
        "settings.test.start": {"ru": "▶ Начать тест (2 сек)", "en": "▶ Start test (2s)", "zh": "▶ 开始测试（2秒）"},
        "settings.test.play": {"ru": "🔊 Прослушать запись", "en": "🔊 Play sample", "zh": "🔊 播放样本"},
        "settings.level": {"ru": "Уровень:", "en": "Level:", "zh": "电平："},
        "settings.dbfs": {"ru": "0.0 dBFS", "en": "0.0 dBFS", "zh": "0.0 dBFS"},
        "settings.lang.detected": {"ru": "Язык: —", "en": "Language: —", "zh": "语言：—"},

        "settings.apply": {"ru": "💾 Сохранить и применить", "en": "💾 Save & apply", "zh": "💾 保存并应用"},
        "settings.cancel": {"ru": "Отмена", "en": "Cancel", "zh": "取消"},

        "settings.test.err": {"ru": "Не удалось запустить тест:\n{}", "en": "Failed to start test:\n{}", "zh": "无法开始测试：\n{}"},
        "settings.play.err": {"ru": "Не удалось воспроизвести запись:\n{}", "en": "Failed to play sample:\n{}", "zh": "无法播放样本：\n{}"},
        "settings.play.no": {"ru": "Нет записанного фрагмента. Сначала выполните тест.", "en": "No recorded sample. Run the test first.", "zh": "没有录到片段，请先进行测试。"},
    }

    @classmethod
    def set_lang(cls, lang: str) -> None:
        if lang not in ("ru", "en", "zh"):
            lang = "ru"
        cls._lang = lang

    @classmethod
    def t(cls, key: str) -> str:
        m = cls._STRINGS.get(key, {})
        return m.get(cls._lang, m.get("en", key))

# Удобный псевдоним
def tr(key: str) -> str:
    return I18N.t(key)
