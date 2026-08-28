# Issue #23 — SalesInvoice payment due date

Status: portable evidence package finalized at the PR-open boundary. Final review, merge and issue state are external GitHub records.

## Result

A fresh executor selected an optional date-only `SalesInvoice.PaymentDueDate`. Direct server posting now rejects a nonblank due date earlier than the invoice calendar date before any posting side effect. Blank, same-day and later values preserve existing behavior.

The production patch changes exactly:

- `Documents/SalesInvoice.xml`;
- `Documents/SalesInvoice/Ext/ObjectModule.bsl`.

It adds no form, migration, external integration, role, shared harness or skill change.

## Contract chronology

- original frozen contract: `4b0ec90eefcac7780291624ff0341279d281dc74`;
- additive amendment: `c8f4e9644254eb47c418558f27af823b09d4726f`;
- independent pre-patch verdict: `PASS`;
- semantic/1C owner interventions: `0`;
- operational storage owner interventions: `1`.

The amendment closes absolute-current-date, day/month component, hidden upper-bound and weak date-qualifier countermodels. See `docs/issue-23-frozen-semantic-contract.md`.

## Native evidence

All four attempts used the unchanged public `scripts/native_cycle.py run-prepared` interface. Each completed `CREATEINFOBASE`, `DESIGNER /LoadConfigFromFiles /UpdateDBCfg`, runtime receipt binding and bounded per-invocation compaction.

| Phase | Invocation | Result |
|---|---|---|
| source baseline | `run-sbsg8yee` | metadata absent, configuration loadable |
| metadata-only RED | `run-up7gk5qy` | metadata accepted/persisted; N1–N4 incorrectly post |
| GREEN | `run-j6xxr6e2` | semantic oracle PASS |
| clean repeat | `run-vw6i7lhd` | semantic oracle PASS |

GREEN and repeat have the same prepared tree identity `978c3953f95dff49d6fa1893d87b684178d885569fb7c4e31feff713b5be1a8d`. They match on all 236 run-independent semantic labels. Raw local run roots remain untracked; published receipts replace only the machine-local `/C` nonce with `<RUN_RECEIPT>`. Raw receipt hashes in `native-runs.json` are local provenance anchors, not independently reproducible authentication without the untracked raw bytes; the portable semantic claims are bound to the manifest-closed published receipts and exact validator constants.

## Behavior matrix

- Positive/preservation: P1, B1, P2, P3, P4 and blank R1 post and create one row in each of Sales, CustomerBalance, InventoryInWarehouses and InventoryCost.
- Negative: N1, N2, N3 and N4 remain unposted; all four recorder row counts are zero; inventory, cost, sales and customer state equal pre-posting values; entered due date survives draft write/reread.
- Existing failure R2 remains unposted with zero movements and unchanged balances because stock is insufficient.

Machine-readable cases are in `behavior-summary.json`; the task-specific deterministic oracle is `oracle.py`.

## Patch and instrumentation boundaries

- `production-patch.diff.gz` contains the minimal LF-normalized two-file production patch against the immutable snapshot export. After deterministic gzip decompression, applying it requires normalizing those two text files to UTF-8/LF first; this was done on a fresh repeat copy after exact pre-normalization SHA checks, and reconstructed the byte-identical GREEN production files.
- `instrumentation.diff.gz` contains only the task-specific ManagedApplication entrypoint and JetServerCall probe. It is not production logic. Its normalized reconstruction also requires restoring the source export’s missing terminal newline in `CommonModules/JetServerCall/Ext/Module.bsl`; `source-identity.json` records this prerequisite and the four byte-exact reconstruction checks.
- `source-identity.json` binds source, production, patch and instrumentation hashes.

## Cost and storage incident

From fresh-executor start to the first packaged candidate: `5222` seconds. From fresh-executor start to PR #24 opening at `2026-08-28T20:30:30Z`: `28294` seconds. Native attempts and `run-prepared` calls: `4`; semantic/1C owner interventions: `0`; operational-storage owner interventions: `1`; manual native lifecycle actions outside the supported command: `0`; changed production files: `2`; common harness/skill changes: `0`.

The end-to-end cycle was **not operationally autonomous or fully low-cost**. After publication of the first candidate, accumulated host data exhausted storage and interrupted Hermes. The exact allocation at the ENOSPC instant and the exact per-command creator history are unavailable, so this package does not assign the whole incident to issue #23. The later read-only recovery inventory found a mixture of issue-23 data and older/shared data. Issue #23 had created four task-prepared trees; two consumed source/metadata-RED trees had already been removed by one exact preparation cleanup event, while `issue23-green` and `issue23-repeat` remained. It also had three external reconstruction/review roots in `/tmp` (allocated `181727232` bytes at inventory time). A separate `storage-policy-evidence-candidate` tree was created by post-incident policy work and is not counted as issue-23 execution data.

The unchanged `run-prepared` lifecycle did compact its own four invocations: each removed only `frozen-input`, `run/work-copy`, `run/ib`, `run/home`, and `run/tmp`, for `898852430` logical bytes in total. It correctly did not own task-prepared inputs, external exact-archive/review roots, platform installations, or legacy data. Thus the accepted native calls were bounded individually, but the surrounding fresh-executor/reviewer lifecycle was not bounded end-to-end.

Owner recovery was required: the owner requested diagnosis and selected the exact cleanup scope. One allowlisted recovery operation took `806.624` seconds wall time and two removal passes (the first stopped on a read-only directory; the retry followed full revalidation and owner-only permission opening). It removed 16 explicitly enumerated old temporary/cache/platform paths and reclaimed `5002485760` allocated bytes (`4.659 GiB`). The largest removed object was the older commercial `1cv8` platform (`4155269120` allocated bytes), so the recovered total must not be described as issue-23-only growth. The filesystem changed from `4.5 GiB` available / `88%` used at recovery-session start to `9.3 GiB` available / `75%` used afterward.

No accepted issue-23 compact run root, prepared GREEN/repeat tree, immutable snapshot, manifest, source CF, training platform, installer, or tracked package file was removed. Therefore no published semantic/native claim depends on bytes lost in the recovery. Raw receipt hashes remain local provenance anchors rather than portable authentication; exact-Git-archive validation below is the portability gate. See `cost-ledger.json` for the machine-readable split between semantic/native cost and operational storage intervention.

## Limitations

Evidence is limited to a disposable file IB on 1C:Enterprise `8.5.1.1150`, direct server posting and the explicit case matrix. It does not prove GUI/form exposure, migration of existing production data, deployment, compatibility with other platform/client modes, localized user messages or business-owner acceptance. The immutable source configuration, source CF and live IB were not modified.
