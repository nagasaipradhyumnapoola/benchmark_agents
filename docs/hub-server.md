# Self-hosting Agent Hub

Agent Hub is a separate source registry. It accepts versioned text-source agents, account comments, and explicitly self-reported benchmark summaries. It starts with no accounts, agents, comments, or reports. It never loads models, installs agent dependencies, runs uploaded code, or exposes the private Lab API and its credentials or result files.

Run the registry on the local loopback interface:

```powershell
bench-agents hub
```

The default registry URL is `http://127.0.0.1:8100`. You can also use the application factory directly:

```powershell
uvicorn benchlab.hub:app_factory --factory --host 127.0.0.1 --port 8100
```

Run the Lab separately and configure `BENCH_AGENTS_HUB_URL` there when connecting to another registry. The Lab's `/api/hub/*` routes proxy the registry; its browser account cookie is HttpOnly and does not expose registry tokens to browser JavaScript. The standalone registry uses `/v1/*` only and does not host the Lab's model or execution routes.

## Storage and configuration

The registry creates `hub.sqlite3` in `BENCH_AGENTS_HUB_DATA_DIR`, defaulting to `.bench-agents/hub`. The factory accepts an explicit `Path` for isolated applications and tests. Keep this directory private to the service account, outside publicly served directories. Back up the database using SQLite's backup facilities or stop the service before copying it. Registry data is separate from Lab state and imported source.

| Setting | Default | Purpose |
| --- | --- | --- |
| `BENCH_AGENTS_HUB_DATA_DIR` | `.bench-agents/hub` | Registry database directory |
| `BENCH_AGENTS_HUB_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1],testserver` | Comma-separated trusted HTTP hostnames |
| `BENCH_AGENTS_HUB_ALLOWED_ORIGINS` | Loopback HTTP origins on ports 8100 and 3000 | Exact browser origins allowed to send requests |
| `BENCH_AGENTS_HUB_SESSION_TTL_SECONDS` | `604800` (7 days) | Session lifetime; 300 through 2592000 seconds |

`testserver` permits local application tests. Replace the default host list when exposing the registry. Neither host nor origin configuration accepts a bare wildcard. Requests without an `Origin` header are accepted for service-to-service clients; the host check still applies. An origin allowlist is a browser boundary, not authentication.

## HTTPS deployment

Put the registry behind an HTTPS reverse proxy and bind its process to a private interface. Expose only the registry port through that proxy. Do not proxy the private Lab port or `.bench-agents` directory publicly.

For example, configure the registry process with:

```powershell
$env:BENCH_AGENTS_HUB_ALLOWED_HOSTS = "hub.example.com"
$env:BENCH_AGENTS_HUB_ALLOWED_ORIGINS = "https://hub.example.com"
$env:BENCH_AGENTS_HUB_DATA_DIR = "D:/private-agent-hub"
uvicorn benchlab.hub:app_factory --factory --host 127.0.0.1 --port 8100
```

Terminate TLS at your proxy, forward the original allowed host, cap request bodies at 2 MiB, and disable request-body and authorization-header logging. Use an HTTPS `BENCH_AGENTS_HUB_URL` from remote Labs. Do not send passwords or bearer tokens over unencrypted public connections.

Authentication attempts are limited to 10 per minute per direct peer in each process, with bounded in-memory tracking. The service ignores forwarded IP headers. Behind a proxy this limit groups clients by the proxy address. Add proxy-level client rate limiting, account abuse controls, storage quotas, and monitoring before opening registration widely. This implementation does not provide distributed rate limiting, email verification, password recovery, account deletion, moderator tooling, or a hosted identity provider. Use one application process for predictable in-process throttling; SQLite transactions coordinate concurrent writes.

Passwords contain 12–256 characters. Usernames contain 3–40 lowercase ASCII letters, digits, underscores or hyphens and start with a letter or digit. Passwords are stored as scrypt hashes with random 16-byte salts (`N=16384`, `r=8`, `p=1`); passwords are wrapped in a redacting secret type at the API boundary. Sessions use random opaque bearer tokens, storing only their SHA-256 hashes and expiry. Login failures use the same message for unknown users and incorrect passwords. Logout revokes the presented session. Error responses omit submitted field values, including passwords and source text.

## Release contract

Publish `{ "manifest": {...}, "files": {"agent.py": "..."} }`. Manifest fields are:

| Field | Contract |
| --- | --- |
| `slug` | Required lowercase letters/digits separated by hyphens, up to 80 characters |
| `name`, `summary`, `readme` | Required text; limits 200, 1000, and 65536 characters |
| `version` | Required safe semantic version such as `1.0.0` or `1.1.0-rc.1` |
| `license` | Required license identifier/text up to 100 characters; the publisher is responsible for license accuracy |
| `runtime` | `python` or `node` |
| `entrypoint` | Existing relative source file ending in `.py` for Python, or `.js`, `.mjs`, `.cjs` for Node |
| `args` | Optional string array, default `[]`; credentials must use environment variables |
| `model_flag` | Optional command flag, such as `--model` |
| `model_base_url_env`, `model_api_key_env` | Optional uppercase environment variable names; no values are uploaded |
| `capabilities` | String array, default `["text"]` |
| `recommended_models`, `benchmark_ids`, `dependencies`, `tags` | Optional bounded string arrays, default `[]`; dependencies are informational |
| `source_url` | Optional public HTTPS URL; no userinfo, query, fragment, local address, or whitespace |

