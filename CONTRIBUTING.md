# Contributing

BenchLab is a development build. Read [architecture](docs/architecture.md), [contracts](docs/contracts.md), [methodology](docs/methodology.md) and [security model](SECURITY.md) before changing evaluation behavior.

1. Install Python 3.12, uv and Node 24 LTS. Clone this repository, run `uv sync --locked`, `npm ci --prefix apps/web` and `npm ci`.
2. Create a branch. Write a failing behavior test, implement the change, then run `uv run pytest`, `uv run ruff check src tests examples`, `uv run mypy src/benchlab` and `npm test --prefix apps/web`.
3. For UI changes run `npm run typecheck`, `npm run build`, start API/web and run `npm run test:e2e`. Include screenshots of changed important states at desktop and mobile widths.
4. For new adapters include credential-free protocol fixtures, deliberately failing outputs, timeout/cancellation checks, conformance tests and truthful setup requirements. Do not require API keys in CI. See [extension guide](docs/plugins.md).
5. Preserve upstream scoring, version manifests and dataset licenses. Public fixtures must never be described as contamination-free. Explain statistical limitations.
6. Open a pull request with tests, user-visible behavior and limitations. Do not include credentials or live provider data without explicit permission. Report security issues through the repository's private vulnerability reporting mechanism when available.

Dependencies are locked with uv.lock and separate npm lockfiles. Review every generated shadcn file and retain its upstream license attribution. Run dependency audits and record limitations; an audit is not a proof of security. Do not add mandatory remote services or telemetry to the default workflow.
