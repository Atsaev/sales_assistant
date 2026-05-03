import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()


class ConfigLoader:
    def __init__(self, config_dir: str = "app/configs"):
        self.config_dir = Path(config_dir)
        self.cache = {}

    def load(self, name: str) -> Dict[str, Any]:
        if name in self.cache:
            return self.cache[name]

        config_path = self.config_dir / name
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            if name.endswith((".yaml", ".yml")):
                config = yaml.safe_load(f)
            else:
                config = f.read()

        config = self._substitute_env_vars(config)
        self.cache[name] = config
        return config

    def _substitute_env_vars(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            if obj.startswith("${") and obj.endswith("}"):
                var_name = obj[2:-1]
                return os.getenv(var_name, obj)
            return obj
        else:
            return obj


config = ConfigLoader()
