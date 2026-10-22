"""Independent deterministic verifiers. Generated code is never executed on the host."""

import json
from pathlib import Path

import jsonschema

from benchlab import sandbox
from benchlab.schemas import AdapterOutput, ExperimentConfig, TaskDefinition, VerificationResult


async def verify(
    task: TaskDefinition, output: AdapterOutput, workspace: Path, config: ExperimentConfig
) -> VerificationResult:
    evidence = {}
    try:
        from benchlab.plugins import _VERIFIERS

        if task.verifier in _VERIFIERS:
            result = await _VERIFIERS[task.verifier].verify(task, output, workspace, config)
            return VerificationResult.model_validate(result)
        if any(secret in output.text for secret in task.verification_config.get("forbidden", [])):
            raise ValueError("Forbidden content disclosed")
        if task.verifier == "exact":
            passed = output.text.strip() == str(task.expected)
        elif task.verifier in {"json", "schema"}:
            value = json.loads(output.text)
            if "schema" in task.verification_config:
                jsonschema.validate(value, task.verification_config["schema"])
            passed = value == task.expected if task.expected is not None else True
            evidence["parsed"] = value
        elif task.verifier == "file-json":
            target = workspace / task.verification_config["path"]
            if (
                target.is_symlink()
                or not target.resolve().is_relative_to(workspace.resolve())
                or target.stat().st_size > 1_000_000
            ):
                raise ValueError("Unsafe verification artifact")
            value = json.loads(target.read_text())
            passed = value == task.expected
            evidence = {"path": task.verification_config["path"], "observed": value}
        elif task.verifier == "python":
            if config.isolation != "docker":
                raise ValueError("Code verification requires Docker isolation")
            evidence = await sandbox.run_python(
                output.text,
                "import json\nprint(json.dumps([dedupe(case) for case in "
                + repr(task.verification_config["cases"])
                + "]))",
                config.task_timeout_seconds,
                config.memory_mb,
                config.cpus,
            )
            passed = (
                evidence.get("exit_code") == 0
                and evidence.get("completed") is True
                and not evidence.get("timed_out", False)
            )
            if passed:
                observed = json.loads(evidence.get("stdout", ""))
                passed = observed == task.expected
                evidence["observed"] = observed
        else:
            raise ValueError(f"Unknown verifier: {task.verifier}")
        return VerificationResult(
            passed=passed,
            verifier=task.verifier,
            evidence=evidence,
            reason=None if passed else "Output failed independent checks",
            failure_category=None if passed else "verification",
        )
    except Exception as exc:
        return VerificationResult(
            passed=False,
            verifier=task.verifier,
            reason=str(exc),
            evidence=evidence,
            failure_category="verifier_error",
        )
