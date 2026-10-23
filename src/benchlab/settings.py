"""Local-only settings and safe structured redaction; credentials never enter saved config."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def environment_setting(name: str, default: str | None = None) -> str | None:
    """Canonical product settings retain compatibility with existing scripts."""
    return os.environ.get("BENCH_AGENTS_" + name, os.environ.get("BENCHLAB_" + name, default))


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    allow_host_process: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(environment_setting("DATA_DIR") or ".bench-agents").resolve(),
            allow_host_process=environment_setting("ALLOW_HOST_PROCESS") == "1",
        )


SENSITIVE = re.compile(
    r"(?:api[_-]?key|authorization|password|secret|access[_-]?token|credential)", re.I
)
TOKEN = re.compile(r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+)", re.I)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if SENSITIVE.search(str(key)) and not str(key).endswith("_env")
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        result = TOKEN.sub("[REDACTED]", value)
        for key, secret in os.environ.items():
            if SENSITIVE.search(key) and len(secret) >= 8:
                result = result.replace(secret, "[REDACTED]")
        return result
    return value
