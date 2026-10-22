import pytest

from benchlab.analysis import compare_runs, summarize


def test_wilson_and_unobserved():
    m = summarize(
        [
            {"passed": True, "duration_seconds": 1, "output": None},
            {"passed": False, "duration_seconds": 3, "output": None},
        ]
    )
    assert m["success_rate"] == 0.5
    assert m["confidence_low"] == pytest.approx(0.09453, abs=0.0001)
    assert m["median_latency_seconds"] == 2
    assert m["tokens"] is None and m["cost_usd"] is None
    assert m["p95_latency_seconds"] is None
    assert summarize([])["success_rate"] is None


def test_comparison_requires_conditions_and_pairs_exact_tasks(tmp_path):
    from benchlab.schemas import (
        AdapterOutput,
        ExperimentConfig,
        RunManifest,
        SystemSpec,
        TaskResult,
        VerificationResult,
    )
    from benchlab.store import Store

    s = Store(tmp_path)
    config = ExperimentConfig(
        name="compare", demo=True, systems=[SystemSpec(model_id="demo-reference")]
    )
    e = s.create_experiment(config)
    ids = []
    for passed, cost in [(True, 1.0), (False, 2.0)]:
        run = s.create_run(
            e["id"],
            RunManifest(
                experiment_id=e["id"],
                system_id="demo-reference",
                system_name="demo",
                system=config.systems[0],
                config=config,
                condition_fingerprint="same",
                demo=True,
                task_ids=["a"],
            ),
        )
        s.add_result(
            run["id"],
            TaskResult(
                task_id="a",
                category="reasoning",
                passed=passed,
                verification=VerificationResult(passed=passed, verifier="exact"),
                duration_seconds=1,
                output=AdapterOutput(cost_usd=cost),
            ),
        )
        s.update_run(run["id"], status="completed")
        ids.append(run["id"])
    result = compare_runs(s, ids)
    assert result["comparable"]
    assert result["paired_differences"][0]["regressed"] == 1
    assert result["pareto"] == [ids[0]]
    assert not compare_runs(s, [ids[0], ids[0]])["comparable"]


def test_category_and_recovery_metrics_remain_observational():
    results = [
        {
            "passed": True,
            "category": "reasoning",
            "attempts": 2,
            "duration_seconds": 1,
            "output": {"tool_calls": [{"name": "lookup"}]},
        },
        {
            "passed": False,
            "category": "safety",
            "attempts": 1,
            "duration_seconds": 1,
            "output": None,
        },
    ]
    m = summarize(results)
    assert m["by_category"]["reasoning"]["success_rate"] == 1
    assert m["recovery_rate"] == 1
    assert m["failed_calls"] == 2
    assert m["tool_call_count"] is None
    assert summarize([])["recovery_rate"] is None


def test_explicit_ablation_keeps_strict_comparison_false_and_reports_changes(tmp_path):
    from benchlab.schemas import (
        ExperimentConfig,
        RunManifest,
        SystemSpec,
        TaskResult,
        VerificationResult,
    )
    from benchlab.store import Store

    s = Store(tmp_path)
    baseline = ExperimentConfig(
        name="base", demo=True, systems=[SystemSpec(model_id="demo-reference")], task_ids=["a"]
    )
    be = s.create_experiment(baseline)
    treatment = baseline.model_copy(
        deep=True,
        update={"name": "treatment", "mode": "ablation", "baseline_id": be["id"], "retries": 1},
    )
    te = s.create_experiment(treatment)
    ids = []
    for experiment, config, passed in [(be, baseline, False), (te, treatment, True)]:
        r = s.create_run(
            experiment["id"],
            RunManifest(
                experiment_id=experiment["id"],
                system_id="demo-reference",
                system_name="demo",
                system=config.systems[0],
                config=config,
                task_ids=["a"],
                condition_fingerprint=config.name,
                demo=True,
                environment={"isolation": "workspace"},
            ),
        )
        s.add_result(
            r["id"],
            TaskResult(
                task_id="a",
                category="reasoning",
                passed=passed,
                verification=VerificationResult(passed=passed, verifier="exact"),
            ),
        )
        s.update_run(r["id"], status="completed")
        ids.append(r["id"])
    result = compare_runs(s, ids)
    assert not result["comparable"]
    assert result["ablation_analysis"][0]["improved"] == 1
    assert "retries" in {k["path"] for k in result["ablation_analysis"][0]["changed_knobs"]}


def test_budget_starved_runs_not_ranked_as_equal_conditions(tmp_path):
    from benchlab.schemas import (
        ExperimentConfig,
        RunManifest,
        SystemSpec,
        TaskResult,
        VerificationResult,
    )
    from benchlab.store import Store

    s = Store(tmp_path)
    config = ExperimentConfig(
        name="capped", demo=True, systems=[SystemSpec(model_id="demo-reference")]
    )
    e = s.create_experiment(config)
    ids = []
    for starved in [False, True]:
        r = s.create_run(
            e["id"],
            RunManifest(
                experiment_id=e["id"],
                system_id="demo-reference",
                system_name="demo",
                system=config.systems[0],
                config=config,
                task_ids=["a"],
                condition_fingerprint="same",
                demo=True,
            ),
        )
        s.add_result(
            r["id"],
            TaskResult(
                task_id="a",
                category="reasoning",
                passed=not starved,
                verification=VerificationResult(
                    passed=not starved,
                    verifier="exact",
                    failure_category="budget" if starved else None,
                ),
                failure_category="budget" if starved else None,
            ),
        )
        s.update_run(r["id"], status="completed")
        ids.append(r["id"])
    comparison = compare_runs(s, ids)
    assert not comparison["comparable"]
    assert any("budget" in reason.lower() for reason in comparison["reasons"])
