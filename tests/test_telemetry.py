def test_run_event_trace_identity_is_valid_and_consistent(tmp_path):
    from benchlab.schemas import ExperimentConfig, RunManifest, SystemSpec, TraceEvent
    from benchlab.store import Store

    store = Store(tmp_path)
    config = ExperimentConfig(
        name="trace", systems=[SystemSpec(model_id="demo-reference")], demo=True
    )
    experiment = store.create_experiment(config)
    run = store.create_run(
        experiment["id"],
        RunManifest(
            experiment_id=experiment["id"],
            system_id="demo-reference",
            system_name="demo",
            system=config.systems[0],
            config=config,
        ),
    )
    first = store.add_event(run["id"], TraceEvent(type="model.request"))
    second = store.add_event(run["id"], TraceEvent(type="model.response"))
    assert first["trace_id"] == second["trace_id"]
    assert len(first["trace_id"]) == 32 and int(first["trace_id"], 16)
    assert len(first["span_id"]) == 16 and first["span_id"] != second["span_id"]


def test_failure_taxonomy_does_not_invent_root_causes():
    from benchlab.telemetry import classify_failure

    assert classify_failure({"passed": True}) is None
    assert (
        classify_failure({"passed": False, "failure_category": "timeout"})["family"]
        == "timeout_resource_exhaustion"
    )
    assert (
        classify_failure({"passed": False, "failure_category": "adapter_error"})["family"]
        == "unknown"
    )
    assert "unconfirmed" in classify_failure({"passed": False})["certainty"]
