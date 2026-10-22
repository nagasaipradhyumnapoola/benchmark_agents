"""Shared application service functions used by both HTTP and CLI interfaces."""

from __future__ import annotations

import importlib.util
import platform
import shutil
from pathlib import Path
from typing import Any

from benchlab import __version__
from benchlab.schemas import ExperimentConfig, SystemSpec


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
