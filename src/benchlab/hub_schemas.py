"""Portable, bounded contracts shared by the registry and local source importer."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)

MAX_FILES = 40
MAX_FILE_BYTES = 128 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
Slug = Annotated[
    str,
    StringConstraints(
        strict=True, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    ),
]
ShortText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200)]
ListText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200)]
_DEVICES = re.compile(r"^(?:CON|PRN|AUX|NUL|CLOCK\$|COM[0-9]|LPT[0-9])(?:\.|$)", re.I)
_SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|"
    r"\b(?:sk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b|"
    r"(?i:(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key|password)[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"'])|"
    r"(?i:authorization[\"']?\s*[:=]\s*[\"'](?:Bearer|Basic) [A-Za-z0-9_./+=-]{8,}[\"'])"
)


def validate_source_path(path: str) -> str:
    """Accept one portable file path, never a link or a credential container."""
    if not isinstance(path, str) or len(path) > 240 or not re.fullmatch(r"[A-Za-z0-9_./-]+", path):
        raise ValueError("Source paths must be portable relative paths")
    parts = path.split("/")
    for part in parts:
        lower = part.lower()
        if (
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or _DEVICES.match(part)
            or lower
            in {
                ".git",
                ".hg",
                ".svn",
                ".ssh",
                "id_rsa",
                "id_dsa",
                "id_ed25519",
                "credentials",
                "credentials.json",
                "secrets.json",
                ".npmrc",
                ".netrc",
                ".pypirc",
            }
            or lower == ".env"
            or lower.startswith(".env.")
            or lower.endswith((".pem", ".key", ".p12", ".pfx", ".lnk", ".symlink", ".link"))
        ):
            raise ValueError(
                "Source paths cannot contain traversal, reserved names, credentials or links"
            )
    return path


def validate_public_https(value: str | None) -> str | None:
    if value is None:
        return value
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("A public HTTPS URL is required")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("A public HTTPS URL is required")
        if (
            host.lower() in {"localhost", "localhost.localdomain"}
            or "." not in host
            or host.lower().endswith((".localhost", ".local", ".internal"))
        ):
            raise ValueError("A public HTTPS URL is required")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("A public HTTPS URL is required")
        if "\\" in value or any(char.isspace() or ord(char) < 32 for char in value):
            raise ValueError("A public HTTPS URL is required")
    except (ValueError, TypeError) as exc:
        raise ValueError("A public HTTPS URL is required") from exc
    return value


class HubContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AgentManifest(HubContract):
    slug: Slug
    name: ShortText
    summary: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1000)]
    readme: Annotated[str, StringConstraints(strict=True, max_length=65536)]
    version: Annotated[
        str,
        StringConstraints(
            strict=True,
            min_length=5,
            max_length=80,
            pattern=r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$",
        ),
    ]
    license: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=100)]
    runtime: Literal["python", "node"]
    entrypoint: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=240)]
    args: list[Annotated[str, StringConstraints(strict=True, max_length=1000)]] = Field(
        default_factory=list, max_length=40
    )
    model_flag: (
        Annotated[str, StringConstraints(strict=True, pattern=r"^--?[A-Za-z][A-Za-z0-9_-]{0,60}$")]
        | None
    ) = None
    model_base_url_env: (
        Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z_][A-Z0-9_]{0,99}$")] | None
    ) = None
    model_api_key_env: (
        Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z_][A-Z0-9_]{0,99}$")] | None
    ) = None
    capabilities: list[ListText] = Field(
        default_factory=lambda: ["text"], min_length=1, max_length=30
    )
    recommended_models: list[ListText] = Field(default_factory=list, max_length=50)
    benchmark_ids: list[ListText] = Field(default_factory=list, max_length=50)
    source_url: Annotated[str, StringConstraints(strict=True, max_length=2048)] | None = None
    dependencies: list[ListText] = Field(default_factory=list, max_length=100)
    tags: list[ListText] = Field(default_factory=list, max_length=30)

    _entrypoint = field_validator("entrypoint")(validate_source_path)
    _public_source = field_validator("source_url")(validate_public_https)

    @model_validator(mode="after")
    def portable_manifest(self) -> AgentManifest:
        extension = self.entrypoint.rsplit(".", 1)[-1].lower()
        if extension not in ({"py"} if self.runtime == "python" else {"js", "mjs", "cjs"}):
            raise ValueError("Entrypoint extension must match runtime")
        serialized = json.dumps(self.model_dump(mode="json"), ensure_ascii=False)
        if _SECRET.search(serialized.replace('\\"', '"')):
            raise ValueError("Manifest appears to contain inline credentials")
        if any(
            re.match(r"^--?(?:api[-_]?key|password|token|secret)(?:=|$)", arg, re.I)
            for arg in self.args
        ):
            raise ValueError("Use an environment variable for credentials")
        return self


class AgentRelease(HubContract):
    manifest: AgentManifest
    files: dict[str, str] = Field(min_length=1, max_length=MAX_FILES)

    @model_validator(mode="after")
    def safe_source(self) -> AgentRelease:
        total = 0
        folded: set[str] = set()
        for path, content in self.files.items():
            validate_source_path(path)
            if path.casefold() in folded:
                raise ValueError("Source paths must be unique across case-insensitive filesystems")
            folded.add(path.casefold())
            try:
                size = len(content.encode("utf-8"))
            except UnicodeError as exc:
                raise ValueError("Source must be valid UTF-8 text") from exc
            if (
                any(ord(char) < 32 and char not in "\t\n\r" for char in content)
                or size > MAX_FILE_BYTES
            ):
                raise ValueError("Each source file must be text of at most 128 KiB")
            total += size
            if _SECRET.search(content):
                raise ValueError("Source appears to contain inline credentials")
        if total > MAX_SOURCE_BYTES:
            raise ValueError("Combined source must be at most 1 MiB")
        if self.manifest.entrypoint not in self.files:
            raise ValueError("Entrypoint must exist in source files")
        if any(
            any(other.casefold().startswith(path.casefold() + "/") for other in self.files)
            for path in self.files
        ):
            raise ValueError("A source path cannot be both a file and a directory")
        return self


def release_digest(release: AgentRelease) -> str:
    """Digest the fully validated contract, including explicit default values."""
    validated = AgentRelease.model_validate(release.model_dump(mode="json"))
    content = json.dumps(
        validated.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class AuthCredentials(HubContract):
    username: Annotated[
        str,
        StringConstraints(
            strict=True, min_length=3, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$"
        ),
    ]
    password: SecretStr = Field(min_length=12, max_length=256)


class CommentInput(HubContract):
    body: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4000)]

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Comment must contain text")
        if _SECRET.search(value):
            raise ValueError("Comment appears to contain inline credentials")
        return value


class ReportInput(HubContract):
    model: ShortText
    benchmark_id: ShortText
    passed: Annotated[int, Field(strict=True, ge=0, le=1000000)]
    total: Annotated[int, Field(strict=True, ge=1, le=1000000)]
    evidence_url: Annotated[str, StringConstraints(strict=True, max_length=2048)] | None = None

    _public_evidence = field_validator("evidence_url")(validate_public_https)

    @model_validator(mode="after")
    def valid_result(self) -> ReportInput:
        if self.passed > self.total:
            raise ValueError("Passed cannot exceed total")
        if _SECRET.search(json.dumps(self.model_dump(mode="json"))):
            raise ValueError("Report appears to contain inline credentials")
        return self
