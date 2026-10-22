"""Observed metrics and explicitly conditioned comparisons."""

import math
import statistics
from itertools import combinations

from .telemetry import classify_failure


def _summarize(results):
    n = len(results)
    passed = sum(bool(r.get("passed")) for r in results)
    rate = passed / n if n else None
    low = high = None
    if n:
        assert rate is not None
        z = 1.959963984540054
        d = 1 + z * z / n
        center = (rate + z * z / (2 * n)) / d
        half = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / d
        low = max(0, center - half)
        high = min(1, center + half)
    lat = [r["duration_seconds"] for r in results if r.get("duration_seconds") is not None]
    outputs = [r.get("output") or {} for r in results]
    tokens = (
        sum(o["input_tokens"] + o["output_tokens"] for o in outputs)
        if n
        and all(
            o.get("input_tokens") is not None and o.get("output_tokens") is not None
            for o in outputs
        )
        else None
    )
    cost = (
        sum(o["cost_usd"] for o in outputs)
        if n and all(o.get("cost_usd") is not None for o in outputs)
        else None
    )
    retried = [r for r in results if r.get("attempts", 0) > 1]
    failed_calls = (
        sum(
            max(0, r["attempts"] - 1)
            + int(
                r["attempts"] > 0
                and r.get("output") is None
                and r.get("failure_category") != "cancelled"
            )
            for r in results
        )
        if n and all("attempts" in r for r in results)
        else None
    )
    tool_calls = (
        sum(len(r["output"]["tool_calls"]) for r in results)
        if n and all(r.get("output") is not None and "tool_calls" in r["output"] for r in results)
        else None
    )
    return dict(
        total=n,
        passed=passed,
        failed=n - passed,
        success_rate=rate,
        failure_rate=1 - rate if rate is not None else None,
        confidence_low=low,
        confidence_high=high,
        duration_seconds=sum(lat) if len(lat) == n and n else None,
        median_latency_seconds=statistics.median(lat) if lat else None,
        p95_latency_seconds=sorted(lat)[math.ceil(0.95 * len(lat)) - 1] if len(lat) >= 20 else None,
        tokens=tokens,
        cost_usd=cost,
        cost_per_success_usd=cost / passed if cost is not None and passed else None,
        failed_calls=failed_calls,
        tool_call_count=tool_calls,
        tool_call_provenance="Adapter/provider-reported call records; planning fixtures are not actual tool executions",
        recovery_rate=sum(bool(r.get("passed")) for r in retried) / len(retried)
        if retried
        else None,
        retried_tasks=len(retried),
        failure_classifications=[
            classification for r in results if (classification := classify_failure(r))
        ],
        warning="Small public fixture sample; Wilson interval assumes independent Bernoulli tasks. Demo results do not measure intelligence."
        if n < 30
        else "Wilson interval assumes independent Bernoulli tasks.",
    )


def summarize(results):
    summary = _summarize(results)
    summary["by_category"] = {
        category: _summarize([r for r in results if r.get("category", "uncategorized") == category])
        for category in sorted({r.get("category", "uncategorized") for r in results})
    }
    return summary


def _changed_knobs(before, after, path=""):
    changes = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            if not path and key in {"name", "description", "tags", "baseline_id", "schema_version"}:
                continue
            changes.extend(
                _changed_knobs(before.get(key), after.get(key), f"{path}.{key}" if path else key)
            )
    elif before != after:
        changes.append(dict(path=path, before=before, after=after))
    return changes


def _ablations(store, runs):
    analyses = []
    for candidate in runs:
        cm = candidate["manifest"]
        baseline_id = cm["config"].get("baseline_id")
        if cm["config"].get("mode") != "ablation" or not baseline_id:
            continue
        for baseline in runs:
            bm = baseline["manifest"]
            if baseline["experiment_id"] != baseline_id or baseline["id"] == candidate["id"]:
                continue
            # A multi-system experiment has one treatment pair per system slot.
            # Never attribute another baseline system's outcomes to this treatment.
            baseline_slots = [
                i for i, system in enumerate(bm["config"]["systems"]) if system == bm["system"]
            ]
            candidate_slots = [
                i for i, system in enumerate(cm["config"]["systems"]) if system == cm["system"]
            ]
            if len(baseline_slots) != 1 or baseline_slots != candidate_slots:
                continue
            if (
                baseline["status"] != "completed"
                or candidate["status"] != "completed"
                or bm.get("demo") != cm.get("demo")
                or baseline["trial"] != candidate["trial"]
            ):
                continue
            if (
                any(
                    bm.get(key) != cm.get(key)
                    for key in ["benchmark_version", "task_ids", "environment"]
                )
                or bm["config"]["benchmark_id"] != cm["config"]["benchmark_id"]
            ):
                continue
            aa = {r["task_id"]: r for r in store.list_results(baseline["id"])}
            bb = {r["task_id"]: r for r in store.list_results(candidate["id"])}
            if not aa or aa.keys() != bb.keys() or set(aa) != set(bm["task_ids"]):
                continue
            if any(r.get("failure_category") == "budget" for r in [*aa.values(), *bb.values()]):
                continue
            differences = [int(bb[key]["passed"]) - int(aa[key]["passed"]) for key in aa]
            analyses.append(
                dict(
                    baseline_run_id=baseline["id"],
                    candidate_run_id=candidate["id"],
                    tasks=len(differences),
                    improved=differences.count(1),
                    regressed=differences.count(-1),
                    unchanged=differences.count(0),
                    mean_success_difference=statistics.mean(differences),
                    changed_knobs=_changed_knobs(bm["config"], cm["config"]),
                    warning="Explicit baseline-linked ablation: treatment conditions differ. Observed paired changes do not establish causality; public fixtures and limited trials constrain conclusions.",
                )
            )
    return analyses


