from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "pubmed-lab" / "config.json"


@dataclass
class Config:
    ncbi_email: str = "you@example.com"
    ncbi_api_key: str | None = None
    ollama_model: str = "qwen3:8b"
    ollama_host: str = "http://localhost:11434"
    obsidian_vault_path: str = str(Path.home() / "Documents" / "Obsidian" / "PubMedLab")
    db_path: str = str(Path.home() / ".local" / "share" / "pubmed-lab" / "pubmed_lab.db")
    try_full_text: bool = True

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text())
            return cls(**{**cls().__dict__, **data})
        cfg = cls()
        cfg.save()
        return cfg

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.__dict__, indent=2))


def env_override(cfg: Config) -> Config:
    cfg.ncbi_email = os.environ.get("NCBI_EMAIL", cfg.ncbi_email)
    cfg.ncbi_api_key = os.environ.get("NCBI_API_KEY", cfg.ncbi_api_key)
    cfg.ollama_model = os.environ.get("OLLAMA_MODEL", cfg.ollama_model)
    cfg.ollama_host = os.environ.get("OLLAMA_HOST", cfg.ollama_host)
    return cfg
