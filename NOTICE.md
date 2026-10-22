# Third-party notices and provenance

Original BenchLab code and original starter fixtures are Apache-2.0. No upstream benchmark dataset or engine implementation is copied into the starter pack.

- FastAPI, Pydantic, httpx, Typer, Next.js, React, Tailwind CSS, shadcn/ui, Radix, TanStack Query, Recharts, Playwright, Inspect AI and lm-evaluation-harness retain their upstream licenses. Their supported public interfaces are called rather than reimplemented.
- shadcn components under `apps/web/src/components/ui/` were generated with the official CLI and remain derived from the MIT-licensed shadcn/ui project. Copyright (c) 2023 shadcn. The complete permission/warranty notice is preserved in [third_party/shadcn-ui-LICENSE.txt](third_party/shadcn-ui-LICENSE.txt).
- Geist font package assets retain the SIL Open Font License; its complete notice is preserved in [third_party/geist-LICENSE.txt](third_party/geist-LICENSE.txt). The application's Apache license does not replace font licensing.
- Docker base/runtime images retain included software licenses; model weights and benchmark datasets have separate cards and restrictions. User downloads are not redistributed here.
- Design/engineering skill collections are development guidance installed locally, not required application runtimes. Project-local Impeccable guidance is ignored by Git; its pinned source is recorded in `.agents/skill-sources.json`. This avoids incorrectly relicensing third-party skill content as application code.

See lockfiles for exact application dependency versions and `docs/integrations.md` for upstream execution/resource boundaries. License metadata review is recorded as evidence; missing metadata must be resolved before redistributing an unfamiliar dependency or dataset. No blanket claim of legal compatibility is made for arbitrary user-installed plugins, models or data.
