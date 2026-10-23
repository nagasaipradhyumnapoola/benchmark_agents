"""SQLite persistence for a standalone source registry; never executes source."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchlab.hub_schemas import AgentRelease, ReportInput, release_digest


class HubError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    try:
        salt = bytes.fromhex(stored.split("$")[4])
        return hmac.compare_digest(_password_hash(password, salt), stored)
    except (ValueError, IndexError):
        return False


class HubStore:
    def __init__(self, data_dir: Path, session_ttl: int = 7 * 24 * 3600):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "hub.sqlite3"
        self.session_ttl = session_ttl
        self._dummy_password = _password_hash(secrets.token_urlsafe(32))
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL REFERENCES users(username),
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
                CREATE TABLE IF NOT EXISTS agents (
                    slug TEXT PRIMARY KEY,
                    owner TEXT NOT NULL REFERENCES users(username),
                    latest_version TEXT NOT NULL,
                    downloads INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS versions (
                    slug TEXT NOT NULL REFERENCES agents(slug),
                    version TEXT NOT NULL,
                    release_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (slug, version)
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT NOT NULL REFERENCES users(username),
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (slug, version) REFERENCES versions(slug, version)
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT NOT NULL REFERENCES users(username),
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (slug, version) REFERENCES versions(slug, version)
                );
            """)

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _session(db: sqlite3.Connection, username: str, ttl: int) -> str:
        token = secrets.token_urlsafe(48)
        now = time.time()
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        db.execute(
            "INSERT INTO sessions(token_hash, username, expires_at) VALUES (?, ?, ?)",
            (hashlib.sha256(token.encode()).hexdigest(), username, now + ttl),
        )
        return token

    def register(self, username: str, password: str) -> dict[str, Any]:
        password_hash = _password_hash(password)
        try:
            with self.connection(write=True) as db:
                db.execute("INSERT INTO users VALUES (?, ?, ?)", (username, password_hash, _now()))
                token = self._session(db, username, self.session_ttl)
        except sqlite3.IntegrityError as exc:
            raise HubError(409, "Username unavailable") from exc
        return {"token": token, "user": {"username": username}}

    def login(self, username: str, password: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
        valid = _password_matches(password, row["password_hash"] if row else self._dummy_password)
        if not valid or row is None:
            raise HubError(401, "Invalid username or password")
        with self.connection(write=True) as db:
            token = self._session(db, username, self.session_ttl)
        return {"token": token, "user": {"username": username}}

    def user_for_token(self, token: str) -> str:
        if len(token) > 200:
            raise HubError(401, "Authentication required")
        with self.connection() as db:
            row = db.execute(
                "SELECT username FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            ).fetchone()
        if row is None:
            raise HubError(401, "Authentication required")
        return str(row["username"])

    def logout(self, token: str) -> None:
        with self.connection(write=True) as db:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )

    @staticmethod
    def _get_version(db: sqlite3.Connection, slug: str, version: str) -> sqlite3.Row:
        row = db.execute(
            "SELECT v.*, a.owner FROM versions v JOIN agents a ON a.slug = v.slug WHERE v.slug = ? AND v.version = ?",
            (slug, version),
        ).fetchone()
        if row is None:
            raise HubError(404, "Agent release not found")
        return row

    @staticmethod
    def _release_detail(row: sqlite3.Row) -> dict[str, Any]:
        source = json.loads(row["release_json"])
        return {
            "slug": row["slug"],
            "owner": row["owner"],
            **source,
            "digest": row["digest"],
            "created_at": row["created_at"],
        }

    def publish(
        self, release: AgentRelease, username: str, *, existing_slug: str | None = None
    ) -> dict[str, Any]:
        slug, version = release.manifest.slug, release.manifest.version
        if existing_slug is not None and existing_slug != slug:
            raise HubError(422, "Manifest slug must match the requested agent")
        digest, created = release_digest(release), _now()
        try:
            with self.connection(write=True) as db:
                agent = db.execute("SELECT owner FROM agents WHERE slug = ?", (slug,)).fetchone()
                if existing_slug is None:
                    if agent is not None:
                        raise HubError(409, "Agent slug already exists")
                    db.execute(
                        "INSERT INTO agents VALUES (?, ?, ?, 0, ?)",
                        (slug, username, version, created),
                    )
                else:
                    if agent is None:
                        raise HubError(404, "Agent not found")
                    if agent["owner"] != username:
                        raise HubError(403, "Only the owner can publish versions")
                db.execute(
                    "INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                    (slug, version, release.model_dump_json(), digest, created),
                )
                db.execute("UPDATE agents SET latest_version = ? WHERE slug = ?", (version, slug))
                row = self._get_version(db, slug, version)
        except sqlite3.IntegrityError as exc:
            raise HubError(409, "Agent version already exists and is immutable") from exc
        return self._release_detail(row)

    def list_agents(
        self, search: str = "", model: str = "", license_name: str = ""
    ) -> dict[str, Any]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT a.*, v.release_json, v.digest FROM agents a JOIN versions v ON v.slug = a.slug AND v.version = a.latest_version ORDER BY a.slug"
            ).fetchall()
        items = []
        for row in rows:
            manifest = json.loads(row["release_json"])["manifest"]
            if (
                search
                and search.casefold()
                not in " ".join(
                    [row["slug"], manifest["name"], manifest["summary"], *manifest["tags"]]
                ).casefold()
            ):
                continue
            if model and model not in manifest["recommended_models"]:
                continue
            if license_name and manifest["license"] != license_name:
                continue
            items.append(
                {
                    "slug": row["slug"],
                    "name": manifest["name"],
                    "summary": manifest["summary"],
                    "owner": row["owner"],
                    "latest_version": row["latest_version"],
                    "digest": row["digest"],
                    "license": manifest["license"],
                    "recommended_models": manifest["recommended_models"],
                    "tags": manifest["tags"],
                    "downloads": row["downloads"],
                }
            )
        return {"items": items, "total": len(items)}

    def agent(self, slug: str) -> dict[str, Any]:
        with self.connection() as db:
            agent = db.execute("SELECT * FROM agents WHERE slug = ?", (slug,)).fetchone()
            if agent is None:
                raise HubError(404, "Agent not found")
            latest = self._get_version(db, slug, agent["latest_version"])
            versions = db.execute(
                "SELECT version, digest, created_at FROM versions WHERE slug = ? ORDER BY rowid DESC",
                (slug,),
            ).fetchall()
        return {
            "slug": slug,
            "owner": agent["owner"],
            "latest_version": agent["latest_version"],
            "manifest": json.loads(latest["release_json"])["manifest"],
            "versions": [dict(row) for row in versions],
            "downloads": agent["downloads"],
        }

    def version(self, slug: str, version: str, *, download: bool = False) -> dict[str, Any]:
        with self.connection(write=download) as db:
            row = self._get_version(db, slug, version)
            if download:
                db.execute("UPDATE agents SET downloads = downloads + 1 WHERE slug = ?", (slug,))
        return self._release_detail(row)

    def comments(
        self, slug: str, version: str, *, author: str | None = None, body: str | None = None
    ) -> dict[str, Any]:
        with self.connection(write=author is not None) as db:
            self._get_version(db, slug, version)
            if author is not None:
                created = _now()
                cursor = db.execute(
                    "INSERT INTO comments(slug, version, author, body, created_at) VALUES (?, ?, ?, ?, ?)",
                    (slug, version, author, body, created),
                )
                return {
                    "id": cursor.lastrowid,
                    "author": author,
                    "body": body,
                    "created_at": created,
                }
            rows = db.execute(
                "SELECT id, author, body, created_at FROM comments WHERE slug = ? AND version = ? ORDER BY id",
                (slug, version),
            ).fetchall()
        return {"items": [dict(row) for row in rows]}

    def reports(
        self,
        slug: str,
        version: str,
        *,
        author: str | None = None,
        report: ReportInput | None = None,
    ) -> dict[str, Any]:
        with self.connection(write=author is not None) as db:
            self._get_version(db, slug, version)
            if author is not None and report is not None:
                created = _now()
                cursor = db.execute(
                    "INSERT INTO reports(slug, version, author, report_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (slug, version, author, report.model_dump_json(), created),
                )
                return {
                    "id": cursor.lastrowid,
                    "author": author,
                    **report.model_dump(mode="json"),
                    "self_reported": True,
                    "created_at": created,
                }
            rows = db.execute(
                "SELECT id, author, report_json, created_at FROM reports WHERE slug = ? AND version = ? ORDER BY id",
                (slug, version),
            ).fetchall()
        return {
            "items": [
                {
                    "id": row["id"],
                    "author": row["author"],
                    **json.loads(row["report_json"]),
                    "self_reported": True,
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        }
