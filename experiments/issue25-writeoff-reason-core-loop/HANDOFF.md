# Issue #25 handoff

## Status

`DONE` — **FUNCTIONAL PASS / BUDGET FAIL**. PR: https://github.com/Kwentin3/1c-agent-harness/pull/26 (open, unmerged, CI Python 3.9/3.12 SUCCESS at handoff).

- Branch: `product/issue-25-writeoff-reason-core-loop`
- Evidence commit opened as PR: `86a23684bcb9c4dcad803af678ee48d424e63279`
- Baseline: `36c3fb2a37b79abe0e8ad77764b3e489afaaa039`
- Deployment: **not deployed**

## Delivered

- frozen task-specific semantic contract;
- applicable two-file production patch (`43 + 5` production lines);
- exact RED/GREEN instrumentation and native receipts;
- compact native lifecycle results;
- external task oracle, which returns PASS independently of the probe.

Native GREEN proves persisted `Reason`, blank draft save, atomic blank/whitespace posting refusal, ordinary valid posting, and preserved insufficient-stock refusal. One incidental form delta in the native prepared tree is disclosed in `green-instrumentation.patch` and excluded from `production.patch`; forms/GUI are not part of the delivered production change.

## Commands and real results

- `python3 scripts/native_cycle.py run-prepared ...red...` — `runtime_contract_completed`, 1C create/load `/DumpResult=0`, honest RED receipt.
- `python3 scripts/native_cycle.py run-prepared ...green...` — `runtime_contract_completed`, 1C create/load `/DumpResult=0`, GREEN receipt.
- `python3 experiments/issue25-writeoff-reason-core-loop/oracle.py` — PASS.
- `git apply --check` plus apply/`cmp` — production patch reconstructs exact native-GREEN production bytes.
- `python3 -m unittest discover -s tests -v` — `Ran 155 tests`, `OK`.
- immutable source identity before/after — `404e86c0cc791b881a15b85c57384e6699d17598dca0f4af2ffad3419f354b7d`.
- live PR CI — Python 3.9 SUCCESS, Python 3.12 SUCCESS; PR open, non-draft, mergeable/CLEAN.

## Cost

- wall time from short-task handoff to PR creation: `1784` seconds;
- active execution time: not separately measurable without inventing a split;
- owner interventions: `0`;
- native attempts: `4` total;
- required `run-prepared` calls: `2`;
- low-level lifecycle calls outside required interface: `2` (one completed RED, one interrupted GREEN); this is why the budget fails;
- production files: `2`; production patch: `48` added lines;
- tracked task evidence before this handoff: `8` files, `692` added lines, `27,375` bytes;
- no new runner/framework/tool and no canonical skill changes;
- canonical clean repeat: `0`.

Issue-owned cleanup validated 78,078 entries, unlinked one inactive Unix socket inside the owned 1C HOME, and removed only the literal allowlist. It deleted `712,177,357` logical / `812,699,648` allocated bytes; `df` free space increased by `968,888,320` bytes. The two accepted runners had already compacted another `550,838,141` logical bytes internally. Free space after cleanup: `9,666,310,144` bytes; free inodes: `9,609,043`. No old/shared root, platform, installer, snapshot, manifest, source CF, or foreign evidence was removed.

## Fresh-executor observations

Actually read: repository `AGENTS.md`, `README.md`, published low-cost/write-cycle docs; skills `1c-enterprise-linux`, `semantic-contract-testing`, `github-issue-to-pr`, `github-pr-workflow`; references `native-write-cycle-runtime`, `data-backed-document-write-probes`, and `bounded-prepared-run-lifecycle`.

The executor independently found `Document.InventoryWriteOff`, its metadata and object-module posting boundary, and derived the builder/probe. The milestone-package instructions were unnecessary for this core loop. The main procedural failure was choosing low-level `run` before using the documented prepared-tree boundary; no requirement conflict justified those calls.

Compared with issue #23: wall time `1784` vs `28294` seconds; native attempts `4` vs `4`; owner interventions `0` vs `1`; tracked evidence remains far smaller than issue #23's 15-file/3115-line package, although the two erroneous low-level calls prevent a budget PASS.

## Remaining owner gate

No implementation work remains. PR #26 must stay open/unmerged until owner acceptance. Merge/deployment were not authorized or performed.
