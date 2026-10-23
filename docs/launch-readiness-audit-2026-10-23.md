# Agent Hub: public-launch readiness audit

**Date:** 2026-10-23. **Decision: do not open the current application as a million-user shared execution service tomorrow.** It is a development implementation with a useful private Lab and a separate self-hostable source registry. Passing functional tests and dependency scans does not establish public-service capacity or security certification.

The initial assessment targets revision `f5e9b9890c521bde1dd1d81a6829d74b5f10e948`. Follow-up changes fix the import boundary and terminal-control defects and add product branding, the original user-supplied logo, publication rules, acknowledgement receipts and bounded catalog pages. Remaining issues below are explicitly open. The private Lab's local trust model is intentional; findings about public/shared deployment are conditional on exposing or repurposing it.

## Scope and evidence

Reviewed the guided terminal, scriptable CLI/SDK, model adapters, subprocess execution, Docker verifier, experiment engine/queue, records/artifacts/exports, registry authentication and storage, source importer/proxy, website data fetching, publishing/discovery/results/community flows, deployment files, CI and operational documentation. Review combined source inspection with bounded disposable probes. This is an internal review by the implementing agent, not an independent penetration test.

The probe script uses temporary stores under `.bench-agents/launch-audit`, HTTP mocks and a simulated terminal. It never executes uploaded agent code, contacts a real model, uses real credentials, changes Docker, floods the running app or creates live inventory. It removes its temporary probe stores. [Baseline observations](evidence/launch-audit/probes.json) retain the pre-fix evidence; they are not passing production acceptance gates. [Current follow-up observations](evidence/launch-audit/probes-current.json) separately record the bounded catalog response and fixed import/control paths. [The script](../scripts/audit_launch_readiness.py) can be rerun against a changed working tree to measure current behavior; do not interpret its successful exit as launch approval.

Observed baseline:

| Probe | Result | Interpretation |
| --- | --- | --- |
| Unauthenticated Lab create/list/delete | 201 / 200 / 204 | No shared-user security boundary |
| Chunked Lab body with no Content-Length | 2,098,270 bytes accepted, 200 | Header-only size gate is bypassed |
| Caller-selected URL and environment reference | Mock loopback request receives dummy credential | Dangerous if a shared server exposes this private configuration API |
| Authentication limiter | Ten attempts allowed; eleventh 429; another app instance accepts again | Per-peer, per-process accounting |
| Registry streaming-body positive control | 413 | Existing Hub body cap works |
| Valid published display name | 120-character name becomes 126 on import and fails | Fixed by bounded local display label |
| Valid published arguments | 40 arguments become 41 with entrypoint and fail | Fixed by preserving space for entrypoint |
| Publisher terminal controls | OSC control reaches captured simulated TTY | Fixed by visible escaping before display |
| Metadata-heavy directory | 801 agents, 4,026,866-byte response; own proxy returns 502 | Unpaged catalog cannot grow safely |
| Provider generation response | All twenty chunks / 1,310,720 bytes received before rejection | Limit is checked after buffering |
| Terminal entry/exit | Help and empty guided session exit 0; 40/96-column captures | Basic terminal flow works |

Catalog fixtures are valid-shaped synthetic metadata inserted transactionally for a bounded test; this was not a million-user load test. The single local list timing in the JSON is not a throughput claim.

Fresh dependency scans reported no known advisories for the locked Python runtime, web runtime, full web dependency set or browser-test dependencies. See [scan files](evidence/launch-audit). Advisory databases and coverage change; absence of known advisories does not establish absence of vulnerabilities. A stricter Ruff security run flagged four `assert` statements. They were inspected as type/arithmetic invariants, not authentication gates; those scanner warnings are not four confirmed exploits. The focused security/terminal/import suite passed 94 cases with four Docker skips before follow-up changes. Broader functional evidence is recorded separately in [the implementation audit](audits.md).

## What “one million people” means

These are different products and workloads:

1. **One million desktop installations:** each Lab executes privately. The central registry serves discovery, accounts, source releases and contributions. This preserves the current separation and is the safer starting architecture.
2. **One million registered accounts:** requires lifecycle, storage, abuse and recovery controls, but does not itself define concurrency.
3. **One million daily active users:** assuming ten API requests each per day gives about 116 requests/second averaged across a day. A hypothetical tenfold peak is about 1,157 requests/second. These are planning arithmetic, not measured capacity.
4. **One million simultaneous users:** a separate, much larger target. With just one poll every two seconds, it implies 500,000 requests/second. Even 10,000 active views under that assumption imply 5,000 requests/second before other traffic.

