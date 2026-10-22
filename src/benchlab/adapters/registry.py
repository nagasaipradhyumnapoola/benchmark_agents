"""Concrete provider and explicit native-process adapters; no provider fallback."""

import asyncio
import difflib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import httpx
import psutil

from benchlab.sandbox import _drain
from benchlab.schemas import AdapterOutput, CompatibilityResult, TraceEvent
from benchlab.settings import redact

http_client = httpx.AsyncClient
_MODEL_PLUGINS: dict[str, tuple[Any, Any]] = {}
_AGENT_PLUGINS: dict[str, tuple[Any, Any]] = {}


def _register(registry, names, name, execute, probe, version):
    if version != "1.0":
        raise ValueError("Unsupported adapter contract version")
    if name in names or name in registry:
        raise ValueError("Adapter already registered")
    if not callable(execute) or not callable(probe):
        raise ValueError("Adapter functions must be callable")
    registry[name] = (execute, probe)
    names.add(name)


def register_model_adapter(name, execute, probe, *, version="1.0"):
    _register(_MODEL_PLUGINS, MODEL_ADAPTERS, name, execute, probe, version)


def register_agent_adapter(name, execute, probe, *, version="1.0"):
    _register(_AGENT_PLUGINS, AGENT_ADAPTERS, name, execute, probe, version)


MODEL_ADAPTERS = {"demo", "openai-compatible", "ollama"}
AGENT_ADAPTERS = {"demo", "subprocess", "codex-cli", "opencode-cli"}
# Explicit demonstration fixtures are separate from verifier task.expected.
_DEMO = {
    "reasoning-inventory": "37",
    "knowledge-protocol": "404",
    "multilingual-es": '{"ciudad":"Lima","dia":"martes"}',
    "structured-invoice": '{"invoice_id":"A-17","subtotal":36,"tax":4,"total":40}',
    "tool-weather": '{"tool":"weather","arguments":{"city":"Oslo"}}',
    "multistep-ledger": '{"balances":[75,115,105],"final":105}',
    "recovery-retry": '{"attempts":2,"value":19,"action":"stop"}',
    "safety-boundary": '{"decision":"refuse","reason":"untrusted instruction"}',
    "coding-dedupe": "def dedupe(values):\n    return list(dict.fromkeys(values))",
}


def snapshot_files(workspace):
    result: dict[str, str] = {}
    if not workspace.exists():
        return result
    for path in workspace.rglob("*"):
        if path.is_symlink():
            raise ValueError("Workspace symlinks are not allowed")
        if path.is_file():
            if not path.resolve().is_relative_to(workspace.resolve()):
                raise ValueError("Workspace path escape")
            if path.stat().st_size > 1_000_000:
                continue
            if sum(len(x) for x in result.values()) > 4_000_000:
                raise ValueError("Workspace artifact budget exceeded")
            try:
                result[path.relative_to(workspace).as_posix()] = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
    return result


async def terminate_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.Error:
                pass
    except psutil.Error:
        pass
    if process.returncode is None:
        process.kill()
        await process.wait()


def host_allowed(config):
    return config.allow_host_process and os.environ.get("BENCHLAB_ALLOW_HOST_PROCESS") == "1"


def process_environment(agent, workspace, model=None):
    # Do not inherit HOME/profile/cloud credentials. Explicit allowlist enables only requested variables.
    allowed = {"PATH", "SystemRoot", "WINDIR", "PATHEXT", "COMSPEC", "TEMP", "TMP"} | set(
        agent.env_allowlist
    )
    # Windows normalizes environment keys to uppercase (SYSTEMROOT, WINDIR).
    # SSL initialization needs SystemRoot; preserve names without inheriting profiles.
    result = {
        key: value
        for key, value in os.environ.items()
        if key in allowed or (os.name == "nt" and key.upper() in {name.upper() for name in allowed})
    }
    result.update(
        {
            "HOME": str(workspace),
            "USERPROFILE": str(workspace),
            "CODEX_HOME": str(workspace / ".codex"),
            "XDG_CONFIG_HOME": str(workspace / ".config"),
        }
    )
    if model:
        if agent.model_base_url_env:
            if not model.base_url:
                raise ValueError("Selected model has no base_url to bind to this harness")
            result[agent.model_base_url_env] = model.base_url
        if agent.model_api_key_env and model.api_key_env:
            secret = os.environ.get(model.api_key_env)
            if not secret:
                raise ValueError("Selected model credential environment variable is unset")
            result[agent.model_api_key_env] = secret
    return result


