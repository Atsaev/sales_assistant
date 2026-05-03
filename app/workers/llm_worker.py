import json
import logging
import random
import time
import urllib.request

from PySide6.QtCore import Signal

from app.configs.config_loader import config
from app.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

llm_cfg = config.load("llm_config.yaml")
suggestions_cfg = config.load("suggestions.yaml")
prompts_cfg = config.load("prompts.yaml")

PROVIDER = llm_cfg["llm"]["provider"]
RULES = suggestions_cfg["suggestions"]


class LLMWorker(BaseWorker):
    suggestion_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self.conversation_history: list[str] = []
        self._needs_analysis = False
        self._last_analysis_time = 0.0
        self._last_defaults: set[str] = set()

        analysis = llm_cfg["analysis"]
        self._context_size = analysis["context_size"]
        self._min_interval = analysis["min_interval_seconds"]

        self._strategy = suggestions_cfg["suggestions"]["strategy"]
        self._system_prompt = prompts_cfg["prompts"]["system_default"]

    # Ollama

    @staticmethod
    def _query_ollama(messages: list[dict[str, str]]) -> str | None:
        ollama = llm_cfg["ollama"]
        payload = {
            "model": ollama["model"],
            "messages": messages,
            "stream": False,
            "options": {"temperature": ollama["temperature"]},
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{ollama['base_url']}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=ollama["timeout_seconds"]) as resp:
                result = json.loads(resp.read())
                return result["message"]["content"]
        except Exception:
            logger.exception("Ошибка вызова Ollama")
            return None

    def _suggest_via_ollama(self, text: str) -> str | None:
        last_turns = self.conversation_history[-(self._context_size * 2) :]
        dialogue = "\n".join(f"Клиент: {t}" for t in last_turns)

        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": f"Диалог:\n{dialogue}\n\nКакая подсказка менеджеру?",
            },
        ]
        return self._query_ollama(messages)

    # Rules

    def _suggest_via_rules(self, text: str) -> tuple[str, bool]:
        """Возвращает (подсказка, найдена_ли_по_ключевым_словам)."""
        text_lower = text.lower()

        for category_key in ("objections", "interest_signals", "questions"):
            category = RULES.get(category_key)
            if not category:
                continue
            if category_key == "objections":
                best = self._match_objections(text_lower, category)
            else:
                best = self._match_keywords(
                    text_lower,
                    category.get("keywords", []),
                    category.get("suggestions", []),
                )
            if best:
                return best, True

        defaults = RULES.get("default", [])
        if not defaults:
            return "Продолжайте диалог", False

        available = [d for d in defaults if d not in self._last_defaults]
        if not available:
            available = defaults
            self._last_defaults.clear()

        choice = random.choice(available)
        self._last_defaults.add(choice)
        if len(self._last_defaults) > 3:
            self._last_defaults.pop()
        return choice, False

    @staticmethod
    def _match_objections(text_lower: str, objections: dict) -> str | None:
        for data in objections.values():
            for keyword in data.get("keywords", []):
                if keyword.lower() in text_lower:
                    suggestions = data.get("suggestions", [])
                    if suggestions:
                        return max(suggestions, key=lambda x: x.get("weight", 0))[
                            "text"
                        ]
        return None

    @staticmethod
    def _match_keywords(
        text_lower: str, keywords: list[str], suggestions: list[dict]
    ) -> str | None:
        for keyword in keywords:
            if keyword.lower() in text_lower:
                if suggestions:
                    return max(suggestions, key=lambda x: x.get("weight", 0))["text"]
        return None

    # Основной цикл

    def run(self) -> None:
        while self._is_running:
            if self._needs_analysis:
                now = time.time()
                if now - self._last_analysis_time < self._min_interval:
                    self.msleep(100)
                    continue

                self._needs_analysis = False
                self._last_analysis_time = now
                context = (
                    self.conversation_history[-1] if self.conversation_history else ""
                )

                suggestion = self._get_suggestion(context)
                if suggestion:
                    self.suggestion_ready.emit(suggestion)

            self.msleep(50)

    def _get_suggestion(self, text: str) -> str:
        if self._strategy == "rules":
            return self._suggest_via_rules(text)[0]

        if self._strategy == "llm" and PROVIDER == "ollama":
            result = self._suggest_via_ollama(text)
            return result if result else self._suggest_via_rules(text)[0]

        if self._strategy == "hybrid":
            suggestion, is_keyword_match = self._suggest_via_rules(text)
            if is_keyword_match:
                return suggestion
            if PROVIDER == "ollama":
                result = self._suggest_via_ollama(text)
                return result if result else suggestion

        return self._suggest_via_rules(text)[0]

    # Публичные методы

    def add_text(self, text: str) -> None:
        self.conversation_history.append(text)
        max_history = self._context_size * 3
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        self._needs_analysis = True
