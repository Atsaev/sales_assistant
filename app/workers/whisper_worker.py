import logging
import re
from collections import Counter
from queue import Empty, Queue

import numpy as np
from faster_whisper import WhisperModel
from PySide6.QtCore import Signal

from app.configs.config_loader import config
from app.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

whisper_cfg = config.load("whisper_config.yaml")
W = whisper_cfg["whisper"]
HALL = W["hallucination"]


class WhisperWorker(BaseWorker):
    text_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self._queue: Queue[np.ndarray] = Queue()

        logger.info(
            "Загрузка модели whisper (%s, %s, %s)...",
            W["model_size"],
            W["device"],
            W["compute_type"],
        )
        self._model = WhisperModel(
            model_size_or_path=W["model_size"],
            device=W["device"],
            compute_type=W["compute_type"],
        )
        self._language = W["language"]
        self._min_text_length = W["conditions"]["min_text_length"]
        self._filler_words = W["conditions"]["filler_words"]
        self._hallucination_patterns = [
            re.compile(p, re.IGNORECASE) for p in HALL["patterns"]
        ]
        logger.info("Модель whisper загружена")

    def add_chunk(self, audio_chunk: np.ndarray) -> None:
        self._queue.put(audio_chunk)

    def run(self) -> None:
        while self._is_running:
            try:
                chunk = self._queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                text = self._transcribe(chunk)
                if text:
                    self.text_ready.emit(text)
            except Exception:
                logger.exception("Ошибка распознавания")

    def _transcribe(self, audio: np.ndarray) -> str | None:
        segments, _ = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=W["transcription"]["beam_size"],
        )

        texts: list[str] = []
        for seg in segments:
            if seg.no_speech_prob > HALL["max_no_speech_prob"]:
                continue
            if seg.avg_logprob < HALL["max_avg_logprob"]:
                continue
            texts.append(seg.text.strip())

        raw = " ".join(texts)
        if not raw or len(raw) < self._min_text_length:
            return None

        if self._is_hallucination_pattern(raw):
            return None

        if self._is_repetitive(raw):
            return None

        cleaned = self._clean_text(raw)
        return cleaned if cleaned else None

    # ── Фильтры галлюцинаций ───────────────────────────────

    def _is_hallucination_pattern(self, text: str) -> bool:
        for pattern in self._hallucination_patterns:
            if pattern.search(text):
                logger.debug("Галлюцинация (паттерн): %s", text)
                return True
        return False

    def _is_repetitive(self, text: str) -> bool:
        words = text.lower().split()
        if len(words) <= 2:
            return False
        most_common = Counter(words).most_common(1)[0][1]
        ratio = most_common / len(words)
        if ratio > HALL["max_repeated_word_ratio"]:
            logger.debug("Галлюцинация (повтор): %s", text)
            return True
        return False

    def _clean_text(self, text: str) -> str:
        lower = text.lower()
        for word in self._filler_words:
            lower = lower.replace(word, "")
        return lower.strip()
