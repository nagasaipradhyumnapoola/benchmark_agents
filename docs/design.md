# Bench Agents design system

Bench Agents is a local operational workspace for configuring model endpoints and agent harnesses, running controlled benchmarks, and inspecting independently verified outcomes. The website serves an Operate mode; its documentation serves a Read mode. Graphite and black remain the pinned visual identity.

## Visual decisions

Use a typographic Bench Agents wordmark with a lighter second word. The shell uses warm graphite surfaces rather than blue-gray dashboard chrome: canvas #111211, navigation #161715, foreground #eeede9, secondary text #aaa9a2, primary action #e8e5da, rule #30322f. Muted green, amber and red indicate observed states or warnings. A local workspace label does not claim that endpoints are connected.

Geist Sans carries the interface. Geist Mono is reserved for code, identifiers and measurement. Page titles are 32px, section headings 16px, and body/controls 13–14px. Fixed sizes, tabular numerals, generous section separation and close label-control grouping keep dense evidence legible.

Sections are separated by horizontal rules. Avoid nested cards, icon-card grids, decorative charts, slogans and marketing heroes. Forms use familiar controls and accessible details disclosures for advanced configuration. Tables scroll within their containers. Primary actions are warm neutral; semantic colors carry actual status only.

## First-run behavior

A fresh workspace displays actual counts for registered models, agents and experiments, followed by the ordered connection workflow: register/probe a model, optionally pair an agent, then build and validate an experiment. Explain that saved settings and a successful connection are distinct states. The overview does not display fabricated metrics or invite automatic sample seeding. Experiment activity retains an intentional empty state until real jobs exist.

The terminal handoff exposes `uv run bench-agents terminal` with setup documentation. The optional offline demonstration is an explicit action within documentation, and its evidence remains visibly labeled. Generic empty states do not launch demonstrations.

Registration selects the saved record and offers a compatibility probe. Custom subprocess harnesses can configure an executable, script path, model flag, endpoint/key environment mapping and additional arguments without raw schema overrides. Native product mode explains its own conditions. A first experiment can select a single quick text task. Validation and probe results present a plain verdict and reasons before technical JSON. Run completion reports the verified pass count separately from orchestration status.

## Responsive and accessibility contract

The desktop sidebar is 248px and condenses to 224px. Below 768px, navigation uses an accessible Radix sheet and the content becomes one column. The setup rail stacks below the workflow at narrower widths. Controls remain at least 44px on touch layouts. Preserve semantic labels, visible focus, skip navigation, keyboard-scrollable evidence and reduced motion. No ornamental entrance animation is added to a working screen.

## Evidence and limitations

All counts, metrics, runs and failure reasons come from the local API. Unobserved costs, tokens and resources remain unavailable. Completion is separate from verified task success. Comparison intervals and scientific limitations remain visible; raw paired, condition and ablation evidence is available in an accessible advanced disclosure.

Implementation validation: component tests cover navigation, registration, honest empty overview states, API errors, and evidence keyboard access. The coordinating agent performs production build and rendered desktop/mobile inspection before release.
