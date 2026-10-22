"""Versioned typing contracts for trusted local extensions, never HTTP-supplied code."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from benchlab.schemas import (
    AdapterOutput,
    AgentConfig,
    CompatibilityResult,
    ExperimentConfig,
    ModelConfig,
    SystemSpec,
    TaskDefinition,
    TraceEvent,
    VerificationResult,
)

API_VERSION = "1.0"
_ENVIRONMENTS: dict = {}
_VERIFIERS: dict = {}
_EXPORTERS: dict = {}


def _register(registry, name, implementation, version):
    if version != API_VERSION or not name or name in registry:
        raise ValueError("Unsupported contract version, empty or duplicate extension name")
    registry[name] = implementation


def register_environment(name, provider, *, version=API_VERSION):
    if name == "builtin":
        raise ValueError("Built-in workspace provider cannot be replaced")
    _register(_ENVIRONMENTS, name, provider, version)


def environment_available(name):
    return name == "builtin" or name in _ENVIRONMENTS


@asynccontextmanager
async def task_environment(name, task, workspace):
    provider = _ENVIRONMENTS.get(name)
    if provider is None:
        if name != "builtin":
            raise ValueError("Environment provider not registered")
        yield workspace
        return
    try:
        prepared = await provider.prepare(task, workspace)
        if Path(prepared).resolve() != workspace.resolve() or workspace.is_symlink():
            raise ValueError("Environment must prepare the assigned isolated workspace")
        yield workspace
    finally:
        await provider.cleanup(workspace)


def register_verifier(name, verifier, *, version=API_VERSION):
    if name in {"exact", "json", "schema", "file-json", "python"}:
        raise ValueError("Built-in verifier cannot be replaced")
    _register(_VERIFIERS, name, verifier, version)


def register_report_exporter(name, exporter, *, version=API_VERSION):
    if name in {"json", "csv", "html", "zip"}:
        raise ValueError("Built-in report exporter cannot be replaced")
    _register(_EXPORTERS, name, exporter, version)


class ModelAdapter(Protocol):
    api_version: str

    async def probe(self, config: ModelConfig) -> CompatibilityResult: ...

    async def execute(
        self,
        system: SystemSpec,
        model: ModelConfig | None,
        agent: AgentConfig | None,
        task: TaskDefinition,
        workspace: Path,
        config: ExperimentConfig,
        emit: Callable[[TraceEvent], None],
    ) -> AdapterOutput: ...


class AgentAdapter(ModelAdapter, Protocol):
    pass


class BenchmarkPack(Protocol):
    api_version: str
    id: str
    version: str

    def tasks(self, task_ids: list[str] | None = None) -> list[TaskDefinition]: ...


class EnvironmentProvider(Protocol):
    api_version: str

    async def prepare(self, task: TaskDefinition, root: Path) -> Path: ...

    async def cleanup(self, workspace: Path) -> None: ...


class Verifier(Protocol):
    api_version: str

    async def verify(
        self, task: TaskDefinition, output: AdapterOutput, workspace: Path, config: ExperimentConfig
    ) -> VerificationResult: ...


class ReportExporter(Protocol):
    api_version: str

    def export(self, experiment: dict, runs: list[dict]) -> bytes: ...