Model calls, downloads, authentication, publishing and jobs need separate workload models. Their resource profiles differ. No million-user, distributed, failover or sustained-load test has been performed. No reliable user-capacity number can be inferred from 236 backend tests or a small local browser run.

## Critical launch blockers

### R01 — Shared Lab authentication and tenant authorization are absent

**Severity:** Critical for shared/public Lab deployment; **priority:** P0; **status:** open. **Impact:** anyone able to reach a shared Lab could read or alter other users' configurations and evidence, submit/cancel jobs, and attempt privileged operations under the server's policy.

Evidence: `src/benchlab/api.py:82` checks Host/Origin rather than identity; model CRUD at `:175`, credentials at `:184`, agents at `:216`, jobs at `:269`, run evidence at `:307` have no user/tenant authorization. The disposable probe confirms unauthenticated access. Hub login protects registry writes, not these routes. Host and Origin checks are useful local-browser defenses, not user authentication. This matches the object-authorization concern described by [OWASP API1](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/).

Required: keep private Labs private. If adding a shared Lab, add a central identity dependency, deny-by-default protected routers, tenant ownership on every object and property, scoped credentials, quotas and cross-tenant negative tests. Test reads, writes, exports, cancellation, credentials, import and queue operations from a second account. An authenticated reverse proxy alone does not supply object ownership.

### R02 — Untrusted agent execution has host privileges

**Severity:** Critical if offered as shared untrusted compute; **priority:** P0; **status:** open. **Impact:** a hostile agent authorized to run could access its host's files, network and other processes; a task folder is not isolation.

Evidence: `src/benchlab/adapters/registry.py:101` filters the environment, but `:379` launches a host process. The dual opt-in is useful consent, not a sandbox. CPU/memory fields are not OS resource limits for that host process. Docker currently isolates generated Python verification, not arbitrary imported agent execution. Its real runtime tests remain blocked.

Required: preserve private trusted execution for the pilot. Shared execution needs separate workers in an independently verified isolation boundary, no control-plane/registry secrets, restricted filesystem/network, enforceable resource limits, short-lived scoped credentials, image provenance and adversarial escape/cleanup tests. Do not solve this by exposing the host Docker socket to the web API.

### R03 — Arbitrary server-side model targets and credential references are unsuitable for a public shared API

**Severity:** Critical/High depending on reachable services and available credentials; **priority:** P0; **status:** open for shared deployment. **Impact:** exposing private registration/probe routes could turn the server into an internal-network requester or forward a chosen server-side credential to a caller-selected destination.

Evidence: `src/benchlab/schemas.py:55` validates URL syntax but intentionally permits local endpoints. `credentials.py:36` resolves environment names. `adapters/registry.py:267` and `:446` attach the credential to the configured target. A mock-only probe confirms both behaviors. They are useful in an owner's private Lab, so blocking loopback globally would break the intended local workflow. [OWASP API7](https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/) explains the public-server risk.

Required: use separate private and public modes. A shared service needs owner-scoped credential storage, endpoint/credential binding, egress policy, DNS/IP checks at connection time, redirect restrictions and denial of metadata/management destinations. Test DNS changes, IPv6, redirects and a second tenant. Do not inherit arbitrary cloud credentials into an execution service.

## High-priority security and capacity gaps

