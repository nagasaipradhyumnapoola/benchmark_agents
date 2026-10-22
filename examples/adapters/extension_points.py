"""Trusted environment, verifier and report extensions; run from the source checkout."""

import asyncio
import json
from pathlib import Path

from benchlab.benchmarks.catalog import get_tasks, register_benchmark
from benchlab.plugins import register_environment, register_report_exporter, register_verifier
from benchlab.schemas import ExperimentConfig, SystemSpec, VerificationResult
from benchlab.sdk import Laboratory


class MarkerEnvironment:
    api_version = "1.0"

    async def prepare(self, task, root):
        (root / "provider-marker.txt").write_text("prepared", encoding="utf-8")
        return root

    async def cleanup(self, workspace):
        (workspace / "provider-marker.txt").unlink(missing_ok=True)


class IntegerVerifier:
    api_version = "1.0"

    async def verify(self, task, output, workspace, config):
        passed = output.text.strip() == str(task.expected)
        return VerificationResult(
            passed=passed,
            verifier=task.verifier,
            evidence={"observed": output.text},
            failure_category=None if passed else "verification",
        )


class EvidenceExporter:
    api_version = "1.0"

    def export(self, experiment, runs):
        return json.dumps({"experiment": experiment, "runs": runs}, ensure_ascii=False).encode()


def register_examples(prefix="example"):
    register_environment(prefix + "-environment", MarkerEnvironment())
    register_verifier(prefix + "-integer", IntegerVerifier())
    register_report_exporter(prefix + "-evidence", EvidenceExporter())
    task = get_tasks("starter-v1", ["reasoning-inventory"])[0]
    task.verifier = prefix + "-integer"
    register_benchmark(
        prefix + "-pack",
        [task],
        {"name": "Trusted extension example", "version": "1.0.0", "license": "Apache-2.0"},
    )


async def main():
    register_examples()
    lab = Laboratory(Path(".benchlab/extension-example"))
    result = await lab.run(
        ExperimentConfig(
            name="Trusted extension pipeline example",
            systems=[SystemSpec(model_id="demo-reference")],
            benchmark_id="example-pack",
            workspace_provider="example-environment",
            demo=True,
            isolation="workspace",
        )
    )
    content, _, _ = lab.report(result["id"], "example-evidence")
    print(content.decode())


if __name__ == "__main__":
    asyncio.run(main())
