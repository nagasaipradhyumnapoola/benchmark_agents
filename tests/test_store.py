import pytest

from benchlab.schemas import ExperimentConfig, RunManifest, SystemSpec, TraceEvent
from benchlab.service import install_demo_inventory
from benchlab.store import Store


def test_store_durable_seed_queue_events_artifacts(tmp_path):
    s = Store(tmp_path)
    assert s.list_models() == []
    install_demo_inventory(s)
    assert len(s.list_models()) == 2
    c = ExperimentConfig(name="test", systems=[SystemSpec(model_id="demo-reference")], demo=True)
    e = s.create_experiment(c)
    assert Store(tmp_path).claim_next()["id"] == e["id"]
    assert s.claim_next() is None
    r = s.create_run(
        e["id"],
        RunManifest(
            experiment_id=e["id"],
            system_id="demo-reference",
            system_name="demo",
            system=c.systems[0],
            config=c,
        ),
    )
    assert [s.add_event(r["id"], TraceEvent(type="test"))["sequence"] for _ in range(3)] == [
        1,
        2,
        3,
    ]
    a = s.add_artifact(r["id"], "result.txt", b"hello")
    assert s.artifact_path(r["id"], a["id"]).read_bytes() == b"hello"
    with pytest.raises(ValueError):
        s.add_artifact(r["id"], "../escape", b"x")
    with pytest.raises(ValueError):
        s.update_run(r["id"], manifest={})
    assert s.recover() == 1
    assert s.get_experiment(e["id"])["status"] == "interrupted"


def test_history_identity_cannot_change(tmp_path):
    s = Store(tmp_path)
    install_demo_inventory(s)
    c = ExperimentConfig(name="test", systems=[SystemSpec(model_id="demo-reference")])
    s.create_experiment(c)
    model = s.get_model("demo-reference")["config"]
    from benchlab.schemas import ModelConfig

    model["name"] = "changed"
    with pytest.raises(ValueError):
        s.save_model(ModelConfig(**model))


def test_artifact_redaction_and_symlink_rejected(tmp_path):
    s = Store(tmp_path)
    c = ExperimentConfig(name="test", systems=[SystemSpec(model_id="demo-reference")])
    e = s.create_experiment(c)
    r = s.create_run(
        e["id"],
        RunManifest(
            experiment_id=e["id"],
            system_id="demo-reference",
            system_name="demo",
            system=c.systems[0],
            config=c,
        ),
    )
    a = s.add_artifact(r["id"], "secret.txt", b"Bearer abcdefghijk")
    assert b"abcdefghijk" not in s.artifact_path(r["id"], a["id"]).read_bytes()
    with pytest.raises(ValueError):
        s.add_artifact(r["id"], "large.txt", b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(KeyError):
        s.artifact_path(r["id"], "../../escape")


def test_claim_is_transactional(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    s = Store(tmp_path)
    s.create_experiment(
        ExperimentConfig(name="test", systems=[SystemSpec(model_id="demo-reference")])
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda _: s.claim_next(), range(4)))
    assert sum(r is not None for r in rows) == 1


def test_terminal_cancel_cannot_be_overwritten_by_stale_worker(tmp_path):
    s = Store(tmp_path)
    e = s.create_experiment(
        ExperimentConfig(name="cancel", systems=[SystemSpec(model_id="demo-reference")])
    )
    s.update_experiment(e["id"], status="cancelled")
    assert s.update_experiment(e["id"], status="completed")["status"] == "cancelled"
    assert Store(tmp_path).get_experiment(e["id"])["status"] == "cancelled"