def validate_system_config(system, model, agent, config) -> CompatibilityResult:
    """Static binding validation shared by preflight and execution; no processes or network."""
    reasons = []
    warnings = []
    if (
        config.tools
        and (agent or model)
        and (agent or model).adapter
        in {"demo", "subprocess", "codex-cli", "opencode-cli", "openai-compatible", "ollama"}
    ):
        reasons.append(
            "This adapter does not enforce custom tool allowlists; use a trusted tool-aware adapter"
        )
    if model and model.context_window is not None and config.max_tokens >= model.context_window:
        reasons.append("Output token limit leaves no room for input in the declared context window")
    if agent and agent.adapter in {"subprocess", "codex-cli", "opencode-cli"}:
        if config.isolation != "workspace":
            reasons.append(
                "Native host agents require isolation=workspace; host execution cannot claim Docker isolation"
            )
        if system.parameters:
            reasons.append(
                f"{agent.adapter} does not support SystemSpec.parameters: {sorted(system.parameters)}"
            )
        if model and agent.adapter in {"codex-cli", "opencode-cli"}:
            reasons.append(
                f"{agent.adapter} cannot forward the selected model endpoint or credential configuration; use native mode without model_id and configure the native product explicitly"
            )
        elif model and agent.adapter == "subprocess":
            if not agent.model_flag:
                reasons.append(
                    "A selected subprocess model requires model_flag; otherwise its model selection is ignored"
                )
            elif config.mode not in {"native"} and (
                not agent.model_base_url_env or not model.base_url
            ):
                reasons.append(
                    "Controlled subprocess model binding requires model_base_url_env and a selected model base_url"
                )
            elif config.mode != "native" and model.api_key_env and not agent.model_api_key_env:
                reasons.append(
                    "Controlled credentialed subprocess binding requires model_api_key_env"
                )
            else:
                warnings.append(
                    "Model name and configured environment bindings are forwarded; the native executable owns sampling and seed"
                )
        warnings.append(
            "Native product sampling and experiment seed are not controlled by this adapter"
        )
    elif not agent and model and model.adapter in {"openai-compatible", "ollama"}:
        unsupported = set(system.parameters) - {"temperature", "top_p", "seed"}
        if unsupported:
            reasons.append(f"Unsupported provider parameters: {sorted(unsupported)}")
    return CompatibilityResult(compatible=not reasons, reasons=reasons, warnings=warnings)


def executable_prefix(agent):
    """Resolve known Windows npm shims without handing task text to cmd.exe."""
    executable = agent.executable or {"codex-cli": "codex", "opencode-cli": "opencode"}.get(
        agent.adapter
    )
    if not executable:
        raise ValueError("An executable is required")
    found = shutil.which(executable)
    if not found:
        raise ValueError("Agent executable not found")
    path = Path(found)
    if path.suffix.lower() in {".cmd", ".bat", ".ps1"}:
        if agent.adapter == "codex-cli":
            entry = path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
            node = shutil.which("node")
            if entry.is_file() and node:
                return [node, str(entry)]
        elif agent.adapter == "opencode-cli":
            entry = path.parent / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
            if entry.is_file():
                return [str(entry)]
        raise ValueError(
            "Shell scripts are not supported; configure a native executable or interpreter and script args"
        )
    return [found]


def cli_argv(agent, model, prompt):
    if agent.adapter == "subprocess" and model and not agent.model_flag:
        raise ValueError("A selected subprocess model requires model_flag")
    prefix = executable_prefix(agent)
    if agent.adapter == "codex-cli":
        args = [*prefix, "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check"]
        if model:
            args += ["--model", model.model]
        args += agent.args + [prompt]
    elif agent.adapter == "opencode-cli":
        args = [*prefix, "run", "--format", "json"]
        if model:
            args += ["--model", model.model]
        args += agent.args + [prompt]
    else:
        args = [*prefix, *agent.args]
        if model and agent.model_flag:
            args += [agent.model_flag, model.model]
    return args


def parse_cli(adapter, stdout):
    if adapter == "subprocess":
        return stdout
    messages = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if adapter == "codex-cli" and event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                messages.append(item.get("text", ""))
        elif adapter == "opencode-cli" and event.get("type") == "text":
            messages.append(event.get("part", {}).get("text", ""))
    if not messages:
        raise ValueError("CLI returned no final text events")
    return "\n".join(messages)


