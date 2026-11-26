# ADR 0001: Authoritative Workspace and Generated Editions

- Status: Accepted
- Date: 2026-11-26

## Context

The professional, macOS, and lite editions share safety rules, memory semantics, release metadata, and validation behavior. Maintaining them as independent copies has already produced repeated fixes, divergent commits, stale tags, and documentation drift. A full merge would damage installability and make the lite edition carry unnecessary complexity.

## Decision

1. Keep separate public repositories as self-contained installation and download endpoints.
2. Introduce an authoritative source workspace for shared behavior and edition-specific overlays.
3. Share only behavior that materially repeats across editions. User-facing safeguards may remain repeated as defense in depth.
4. Keep `project-health-lite` intentionally thin; it adopts shared safety and release primitives, not the professional recorder or full structural schema.
5. Generate release metadata and edition packages from one source, then verify each generated package independently.

## Consequences

- A shared runtime module becomes the home for scope selection, atomic writes, locking, redaction, and root validation.
- Release version, date, tag target, CI evidence, and coverage boundaries should come from structured metadata rather than hand-edited prose.
- The PowerShell verifier should become a thin adapter over the same semantics, not a second independent rule engine.
- Public repositories remain installable offline and do not require access to another private or sibling repository.

## Migration Order

1. Add concise repository-role memory and this decision record.
2. Introduce structured release metadata and cross-edition validation.
3. Extract the shared Skill runtime module and make recorders thin adapters.
4. Build self-contained edition packages from the authoritative source.
5. Add release automation that checks tag, commit, CI evidence, and package digest together.
