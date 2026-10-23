"""Shared application service functions used by both HTTP and CLI interfaces."""

from __future__ import annotations

import importlib.util
import platform
import shutil
from pathlib import Path
from typing import Any

from benchlab import __version__
from benchlab.credentials import SESSION_PREFIX, forget_key, remember_key
from benchlab.schemas import AgentConfig, ExperimentConfig, ModelConfig, SystemSpec


def connect_model(store, model: ModelConfig, api_key: str | None = None):
    """Save an endpoint with a write-only process credential, shared by HTTP and terminal."""
    previous = next((row for row in store.list_models() if row["id"] == model.id), None)
    reference = None
    if model.api_key_env and model.api_key_env.startswith(SESSION_PREFIX):
        if not previous or previous["config"].get("api_key_env") != model.api_key_env:
            raise ValueError("Session credential references are generated for each connected model")
    if api_key is not None:
        if model.api_key_env:
            raise ValueError("Choose either an environment reference or an entered session API key")
        reference = remember_key(api_key)
        model = model.model_copy(update={"api_key_env": reference})
    try:
        row = store.save_model(model)
    except Exception:
        forget_key(reference)
        raise
    if previous and previous["config"].get("api_key_env") != model.api_key_env:
        forget_key(previous["config"].get("api_key_env"))
    return row


def install_demo_inventory(store, *, include_agents=False):
    """Install fixtures only after an explicit demo request; ordinary startup stays empty."""
    existing = {row["id"]: row["config"] for row in store.list_models()}
    for identity, variant in [("demo-reference", "reference"), ("demo-flawed", "flawed")]:
        if identity in existing:
            saved = existing[identity]
            if not saved["demo"] or saved["adapter"] != "demo" or saved["model"] != variant:
                raise ValueError("Reserved demo model ID belongs to a different configuration")
        else:
            store.save_model(
                ModelConfig(
                    id=identity, name=f"Demo {variant}", adapter="demo", model=variant, demo=True
                )
            )
    if include_agents:
        agents = {row["id"] for row in store.list_agents()}
        for identity in ["demo-agent", "demo-agent-flawed"]:
            if identity not in agents:
                store.save_agent(AgentConfig(id=identity, name=identity, adapter="demo", demo=True))


def demo_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="Offline verification demonstration",
        description="Deterministic public fixtures exercise orchestration and independent verification. These are not model intelligence measurements.",
        systems=[SystemSpec(model_id="demo-reference"), SystemSpec(model_id="demo-flawed")],
        benchmark_id="starter-v1",
        trials=1,
        isolation="workspace",
        demo=True,
        tags=["demo", "pipeline-validation"],
    )


def diagnostics(data_dir: Path) -> dict[str, Any]:
    from benchlab.sandbox import diagnostics as sandbox_diagnostics

    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.system(),
        "storage": {"backend": "sqlite", "data_dir": str(data_dir), "local": True},
        "sandbox": sandbox_diagnostics(),
        "executables": {
            name: bool(shutil.which(name))
            for name in ["codex", "opencode", "docker", "ollama", "lm_eval", "harbor"]
        },
        "optional_packages": {
            name: importlib.util.find_spec(name) is not None
            for name in ["inspect_ai", "mlflow", "duckdb", "pyarrow"]
        },
        "telemetry": "No mandatory external telemetry; events persist locally.",
        "release_status": "development; see docs/implementation-status.md for verified scope",
    }
