from fastapi.testclient import TestClient

from benchlab.api import create_app
from benchlab.sdk import Laboratory
from benchlab.store import Store


def test_new_and_reopened_workspaces_never_install_sample_records(tmp_path):
    for _ in range(2):
        store = Store(tmp_path)
        assert store.list_models() == []
        assert store.list_agents() == []
        assert store.list_experiments() == []
        assert store.list_runs() == []


def test_read_only_api_and_cli_startup_leave_workspace_empty(tmp_path):
    with TestClient(create_app(tmp_path, run_worker=False)) as client:
        overview = client.get("/api/overview").json()
        assert overview["models"] == overview["agents"] == overview["experiments"] == []
    assert Laboratory(tmp_path).store.list_models() == []


async def test_demo_records_are_created_only_by_explicit_demo_action(tmp_path):
    lab = Laboratory(tmp_path)
    assert lab.store.list_models() == []
    result = await lab.demo()
    assert result["status"] == "completed"
    assert all(row["demo"] for row in lab.store.list_models())
    assert len(lab.store.list_models()) == 2
    assert lab.store.list_agents() == []
    await lab.demo()
    assert len(lab.store.list_models()) == 2
