import json

from benchlab.reports import export_experiment
from benchlab.schemas import ExperimentConfig, SystemSpec
from benchlab.store import Store


def test_exports_safe(tmp_path):
    s = Store(tmp_path)
    e = s.create_experiment(
        ExperimentConfig(
            name="<script>alert(1)</script>",
            demo=True,
            systems=[SystemSpec(model_id="demo-reference")],
        )
    )
    data, mime, name = export_experiment(s, e["id"], "html")
    assert b"<script>" not in data and b"&lt;script&gt;" in data
    data, _, _ = export_experiment(s, e["id"], "json")
    assert json.loads(data)["experiment"]["demo"] is True
    data, _, _ = export_experiment(s, e["id"], "zip")
    assert data.startswith(b"PK")


def test_csv_preserves_manifest_uncertainty_and_escapes_formulas(tmp_path):
    import csv
    import io

    s = Store(tmp_path)
    e = s.create_experiment(
        ExperimentConfig(
            name='=HYPERLINK("evil")', demo=True, systems=[SystemSpec(model_id="demo-reference")]
        )
    )
    data, _, _ = export_experiment(s, e["id"], "csv")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[0]["experiment_name"].startswith("'=")
    assert rows[0]["experiment_demo"] == "True"
    assert "manifest" in rows[0] and "confidence_low" in rows[0]
