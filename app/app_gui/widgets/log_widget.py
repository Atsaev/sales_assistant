from datetime import datetime

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget


class LogWidget(QWidget):
    """Виджет для отображения лога диалога"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        from PySide6.QtWidgets import QLabel

        label = QLabel("[LOG] Расшифровка диалога")
        label.setObjectName("log_label")

        self.clear_btn = QPushButton("[X] Очистить")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self.clear)

        header.addWidget(label)
        header.addStretch()
        header.addWidget(self.clear_btn)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setObjectName("log_text")

        layout.addLayout(header)
        layout.addWidget(self.text_edit)

    def add_log(self, text: str, log_type: str = "info"):
        """Добавляет запись в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        icons = {
            "speech": "[>]",
            "suggestion": "[!]",
            "system": "[i]",
            "error": "[X]",
            "info": "[i]",
        }

        icon = icons.get(log_type, "[i]")
        self.text_edit.append(f"[{timestamp}] {icon} {text}")

        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        self.text_edit.clear()
        self.add_log("Лог очищен", "system")

    def get_text(self):
        return self.text_edit.toPlainText()
