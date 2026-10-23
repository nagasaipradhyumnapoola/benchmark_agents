# Community suggestions

Open **Community** in the website to discover repository-backed recommendations or save an agent, model pairing, or benchmark suggestion. The initial packaged catalog is empty. No scores or compatibility claims are manufactured.

Suggestions are metadata. Saving one never downloads source code, installs an agent, registers an executable, connects a model, or launches a benchmark. Review code, licenses and model compatibility before configuring anything in your own workspace.

## Save and share a suggestion

1. Choose an open-source agent, agent/model pairing, or benchmark suggestion. Enter a title and description. Agent suggestions require a public source-code URL and a license identifier or clear license name. Supply exact model identifiers, one per line; benchmark IDs and public evidence links are optional.
2. Use **Save local draft**. The proposal is saved in this machine's workspace database as a `community_proposal`. It is labeled **Local draft · unverified** and is not publicly visible. This installation does not provide a public multiuser community server or accounts.
3. Download the contribution JSON for review, or choose **Review GitHub submission**. Review the displayed issue title and body before opening GitHub. The title and body are included in the GitHub link, so opening it sends that metadata to GitHub. Never include private material. Nothing is posted automatically.
4. Choose **Open GitHub to submit yourself**, sign in to GitHub if required, review the issue again, and submit it yourself. Your GitHub account and issue follow GitHub's normal public issue visibility. Drafts on your machine are not automatically synchronized with the issue or removed after submission.

Browse public discussion in the [repository issue list](https://github.com/nagasaipradhyumnapoola/benchmark_agents/issues). The issue template is also available from **New issue** on GitHub. Saving a local draft does not create a public issue.

Only share public metadata: no keys, bearer tokens, provider endpoints, credential environment references, allowlists, executable configuration, machine paths, or private code. Source and evidence URLs must use public HTTPS, with no embedded credentials, query or fragment. Literal private addresses and local hostnames are rejected. Links are never fetched by the community API. Basic validation catches obvious secrets, but you must still review the full text before sharing; it cannot identify every private value.

## Contribute an accepted catalog entry

The published catalog lives in [`src/benchlab/community_catalog.json`](../src/benchlab/community_catalog.json). It ships with the application; the page never fetches an online catalog. An accepted issue becomes visible after a maintainer-reviewed pull request updates that file and the user updates this installation.

1. Discuss the suggestion in a repository issue, or propose a pull request directly using the repository's normal contribution process.
2. Download the draft JSON. Its `proposal` object contains only submitted fields. The export's `publication_status` and `verification_status` describe the local draft; they are not catalog fields.
3. Add an object containing a stable unique `id` and the fields from `proposal` to the catalog JSON list. Do not copy the export wrapper, local draft ID/timestamps, share URL, executable configuration or secret fields. Catalog IDs accept letters, digits, underscores and hyphens, up to 128 characters.
4. Have maintainers review source ownership, open-source license, suitability, exact model names and any supplied evidence. Link the public issue in the pull request. Keep the catalog as `[]` when there are no accepted entries.
5. Run `python -m pytest tests/test_community.py` with the project environment and include the relevant evidence in the pull request. Catalog entries are validated on load; missing, malformed, duplicate-ID or unsafe entries return an unavailable error instead of pretending the catalog loaded successfully.

Catalog entry fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable catalog identity, unique within the list |
| `kind` | `agent`, `pairing`, or `benchmark` |
| `title` | Short suggestion title, up to 120 characters |
| `description` | Rationale and intended use, up to 1,500 characters |
| `author_name` | Optional public display name, up to 80 characters |
| `source_url` | Optional public HTTPS source URL; required for agents |
| `license` | Optional license name, up to 100 characters; required for agents |
| `recommended_models` | Up to 12 exact model names, each up to 200 characters |
| `benchmark_ids` | Up to 12 proposed benchmark IDs, each up to 200 characters |
| `evidence_url` | Optional public HTTPS link to contributor-supplied evidence |

Published entries remain **Unverified recommendation**. An evidence link is a contributor's reference, not an independently verified score. Benchmark results must come from the normal evidence-producing experiment workflow. Catalog publication grants no execution permissions.

## Local API

- `GET /api/community` returns `published`, `drafts`, fixed repository and issue/documentation URLs, and a publication explanation. There is no public-server authentication or automatic remote synchronization.
- `POST /api/community` accepts the proposal fields above except `id`, rejects unknown fields, and persists a local draft. It returns the draft's identity, local/unverified labels and the reviewable `share_body`/GitHub `share_url`.
- `GET /api/community/{id}/export` downloads a JSON wrapper with the proposal and local/unverified labels. It excludes store paths, credentials, share URLs and unrelated workspace settings. Missing drafts return 404.

Keep using the application's local host/origin protections. Do not expose the development backend publicly to turn drafts into a shared service.
