# Security policy and threat model

BenchLab runs locally and is security-sensitive because registered agents and model output may be hostile. This development build has not completed the V1.0 release gate. Report suspected vulnerabilities privately through GitHub's repository security reporting facility if enabled, or request a private maintainer contact. Do not put credentials, exploit targets or private traces in public issues. No guaranteed response-time SLA is offered.

## Trust boundaries

- API binds to loopback in the documented native setup. Host and Origin checks resist browser-based access to local configuration. This is not a multi-user, Internet-exposed authentication system. Keep the service local; a reverse proxy needs its own authenticated access policy. Never expose a Docker socket.
- Provider secrets live in the backend environment. Saved configurations contain environment variable names. Provider keys, token-like strings and matching secret environment values are redacted on persistence and export. Redaction is best effort for unknown/custom secrets; do not send private source or secrets to a benchmark unless intentionally authorized.
- Registered native CLI agents are privileged host processes. Two explicit opt-ins are required. A fresh cwd and restricted environment reduce accidental exposure; they do not constrain filesystem or network access of arbitrary executables. Use a dedicated OS account or VM, especially for third-party agents. BenchLab does not silently reuse the user's native auth profile.
- Generated code verification uses a non-root, read-only, network-disabled, resource-capped Docker container with no host mounts. Docker is not an absolute security boundary; kernel/container escapes and malicious daemon/image risks remain. Use a VM or stronger sandbox for hostile code. Docker Desktop must be patched and functioning.
- Verifier logic is outside the writable agent workspace. File-state verification reads actual files independently. Coding verification compares serialized function behavior in trusted host code; expected answers never enter model prompts. Public fixtures are not secret, anti-cheat, held-out or contamination-resistant tests. Adversarial Python introspection cannot be treated as formally prevented.
- File artifacts are size-capped, symlink-rejected and contained under the data directory. Browser artifacts download as octet streams; preview is escaped text, not executable HTML. HTML reports escape output and use a restrictive content security policy; CSV exports neutralize formula-leading strings.
- Trusted Python plugins run as application code. HTTP cannot import or install plugins. Review local extensions before import.

## Operational boundaries

One daemon per data directory is the supported deployment. OS experiment locks prevent duplicate API/CLI execution and recovery skips live locks. Interrupted jobs are explicit. Cancellation and finite deadlines stop supported subprocess/model work and clean up generated containers. No automatic external telemetry, account creation, model downloads or image pulls occur in the default demo.

The Compose application intentionally has no Docker-socket mount. Its demo/model workflows work without nested Docker; sandboxed coding requires a separately managed, appropriately isolated runner. Do not solve this by mounting a privileged host Docker socket into the web API.

## Current environment limitation

Docker Desktop on the implementation machine fails during Inference-manager socket initialization. Real sandbox and adversarial runtime tests have not passed on this host and remain explicit release blockers; no factory reset or user data removal was performed.
