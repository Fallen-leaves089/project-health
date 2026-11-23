# DSH D7 Decision Path

## Scope

This decision path starts from the fifth user request in the test conversation:
the request to run a 3M-token drift test with `project-health` in DSH. It records
each later decision through the heuristic fix and documentation update.

Local absolute paths, credentials, private addresses, and raw session secrets
are not included. `DSH_HOME`, `test-workspace`, and `test-cache` are placeholders.

## Decision Path

### DP-01: Start The D7 Test

- User request: run the `project-health` skill in WSL DSH for a 3M-token
  long-context drift test; temporarily remove the DSH built-in skill and restore
  it afterward.
- Decision: use the public `project-health` repository at version 1.4.8, preserve
  the installed 1.2.3 skill as a recoverable backup, and run the test through a
  persisted DSH headless session.
- Evidence: repository remotes, skill versions, source commit, baseline manifest.
- Consequence: the test is isolated from the installed skill and can be restored
  byte-for-byte.

### DP-02: Add A Smoke Gate

- User request: run a short session smoke test immediately after extracting the
  runtime archive.
- Decision: do not start the long test until the skill loads, the model proxy
  responds, session persistence works, and a second invocation can resume the
  same session.
- Evidence: smoke round 1 and round 2 JSON events.
- Consequence: environment failures are separated from model drift.

### DP-03: Require Active Read Evidence

- User request: in the first two smoke rounds, check whether the agent actively
  reads project structure, baseline files, and standards.
- Decision: treat a missing active read as a skill-loading failure and stop.
- Evidence: tool order was `skill` -> `bash` tree/Git -> `bash` file presence ->
  four `read` calls -> Git clean recheck.
- Consequence: the observed long-context behavior starts only after the initial
  audit mechanism is proven active.

### DP-04: Fix The Test Sequence

- User request: use the order `extract -> baseline -> smoke -> 3M tokens ->
  restore -> compare baseline`.
- Decision: record file hashes, ACLs, WSL modes, UID/GID, sizes, and paths before
  changing the skill; use a separate backup path outside skill discovery.
- Evidence: 41 baseline entries and an independent restore manifest.
- Consequence: any file, permission, or metadata drift after the test is
  detectable.

### DP-05: Complete D7 Re-acquisition

- User request: after the first rule-retention probe, approve a full D7 phase.
- Decision: resume the same session, prohibit skill reload, allow only read-only
  tools, require fresh reads of the tree, documents, source, and Git state, then
  compare the new HEAD with the retained baseline.
- Evidence: no `skill` call; `bash`/`read` calls succeeded; HEAD remained
  `de5c4a770544625a0327b3f0f534880d68e00fdf`; working tree stayed clean.
- Consequence: the result covers both rule retention and post-compaction
  re-acquisition.

### DP-06: Correct The Object Mapping

- User request: identify `project-health` as the repository under test and DSH as
  an ecosystem repository rather than an unrelated external object.
- Decision: distinguish four layers in every record:
  1. repository under test: `Fallen-leaves089/project-health`;
  2. ecosystem adapter: `Fallen-leaves089/dsh-grounded-audit`;
  3. runtime host: DeepSeek Harness;
  4. isolated test workspace.
- Evidence: repository remotes and revised D7 record.
- Consequence: the result cannot be misattributed to the wrong repository.

### DP-07: Update The Main Repository

- User request: update the main `project-health` repository.
- Decision: add the D7 observation, README entry points, an Unreleased changelog
  entry, and a contract test. Keep the result at `observed`; do not bump the
  version or claim `validated`.
- Evidence: `tests/agent-evals/`, README links, and `tests/test_agent_evals.py`.
- Consequence: the main repository owns the behavior evidence without turning a
  single run into a release gate.

### DP-08: Diagnose The Heuristic Defect

- User request: determine whether the DSH heuristic defect was fixed.
- Decision: inspect the installed `dsh-token-meter`. The implementation still
  used four characters per token globally while high-entropy hex was closer to
  two characters per token.
- Evidence: `CHARS_PER_TOKEN = 4`, the failed 1M-character block, and the
  provider context-window error.
- Consequence: large random or encoded inputs can evade proactive compaction and
  can make overflow-recovery summaries exceed the context window.

### DP-09: Apply A Conservative, Reversible Fix

- User request: fix the heuristic and record this decision path.
- Decision: patch both the token-meter entry point and its standalone estimator
  with content-aware density:
  - normal text: 4 characters/token;
  - high-entropy hex/base64 above 15% of the text: 2 characters/token;
  - CJK above 15% of the text: 1.5 characters/token.
- Implementation: a version-checked patch script with backups, idempotence,
  `--check`, `--dry-run`, and `--restore`.
- Evidence: a 1,000,000-character random-hex sample is estimated at `500,004`
  tokens after the patch instead of about `250,004`.
- Consequence: proactive compaction is much less likely to underprice dense
  content; normal and CJK estimates remain deterministic.

### DP-10: Sanitize The Record

- User request: ensure the decision path is redacted.
- Decision: replace local absolute paths with placeholders; omit API keys,
  credentials, private addresses, and raw logs; keep only public repository
  names, hashes, versions, and aggregate token counts.
- Evidence: agent-eval contract test scans this document for local path and
  common secret markers.
- Consequence: the document can be reviewed or published without exposing the
  local environment.

### DP-11: Final Review And Commit

- User request: inspect all changes, verify the decision path, and commit both
  repositories.
- Decision: review both diffs, rerun package verification and the full test
  suites, confirm the sanitization contract, confirm the installed DSH patch and
  rollback path, then commit the main project and ecosystem adapter separately.
- Evidence: package verification, full test counts, `git diff --check`, patch
  `--check`, and final clean worktrees after commit.
- Consequence: the observation, decision path, heuristic patch, documentation,
  and tests become durable repository history.

## Final State

- D7 long-context observation: `observed pass`.
- Triggered compactions: 6.
- Compaction errors: 0.
- Final cumulative provider tokens: 19,969,040.
- Built-in DSH skill restored to 1.2.3.
- Restore comparison: 41 entries, 0 differences.
- Token-meter patch: applied locally and reproducible from the ecosystem script.
- Repository changes: committed separately in the main project and ecosystem
  adapter after final verification.

## Uncovered

- The patched density function is deterministic, not an exact tokenizer.
- Repeating the full 3M test after the patch remains future work.
- The patch is version-checked for DSH `0.2.0-rc.2`; upgrades require review.
- Tests, builds, deployment, and other models remain outside this observation.
