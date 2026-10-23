"""Transactional local records and contained artifacts."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .schemas import new_id, utcnow
from .settings import redact


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = self.data_dir / "artifacts"
        self.workspaces_dir = self.data_dir / "workspaces"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.workspaces_dir.mkdir(exist_ok=True)
        self.db = self.data_dir / "bench-agents.sqlite3"
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT PRIMARY KEY,parent TEXT,payload TEXT NOT NULL)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS records_kind_parent ON records(kind,parent)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _exists(self, id):
        with self._connect() as db:
            return db.execute("SELECT 1 FROM records WHERE id=?", (id,)).fetchone() is not None

    def _list(self, kind, parent=None):
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload FROM records WHERE kind=? AND (? IS NULL OR parent=?) ORDER BY rowid",
                (kind, parent, parent),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def _get(self, kind, id):
        with self._connect() as db:
            row = db.execute(
                "SELECT payload FROM records WHERE kind=? AND id=?", (kind, id)
            ).fetchone()
        if row is None:
            raise KeyError(id)
        return json.loads(row[0])

    def _put(self, kind, row, parent=None):
        row = redact(row)
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records VALUES(?,?,?,?)",
                (kind, row["id"], parent, json.dumps(row, allow_nan=False)),
            )
        return row

    def _save_config(self, kind, config):
        if self._exists(config.id):
            old = self._get(kind, config.id)
            if old["config"] == config.model_dump(mode="json"):
                return old
            self._check_unused(config.id)
        now = utcnow()
        return self._put(
            kind,
            dict(
                id=config.id,
                name=config.name,
                config=config.model_dump(mode="json"),
                demo=config.demo,
                created_at=now,
                updated_at=now,
            ),
        )

    def _check_unused(self, id):
        for e in self.list_experiments():
            if any(id in (s.get("model_id"), s.get("agent_id")) for s in e["config"]["systems"]):
                raise ValueError(
                    "Historical configuration identity is immutable; register a new ID"
                )

    def _delete(self, kind, id):
        self._get(kind, id)
        self._check_unused(id)
        with self._connect() as db:
            db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, id))

    def list_models(self):
        return self._list("model")

    def get_model(self, id):
        return self._get("model", id)

    def save_model(self, config):
        return self._save_config("model", config)

    def delete_model(self, id):
        return self._delete("model", id)

    def list_agents(self):
        return self._list("agent")

    def get_agent(self, id):
        return self._get("agent", id)

    def save_agent(self, config):
        return self._save_config("agent", config)

    def delete_agent(self, id):
        return self._delete("agent", id)

    def create_experiment(self, config):
        now = utcnow()
        return self._put(
            "experiment",
            dict(
                id=new_id(),
                name=config.name,
                mode=config.mode,
                status="queued",
                config=config.model_dump(mode="json"),
                demo=config.demo,
                created_at=now,
                updated_at=now,
            ),
        )

    def list_experiments(self):
        return self._list("experiment")

    def get_experiment(self, id):
        return self._get("experiment", id)

    def update_experiment(self, id, **fields):
        return self._update(
            "experiment", id, fields, {"status", "error", "started_at", "finished_at"}
        )

    def _update(self, kind, id, fields, allowed):
        if fields.keys() - allowed:
            raise ValueError("Immutable or unknown fields")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            record = db.execute(
                "SELECT payload FROM records WHERE kind=? AND id=?", (kind, id)
            ).fetchone()
            if record is None:
                raise KeyError(id)
            row = json.loads(record[0])
            terminal = {"completed", "failed", "cancelled", "interrupted"}
            if (
                row.get("status") in terminal
                and fields.get("status", row["status"]) != row["status"]
            ):
                return row
            row.update(redact(fields))
            row["updated_at"] = utcnow()
            db.execute(
                "UPDATE records SET payload=? WHERE kind=? AND id=?",
                (json.dumps(row, allow_nan=False), kind, id),
            )
        return row

    def create_run(self, experiment_id, manifest):
        self.get_experiment(experiment_id)
        return self._put(
            "run",
            dict(
                id=new_id(),
                experiment_id=experiment_id,
                system_id=manifest.system_id,
                system_name=manifest.system_name,
                trial=manifest.trial,
                status="running",
                manifest=manifest.model_dump(mode="json"),
                metrics={},
                error=None,
                started_at=utcnow(),
                finished_at=None,
                demo=manifest.demo,
            ),
            experiment_id,
        )

    def list_runs(self, experiment_id=None):
        return self._list("run", experiment_id)

    def get_run(self, id):
        return self._get("run", id)

    def update_run(self, id, **fields):
        return self._update(
            "run", id, fields, {"status", "metrics", "error", "started_at", "finished_at"}
        )

    def add_event(self, run_id, event):
        self.get_run(run_id)
        event = event.model_copy(
            update={"trace_id": hashlib.sha256(run_id.encode()).hexdigest()[:32]}
        )
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            sequence = (
                db.execute(
                    "SELECT COUNT(*) FROM records WHERE kind='event' AND parent=?", (run_id,)
                ).fetchone()[0]
                + 1
            )
            row = redact(
                dict(event.model_dump(mode="json"), id=new_id(), run_id=run_id, sequence=sequence)
            )
            db.execute(
                "INSERT INTO records VALUES(?,?,?,?)", ("event", row["id"], run_id, json.dumps(row))
            )
        return row

    def list_events(self, run_id, after=0):
        self.get_run(run_id)
        return [e for e in self._list("event", run_id) if e["sequence"] > after]

    def add_result(self, run_id, result):
        self.get_run(run_id)
        return self._put(
            "result", dict(result.model_dump(mode="json"), id=new_id(), run_id=run_id), run_id
        )

    def list_results(self, run_id):
        self.get_run(run_id)
        return self._list("result", run_id)

    def _safe_path(self, root, path):
        root = Path(root)
        if (
            root.is_symlink()
            or path.is_symlink()
            or any(p.is_symlink() for p in path.parents if p != root.parent)
        ):
            raise ValueError("Symlink rejected")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Path escapes storage")
        return path

    def add_artifact(self, run_id, name, content, media_type="text/plain"):
        self.get_run(run_id)
        if not name or "/" in name or "\\" in name or ":" in name or name in {".", ".."}:
            raise ValueError("Unsafe artifact name")
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("Artifact exceeds 10 MiB")
        try:
            content = redact(content.decode("utf-8")).encode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Only auditable UTF-8 artifacts are supported") from None
        id = new_id()
        folder = self._safe_path(self.artifacts_dir, self.artifacts_dir / run_id)
        folder.mkdir(exist_ok=True)
        path = self._safe_path(self.artifacts_dir, folder / id)
        path.write_bytes(content)
        return self._put(
            "artifact",
            dict(
                id=id,
                run_id=run_id,
                name=name,
                media_type=media_type,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                created_at=utcnow(),
            ),
            run_id,
        )

    def list_artifacts(self, run_id):
        self.get_run(run_id)
        return self._list("artifact", run_id)

    def artifact_path(self, run_id, artifact_id):
        if not any(a["id"] == artifact_id for a in self.list_artifacts(run_id)):
            raise KeyError(artifact_id)
        return self._safe_path(self.artifacts_dir, self.artifacts_dir / run_id / artifact_id)

    def claim_next(self):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for id, payload in db.execute(
                "SELECT id,payload FROM records WHERE kind='experiment' ORDER BY rowid"
            ):
                row = json.loads(payload)
                if row["status"] == "queued":
                    row.update(status="running", started_at=utcnow(), updated_at=utcnow())
                    db.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(row), id))
                    return row
        return None

    @contextmanager
    def execution_lock(self, experiment_id):
        """OS-released ownership survives neither a crash nor process termination."""
        self.get_experiment(experiment_id)
        directory = self.data_dir / "locks"
        directory.mkdir(exist_ok=True)
        filename = directory / (hashlib.sha256(experiment_id.encode()).hexdigest() + ".lock")
        self._safe_path(self.data_dir, filename)
        handle = filename.open("a+b")
        handle.seek(0)
        if filename.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        acquired = False
        try:
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl = importlib.import_module("fcntl")
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError:
                pass
            yield acquired
        finally:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl = importlib.import_module("fcntl")
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def recover(self):
        count = 0
        for e in self.list_experiments():
            with self.execution_lock(e["id"]) as acquired:
                if not acquired:
                    continue
                current = self.get_experiment(e["id"])
                if current["status"] == "running":
                    self.update_experiment(
                        e["id"],
                        status="interrupted",
                        error="Process interrupted",
                        finished_at=utcnow(),
                    )
                    count += 1
                for r in self.list_runs(e["id"]):
                    if r["status"] == "running":
                        self.update_run(
                            r["id"],
                            status="cancelled"
                            if current["status"] == "cancelled"
                            else "interrupted",
                            error="Process interrupted",
                            finished_at=utcnow(),
                        )
        return count
