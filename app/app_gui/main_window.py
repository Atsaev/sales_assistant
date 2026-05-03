import logging
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.app_gui.widgets.control_panel import ControlPanel
from app.app_gui.widgets.log_widget import LogWidget
from app.app_gui.widgets.suggestion_widget import SuggestionWidget
from app.audio.audio_capture import AudioCaptureThread
from app.configs.config_loader import config
from app.workers.llm_worker import LLMWorker
from app.workers.whisper_worker import WhisperWorker

logger = logging.getLogger(__name__)

app_config = config.load("app_config.yaml")
styles_config = config.load("styles_config.yaml")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        window_cfg = app_config["app"]["window"]
        self.setWindowTitle(app_config["app"]["name"])
        self.setMinimumSize(window_cfg["min_width"], window_cfg["min_height"])
        self.resize(window_cfg["width"], window_cfg["height"])

        self._init_threads()
        self._init_ui()
        self._connect_signals()
        self._load_styles()
        self._load_settings()

    # Инициализация
    def _init_threads(self) -> None:
        self._audio_thread = AudioCaptureThread()
        self._whisper_thread = WhisperWorker()
        self._llm_thread = LLMWorker()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self._control_panel = ControlPanel()
        self._suggestion_widget = SuggestionWidget(config=app_config["app"]["gui"])
        self._log_widget = LogWidget()

        layout.addWidget(self._control_panel)
        layout.addWidget(self._suggestion_widget)
        layout.addWidget(self._log_widget)

        self._setup_shortcuts()

    def _connect_signals(self) -> None:
        self._control_panel.start_clicked.connect(self._start_recording)
        self._control_panel.stop_clicked.connect(self._stop_recording)

        self._audio_thread.chunk_ready.connect(self._whisper_thread.add_chunk)
        self._whisper_thread.text_ready.connect(self._on_text_recognized)
        self._llm_thread.suggestion_ready.connect(self._update_suggestion)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("F1"), self).activated.connect(self._start_recording)
        QShortcut(QKeySequence("F2"), self).activated.connect(self._stop_recording)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(
            self._log_widget.clear
        )

    def _load_styles(self) -> None:
        theme = styles_config["styles"]["colors"]
        sheets = []

        for path in styles_config["styles"]["files"].values():
            style_path = Path(path)
            if not style_path.exists():
                continue
            content = style_path.read_text(encoding="utf-8")
            for name, value in theme.items():
                content = content.replace(f"%{name.upper()}%", value)
            sheets.append(content)

        if sheets:
            self.setStyleSheet("\n".join(sheets))

    # Управление записью
    def _start_recording(self) -> None:
        try:
            self._log_widget.clear()
            self._log_widget.add_log("🟢 Звонок начат", "system")

            self._audio_thread.wait_for_stop()
            self._whisper_thread.wait_for_stop()
            self._llm_thread.wait_for_stop()

            self._audio_thread.start()
            self._whisper_thread.start()
            self._llm_thread.start()

            self._control_panel.set_recording(True)
            self._suggestion_widget.set_state("listening")

            logger.info("Запись запущена")
        except Exception:
            logger.exception("Ошибка при запуске записи")
            self._log_widget.add_log("❌ Ошибка запуска записи", "error")
            self._stop_recording()

    def _stop_recording(self) -> None:
        try:
            self._audio_thread.stop()
            self._whisper_thread.stop()
            self._llm_thread.stop()

            self._control_panel.set_recording(False)
            self._suggestion_widget.set_state("idle")
            self._log_widget.add_log("🔴 Звонок завершён", "system")

            logger.info("Запись остановлена")
        except Exception:
            logger.exception("Ошибка при остановке записи")

    def _stop_threads(self) -> None:
        self._audio_thread.stop()
        self._whisper_thread.stop()
        self._llm_thread.stop()
        self._audio_thread.wait_for_stop()
        self._whisper_thread.wait_for_stop()
        self._llm_thread.wait_for_stop()

    # Обработка результатов
    def _on_text_recognized(self, text: str) -> None:
        self._log_widget.add_log(text, "speech")
        self._llm_thread.add_text(text)
        self._suggestion_widget.set_state("processing")

    def _update_suggestion(self, suggestion: str) -> None:
        self._suggestion_widget.set_suggestion(suggestion)
        self._log_widget.add_log(f"💡 {suggestion}", "suggestion")
        self._control_panel.set_status_message("💡 Новая подсказка!", 2000)

    # Состояние окна
    def _load_settings(self) -> None:
        geometry = QSettings("SalesAssistant", "Settings").value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _save_settings(self) -> None:
        QSettings("SalesAssistant", "Settings").setValue(
            "geometry", self.saveGeometry()
        )

    def closeEvent(self, event) -> None:
        if self._control_panel.is_recording:
            msg = QMessageBox(
                QMessageBox.Icon.Question,
                "Подтверждение",
                "Звонок ещё идёт. Остановить и закрыть?",
            )
            yes = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
            msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
            msg.setDefaultButton(yes)
            msg.exec()

            if msg.clickedButton() is not yes:
                event.ignore()
                return

            self._stop_recording()

        self._stop_threads()
        self._save_settings()
        event.accept()
