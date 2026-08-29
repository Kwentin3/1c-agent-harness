# Issue #25 handoff

## Status

`DONE` — **FUNCTIONAL FAIL — partial feature proof on a non-canonical fixture / fresh-agent end-to-end goal not proven**. The separate budget result is also FAIL. PR: https://github.com/Kwentin3/1c-agent-harness/pull/26 (open and unmerged; live CI and review state are external GitHub records).

This is an issue-level product verdict, not a claim that the BSL feature itself failed. The preserved partial result is: feature behavior passed natively on the frozen 5,002-file Jet `1.0.2.1` tree; `production.patch` applies statically to the canonical 5,099-file JetTr `1.0.3.1` snapshot; canonical native behavior is unproven.

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
- frozen 5,002-file input identity before/after — `404e86c0cc791b881a15b85c57384e6699d17598dca0f4af2ffad3419f354b7d`.
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

## Executor boundary reconstructed from the saved trace

The fresh delegated executor ran from `2026-08-28T21:52:47Z` until its timeout at `22:02:47Z`. Its append-only trace is retained on the execution host as `/data/hermes-home/cache/delegation/live/deleg_668509b8/task-0.log`. The trace records that it read repository `AGENTS.md`, `README.md`, `docs/issue-20-low-cost-native-loop.md`, `docs/write-cycle-knowledge-handoff.md`, `scripts/native_cycle.py`; skills `1c-enterprise-linux` and `semantic-contract-testing`; and installed references `native-write-cycle-runtime.md` and `data-backed-document-write-probes.md`. It did **not** read a reference named `bounded-prepared-run-lifecycle` and did not read the two GitHub skills previously listed here.

After that executor timed out, the parent continuation read an **installed, non-repository** reference at `/data/hermes-home/skills/1c/1c-enterprise-linux/references/bounded-prepared-run-lifecycle.md`. The exact returned content is durably recorded in Hermes session `6b8b73fbaf97`, message `109132`, tool call `call_52XuX6qxrlQRkjgJPKc7GXvb`, timestamp `2026-08-28T22:03:09.3163786Z`: `4,130` UTF-8 bytes, SHA-256 `5c0a94e5cf9839a5165ce7d0418b7beb446c02a414299ea7b39250464f32dc81`, first line `# Bounded prepared-run lifecycle and goal-loop continuity`. The installed file was later changed, so its current hash is not evidence of the bytes read then. Consequently, the original “repository docs/canonical skills only” statement describes the fresh delegated executor's initial boundary, not the complete parent continuation.

The fresh executor independently found `Document.InventoryWriteOff`, its metadata and object-module posting boundary, and derived the builder/probe before timeout. It did not complete the required end-to-end `understand → locate → contract → RED → patch → GREEN → PR` goal. The parent continuation preserved that work and completed the remaining stages after reading the installed non-repository reference described above. Therefore the fresh-agent end-to-end product claim is not proven. The two low-level `run` calls before the accepted `run-prepared` calls additionally preserve the budget failure; no requirement conflict justified them.

Compared with issue #23: wall time `1784` vs `28294` seconds; native attempts `4` vs `4`; owner interventions `0` vs `1`; tracked evidence remains far smaller than issue #23's 15-file/3115-line package. The two erroneous low-level calls prevent a budget PASS independently of the issue-level functional failure.

## Source identity and canonical-snapshot boundary

The 5,002-file tree is **not** the canonical native snapshot and is not proven to derive from its source CF. It is `.local/upstream-jet/cf` at Git commit `80884def67e2a75185452a6a13ff394075e457e0` / tree `3ca86058f10c4ff5eded8691680e47fabb71e87a`, remote `https://github.com/1Ci-Company/Jet.git`, branch `community`. Its `Configuration.xml` identifies `Name=Jet`, `Version=1.0.2.1`; its runner identity is `files=5002`, `directories=4744`, `bytes=72790943`, SHA-256 `404e86c0cc791b881a15b85c57384e6699d17598dca0f4af2ffad3419f354b7d`. `.local/fixtures/jet/cf` has the same exact runner identity.

The canonical lab source is instead the release CF `.local/dist/Jet-1.0.3.1-tr.cf`, SHA-256 `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`; its native dump is `.local/runs/training-jet-review-final/snapshot`, whose manifest SHA-256 is `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691` with 5,099 declared/actual files. Its `Configuration.xml` identifies `Name=JetTr`, `Version=1.0.3.1`.

The apparent `97`-file gap is only a net count, not a filter category: exact path comparison gives `107` canonical-only paths and `10` upstream-only paths (`5,099 - 5,002 = 107 - 10`), with 4,992 common paths and 3,905 byte-different common files. Therefore there is no truthful “97 omitted files” list and no established derivation between these trees.

Exact unpatched target hashes are:

| Target | 5,002-file Jet 1.0.2.1 tree | canonical JetTr 1.0.3.1 snapshot |
|---|---|---|
| `Documents/InventoryWriteOff.xml` | `5a3666d1a66df8dfa197a26bd3e359c4b27e6384797422dda0b130a033cbc4a8` | `4ed53164000d9f6c363d86c46161bbdf55939fb6b9a578c6cc17cebf5c8c6479` |
| `Documents/InventoryWriteOff/Ext/ObjectModule.bsl` | `86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c` | `86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c` |

In isolated two-file copies, `git apply --check production.patch` and `git apply production.patch` both return `0` for each target tree. On the 5,002-file tree the patched hashes are `0009ea15c08b52b6bf75ba9c086b3d3d93716efd2571f17d60f140a4de484bf7` and `10d376f9fa4b25f3aadcc1ecc8540cb5aad8db3ff62e947790120a731bdf05be`; on the canonical snapshot they are `5ee01189f5063a4c1d94818f451882e490f676d48a97dba50eddb7b54579b555` and the same BSL hash. Thus the patch is statically applicable to the canonical snapshot, but native RED/GREEN proves behavior only on the frozen 5,002-file Jet `1.0.2.1` tree; no canonical JetTr runtime claim is made.

## Receipt byte binding

The tracked receipts are LF/no-BOM representations. Restoring a UTF-8 BOM and converting each LF to CRLF reconstructs the exact native bytes in `native-results.json`: RED `103` bytes / `095a876a70aa8e0c0eb1fb8b99c1393c7b53ff4ac87c8d84e99e6764adc16558`; GREEN `574` bytes / `acf254ddbe09baf0fb7733a81b3ea7a61e20b4e09756de88ef512691687d425a`.

## Remaining owner gate

No implementation work remains. PR #26 must stay open/unmerged until owner acceptance. Merge/deployment were not authorized or performed.
