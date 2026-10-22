"""Durable, bounded asynchronous experiment orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import json
import platform
import time
from importlib.metadata import version

from .analysis import summarize
from .schemas import (
    AgentConfig,
    CompatibilityResult,
    ExperimentConfig,
    ModelConfig,
    RunManifest,
    TaskResult,
    TraceEvent,
    VerificationResult,
    utcnow,
)


class Engine:
    def __init__(self, store):
        self.store = store
        self._active = {}

    def _resolve(self, system):
        return (
            ModelConfig(**self.store.get_model(system.model_id)["config"])
            if system.model_id
            else None,
            AgentConfig(**self.store.get_agent(system.agent_id)["config"])
            if system.agent_id
            else None,
        )

    async def validate(self, config):
        from .adapters.registry import (
            host_allowed,
            probe_agent,
            probe_model,
            validate_system_config,
        )
        from .benchmarks.catalog import get_tasks
        from .plugins import environment_available

        reasons = []
        warnings = []
        if not environment_available(config.workspace_provider):
            reasons.append("Workspace environment provider is not registered")
        try:
            tasks = get_tasks(config.benchmark_id, config.task_ids or None)
        except (KeyError, ValueError) as exc:
            return CompatibilityResult(compatible=False, reasons=[str(exc)])
        if not tasks:
            reasons.append("No tasks selected")
        models = set()
        for system in config.systems:
            try:
                model, agent = self._resolve(system)
            except KeyError as exc:
                reasons.append(f"Unknown system: {exc}")
                continue
            if model:
                models.add(model.id)
            binding = validate_system_config(system, model, agent, config)
            reasons.extend(binding.reasons)
            warnings.extend(binding.warnings)
            demo = any(x.demo for x in (model, agent) if x)
            if len({x.demo for x in (model, agent) if x}) > 1:
                reasons.append("Demo and real components cannot be combined")
            if demo != config.demo:
                reasons.append("Demo systems require demo=True; real and demo systems cannot mix")
            if any(x and x.adapter == "demo" and not x.demo for x in (model, agent)):
                reasons.append("Demo adapters must be marked demo")
            if config.mode == "model" and agent:
                reasons.append("Model mode requires model-only systems")
            if config.mode in {"agent", "native"} and not agent:
                reasons.append("Agent/native mode requires agents")
            if agent and agent.native and config.mode != "native":
                reasons.append("Native agent requires native mode")
            if agent and agent.adapter != "demo" and not host_allowed(config):
                reasons.append("Host agent execution requires experiment and server opt-in")
            for item, probe in [(model, probe_model), (agent, probe_agent)]:
                if item:
                    check = await probe(item)
                    reasons.extend(check.reasons if not check.compatible else [])
                    warnings.extend(check.warnings)
            capabilities = set((agent or model).capabilities)
            for task in tasks:
                if set(task.required_capabilities) - capabilities:
                    reasons.append(f"{task.id}: missing capabilities")
        if config.mode == "agent" and len(models) > 1:
            reasons.append("Controlled agent comparison requires the same model")
        if config.mode == "agent" and any(not system.model_id for system in config.systems):
            reasons.append("Controlled agent mode requires an explicit model for every agent")
        if any(t.requires_execution for t in tasks):
            from .sandbox import diagnostics

            if config.isolation != "docker":
                reasons.append("Executable tasks require Docker isolation")
            diagnostic = diagnostics()
            if not diagnostic.get("available", diagnostic.get("docker_available", False)):
                reasons.append("Docker runtime unavailable for executable tasks")
        if config.max_total_tokens or config.max_cost_usd:
            warnings.append(
                "Usage budgets stop subsequent tasks after observed usage; provider usage may be unavailable, which fails closed"
            )
        return CompatibilityResult(
            compatible=not reasons,
            reasons=list(dict.fromkeys(reasons)),
            warnings=list(dict.fromkeys(warnings)),
        )

    async def submit(self, config):
        check = await self.validate(config)
        if not check.compatible:
            raise ValueError("; ".join(check.reasons))
        return self.store.create_experiment(config)

    async def work_once(self):
        row = self.store.claim_next()
        if row is None:
            return False
        await self.execute(row["id"])
        return True

    def recover(self):
        return self.store.recover()

    def cancel(self, experiment_id):
        row = self.store.get_experiment(experiment_id)
        if row["status"] in {"queued", "running"}:
            self.store.update_experiment(experiment_id, status="cancelled", finished_at=utcnow())
            active = self._active.get(experiment_id)
            if active:
                active.cancel()
        return self.store.get_experiment(experiment_id)

    async def execute(self, experiment_id):
        with self.store.execution_lock(experiment_id) as acquired:
            if not acquired:
                return self.store.get_experiment(experiment_id)
            return await self._execute_owned(experiment_id)

    async def _execute_owned(self, experiment_id):
        if experiment_id in self._active:
            raise ValueError("Experiment already executing")
        row = self.store.get_experiment(experiment_id)
        if row["status"] not in {"queued", "running"}:
            return row
        task = asyncio.create_task(self._execute(experiment_id))
        self._active[experiment_id] = task

        async def observe_cancel():
            while not task.done():
                if self.store.get_experiment(experiment_id)["status"] == "cancelled":
                    task.cancel()
                    return
                await asyncio.sleep(0.05)

        watcher = asyncio.create_task(observe_cancel())
        try:
            await task
        except asyncio.CancelledError:
            current = asyncio.current_task()
            interrupted = bool(current and current.cancelling())
            status = "interrupted" if interrupted else "cancelled"
            for run in self.store.list_runs(experiment_id):
                if run["status"] == "running":
                    self.store.update_run(
                        run["id"],
                        status=status,
                        finished_at=utcnow(),
                        metrics=summarize(self.store.list_results(run["id"])),
                    )
            self.store.update_experiment(experiment_id, status=status, finished_at=utcnow())
            if interrupted:
                raise
        except Exception as exc:
            for run in self.store.list_runs(experiment_id):
                if run["status"] == "running":
                    self.store.update_run(
                        run["id"],
                        status="failed",
                        error=str(exc),
                        finished_at=utcnow(),
                        metrics=summarize(self.store.list_results(run["id"])),
                    )
            self.store.update_experiment(
                experiment_id, status="failed", error=str(exc), finished_at=utcnow()
            )
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
            self._active.pop(experiment_id, None)
        return self.store.get_experiment(experiment_id)

    async def _execute(self, experiment_id):
        from .adapters.registry import execute_system
        from .benchmarks.catalog import get_tasks
        from .plugins import task_environment
        from .verification import verify

        config = ExperimentConfig(**self.store.get_experiment(experiment_id)["config"])
        check = await self.validate(config)
        if not check.compatible:
            raise ValueError("; ".join(check.reasons))
        if self.store.get_experiment(experiment_id)["status"] == "cancelled":
            return
        self.store.update_experiment(experiment_id, status="running", started_at=utcnow())
        tasks = get_tasks(config.benchmark_id, config.task_ids or None)
        deadline = time.monotonic() + config.budget_seconds
        used_tokens = 0
        used_cost = 0.0
        exhausted = None
        environment = dict(
            python=platform.python_version(),
            platform=platform.system(),
            isolation=config.isolation,
            workspace_provider=config.workspace_provider,
            memory_mb=config.memory_mb,
            cpus=config.cpus,
            network=config.network,
            policy_scope="Resource/network limits apply to Docker verification; native agents are privileged host processes and provider HTTP is outside that container policy",
            runtime_versions={
                name: version(name) for name in ["benchlab", "pydantic", "httpx", "fastapi"]
            },
            task_definition_sha256=hashlib.sha256(
                json.dumps([t.model_dump(mode="json") for t in tasks], sort_keys=True).encode()
            ).hexdigest(),
            docker_verifier_image="python:3.12.10-slim"
            if any(t.requires_execution for t in tasks)
            else None,
        )
        for system in config.systems:
            model, agent = self._resolve(system)
            identity = system.agent_id or system.model_id
            assert identity is not None
            for trial in range(1, config.trials + 1):
                condition = dict(
                    benchmark=config.benchmark_id,
                    versions={t.id: t.version for t in tasks},
                    environment=environment,
                    parameters=system.parameters,
                    mode=config.mode,
                    seed=config.seed,
                    max_tokens=config.max_tokens,
                    timeout=config.task_timeout_seconds,
                    budget=config.budget_seconds,
                    retries=config.retries,
                    retry_delay_seconds=config.retry_delay_seconds,
                    max_total_tokens=config.max_total_tokens,
                    max_cost_usd=config.max_cost_usd,
                    controlled_model=model.model_dump(mode="json")
                    if model and config.mode == "agent"
                    else None,
                    tools=config.tools,
                )
                fingerprint = hashlib.sha256(
                    json.dumps(condition, sort_keys=True).encode()
                ).hexdigest()
                manifest = RunManifest(
                    experiment_id=experiment_id,
                    system_id=identity,
                    system_name=system.label or (agent or model).name,
                    system=system,
                    trial=trial,
                    config=config,
                    model=model,
                    agent=agent,
                    task_ids=[t.id for t in tasks],
                    environment=environment,
                    condition_fingerprint=fingerprint,
                    demo=config.demo,
                )
                run = self.store.create_run(experiment_id, manifest)
                rid = run["id"]

                def emit(event, run_id=rid):
                    return self.store.add_event(run_id, event)

                emit(
                    TraceEvent(
                        type="run.started",
                        message="Independent verifier enabled",
                        provenance="demo" if config.demo else "observed",
                    )
                )
                for taskdef in tasks:
                    await asyncio.sleep(0)
                    if self.store.get_experiment(experiment_id)["status"] == "cancelled":
                        raise asyncio.CancelledError
                    started = time.monotonic()
                    output = None
                    error = None
                    attempts = 0
                    category = None
                    workspace = self.store.workspaces_dir / rid / taskdef.id
                    if (
                        not workspace.resolve().is_relative_to(self.store.workspaces_dir.resolve())
                        or workspace.is_symlink()
                    ):
                        raise ValueError("Unsafe task workspace")
                    workspace.mkdir(parents=True, exist_ok=False)
                    async with task_environment(config.workspace_provider, taskdef, workspace):
                        emit(TraceEvent(type="task.started", task_id=taskdef.id))
                        if time.monotonic() >= deadline:
                            exhausted = "Experiment wall-clock budget exhausted"
                        if exhausted:
                            error = exhausted
                            category = "budget"
                        else:
                            for attempt in range(config.retries + 1):
                                if exhausted:
                                    break
                                attempts = attempt + 1
                                output = None
                                remaining = min(
                                    config.task_timeout_seconds, deadline - time.monotonic()
                                )
                                if remaining <= 0:
                                    error = "Experiment wall-clock budget exhausted"
                                    category = "budget"
                                    break
                                try:
                                    async with asyncio.timeout(remaining):
                                        output = await execute_system(
                                            system, model, agent, taskdef, workspace, config, emit
                                        )
                                        if config.max_total_tokens:
                                            if (
                                                output.input_tokens is None
                                                or output.output_tokens is None
                                            ):
                                                exhausted = (
                                                    "Token usage unavailable under enforced budget"
                                                )
                                            else:
                                                used_tokens += (
                                                    output.input_tokens + output.output_tokens
                                                )
                                                if used_tokens >= config.max_total_tokens:
                                                    exhausted = "Token budget exhausted"
                                        if config.max_cost_usd:
                                            if output.cost_usd is None:
                                                exhausted = "Cost unavailable under enforced budget"
                                            else:
                                                used_cost += output.cost_usd
                                                if used_cost >= config.max_cost_usd:
                                                    exhausted = "Cost budget exhausted"
                                        verification = await verify(
                                            taskdef, output, workspace, config
                                        )
                                    error = None
                                    break
                                except asyncio.CancelledError:
                                    self.store.add_result(
                                        rid,
                                        TaskResult(
                                            task_id=taskdef.id,
                                            task_name=taskdef.name,
                                            category=taskdef.category,
                                            status="cancelled",
                                            passed=False,
                                            verification=VerificationResult(
                                                passed=False,
                                                verifier=taskdef.verifier,
                                                reason="Cancelled",
                                                failure_category="cancelled",
                                            ),
                                            duration_seconds=time.monotonic() - started,
                                            attempts=attempts,
                                            failure_category="cancelled",
                                            demo=config.demo,
                                        ),
                                    )
                                    raise
                                except Exception as exc:
                                    error = str(exc) or type(exc).__name__
                                    category = (
                                        "timeout"
                                        if isinstance(exc, TimeoutError)
                                        else "adapter_error"
                                    )
                                    if output is not None:
                                        category = "verifier_error"
                                    emit(
                                        TraceEvent(
                                            type="task.attempt_failed",
                                            task_id=taskdef.id,
                                            message=error,
                                            severity="error",
                                            data={"attempt": attempts},
                                        )
                                    )
                                    if output is not None:
                                        break
                                    if config.max_total_tokens or config.max_cost_usd:
                                        exhausted = "Usage unknown after adapter failure under enforced budget"
                                        break
                                    if attempt < config.retries:
                                        await asyncio.sleep(
                                            min(
                                                config.retry_delay_seconds,
                                                max(0, deadline - time.monotonic()),
                                            )
                                        )
                        if error:
                            verification = VerificationResult(
                                passed=False,
                                verifier=taskdef.verifier,
                                reason=error,
                                failure_category=category,
                            )
                        result = TaskResult(
                            task_id=taskdef.id,
                            task_name=taskdef.name,
                            category=taskdef.category,
                            status="failed" if error else "completed",
                            passed=verification.passed,
                            output=output,
                            verification=verification,
                            duration_seconds=time.monotonic() - started,
                            attempts=attempts,
                            error=error,
                            failure_category=verification.failure_category,
                            demo=config.demo,
                        )
                        self.store.add_result(rid, result)
                        emit(
                            TraceEvent(
                                type="task.finished",
                                task_id=taskdef.id,
                                data={"passed": result.passed, "attempts": attempts},
                            )
                        )
                        if output:
                            self.store.add_artifact(
                                rid,
                                f"{taskdef.id}.json",
                                json.dumps(
                                    output.model_dump(mode="json"), ensure_ascii=False
                                ).encode(),
                                "application/json",
                            )
                if self.store.get_experiment(experiment_id)["status"] == "cancelled":
                    raise asyncio.CancelledError
                metrics = summarize(self.store.list_results(rid))
                self.store.update_run(
                    rid, status="completed", metrics=metrics, finished_at=utcnow()
                )
                emit(TraceEvent(type="run.finished", data=metrics))
        self.store.update_experiment(experiment_id, status="completed", finished_at=utcnow())