async def _provider(model, task, config, parameters):
    if not model.base_url:
        raise ValueError("Provider base_url is required")
    headers = {}
    if model.api_key_env:
        key = os.environ.get(model.api_key_env)
        if not key:
            raise ValueError(f"Credential environment variable {model.api_key_env} is unset")
        headers["Authorization"] = "Bearer " + key
    messages = [{"role": "user", "content": task.prompt}]
    unsupported = set(parameters) - {"temperature", "top_p", "seed"}
    if unsupported:
        raise ValueError(f"Unsupported provider parameters: {sorted(unsupported)}")
    body = {"model": model.model, "messages": messages, "stream": False}
    if model.adapter == "ollama":
        body["options"] = {"num_predict": config.max_tokens, "seed": config.seed, **parameters}
        endpoint = "/api/chat"
    else:
        body.update({"max_tokens": config.max_tokens, "seed": config.seed, **parameters})
        endpoint = "/chat/completions"
    async with http_client(timeout=config.task_timeout_seconds, trust_env=False) as client:
        response = await client.post(model.base_url + endpoint, json=body, headers=headers)
        response.raise_for_status()
        if len(response.content) > 1_000_000:
            raise ValueError("Provider response exceeds size limit")
        data = response.json()
    if model.adapter == "ollama":
        message = data["message"]
        incoming = data.get("prompt_eval_count")
        outgoing = data.get("eval_count")
    else:
        message = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        incoming = usage.get("prompt_tokens")
        outgoing = usage.get("completion_tokens")
    cost = None
    if (
        incoming is not None
        and outgoing is not None
        and model.input_cost_per_million is not None
        and model.output_cost_per_million is not None
    ):
        cost = (
            incoming * model.input_cost_per_million + outgoing * model.output_cost_per_million
        ) / 1_000_000
    return AdapterOutput(
        text=message.get("content") or "",
        tool_calls=message.get("tool_calls") or [],
        input_tokens=incoming,
        output_tokens=outgoing,
        cost_usd=cost,
        metadata={"usage_provenance": "provider-reported"},
    )


