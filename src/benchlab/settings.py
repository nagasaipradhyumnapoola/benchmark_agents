"""Local-only settings and safe structured redaction; credentials never enter saved config."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchlab.credentials import is_session_reference, secret_values


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

# Short keys can be ordinary protocol words. Preserve schema metadata needed to
# reconstruct records, but never apply that exemption inside provider output or
# other free-text payloads, even if those payloads contain similarly named keys.
STRUCTURAL_FIELDS = {
    "id",
    "model_id",
    "agent_id",
    "system_id",
    "experiment_id",
    "task_id",
    "benchmark_id",
    "baseline_id",
    "task_ids",
    "benchmark_ids",
    "recommended_models",
    "schema_version",
    "adapter",
    "model",
    "base_url",
    "source_url",
    "evidence_url",
    "connection_type",
    "mode",
    "status",
    "publication_status",
    "verification_status",
    "isolation",
    "verification",
    "workspace_provider",
    "capabilities",
    "category",
    "verifier",
    "model_flag",
    "model_base_url_env",
    "model_api_key_env",
    "api_key_env",
    "env_allowlist",
    "executable",
    "tools",
}
FREE_TEXT_FIELDS = {
    "output",
    "error",
    "errors",
    "message",
    "text",
    "stderr",
    "stdout",
    "diff",
    "content",
    "reason",
    "reasons",
    "warnings",
    "description",
    "prompt",
    "evidence",
    "files",
    "parameters",
}


def redact(value: Any, *, _field: str | None = None, _free_text: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if SENSITIVE.search(str(key)) and not str(key).endswith("_env")
            else redact(
                item,
                _field=str(key),
                _free_text=_free_text or str(key) in FREE_TEXT_FIELDS,
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, _field=_field, _free_text=_free_text) for item in value]
    if isinstance(value, str):
        if is_session_reference(value):
            return value
        result = TOKEN.sub("[REDACTED]", value)
        for secret in sorted(set(secret_values()), key=len, reverse=True):
            if len(secret) >= 8:
                result = result.replace(secret, "[REDACTED]")
            elif _free_text or _field not in STRUCTURAL_FIELDS:
                result = re.sub(r"(?<!\w)" + re.escape(secret) + r"(?!\w)", "[REDACTED]", result)
        for key, secret in os.environ.items():
            if SENSITIVE.search(key) and len(secret) >= 8:
                result = result.replace(secret, "[REDACTED]")
        return result
    return value
