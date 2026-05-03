import logging
import sys
import warnings
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.app_gui.main_window import MainWindow

# faster-whisper не чистит за собой семафоры
warnings.filterwarnings(
    "ignore", message=".*resource_tracker.*", module="multiprocessing"
)


def setup_logging() -> None:
    log_dir = Path("app/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    setup_logging()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
