import logging

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Signal

from app.configs.config_loader import config
from app.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)
audio_cfg = config.load("audio_config.yaml")


class AudioCaptureThread(BaseWorker):
    chunk_ready = Signal(np.ndarray)

    def __init__(self):
        super().__init__()
        audio = audio_cfg["audio"]
        self._sample_rate: int = audio["sample_rate"]
        self._chunk_duration: float = audio["chunk_duration"]
        self._chunk_samples: int = int(self._sample_rate * self._chunk_duration)

    def run(self) -> None:
        self._is_running = True

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype=np.float32,
                latency="high",
            ) as stream:
                buffer = np.array([], dtype=np.float32)
                step = int(self._sample_rate * 0.5)
                while self._is_running:
                    data, overflowed = stream.read(step)
                    if overflowed:
                        logger.warning("Аудио переполнено")
                    buffer = np.append(buffer, data.flatten())
                    if len(buffer) >= self._chunk_samples:
                        self.chunk_ready.emit(buffer[: self._chunk_samples])
                        buffer = buffer[self._chunk_samples :]

        except Exception as e:
            logger.exception("Ошибка при захвате аудио: %s", e)