| ID / priority | Evidence and impact | Required change and acceptance check |
| --- | --- | --- |
| **R04 / P1 — Actual Lab request bytes are unbounded** | `api.py:99` trusts optional Content-Length. The chunked probe exceeds 2 MiB and returns 200. | Enforce received bytes before JSON decoding, plus read/concurrency limits at a trusted ingress. Chunked, missing-length, malformed-length and slow/disconnected-body tests must fail safely. The Hub already provides a positive example at `hub.py:22`. |
| **R05 / P1 — Provider response cap comes after allocation** | `adapters/registry.py:288` reads the response before `:290` checks size; discovery at `:468` has no equivalent cap. Malicious or broken endpoints can consume memory before rejection. | Stream both discovery and generation with strict decoded-byte bounds; stop reading as soon as the cap is exceeded. Verify early termination and compressed/oversized responses using bounded mocks. |
| **R06 / P1 — Unbounded listings (catalog fixed; histories/search scale remain open)** | `hub_store.py:220` fetches every full release JSON before Python filtering. `:258`, `:284`, `:307` return entire histories. `hub_client.py:121` correctly caps upstream bytes, so a growing catalog breaks the UI rather than silently accepting unlimited memory. | Follow-up: catalog filtering/paging now runs in SQLite before Python materialization, with a hard maximum of 24 rows and URL-persisted next/previous UI. The follow-up fixture returns 24 of 802 agents in 120,858 bytes and proxy 200. This is a single bounded check, not capacity evidence. Still required: indexed metadata separate from source, cursor pagination for deep catalogs, bounded comments/reports/version histories and staged load testing. |
| **R07 / P1 — Authentication limiter is neither tenant-aware nor shared** | `hub.py:95` stores per-peer attempts in process memory. All clients behind a common proxy/egress can share one ten-attempt limit, while replicas have separate counters. Both effects were reproduced. | Configure a trusted proxy boundary and shared rate accounting for account, IP/device and sensitive actions; use adaptive bot controls. Verify distinct users do not lock one another out and replicas share limits. Do not trust arbitrary forwarded IP headers. |
| **R08 / P1 — Publishing and community abuse controls are incomplete** | `hub.py:213`, `:241`, `:254` authenticate writes but provide no per-account storage/write quotas or moderator actions. Records grow indefinitely. | Add storage/write quotas, report/appeal queues, moderator roles, suspension, tombstoned withdrawal with retained audit history and a real operator response process. Test an abusive account without live public traffic. Publication acknowledgement now exists but does not replace these controls. |
| **R09 / P1 — Password work factor and account lifecycle need hardening** | `hub_store.py:33` uses scrypt N=16384/r=8/p=1. Salt and constant-time comparison are present, but that work factor is below the current [OWASP scrypt configurations](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Recovery, verified contact, MFA/passkeys, password change and revoke-all-sessions are absent. | Use an established password/identity implementation; benchmark a stronger KDF under bounded concurrency, support versioned hashes and rehash-on-login, and implement secure recovery/revocation. Do not merely increase memory until authentication exhausts the host. |
| **R10 / P1 — Persistence is a single-host deployment design** | `hub_store.py:98` opens SQLite for each operation; downloads take a write transaction at `:277`. The Lab records backend and OS job locks also live on one filesystem. | For a central service, introduce a storage interface, transactional migrations, pooled shared persistence, source object storage and cacheable immutable downloads. SQLite is useful locally; even WAL has one writer and same-host constraints, per the [SQLite documentation](https://sqlite.org/wal.html). No existing cluster capacity is claimed. |
| **R11 / P1 — Jobs lack public-service scheduling and admission control** | `api.py:43` executes a local worker loop; `store.py:297` scans stored experiments to claim work. Experiment budgets can be long and the queue has no tenant admission/fairness limits. | Separate request handling from execution, use leased/recoverable jobs, idempotency keys, admission limits, fair scheduling and bounded queue depth. Test retries, duplicate delivery, worker loss, cancellation and starvation. Adding web workers alone does not supply these properties. |
| **R12 / P1 — Session credentials do not survive worker boundaries** | `credentials.py:14` has process-local active keys and lifetime masking history. Multiple independent workers cannot resolve each other's entered session keys. Masking work/history can also grow with rotations. | Keep one-process semantics explicit for local use. A shared service needs tenant-scoped encrypted credential brokerage, short lifetimes and bounded masking resources; test restart and routing across replicas. Never persist raw keys to ordinary config JSON to solve this. |

## Operations, release and product gaps

### R13 — Recovery, retention and incident handling are not launch-verified (P1, open)

`docs/hub-server.md:21` gives manual backup guidance. No automated restore drill, recovery point/time objective, replicated durability, storage quota/retention policy, data export/delete workflow or incident exercise is present. A database backup without a tested restore and matching artifacts is not a recovery plan. Add an operator runbook, automated consistent backups, encrypted off-host copies, key rotation/revocation procedures, corruption/disk-full tests and staging restore evidence.

### R14 — Service observability is not implemented by the metric dictionary (P1, open)

`api.py:358` exposes metric definitions; `telemetry.py` describes benchmark measurements. That is not request latency/error monitoring, database lock/wait metrics, queue age, failed login alerts, storage pressure, security audit trails or an on-call system. Add redacted structured logs with correlation IDs, operational metrics, tracing, alerts and dashboards. Health routes currently return simple process status, not full readiness. Never log auth headers, passwords, source bodies or provider keys by default.

### R15 — Public deployment and supply-chain controls need their own acceptance gates (P1, open)

`compose.yaml:1` has private API/web services and resource limits but no Hub service/configuration; its local default Hub URL is not a usable separate container. `Dockerfile:1` uses mutable base tags; CI actions use version tags and no recurring dependency/image audit, release signing/SBOM or migration/restore/load gates are configured. Host Docker runtime/build verification remains blocked. Production TLS/proxy behavior, cookie Secure flags through the real proxy chain, browser CSP/framing controls, ingress body/time limits and rollout/rollback must be verified in the intended deployment. Do not label absence of TLS on the local preview a vulnerability. [FastAPI's deployment guidance](https://fastapi.tiangolo.com/deployment/server-workers/) distinguishes process replication from the other deployment responsibilities.

### R16 — Terminal control injection (P1, fixed)

`terminal.py:21` previously passed redacted but unescaped text into a real terminal. Imported publisher names accepted OSC/control sequences; the simulated-TTY probe reproduced the path without executing source. Terminal support determines whether a sequence changes display or requests clipboard access; clipboard modification was not attempted or claimed. Commit `4defe43` visibly escapes C0/C1, carriage-return and bidi control characters in plain/Rich output. A regression test reproduces the original issue. Secret masking and terminal escaping address different risks.

### R17 — Publish/import contracts disagreed at legal limits (P1, fixed)

`hub_schemas.py:121` permits names up to 200 characters and `:136` permits forty arguments. `imports.py:110` originally appended a version to a 120-character local label and prepended an entrypoint to forty local argument slots. Valid published releases therefore failed one-click import, with source staged before the later validation failure. Commit `102f8fd` bounds the display label without changing slug/version/digest and reserves the extra entrypoint argument. Boundary regressions pass. Environment installation and framework wrapping still remain separate tasks.

### R18 — Publication rules and consent needed a real product path (P1, implemented in follow-up)

The website now has `/rules`, publication guidance, privacy/data boundaries, safe-execution instructions, honest-result rules, conduct and reporting links. Publishing requires acknowledgement in the form and `X-Agent-Hub-Rules: 2026-10-23` at the registry API. The registry atomically stores an account/release/version/time receipt in `publication_acceptances`. Missing/stale acknowledgement gets 428. This is enforceable versioned attestation, not proof the source is safe or that the user read every word. It does not create a staffed moderation service, legal review, automatic deletion or a hosted-service privacy contract.

### R19 — Terminal and automation do not yet cover the public developer lifecycle (P2, open)

The terminal can register local endpoints/harnesses, choose model-agent combinations, validate, run, inspect, compare and export. Its basic entry/exit, small-width layout and real loopback/subprocess paths are tested. The product is now called Agent Hub, with a width-safe ASCII wordmark, `NO_COLOR` behavior and `--no-color`; the original raster logo remains unchanged for the website/icon. `agent-hub` is the new command alias; storage/environment/package names retain compatibility.

Missing for a broad developer platform: terminal login to remote registries, search/publish/import/download/version commands, profile switching, dependency/environment creation, a release lockfile/reproducible install, update/diff/rollback/uninstall management, named remote job contexts, watch/resume support, shell automation examples and signed multi-platform distribution. The existing `hub` command starts a registry server; it is not a remote registry client. Large local inventories still print full selection lists. Terminal prompts expose engineering concepts such as binding flags and JSON arguments; they need guided templates and inline recovery paths. Banner polish alone does not solve those tasks.

### R20 — Website developer workflows remain narrower than a mature public registry (P2, open)

Working: registration/account login, source publication, immutable version selection, source/license inspection, pinned import, local/hosted model setup, matrix preview, validation, execution, comparison/replay/exports, comments and self-reported summaries. Latest branding adds the exact supplied logo, ink-and-paper catalog, Rules & Safety navigation, bounded pages and URL-preserved filters. Desktop/mobile browser tests cover these core flows.

Missing: organizations/roles and per-owner namespaces, collaborative ownership transfer, private/gated agents, saved drafts/autosave and unsaved-change warnings, multi-file path editing/removal in later releases, rendered/sanitized README content, release diff and dependency lockfiles, install/update status, useful sorting/facets and cursor pagination for deep catalogs, favorites/follows, notifications, account settings/recovery/delete, abuse/moderator UI, large-data views and reliable request timeout/cancellation behavior. Existing source is displayed as escaped text, which is safer than blindly rendering uploaded HTML; richer formatting needs its own XSS policy. These are product gaps, not all security vulnerabilities.

### R21 — Registry scores are not a verified leaderboard (P1 for ranking claims, open)

The source digest and local-run association help identify the declared release. Reports still come from users and can be submitted manually; labels correctly say self-reported. Starter fixtures are small/public, and native-agent sampling/usage is only partially controlled. There is no held-out evaluation service, trusted execution attestation, anti-cheating system, cross-hardware calibration or independent verification of a public ranking. Preserve labels and conditions. Introduce verified results only after the isolated evaluator, methodology and signed evidence are implemented and tested. Do not market current summaries as a universal best-agent ranking.

## Coverage matrix and controls worth retaining

| Surface | Reviewed/exercised | Still unverified or missing |
| --- | --- | --- |
| Terminal / CLI / SDK | Menu/exit, widths, masking, subprocess/model pairing, output escaping regression, import boundaries | Remote lifecycle client, distribution, long-running recovery, broad OS matrix |
| Website / UX | Real core browser workflow, responsive routes, accessibility scans, original-logo byte identity and policy flow checks | Large inventories, assistive-technology manual audit, account/moderator lifecycle |
| Authentication / secrets | Salted KDF, opaque hashed sessions, expiry/logout, HttpOnly/SameSite cookie, validation input omission | Stronger work factor, MFA/recovery, revoke-all, deployed proxy/cookie review, tenant scope |
| Source / supply chain | Digest/path/size validation, no execution on import, declared-file checks | Dependency verification, publisher provenance, moderation/withdrawal, runtime isolation |
| API / network | Local Host/Origin checks, strict schemas, no shell-string invocation, bounded Hub responses | Shared authentication/authorization, safe hosted egress, complete byte/rate bounds |
| Storage / reports | Parameterized SQL, transactions, artifact containment, escaped HTML/text, CSV formula defenses | Clustered durability, bounded histories, migration/restore/retention tests, streaming large exports |
| Benchmark engine | Persisted evidence, condition checks, cancellation, bounded attempts/time, explicit demo provenance | Public queue fairness/admission, trusted hosted evaluation and hard cost controls |
| Operations / deployment | Non-root container definitions, local ports, several resource limits, CI functional checks | Actual Docker execution, production topology, DDoS/abuse controls, monitoring, SLO/load/failover tests |

No confirmed SQL injection or stored script execution was found in the reviewed parameterized queries and escaped-text paths. That is a scoped observation, not an exhaustive absence claim. No live credentials were printed or used. The original logo was copied byte-for-byte, without regeneration, cropping or recoloring; [identity evidence](evidence/logo-identity.json) records its SHA-256.

## Release sequence and acceptance requirements

1. **Private pilot:** retain private Labs and explicitly trusted host execution. Fix bounded request/response handling, history bounds, indexed catalog search and remaining reproducible defects. Keep real-model/Docker/native gates unpassed until actually exercised.
2. **Public read-only discovery:** serve immutable source separately; introduce bounded indexed listings, shared storage/cache, operator monitoring, backups/restore and a defined abuse channel. Load-test realistic release sizes, not tiny empty records.
3. **Invited publishing:** complete account recovery/revocation, shared rate limits, storage quotas, moderator roles/withdrawal and incident procedures. Exercise two-account authorization and abuse scenarios.
4. **Broad public registration:** pass staged ramp, sustained peak, noisy-tenant, worker/database failure, disk-full, restored-backup and rollout/rollback tests. For any shared compute, finish R01–R03 and independent adversarial isolation review first.

Proposed initial service objectives to agree before load testing: at least 99.9% successful valid read requests, p95 catalog reads below 500 ms, no unbounded memory growth, and explicit maximum queue age/storage per account. These are proposed gates, not measured achievements. Run load tests only in authorized staging with synthetic accounts, capped resources and mock inference. Do not use this low-memory workstation or paid model APIs as the target for a million-user test.

**Launch verdict remains no-go for a million-user public service until the relevant open gates pass.** A polished logo, ASCII banner and rules page improve clarity; they do not substitute for those security and operational controls.
