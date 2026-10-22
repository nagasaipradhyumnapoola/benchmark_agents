"""Portable reports; demo provenance and failed tasks remain visible."""

import csv
import html
import io
import json
import zipfile

from .analysis import summarize
from .settings import redact


def export_experiment(store, experiment_id, format):
    experiment = store.get_experiment(experiment_id)
    runs = []
    for run in store.list_runs(experiment_id):
        results = store.list_results(run["id"])
        runs.append(
            dict(
                run,
                results=results,
                events=store.list_events(run["id"]),
                artifacts=store.list_artifacts(run["id"]),
                summary=summarize(results),
            )
        )
    payload = redact(
        dict(
            experiment=experiment,
            runs=runs,
            methodology="Independent deterministic verification; demo observations are pipeline tests, not intelligence measurements. Unavailable metrics are null. Wilson intervals assume independent tasks.",
        )
    )
    name = f"benchlab-{experiment_id}"
    from .plugins import _EXPORTERS

    if format in _EXPORTERS:
        # Plugins receive the same redacted payload as built-in exporters.
        return (
            _EXPORTERS[format].export(payload["experiment"], payload["runs"]),
            "application/octet-stream",
            name + ".bin",
        )
    if format == "json":
        return (
            json.dumps(payload, indent=2, ensure_ascii=False).encode(),
            "application/json",
            name + ".json",
        )
    if format == "csv":
        output = io.StringIO(newline="")
        columns = [
            "record_type",
            "experiment_id",
            "experiment_name",
            "experiment_demo",
            "experiment_config",
            "methodology",
            "run_id",
            "system",
            "demo",
            "task_id",
            "passed",
            "status",
            "duration_seconds",
            "failure_category",
            "error",
            "manifest",
            "events",
            "artifacts",
            "summary",
            "confidence_low",
            "confidence_high",
            "output",
            "verification",
        ]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        def safe(v):
            if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                return "'" + v
            return v

        base = dict(
            experiment_id=experiment_id,
            experiment_name=payload["experiment"]["name"],
            experiment_demo=experiment["demo"],
            experiment_config=json.dumps(payload["experiment"]["config"], ensure_ascii=False),
            methodology=payload["methodology"],
        )
        records = []
        for run in payload["runs"]:
            run_base = dict(
                base,
                run_id=run["id"],
                system=run["system_name"],
                demo=run["demo"],
                manifest=json.dumps(run["manifest"], ensure_ascii=False),
                events=json.dumps(run["events"], ensure_ascii=False),
                artifacts=json.dumps(run["artifacts"], ensure_ascii=False),
                summary=json.dumps(run["summary"]),
                confidence_low=run["summary"]["confidence_low"],
                confidence_high=run["summary"]["confidence_high"],
            )
            for result in run["results"]:
                record = dict(run_base, record_type="task")
                record.update(
                    {
                        key: result.get(key)
                        for key in [
                            "task_id",
                            "passed",
                            "status",
                            "duration_seconds",
                            "failure_category",
                            "error",
                        ]
                    }
                )
                record.update(
                    output=json.dumps(result.get("output"), ensure_ascii=False),
                    verification=json.dumps(result["verification"], ensure_ascii=False),
                )
                records.append(record)
            if not run["results"]:
                records.append(dict(run_base, record_type="run", status=run["status"]))
        if not records:
            records.append(dict(base, record_type="experiment", status=experiment["status"]))
        for record in records:
            writer.writerow({key: safe(value) for key, value in record.items()})
        return output.getvalue().encode("utf-8-sig"), "text/csv", name + ".csv"
    if format == "html":
        text = (
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>BenchLab report</title><body><h1>'
            + html.escape(experiment["name"])
            + "</h1><p>"
            + (
                "DEMONSTRATION — pipeline test only"
                if experiment["demo"]
                else "Observed benchmark experiment"
            )
            + "</p><pre>"
            + html.escape(json.dumps(payload, indent=2, ensure_ascii=False))
            + "</pre></body></html>"
        )
        return text.encode(), "text/html", name + ".html"
    if format == "zip":
        zip_output = io.BytesIO()
        with zipfile.ZipFile(zip_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for kind in ["json", "csv", "html"]:
                data, _, filename = export_experiment(store, experiment_id, kind)
                archive.writestr(filename, data)
            for run in runs:
                for artifact in run["artifacts"]:
                    content = store.artifact_path(run["id"], artifact["id"]).read_bytes()
                    archive.writestr(
                        "artifacts/" + run["id"] + "/" + artifact["id"] + ".txt",
                        redact(content.decode("utf-8")).encode(),
                    )
        return zip_output.getvalue(), "application/zip", name + ".zip"
    raise ValueError("Supported formats: json, csv, html, zip")
