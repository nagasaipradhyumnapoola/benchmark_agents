"""Validate and stage an immutable Hub release; importing never executes source."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from benchlab.hub_schemas import AgentRelease, release_digest
from benchlab.schemas import AgentConfig, utcnow


def _contained(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Imported source path escapes its storage directory")
    current = path
    while current != root.parent:
        if current.is_symlink():
            raise ValueError("Imported source paths cannot be symlinks")
        if current == root:
            break
        current = current.parent


def _verify_files(target: Path, release: AgentRelease, root: Path) -> None:
    for name, content in release.files.items():
        path = target / name
        _contained(path, root)
        if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Previously staged source was modified; use a clean release directory")


def verify_import(store, agent: AgentConfig) -> None:
    """Refuse edited imported configuration or source before executing a pinned release."""
    try:
        record = store._get("hub_import", "import-" + agent.id)
    except KeyError:
        return
    if record.get("agent_config") != agent.model_dump(mode="json"):
        raise ValueError(
            "Imported agent configuration changed; import a clean release or register your changes separately"
        )
    source = record["source"]
    root = store.data_dir / "imported-agents"
    target = root / source["slug"] / source["version"] / source["digest"]
    for name, digest in record["file_hashes"].items():
        path = target / name
        _contained(path, root)
        if (
            not path.is_file()
            or path.stat().st_size > 128 * 1024
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(
                "Imported agent source changed; import a clean release or publish a new version"
            )


def install_release(store, payload: dict, hub_url: str, expected_digest: str) -> dict:
    release = AgentRelease.model_validate(
        {"manifest": payload.get("manifest"), "files": payload.get("files")}
    )
    digest = release_digest(release)
    if (
        not re.fullmatch(r"[0-9a-f]{64}", expected_digest)
        or not hmac.compare_digest(digest, expected_digest)
        or not hmac.compare_digest(str(payload.get("digest", "")), digest)
        or payload.get("slug", release.manifest.slug) != release.manifest.slug
    ):
        raise ValueError("Release digest or identity changed; review the selected version again")
    manifest = release.manifest
    root = store.data_dir / "imported-agents"
    _contained(root, store.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / manifest.slug / manifest.version / digest
    _contained(target, root)
    if target.exists():
        _verify_files(target, release, root)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        _contained(target.parent, root)
        stage = Path(tempfile.mkdtemp(prefix="release-", dir=root))
        try:
            for name, content in release.files.items():
                path = stage / name
                _contained(path, root)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode("utf-8"))
            try:
                os.rename(stage, target)
            except OSError:
                if not target.exists():
                    raise
                _verify_files(target, release, root)
        finally:
            if stage.exists():
                _contained(stage, root)
                shutil.rmtree(stage)
    identity = (
        "hub-"
        + hashlib.sha256(
            f"{hub_url}|{manifest.slug}|{manifest.version}|{digest}".encode()
        ).hexdigest()[:32]
    )
    config = AgentConfig(
        id=identity,
        name=f"{manifest.name} {manifest.version}",
        adapter="subprocess",
        executable=sys.executable
        if manifest.runtime == "python"
        else (shutil.which("node") or "node"),
        args=[str((target / manifest.entrypoint).resolve()), *manifest.args],
        model_flag=manifest.model_flag,
        model_base_url_env=manifest.model_base_url_env,
        model_api_key_env=manifest.model_api_key_env,
        capabilities=manifest.capabilities,
        description=f"Imported {manifest.slug}@{manifest.version}; license {manifest.license}; SHA-256 {digest}. Review the source and configure dependencies before authorizing execution.",
    )
    row = store.save_agent(config)
    source = dict(
        slug=manifest.slug,
        version=manifest.version,
        digest=digest,
        hub_url=hub_url,
        license=manifest.license,
    )
    store._put(
        "hub_import",
        dict(
            id="import-" + identity,
            source=source,
            dependencies=manifest.dependencies,
            agent_config=config.model_dump(mode="json"),
            file_hashes={
                name: hashlib.sha256(content.encode("utf-8")).hexdigest()
                for name, content in release.files.items()
            },
            created_at=utcnow(),
        ),
    )
    return dict(agent=row, dependencies=manifest.dependencies, source=source)
