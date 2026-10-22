"""Metric definitions and normalized event taxonomy (observable behavior only)."""

from benchlab.schemas import Metric

FAILURE_CATEGORIES = [
    "model_output_failure",
    "invalid_tool_arguments",
    "tool_environment_failure",
    "context_state_loss",
    "repeated_unsuccessful_action",
    "test_failure",
    "incomplete_implementation",
    "premature_completion",
    "timeout_resource_exhaustion",
    "permission_safety_failure",
    "infrastructure_failure",
    "unknown",
]


def classify_failure(result):
    """Classify confirmed observations conservatively; never invent an internal cause."""
    if result.get("passed"):
        return None
    code = result.get("failure_category")
    family = {
        "verification": "test_failure",
        "timeout": "timeout_resource_exhaustion",
        "budget": "timeout_resource_exhaustion",
        "verifier_error": "tool_environment_failure",
    }.get(code, "unknown")
    return {
        "family": family,
        "observed_code": code,
        "certainty": "observed failure category; underlying cause unconfirmed",
        "evidence": result.get("error") or (result.get("verification") or {}).get("reason"),
    }


def metric_registry() -> list[dict]:
    definitions = [
        (
            "success_rate",
            "Verified success",
            "fraction",
            "Independent verifier passes divided by all attempted tasks, including failures.",
            "calculated",
            True,
        ),
        (
            "duration_seconds",
            "Time to verified result",
            "seconds",
            "Observed execution and verification wall-clock duration.",
            "observed",
            True,
        ),
        (
            "failure_rate",
            "Failure rate",
            "fraction",
            "One minus verified success rate; failed, timed-out and cancelled attempts remain in denominator.",
            "calculated",
            True,
        ),
        (
            "recovery_rate",
            "Recovery rate",
            "fraction",
            "Tasks passing after a recorded failed attempt divided by tasks with failed attempts.",
            "calculated",
            True,
        ),
        (
            "tokens",
            "Token usage",
            "tokens",
            "Provider-reported input and output usage; null if any provider usage is unavailable.",
            "provider-reported",
            True,
        ),
        (
            "cost_usd",
            "Execution cost",
            "USD",
            "Reported usage multiplied by user-provided per-million pricing; null without complete usage/pricing.",
            "estimated",
            True,
        ),
        (
            "cost_per_success_usd",
            "Cost per verified success",
            "USD",
            "Total known cost divided by verified successful tasks, undefined with zero successes or unknown costs.",
            "calculated",
            True,
        ),
        (
            "median_latency_seconds",
            "Median task latency",
            "seconds",
            "Median of observed task execution and verification durations.",
            "calculated",
            True,
        ),
        (
            "p95_latency_seconds",
            "Tail latency",
            "seconds",
            "95th percentile of observed durations; withheld with fewer than 20 samples.",
            "calculated",
            True,
        ),
        (
            "tool_calls",
            "Observed tool calls",
            "count",
            "Tool invocations explicitly emitted by an adapter; text plans are not counted as executed tools.",
            "observed",
            True,
        ),
        (
            "human_interventions",
            "Human interventions",
            "count",
            "Explicit recorded human intervention events; unavailable if the native adapter cannot expose them.",
            "observed",
            False,
        ),
        (
            "cpu_percent",
            "CPU usage",
            "percent",
            "Requires process-scoped sampler; host diagnostics are not run measurements.",
            "unavailable",
            False,
        ),
        (
            "ram_bytes",
            "Peak RAM",
            "bytes",
            "Requires process/container scoped sampler.",
            "unavailable",
            False,
        ),
        (
            "vram_bytes",
            "Peak VRAM",
            "bytes",
            "Requires compatible GPU instrumentation.",
            "unavailable",
            False,
        ),
        (
            "energy_joules",
            "Energy",
            "joules",
            "Requires a calibrated hardware energy meter.",
            "unavailable",
            False,
        ),
        (
            "permission_violations",
            "Permission violations",
            "count",
            "Confirmed denial or policy violation events only; absence is not proof of complete monitoring.",
            "unavailable",
            False,
        ),
    ]
    return [
        Metric(
            id=key,
            name=name,
            unit=unit,
            definition=definition,
            provenance=provenance,
            available=available,
        ).model_dump()
        for key, name, unit, definition, provenance, available in definitions
    ]
