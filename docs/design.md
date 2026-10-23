# Agent Hub design system

Agent Hub is a local operational workspace for configuring model endpoints and agent harnesses, running controlled benchmarks, and inspecting independently verified outcomes. The website serves an Operate mode; its documentation serves a Read mode. Graphite and black remain the pinned visual identity.

## Visual decisions

Use the exact supplied 386×502 black-and-white portrait alongside a bold Agent Hub wordmark. Preserve its bytes and aspect ratio; do not crop, recolor or regenerate it. The catalog takes its ink-and-paper palette from this image: #f2f0e8 ground, #181916 ink and #55554e secondary text. Its signature is a ruled source index with a crisp black code mark beside each release. Standard search, filters, result lists and pagination remain familiar web controls. The dark workspace shell frames this light catalog surface; operational status colors still carry meaning. The shell uses warm graphite surfaces rather than blue-gray dashboard chrome: canvas #111211, navigation #161715, foreground #eeede9, secondary text #aaa9a2, primary action #e8e5da, rule #30322f. Muted green, amber and red indicate observed states or warnings. A local workspace label does not claim that endpoints are connected.

Geist Sans carries the interface. Geist Mono is reserved for code, identifiers and measurement. Page titles are 32px, section headings 16px, and body/controls 13–14px. Fixed sizes, tabular numerals, generous section separation and close label-control grouping keep dense evidence legible.

Sections are separated by horizontal rules. Avoid nested cards, icon-card grids, decorative charts, slogans and marketing heroes. Forms use familiar controls and accessible details disclosures for advanced configuration. Tables scroll within their containers. Primary actions are warm neutral; semantic colors carry actual status only.

## First-run behavior

Agent Hub is the discovery and sharing surface. Place it in a Discover & share navigation group above private workspace tools. On desktop, give search/model/license filters a narrow left rail and agent releases a bounded, alphabetically ordered list (at most 24 per page) with owner, source identity, version, license, model suggestions and actual download counts. Counts reflect registry data, never fabricated activity. Search/model/license filters and page persist in the URL, survive refresh and browser history, and remain in next/previous links. Empty filters and out-of-range pages offer recovery. Rows show up to three model suggestions; release details retain the full list. At narrow widths, filters stack above results. Agent release pages expose usage, source, results and discussion through section links. Publishing groups details, source/runtime and model/discovery metadata. Keep import, trusted execution and result sharing as distinct explicit actions.

A fresh workspace displays actual counts for registered models, agents and experiments, followed by the ordered connection workflow: register/probe a model, optionally pair an agent, then build and validate an experiment. Explain that saved settings and a successful connection are distinct states. The overview does not display fabricated metrics or invite automatic sample seeding. Experiment activity retains an intentional empty state until real jobs exist.

The terminal handoff exposes `uv run agent-hub terminal` with setup documentation. The optional offline demonstration is an explicit action within documentation, and its evidence remains visibly labeled. Generic empty states do not launch demonstrations.

Registration selects the saved record and offers a compatibility probe. Custom subprocess harnesses can configure an executable, script path, model flag, endpoint/key environment mapping and additional arguments without raw schema overrides. Native product mode explains its own conditions. A first experiment can select a single quick text task. Validation and probe results present a plain verdict and reasons before technical JSON. Run completion reports the verified pass count separately from orchestration status.

## Responsive and accessibility contract

The desktop sidebar is 248px and condenses to 224px. Below 768px, navigation uses an accessible Radix sheet and the content becomes one column. The setup rail stacks below the workflow at narrower widths. Controls remain at least 44px on touch layouts. Preserve semantic labels, visible focus, skip navigation, keyboard-scrollable evidence and reduced motion. No ornamental entrance animation is added to a working screen.

## Evidence and limitations

All counts, metrics, runs and failure reasons come from the local API. Unobserved costs, tokens and resources remain unavailable. Completion is separate from verified task success. Comparison intervals and scientific limitations remain visible; raw paired, condition and ablation evidence is available in an accessible advanced disclosure.

Implementation validation: component tests cover navigation, registration, honest empty overview states, API errors, and evidence keyboard access. The coordinating agent performs production build and rendered desktop/mobile inspection before release.
