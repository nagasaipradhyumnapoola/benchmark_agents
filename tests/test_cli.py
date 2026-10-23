import json

from typer.testing import CliRunner

runner = CliRunner()


def test_cli_catalog_and_demo_share_storage(tmp_path, monkeypatch):
    from benchlab.cli import app

    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path))
    response = runner.invoke(app, ["models", "list"])
    assert response.exit_code == 0, response.output
    assert json.loads(response.stdout) == []
    demo = runner.invoke(app, ["demo"])
    assert demo.exit_code == 0, demo.output
    experiment = json.loads(demo.stdout)
    listing = runner.invoke(app, ["experiments", "list"])
    assert experiment["id"] in listing.stdout
    report = runner.invoke(app, ["report", experiment["id"], "--format", "json"])
    assert report.exit_code == 0
    assert "demo" in report.stdout.lower()


def test_cli_invalid_run_is_nonzero(tmp_path, monkeypatch):
    from benchlab.cli import app

    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path))
    result = runner.invoke(app, ["run", "--model", "not-registered"])
    assert result.exit_code != 0


def test_hub_command_runs_only_the_standalone_registry(monkeypatch):
    import uvicorn

    from benchlab.cli import app

    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    result = runner.invoke(app, ["hub", "--port", "8102"])
    assert result.exit_code == 0, result.output
    assert calls == [
        (("benchlab.hub:app_factory",), {"factory": True, "host": "127.0.0.1", "port": 8102})
    ]


def test_default_registry_child_does_not_inherit_provider_credentials(tmp_path, monkeypatch):
    import subprocess

    import httpx

    from benchlab.cli import _start_local_hub

    monkeypatch.setenv("BENCH_AGENTS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("BENCH_AGENTS_HUB_URL", raising=False)
    monkeypatch.delenv("BENCHLAB_HUB_URL", raising=False)
    monkeypatch.setenv("PROVIDER_API_KEY", "private-key-for-the-lab-only")
    monkeypatch.setenv("UNRELATED_SECRET", "not-for-a-registry-child")
    monkeypatch.setattr(
        httpx.Client, "get", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("offline"))
    )
    captured = {}
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: captured.update(kw) or object())
    _start_local_hub()
    leaked_names = {"PROVIDER_API_KEY", "UNRELATED_SECRET"} & set(captured["env"])
    assert not leaked_names
    assert captured["env"]["BENCH_AGENTS_HUB_DATA_DIR"] == str(tmp_path / "hub")
