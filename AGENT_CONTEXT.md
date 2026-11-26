# Agent Context

- **Repository role**: full, evidence-driven project audit and delivery-acceptance Skill. It is the current canonical source for shared safety semantics while the workspace migration is in progress.
- **Public contract**: each edition remains a self-contained installable Skill package. Do not make runtime installation depend on a sibling checkout or shared network service.
- **Edition split**: `project-health-macos` is the macOS-focused edition; `project-health-lite` is the thin, first-pass edition. Keep their product boundaries instead of copying all professional internals.
- **Current decision**: see [ADR 0001](docs/adr/0001-authoritative-workspace-and-generated-editions.md).
- **Start with**: `AGENTS.md`, `SKILL.md`, `CHANGELOG.md`, then the relevant scripts and tests.
