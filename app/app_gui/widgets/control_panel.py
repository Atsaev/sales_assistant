from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class ControlPanel(QWidget):
    """Панель управления с кнопками старт/стоп"""

    start_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self.is_recording = False
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.start_btn = QPushButton("🎙️ Начать звонок")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setMinimumWidth(120)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)

        self.status_indicator = QLabel("⚪")
        self.status_indicator.setObjectName("status_indicator")
        self.status_indicator.setFixedSize(20, 20)

        self.status_label = QLabel("Готов")
        self.status_label.setObjectName("status_label")

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _on_start_clicked(self):
        self.start_clicked.emit()

    def _on_stop_clicked(self):
        self.stop_clicked.emit()

    def set_recording(self, recording: bool):
        self.is_recording = recording
        self.start_btn.setEnabled(not recording)
        self.stop_btn.setEnabled(recording)

        if recording:
            self.status_indicator.setText("🔴")
            self.status_label.setText("Идёт запись")
            self.status_label.setProperty("status", "recording")
        else:
            self.status_indicator.setText("⚪")
            self.status_label.setText("Готов")
            self.status_label.setProperty("status", "ready")

        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_processing(self, processing: bool):
        if processing:
            self.status_indicator.setText("🟡")
            self.status_label.setText("Обработка...")
            self.status_label.setProperty("status", "processing")
        elif self.is_recording:
            self.status_indicator.setText("🔴")
            self.status_label.setText("Идёт запись")
            self.status_label.setProperty("status", "recording")
        else:
            self.status_indicator.setText("⚪")
            self.status_label.setText("Готов")
            self.status_label.setProperty("status", "ready")

        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_status_message(self, message: str, duration_ms: int = 2000):
        """Временно показывает сообщение в статусе"""
        old_text = self.status_label.text()
        self.status_label.setText(message)
        QTimer.singleShot(duration_ms, lambda: self.status_label.setText(old_text))

    def enable_start(self, enabled: bool = True):
        self.start_btn.setEnabled(enabled and not self.is_recording)

    def enable_stop(self, enabled: bool = True):
        self.stop_btn.setEnabled(enabled and self.is_recording)

    def get_state(self) -> dict:
        return {
            "is_recording": self.is_recording,
            "start_enabled": self.start_btn.isEnabled(),
            "stop_enabled": self.stop_btn.isEnabled(),
            "status_text": self.status_label.text(),
        }
