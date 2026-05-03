from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SuggestionWidget(QWidget):
    """Виджет для отображения подсказок"""

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self._state = "idle"
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("Нажмите 'Начать звонок'")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumHeight(self.config.get("min_height", 150))
        self.label.setObjectName("suggestion_display")

        layout.addWidget(self.label)

    def set_suggestion(self, text: str, blink: bool = True):
        """Устанавливает подсказку"""
        self.label.setText(text)
        self._state = "suggestion"
        self.update_property()

        if blink:
            QTimer.singleShot(100, lambda: self._reset_state())

    def set_state(self, state: str):
        """Устанавливает состояние: idle, listening, processing, suggestion"""
        self._state = state
        self.update_property()

        states_text = {
            "idle": "Готов",
            "listening": "Слушаю...",
            "processing": "Анализирую...",
            "suggestion": "Подсказка",
        }

        if not self.label.text() or self.label.text() == "":
            self.label.setText(states_text.get(state, ""))

    def _reset_state(self):
        if self._state == "suggestion":
            self._state = "listening"
            self.update_property()

    def update_property(self):
        """Обновляет property для стилей"""
        self.label.setProperty("state", self._state)
        self.label.style().unpolish(self.label)
        self.label.style().polish(self.label)

    def get_text(self):
        return self.label.text()
