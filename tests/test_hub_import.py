"""Pinned source imports stage code and configuration without executing a release."""

import sys

import pytest

from benchlab.hub_schemas import AgentRelease, release_digest
from benchlab.store import Store


def release():
    return AgentRelease.model_validate(
        {
            "manifest": {
                "slug": "safe-harness",
                "name": "Safe harness",
                "summary": "Local protocol fixture",
                "readme": "Review before executing.",
                "version": "1.0.0",
                "license": "MIT",
                "runtime": "python",
                "entrypoint": "src/agent.py",
                "model_flag": "--model",
                "model_base_url_env": "HARNESS_BASE_URL",
                "model_api_key_env": "HARNESS_API_KEY",
            },
            "files": {"src/agent.py": "raise RuntimeError('must not execute during import')\n"},
        }
    )


def payload(item):
    return {
        **item.model_dump(mode="json"),
        "digest": release_digest(item),
        "slug": item.manifest.slug,
        "owner": "author",
    }


def test_one_click_import_is_pinned_idempotent_and_never_executes_source(tmp_path):
    from benchlab.imports import install_release

    store = Store(tmp_path)
    item = release()
    result = install_release(store, payload(item), "http://127.0.0.1:8100", release_digest(item))
    agent = result["agent"]["config"]
    assert agent["executable"] == sys.executable
    assert agent["model_base_url_env"] == "HARNESS_BASE_URL"
    from pathlib import Path

    path = Path(agent["args"][0])
    assert path.is_relative_to(tmp_path / "imported-agents")
    assert path.read_text() == item.files["src/agent.py"]
    assert (
        install_release(store, payload(item), "http://127.0.0.1:8100", release_digest(item))[
            "agent"
        ]["id"]
        == result["agent"]["id"]
    )
    assert len(store.list_agents()) == 1 and store.list_experiments() == []


@pytest.mark.parametrize("mutation", ["digest", "source", "path"])
def test_tampered_import_never_registers_or_writes_source(tmp_path, mutation):
    from benchlab.imports import install_release

    store = Store(tmp_path)
    item = release()
    data = payload(item)
    if mutation == "digest":
        data["digest"] = "0" * 64
    elif mutation == "source":
        data["files"]["src/agent.py"] = "print('modified')"
    else:
        data["files"] = {"../escape.py": "print('modified')"}
    with pytest.raises(ValueError):
        install_release(store, data, "http://127.0.0.1:8100", release_digest(item))
    assert store.list_agents() == []
    assert not (tmp_path.parent / "escape.py").exists()


def test_reimport_does_not_trust_changed_staged_source(tmp_path):
    from pathlib import Path

    from benchlab.imports import install_release

    store = Store(tmp_path)
    item = release()
    saved = install_release(store, payload(item), "http://127.0.0.1:8100", release_digest(item))
    Path(saved["agent"]["config"]["args"][0]).write_text("print('tampered')")
    with pytest.raises(ValueError, match="modified"):
        install_release(store, payload(item), "http://127.0.0.1:8100", release_digest(item))


@pytest.mark.parametrize("mutation", ["source", "configuration"])
def test_engine_resolution_rejects_edited_imports(tmp_path, mutation):
    from pathlib import Path

    from benchlab.engine import Engine
    from benchlab.imports import install_release
    from benchlab.schemas import AgentConfig, SystemSpec

    store = Store(tmp_path)
    item = release()
    result = install_release(store, payload(item), "http://127.0.0.1:8100", release_digest(item))
    config = result["agent"]["config"]
    system = SystemSpec(agent_id=config["id"])
    assert Engine(store)._resolve(system)[1].id == config["id"]
    if mutation == "source":
        Path(config["args"][0]).write_text("print('modified')")
    else:
        config["args"].append("--changed")
        store.save_agent(AgentConfig.model_validate(config))
    with pytest.raises(ValueError, match="changed"):
        Engine(store)._resolve(system)
