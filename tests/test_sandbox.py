import pytest

from benchlab import sandbox


def test_diagnostics_is_explicit():
    state = sandbox.diagnostics()
    assert isinstance(state["available"], bool)
    assert state["network"] == "none"


@pytest.mark.asyncio
async def test_unavailable_refuses_host_execution(monkeypatch):
    monkeypatch.setattr(sandbox, "diagnostics", lambda: {"available": False})
    with pytest.raises(RuntimeError, match="Docker"):
        await sandbox.run_python("print(1)", "assert True", 1)


@pytest.mark.asyncio
async def test_docker_hardening_and_completion_contract(monkeypatch):
    import asyncio
    import json

    monkeypatch.setattr(sandbox, "diagnostics", lambda: {"available": True, "executable": "docker"})
    calls = []

    class Sink:
        def write(self, data):
            self.data = json.loads(data)

        async def drain(self):
            pass

        def close(self):
            pass

    class Process:
        def __init__(self, args):
            self.returncode = 0
            self.stdin = Sink()
            self.stdout = asyncio.StreamReader()
            self.stderr = asyncio.StreamReader()
            self.stdout.feed_eof()
            self.stderr.feed_eof()

        async def wait(self):
            return self.returncode

        def kill(self):
            self.returncode = -9

    async def create(*args, **kwargs):
        calls.append(args)
        return Process(args)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    result = await sandbox.run_python("import sys;sys.exit(0)", "assert False", 1)
    assert result["exit_code"] == 0 and result["completed"] is False
    args = calls[0]
    for flag in [
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--pull=never",
    ]:
        assert flag in args
    assert "--mount" not in args and "-v" not in args
    assert calls[-1][:3] == ("docker", "rm", "-f")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        "import sys;sys.exit(0)",
        "def dedupe(values): return []",
        'def dedupe(values): raise RuntimeError("boom")',
        "import builtins; builtins.print=lambda *args:None\ndef dedupe(values):return []",
    ],
)
async def test_real_docker_rejects_adversarial_submission(code, tmp_path):
    import os

    if os.environ.get("BENCHLAB_TEST_DOCKER") != "1":
        pytest.skip("Docker runtime requires explicit BENCHLAB_TEST_DOCKER=1")
    from benchlab.benchmarks.catalog import get_tasks
    from benchlab.schemas import AdapterOutput, ExperimentConfig, SystemSpec
    from benchlab.verification import verify

    config = ExperimentConfig(name="sandbox", systems=[SystemSpec(model_id="fixture")])
    assert not (
        await verify(
            get_tasks("starter-v1", ["coding-dedupe"])[0],
            AdapterOutput(text=code),
            tmp_path,
            config,
        )
    ).passed
