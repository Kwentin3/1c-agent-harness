# Issue #33 experiment receipt

## Frozen candidate

- Base commit: `18db0c1d671d6267ab750c89b53076fbbf9a4e23`
- Skill/task candidate commit: `f8b94fa4dd1644dd6d38d4c35d88f89d0796ba14`
- Candidate tree: `94531ecf9f210ef22edf4622264fbd912db66483`
- Canonical source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- Canonical manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- Canonical snapshot: `5,099` regular files, `1,258` BSL files; `scripts/project_target.py` returned `status=ready` before and after the experiment.

## Exact task and allowed context

The exact task is `task.md` (SHA-256 `58cc42936592ac0288d64bd1575b357a53452ba34f444f2d6be337fd6a4ea21c`).

The fresh executor was allowed to read only:

- `task.md`;
- the candidate versions of `skills/software-development/semantic-contract-testing/SKILL.md` and `skills/1c/1c-enterprise-linux/SKILL.md`;
- `project-target.json`, `scripts/project_target.py`, canonical manifest and `Configuration.xml` for continuity checks;
- ordinary read-only searches and cited XML/BSL files in the canonical snapshot.

It was forbidden to read issue/PR history, prior answers or review artifacts, and forbidden to run 1C/Xvfb/native commands or modify files.

## Fresh executor

- Identity: Hermes isolated subagent `sa-0-361be8cc`, model `gpt-5.6-sol`.
- Source-work interval: `2026-08-30T11:02:43Z`–`11:04:51Z`, `128 s`.
- Full orchestration wall time: `178 s`.
- Initial result: `initial-preflight.md`, SHA-256 `5bea2b90ec098d53a099958d0c467c98602e3f89a523902866bef5a796f22422`.
- Initial verdict: `READY FOR NATIVE`.
- Native attempts: `0`; files modified: `0`; owner interventions: `0`.
- One disclosed non-native retry: `project_target.py status` was rejected because the CLI has no subcommand; the correct no-argument invocation returned `ready`. The timer was not reset.

The checklist forced the executor to identify the exported manager-module procedure, server-capable compile context, lock/transaction/read/write path, default-date normalization, creation branch, persisted register state and all production callers found in the bounded scan. It also produced counterimplementations and explicit unknowns instead of proposing a BSL patch.

## Independent reviewer

- Identity: Hermes isolated subagent `sa-0-e7a8d97a`, model `gpt-5.6-sol`.
- Blind checkpoint was written before reading the initial result; SHA-256 `ab795af7cb3d1d1850685406e1b07b46459deba19e2552707c966a587d591e75`.
- Measured review duration: `305 s`; full orchestration wall time: `387 s`.
- Review: `review.md`, SHA-256 `ad6398c93c3c25da8fb8e926521b751a6cc8599fce63047d7d644e5d826c3a5f`.
- Verdict on the immutable initial result: `CHECKLIST FAIL`.
- Native attempts: `0`; repository/snapshot modifications: `0`.

The material finding was that the initial omitted-date observation lacked an explicit pre-state. An implementation that applied monotonicity only to explicit dates could pass the initial matrix and still reduce an existing future date. The reviewer also rejected an unsupported physical `write_count=0` claim and required the API scope to be stated.

The reviewer auto-loaded global procedural skills before the source phase. This is disclosed as context contamination. After an explicit boundary correction, the reviewer used only the exact candidate task/skills and canonical source as factual evidence for the verdict.

## Single transparent correction

The initial result was not rewritten. The only correction is `correction.md`, SHA-256 `9ca25e8f8377f41d2090fc0c046ea728105c118bfed1d697679e268477f4a2a1`.

It:

- adds explicit existing-older/equal/future pre-states for omitted input;
- applies normalization before the monotonic comparison;
- replaces the unsupported physical write-count claim with observable persisted-state semantics;
- limits the claim to the exported manager API rather than all possible writers;
- records the generic safe-mode `BeforeWrite` subscription and preserves it as an adjacent invariant;
- retains at least two independently killed counterimplementations.

No second reviewer was introduced: the issue budget allowed one final reviewer and one transparent correction. Therefore the recorded independent verdict remains `CHECKLIST FAIL` on the initial result; the master adjudication after the single correction is `READY FOR NATIVE` for one bounded future experiment, not authorization for a production patch or native loop.

## Recovery accounting, separate from the experiment

Canonical recovery happened before the fresh experiment and is not counted as an experiment native attempt.

- First recovery sequence: three platform invocations (`CREATE/LOAD/DUMP`), `6 + 7 + 10 = 23 s`; the `5,099/5,099` candidate matched but publication failed because write bits were removed before a cross-parent rename. Scratch cleanup succeeded and no canonical destination was published.
- One bounded retry after the user delegated the choice to the master: three platform invocations, `1 + 7 + 14 = 22 s`; exact candidate published, post-flight passed.
- Recovery total: `6` platform invocations, `45 s` native command time.
- Owner infrastructure interventions: `1` bounded platform/XKB publication before recovery. Persistent root/sudo was not granted.

## KISS and final verdict

- Full fresh-executor plus reviewer orchestration: `178 + 387 = 565 s`, below the `10 min` target.
- Experiment native attempts: `0`.
- Experiment owner interventions: `0`.
- New runtime components, parsers, indexes, schemas, validators or generic frameworks: `0`.
- Existing skills changed: exactly `2`.
- Public artifacts are limited to task, immutable initial result, independent review, single correction and this receipt.

Final evidence-based verdict:

- `CONTEXT VALUE: YES` — the checklist exposed the actual server/register execution path and neighboring invariants before implementation.
- `ROBUSTNESS: INITIAL FAIL, ONE CORRECTION` — the independent counterexample materially improved the contract.
- `KISS PASS` — the full experiment completed in `565 s` with no native experiment attempt or owner intervention.
- `MERGE AUTHORIZATION: NO` — this package does not authorize a production BSL patch, native loop or merge.
