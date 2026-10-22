import json

from typer.testing import CliRunner

runner = CliRunner()


def test_cli_catalog_and_demo_share_storage(tmp_path, monkeypatch):
    from benchlab.cli import app

    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path))
    response = runner.invoke(app, ["models", "list"])
    assert response.exit_code == 0, response.output
    assert len(json.loads(response.stdout)) >= 2
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