async def execute_system(system, model, agent, task, workspace: Path, config, emit):
    compatibility = validate_system_config(system, model, agent, config)
    if not compatibility.compatible:
        raise ValueError("; ".join(compatibility.reasons))
    start = time.monotonic()
    selected = agent or model
    workspace.mkdir(parents=True, exist_ok=True)
    for name, content in task.files.items():
        target = workspace / name
        if target.is_symlink() or not target.resolve().is_relative_to(workspace.resolve()):
            raise ValueError("Unsafe task fixture path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    before = snapshot_files(workspace)
    if selected is None:
        raise ValueError("No configured system")
    emit(
        TraceEvent(
            type="adapter.start",
            task_id=task.id,
            message=f"Executing {selected.adapter}",
            provenance="demo" if selected.demo else "observed",
        )
    )
    plugins = _AGENT_PLUGINS if agent else _MODEL_PLUGINS
    if selected.adapter in plugins:
        return await plugins[selected.adapter][0](
            system, model, agent, task, workspace, config, emit
        )
    if selected.adapter == "demo":
        if not selected.demo:
            raise ValueError("Demo adapter requires demo=true")
        flawed = "flawed" in selected.id or (model and model.model == "flawed")
        if task.id == "workspace-normalize" and not flawed:
            rows = json.loads((workspace / "inventory.json").read_text())
            totals: dict[str, int] = {}
            for row in rows:
                name = row["name"].strip().lower()
                totals[name] = totals.get(name, 0) + row["quantity"]
            (workspace / "normalized.json").write_text(
                json.dumps([{"name": key, "quantity": totals[key]} for key in sorted(totals)])
            )
        output = AdapterOutput(
            text="deliberately incorrect demo answer"
            if flawed
            else _DEMO.get(task.id, "unsupported demo task"),
            metadata={"demo": True},
        )
    elif agent:
        if agent.adapter not in AGENT_ADAPTERS:
            raise ValueError(f"Unsupported agent adapter: {agent.adapter}")
        if not host_allowed(config):
            raise PermissionError(
                "Native execution requires BENCHLAB_ALLOW_HOST_PROCESS=1 and allow_host_process=true"
            )
        workspace.mkdir(parents=True, exist_ok=True)
        args = cli_argv(agent, model, task.prompt)
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=workspace,
            env=process_environment(agent, workspace, model),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdin is not None
        try:
            if agent.adapter == "subprocess":
                process.stdin.write(task.prompt.encode())
                await process.stdin.drain()
            process.stdin.close()
            async with asyncio.timeout(config.task_timeout_seconds):
                stdout, stderr = await asyncio.gather(
                    _drain(process.stdout), _drain(process.stderr)
                )
                await process.wait()
            if process.returncode:
                raise RuntimeError(
                    f"Agent exited with status {process.returncode}: {redact(stderr.decode(errors='replace'))[:1000]}"
                )
            output = AdapterOutput(
                text=parse_cli(agent.adapter, stdout.decode(errors="replace")),
                exit_code=process.returncode,
                metadata={"native_host_process": True},
            )
        finally:
            await terminate_tree(process)
    elif model.adapter in {"openai-compatible", "ollama"}:
        output = await _provider(model, task, config, system.parameters)
    else:
        raise ValueError(f"Unsupported model adapter: {model.adapter}")
    after = snapshot_files(workspace)
    output.files = {name: content for name, content in after.items() if before.get(name) != content}
    for name, content in output.files.items():
        diff = "".join(
            difflib.unified_diff(
                before.get(name, "").splitlines(True),
                content.splitlines(True),
                fromfile=name,
                tofile=name,
            )
        )
        emit(
            TraceEvent(
                type="file.changed",
                task_id=task.id,
                message=f"Workspace file changed: {name}",
                data={"path": name, "diff": redact(diff[:20000])},
                provenance="demo" if selected.demo else "observed",
            )
        )
    output.duration_seconds = time.monotonic() - start
    emit(
        TraceEvent(
            type="adapter.output",
            task_id=task.id,
            message="System returned output",
            data={"text": redact(output.text), "duration_seconds": output.duration_seconds},
            provenance="demo" if selected.demo else "observed",
        )
    )
    return output


async def probe_model(config):
    if config.adapter in _MODEL_PLUGINS:
        return await _MODEL_PLUGINS[config.adapter][1](config)
    if config.adapter not in MODEL_ADAPTERS:
        return CompatibilityResult(compatible=False, reasons=["Unsupported model adapter"])
    if config.adapter == "demo":
        return CompatibilityResult(
            compatible=config.demo,
            reasons=[] if config.demo else ["Demo adapter requires demo=true"],
            warnings=["Deterministic demonstration; not an intelligence measurement"],
        )
    if not config.base_url:
        return CompatibilityResult(compatible=False, reasons=["base_url is required"])
    try:
        headers = {}
        if config.api_key_env:
            if not os.environ.get(config.api_key_env):
                raise ValueError("Credential environment variable is unset")
            headers["Authorization"] = "Bearer " + os.environ[config.api_key_env]
        path = "/api/tags" if config.adapter == "ollama" else "/models"
        async with http_client(timeout=5, trust_env=False) as client:
            result = await client.get(config.base_url + path, headers=headers)
            result.raise_for_status()
            data = result.json()
        models = (
            [m.get("name") for m in data.get("models", [])]
            if config.adapter == "ollama"
            else [m.get("id") for m in data.get("data", [])]
        )
        return CompatibilityResult(
            compatible=config.model in models,
            reasons=[]
            if config.model in models
            else ["Configured model not advertised by endpoint"],
            warnings=["Discovery only; generation and capabilities must be tested"],
        )
    except Exception as exc:
        return CompatibilityResult(compatible=False, reasons=[redact(str(exc))])


async def probe_agent(config):
    if config.adapter in _AGENT_PLUGINS:
        return await _AGENT_PLUGINS[config.adapter][1](config)
    if config.adapter not in AGENT_ADAPTERS:
        return CompatibilityResult(compatible=False, reasons=["Unsupported agent adapter"])
    if config.adapter == "demo":
        return CompatibilityResult(
            compatible=config.demo, warnings=["Deterministic demonstration adapter"]
        )
    try:
        executable_prefix(config)
        reason = []
    except ValueError as exc:
        reason = [str(exc)]
    return CompatibilityResult(
        compatible=not reason,
        reasons=reason,
        warnings=[
            "Executable discovery only; native host execution is privileged and requires two explicit opt-ins"
        ],
        requirements=["BENCHLAB_ALLOW_HOST_PROCESS=1", "Experiment allow_host_process=true"],
    )
