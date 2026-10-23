"""Local community drafts and a reviewed, repository-backed recommendation catalog.

Links are metadata: this module never fetches sources or registers executable agents.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .schemas import new_id, utcnow
from .store import Store

REPOSITORY_URL = "https://github.com/nagasaipradhyumnapoola/benchmark_agents"
ISSUES_URL = REPOSITORY_URL + "/issues"
CATALOG_PATH = Path(__file__).with_name("community_catalog.json")
PUBLICATION_NOTE = (
    "Drafts stay on this machine until you review and submit a GitHub issue yourself. "
    "Maintainers publish accepted contributions through a reviewed catalog pull request. "
    "Accepted entries appear when this installation receives the catalog update."
)
Text = Annotated[str, Field(min_length=1, max_length=200)]
_SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}|\bBearer\s+\S+|BENCH_AGENTS_SESSION_", re.I)


class MetadataRoute(APIRoute):
    """Validation reports explain the problem without reflecting rejected private values."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_validation(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                errors = [
                    {key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()
                ]
                return JSONResponse(status_code=422, content={"detail": errors})

        return safe_validation


class CommunityProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    kind: Literal["agent", "pairing", "benchmark"]
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1500)
    author_name: str | None = Field(default=None, min_length=1, max_length=80)
    source_url: str | None = Field(default=None, max_length=500)
    license: str | None = Field(default=None, min_length=1, max_length=100)
    recommended_models: list[Text] = Field(default_factory=list, max_length=12)
    benchmark_ids: list[Text] = Field(default_factory=list, max_length=12)
    evidence_url: str | None = Field(default=None, max_length=500)

    @field_validator("source_url", "evidence_url")
    @classmethod
    def public_link(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = urlsplit(value)
            host = (parsed.hostname or "").lower().rstrip(".")
            if (
                parsed.scheme != "https"
                or not host
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or "?" in value
                or "#" in value
                or "\\" in value
                or any(c.isspace() or ord(c) < 32 for c in value)
                or parsed.port not in (None, 443)
            ):
                raise ValueError("Invalid public link")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                labels = host.split(".")
                if (
                    len(labels) < 2
                    or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid"))
                    or not any(c.isalpha() for c in labels[-1])
                    or any(
                        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
                        for label in labels
                    )
                ):
                    raise ValueError("Invalid public hostname") from None
            else:
                if not address.is_global:
                    raise ValueError("Private addresses are not public sources")
        except ValueError:
            raise ValueError(
                "Use a public HTTPS link without credentials, query or fragment"
            ) from None
        return value

    @model_validator(mode="after")
    def safe_metadata(self):
        if self.kind == "agent" and (not self.source_url or not self.license):
            raise ValueError("Agent suggestions require a public source URL and license")
        if _SECRET.search(json.dumps(self.model_dump())):
            raise ValueError("Remove credentials and private credential references before sharing")
        return self


class CatalogEntry(CommunityProposal):
    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


def load_catalog() -> list[dict]:
    """Fail closed on a missing or invalid catalog; never present it as an empty success."""
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Catalog must be a list")
        rows = [CatalogEntry.model_validate(item).model_dump() for item in raw]
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError("Duplicate catalog identity")
    except (OSError, ValueError, ValidationError):
        raise HTTPException(503, "Community catalog is unavailable or invalid") from None
    return [
        dict(row, publication_status="published", verification_status="unverified") for row in rows
    ]


def share_body(proposal: CommunityProposal) -> str:
    return (
        "Community proposal (unverified recommendation). Please review the source, license "
        "and evidence before accepting. This is metadata, not an executable registration.\n\n"
        "```json\n" + json.dumps(proposal.model_dump(), indent=2, ensure_ascii=False) + "\n```"
    )


def draft_view(row: dict) -> dict:
    # Revalidate and project only known metadata; never leak unrelated store fields.
    proposal = CommunityProposal.model_validate(
        {key: row[key] for key in CommunityProposal.model_fields if key in row}
    )
    body = share_body(proposal)
    title = "[Community] " + proposal.title
    share_url = ISSUES_URL + "/new?" + urlencode({"title": title, "body": body})
    requires_paste = len(share_url.encode("ascii")) > 7000
    if requires_paste:
        share_url = ISSUES_URL + "/new?" + urlencode({"title": title})
    return dict(
        proposal.model_dump(),
        id=row["id"],
        created_at=row["created_at"],
        publication_status="local_draft",
        verification_status="unverified",
        share_body=body,
        share_url=share_url,
        share_requires_paste=requires_paste,
    )


def build_community_router(store: Store) -> APIRouter:
    router = APIRouter(prefix="/api/community", tags=["community"], route_class=MetadataRoute)

    @router.get("")
    def community():
        return dict(
            published=load_catalog(),
            drafts=[draft_view(row) for row in store._list("community_proposal")],
            repository_url=REPOSITORY_URL,
            public_issues_url=ISSUES_URL,
            contribution_docs_url=REPOSITORY_URL + "/blob/main/docs/community.md",
            publication_note=PUBLICATION_NOTE,
        )

    @router.post("", status_code=201)
    def suggest(proposal: CommunityProposal):
        row = store._put(
            "community_proposal",
            dict(proposal.model_dump(), id=new_id(), created_at=utcnow()),
        )
        return draft_view(row)

    @router.get("/{proposal_id}/export")
    def export(proposal_id: str):
        try:
            row = store._get("community_proposal", proposal_id)
        except KeyError:
            raise HTTPException(404, "Community draft not found") from None
        view = draft_view(row)
        payload = {key: view[key] for key in CommunityProposal.model_fields}
        return JSONResponse(
            dict(
                schema_version="1.0",
                publication_status="local_draft",
                verification_status="unverified",
                proposal=payload,
            ),
            headers={"Content-Disposition": f'attachment; filename="community-{row["id"]}.json"'},
        )

    return router
