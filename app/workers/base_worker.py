import logging

from PySide6.QtCore import QThread

logger = logging.getLogger(__name__)


class BaseWorker(QThread):
    """Базовый класс для всех воркеров с единым паттерном жизненного цикла."""

    def __init__(self) -> None:
        super().__init__()
        self._is_running = False

    def start(
        self, priority: QThread.Priority = QThread.Priority.NormalPriority
    ) -> None:
        self._is_running = True
        super().start(priority)

    def stop(self) -> None:
        self._is_running = False

    def wait_for_stop(self, timeout: int = 10000) -> None:
        if self.isRunning():
            self.wait(timeout)

    def is_running(self) -> bool:
        return self._is_running
