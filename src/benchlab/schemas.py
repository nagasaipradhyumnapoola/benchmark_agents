"""Versioned contracts. Unknown configuration keys are rejected, never silently ignored."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

SCHEMA_VERSION: Literal["1.0"] = "1.0"


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    return str(uuid4())


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = SCHEMA_VERSION


class Status(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ModelConfig(Contract):
    id: str = Field(
        default_factory=new_id, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )
    name: str = Field(min_length=1, max_length=120)
    adapter: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)
    base_url: str | None = None
    connection_type: Literal["local", "hosted"] | None = None
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    capabilities: list[str] = Field(default_factory=lambda: ["text"])
    context_window: int | None = Field(default=None, ge=1)
    input_cost_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_cost_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    demo: bool = False
    description: str = Field(default="", max_length=2000)

    @field_validator("base_url")
    @classmethod
    def endpoint_is_credential_free(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Use an HTTP(S) base URL without credentials, query or fragment")
        return value.rstrip("/")


SessionKey = Annotated[SecretStr, Field(min_length=1, max_length=8192)]


class ModelConnection(Contract):
    config: ModelConfig
    api_key: SessionKey | None = Field(default=None, exclude=True)


class ModelCredential(Contract):
    api_key: SessionKey = Field(exclude=True)


class AgentConfig(Contract):
    id: str = Field(
        default_factory=new_id, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )
    name: str = Field(min_length=1, max_length=120)
    adapter: str = Field(min_length=1, max_length=80)
    executable: str | None = None
    args: list[str] = Field(default_factory=list, max_length=40)
    model_flag: str | None = None
    model_base_url_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    model_api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    capabilities: list[str] = Field(default_factory=lambda: ["text"])
    env_allowlist: list[str] = Field(default_factory=list)
    demo: bool = False
    native: bool = False
    description: str = Field(default="", max_length=2000)

    @field_validator("env_allowlist")
    @classmethod
    def environment_names(cls, names: list[str]) -> list[str]:
        import re

        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names):
            raise ValueError("Environment allowlist must contain variable names, never values")
        return names


class SystemSpec(Contract):
    model_id: str | None = None
    agent_id: str | None = None
    label: str | None = Field(default=None, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identifiable(self) -> SystemSpec:
        if not self.model_id and not self.agent_id:
            raise ValueError("Choose a model or agent")
        return self


Mode = Literal["model", "agent", "native", "matrix", "ablation", "reliability", "baseline"]


class ExperimentConfig(Contract):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    mode: Mode = "model"
    systems: list[SystemSpec] = Field(min_length=1, max_length=16)
    benchmark_id: str = "starter-v1"
    task_ids: list[str] = Field(default_factory=list, max_length=200)
    trials: int = Field(default=1, ge=1, le=50)
    budget_seconds: float = Field(default=300, gt=0, le=86400, allow_inf_nan=False)
    task_timeout_seconds: float = Field(default=30, gt=0, le=3600, allow_inf_nan=False)
    max_tokens: int = Field(default=2048, ge=1, le=131072)
    max_total_tokens: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    retries: int = Field(default=0, ge=0, le=3)
    retry_delay_seconds: float = Field(default=0.2, ge=0, le=60, allow_inf_nan=False)
    memory_mb: int = Field(default=256, ge=64, le=32768)
    cpus: float = Field(default=1, ge=0.1, le=16, allow_inf_nan=False)
    isolation: Literal["docker", "workspace"] = "docker"
    workspace_provider: str = "builtin"
    allow_host_process: bool = False
    network: bool = False
    tools: list[str] = Field(default_factory=list)
    verification: Literal["strict"] = "strict"
    tags: list[str] = Field(default_factory=list, max_length=20)
    baseline_id: str | None = None
    seed: int = 42
    demo: bool = False


class TaskDefinition(Contract):
    id: str
    name: str
    category: str
    prompt: str
    version: str = "1.0.0"
    verifier: str
    expected: Any = None
    verification_config: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=lambda: ["text"])
    files: dict[str, str] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    requires_execution: bool = False
    public: bool = True


class CompatibilityResult(Contract):
    compatible: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    capabilities: dict[str, str] = Field(default_factory=dict)
    requirements: list[str] = Field(default_factory=list)
    checked_at: str = Field(default_factory=utcnow)


class AdapterOutput(Contract):
    text: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    exit_code: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(Contract):
    passed: bool
    verifier: str
    version: str = "1.0.0"
    evidence: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    failure_category: str | None = None


class TraceEvent(Contract):
    type: str
    timestamp: str = Field(default_factory=utcnow)
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: str | None = None
    task_id: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["info", "warning", "error"] = "info"
    provenance: Literal["observed", "provider-reported", "calculated", "estimated", "demo"] = (
        "observed"
    )


class RunManifest(Contract):
    experiment_id: str
    system_id: str
    system_name: str
    system: SystemSpec
    trial: int = 1
    config: ExperimentConfig
    model: ModelConfig | None = None
    agent: AgentConfig | None = None
    benchmark_version: str = "1.0.0"
    task_ids: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    condition_fingerprint: str = ""
    demo: bool = False
    created_at: str = Field(default_factory=utcnow)
    app_version: str = "0.1.0"
    source_revision: str | None = None


class TaskResult(Contract):
    task_id: str
    task_name: str = ""
    category: str
    status: str = "completed"
    passed: bool
    output: AdapterOutput | None = None
    verification: VerificationResult
    duration_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    attempts: int = Field(default=1, ge=0)
    error: str | None = None
    failure_category: str | None = None
    demo: bool = False


class Artifact(Contract):
    id: str = Field(default_factory=new_id)
    run_id: str
    name: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: str = Field(default_factory=utcnow)


class Metric(Contract):
    id: str
    name: str
    unit: str
    definition: str
    provenance: str
    available: bool = True


class Experiment(Contract):
    """Persisted experiment record, separate from immutable launch configuration."""

    id: str
    name: str
    mode: Mode
    config: ExperimentConfig
    status: Status
    demo: bool
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class RunResult(Contract):
    """A durable execution record; completed orchestration is not verifier success."""

    id: str
    experiment_id: str
    system_id: str
    system_name: str
    trial: int
    status: Status
    manifest: RunManifest
    metrics: dict[str, Any] = Field(default_factory=dict)
    demo: bool
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    error: str | None = None