Unknown fields are rejected. Releases contain at most 40 UTF-8 text files, 128 KiB per file, and 1 MiB combined file contents. Requests additionally have a 2 MiB serialized-body cap, including escaped text and manifest metadata. Source paths use ASCII letters, digits, underscores, hyphens, dots and `/`; absolute paths, empty path components, traversal, backslashes, colons, Windows device names, trailing dots, VCS internals, credential files and link-like extensions are rejected. Case-insensitive duplicates and file/directory collisions are rejected. Binary control characters are rejected; tabs and line endings are allowed. There is no archive extraction or upload of filesystem links.

The shared `AgentRelease` validator and `release_digest()` function are also used during Lab import. The digest is the hex SHA-256 of the validated release's JSON, including explicit manifest defaults, sorted keys, compact separators, UTF-8 encoding and unescaped Unicode. A digest identifies bytes and metadata; it does not establish publisher trust or code safety.

The service scans text for obvious credential assignments, recognizable token formats and private keys. This is a best-effort rejection check, not a guarantee of secret detection. Review source, README text, arguments, URLs and metadata before publishing; rotate any secret accidentally exposed. The service never fetches source or evidence URLs. Model recommendations are publisher guidance; the Hub does not verify model availability or compatibility.

## Routes and behavior

All routes begin with `/v1`:

| Method / path | Result |
| --- | --- |
| `GET /policies` | Current publication rules version and acknowledgement requirement |
| `GET /health` | `{status:"ok"}` |
| `POST /auth/register`, `POST /auth/login` | Accept `{username,password}`; return `{token,user:{username}}` |
| `GET /auth/me` | Bearer authentication; `{user:{username}}` |
| `POST /auth/logout` | Bearer authentication; revokes the session and returns `{status:"ok"}` |
| `GET /agents?search=&model=&license=&page=1&page_size=24` | `{items:[...],total,page,page_size,pages}`; model/license filters match exact values; text search includes slug, name, summary and tags |
| `POST /agents` | Authenticated initial release, owns its slug; returns release detail |
| `GET /agents/{slug}` | Owner, latest manifest, versions with digests/timestamps, and downloads |
| `POST /agents/{slug}/versions` | Owner-only new immutable version, returns release detail |
| `GET /agents/{slug}/versions/{version}` | Source preview/release detail |
| `GET /agents/{slug}/versions/{version}/download` | Release detail and one actual successful download retrieval |
| `GET /agents/{slug}/versions/{version}/comments` | `{items:[{id,author,body,created_at}]}` |
| `POST /agents/{slug}/versions/{version}/comments` | Authenticated `{body}`; returns the created comment |
| `GET /agents/{slug}/versions/{version}/reports` | `{items:[...]}` |
| `POST /agents/{slug}/versions/{version}/reports` | Authenticated `{model,benchmark_id,passed,total,evidence_url?}`; returns created report |

Catalog pages default to 24 results and accept a page size of 1–24; pages start at 1. Filtering precedes pagination, results are ordered by slug, and source files are excluded. The website stores filters and page in the URL. Offset pagination bounds responses but does not establish million-user search capacity; indexed metadata/search and bounded histories remain launch work.

Publishing initial releases and new versions also requires `X-Agent-Hub-Rules: 2026-10-23`; absent or stale acknowledgement returns 428. Read `/v1/policies` for the active version. Successful publication stores an account/version/timestamp acknowledgement atomically with the release. Review the website’s `/rules` page and the operator responsibilities below.

Release detail is `{slug,owner,manifest,files,digest,created_at}`. Listing rows include `{slug,name,summary,owner,latest_version,digest,license,recommended_models,tags,downloads}`. The latest version is the most recently published release; publishing never overwrites an existing version. Slug/version collisions return 409, another user's version publication returns 403, and missing records return 404. These writes are atomic transactions.

Comments are limited to 4000 characters. Reports have integer counts with `0 <= passed <= total`, `1 <= total <= 1000000`. Reports include `{id,author,model,benchmark_id,passed,total,evidence_url,self_reported:true,created_at}`. The API does not accept a `self_reported` override or verified-score fields. These are user claims, with optional public evidence links; the Hub has not run or verified their benchmarks.

Preview, list, metadata, missing-download, and HEAD requests do not increment download counts. Successful GETs of the download route increment once each, including repeat retrievals by the same client. These counters measure retrievals, not unique users or successful agent execution.

One-click import stages validated source and creates a local agent registration. It does not execute source, install dependencies, load model weights, or certify the publisher. Host execution requires the Lab's explicit trust workflow and separately configured model access.

The Lab checks imported configuration and declared source hashes before execution. Register local edits separately or publish a new version rather than presenting them as the original release. This check does not sandbox privileged source or provide protection against a malicious OS user. Publishing a completed local run sends only the derived model/benchmark/pass-count summary to its original registry and source version. The Hub still labels it self-reported.
