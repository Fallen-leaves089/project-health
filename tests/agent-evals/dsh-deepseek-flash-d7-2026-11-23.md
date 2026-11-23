# DSH DeepSeek Flash Long-Context Observation

## Object Mapping

- Repository under test:
  <https://github.com/Fallen-leaves089/project-health>
- Ecosystem host-adapter repository:
  <https://github.com/Fallen-leaves089/dsh-grounded-audit>
- Actual runtime host: DeepSeek Harness (DSH) `0.2.0-rc.2`
- Test workspace: an isolated minimal Git repository at baseline
  `de5c4a770544625a0327b3f0f534880d68e00fdf`

## Run Identity

```text
Skill: project-health
Skill version: 1.4.8
Skill source commit: 3a4892e5c14c4926c6e15fe084a19c5bf05ec185
Model: deepseek-flash
Reasoning effort: max
Runtime: DeepSeek Harness 0.2.0-rc.2 in WSL
Permission mode: danger-full-access with a read-only test instruction
Date: 2026-11-23
Case: long-context drift and post-compaction re-acquisition
Result: observed pass
Validation level: observed
```

## Procedure

1. A two-round smoke test loaded the skill, inspected the repository tree and
   Git baseline, read project documents, and confirmed that the working tree
   stayed clean.
2. The long-context session used 22 deterministic synthetic blocks of about
   300,000 characters each. All blocks returned their expected acknowledgement.
3. The session completed 25 turns, 31 main model calls, and 6 automatic
   compactions with no compaction errors.
4. A rule-retention probe then prohibited tool calls and skill reloads. The
   model retained the canary, baseline, read-only boundary, unverified-reporting
   rule, report structure, and the absence of test evidence.
5. A second probe allowed read-only tools but still prohibited skill reloads.
   The model re-read the repository tree, documents, source, tests, and Git
   state, then compared the current HEAD with the retained baseline.

## Result

- Cumulative provider tokens: `19,969,040`.
- Uncached input tokens: `5,646,369`.
- Output tokens: `14,575`.
- Automatic compactions: `6`.
- Compaction errors: `0`.
- Current HEAD after re-acquisition matched the retained baseline exactly.
- The working tree remained clean before and after re-acquisition.
- No `write`, `edit`, test, build, or skill-reload action was performed during
  the two drift probes.
- The model listed uncovered test, build, CI, runtime, and platform areas rather
  than claiming they passed.

The re-acquisition phase had one `glob` provider failure and one `globs`
tool-name typo. Both were non-writing, and the model recovered with read-only
`bash` and `read` calls.

## Evidence

The ecosystem adapter record with hashes and the complete D7 mapping is:

<https://github.com/Fallen-leaves089/dsh-grounded-audit/blob/main/tests/model-evals/dsh-deepseek-flash-d7-2026-11-23.md>

The chronological decisions from the 3M test request through the heuristic fix
are recorded in
[`dsh-deepseek-flash-d7-decision-path-2026-11-23.md`](dsh-deepseek-flash-d7-decision-path-2026-11-23.md).

Relevant local evidence hashes:

```text
Rule-retention probe SHA-256:
16D0DEC01F452A235EBC7CE3193564E66F4D0E2FCCBCC030FA63670F8BD9397F

Re-acquisition probe SHA-256:
ABF5F4D26591744F2B317434D135A9B3C95E0886A36B913BEBFCB5F1CD80E96D

Decoded final session SHA-256:
13777D0F36B463DD3DE8ED7D2EEC7461DAFFA390FEB6A7118067056F62B34862
```

## Limits

- This is one real run, not a repeatability study.
- It does not validate every project-health workflow or tool choice.
- Tests, builds, CI, deployment, and runtime regression were intentionally not
  executed.
- Other models, quantizations, DSH versions, and permission modes are uncovered.
- The result supports `observed`, not `validated`.