def compare_runs(store, run_ids):
    runs = [store.get_run(i) for i in run_ids]
    reasons = []
    rows: list[dict] = []
    summaries = []
    for run in runs:
        result = store.list_results(run["id"])
        if any(
            item.get("failure_category") == "budget"
            or (item.get("verification") or {}).get("failure_category") == "budget"
            for item in result
        ):
            reasons.append(
                "Ordered experiment budget allocation starved a run; these outcomes cannot be ranked as equal execution opportunities"
            )
        metrics = summarize(result)
        summaries.append(
            dict(
                run_id=run["id"],
                system_name=run["system_name"],
                demo=run.get("demo", False),
                **metrics,
            )
        )
        rows.extend(dict(r, system_name=run["system_name"]) for r in result)
    if len(runs) < 2:
        reasons.append("Select at least two runs")
    if len(set(run_ids)) != len(run_ids):
        reasons.append("Choose distinct runs")
    if any(not r["manifest"].get("condition_fingerprint") for r in runs):
        reasons.append("Condition fingerprint unavailable")
    if len({r["manifest"].get("condition_fingerprint") for r in runs}) > 1:
        reasons.append(
            "Conditions differ: benchmark/tasks, environment, parameters, or evaluation mode"
        )
    if any(r["status"] != "completed" for r in runs):
        reasons.append("Runs must be completed")
    if len({r.get("demo", False) for r in runs}) > 1:
        reasons.append("Demo and real observations cannot be compared")
    paired = []
    if not reasons:
        for a, b in combinations(runs, 2):
            aa = {r["task_id"]: r for r in store.list_results(a["id"])}
            bb = {r["task_id"]: r for r in store.list_results(b["id"])}
            if aa.keys() != bb.keys():
                reasons.append("Observed task sets differ")
                continue
            differences = [int(bb[k]["passed"]) - int(aa[k]["passed"]) for k in aa]
            positive = differences.count(1)
            negative = differences.count(-1)
            discordant = positive + negative
            p = (
                min(
                    1,
                    2
                    * sum(math.comb(discordant, i) for i in range(min(positive, negative) + 1))
                    / 2**discordant,
                )
                if discordant
                else 1
            )
            paired.append(
                dict(
                    baseline_run_id=a["id"],
                    candidate_run_id=b["id"],
                    tasks=len(differences),
                    mean_success_difference=statistics.mean(differences) if differences else None,
                    improved=positive,
                    regressed=negative,
                    mcnemar_exact_p=p,
                    warning="Exploratory paired task analysis; no multiple-comparison correction",
                )
            )
    pareto = []
    if not reasons:
        eligible = [
            s
            for s in summaries
            if s["success_rate"] is not None
            and s["cost_usd"] is not None
            and s["median_latency_seconds"] is not None
        ]
        for a in eligible:
            if not any(
                b["success_rate"] >= a["success_rate"]
                and b["cost_usd"] <= a["cost_usd"]
                and b["median_latency_seconds"] <= a["median_latency_seconds"]
                and (
                    b["success_rate"] > a["success_rate"]
                    or b["cost_usd"] < a["cost_usd"]
                    or b["median_latency_seconds"] < a["median_latency_seconds"]
                )
                for b in eligible
            ):
                pareto.append(a["run_id"])
    return dict(
        runs=runs,
        summary=summaries,
        tasks=rows,
        task_rows=rows,
        comparable=not reasons,
        reasons=reasons,
        paired_differences=paired if not reasons else [],
        ablation_analysis=_ablations(store, runs),
        pareto=pareto,
        changes=[
            dict(
                run_id=r["id"],
                condition_fingerprint=r["manifest"].get("condition_fingerprint"),
                parameters=r["manifest"]["system"].get("parameters"),
            )
            for r in runs
        ],
    )
