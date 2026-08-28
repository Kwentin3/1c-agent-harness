# Issue #23 — SalesInvoice payment due date

Status: native baseline/RED/GREEN/clean-repeat complete; exact candidate review and PR are pending.

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
- owner interventions: `0`.

The amendment closes absolute-current-date, day/month component, hidden upper-bound and weak date-qualifier countermodels. See `docs/issue-23-frozen-semantic-contract.md`.

## Native evidence

All four attempts used the unchanged public `scripts/native_cycle.py run-prepared` interface. Each completed `CREATEINFOBASE`, `DESIGNER /LoadConfigFromFiles /UpdateDBCfg`, runtime receipt binding and bounded per-invocation compaction.

| Phase | Invocation | Result |
|---|---|---|
| source baseline | `run-sbsg8yee` | metadata absent, configuration loadable |
| metadata-only RED | `run-up7gk5qy` | metadata accepted/persisted; N1–N4 incorrectly post |
| GREEN | `run-j6xxr6e2` | semantic oracle PASS |
| clean repeat | `run-vw6i7lhd` | semantic oracle PASS |

GREEN and repeat have the same prepared tree identity `978c3953f95dff49d6fa1893d87b684178d885569fb7c4e31feff713b5be1a8d`. They match on all 236 run-independent semantic labels. Raw local run roots remain untracked; published receipts replace only the machine-local `/C` nonce with `<RUN_RECEIPT>`. Raw hashes remain bound in `native-runs.json`.

## Behavior matrix

- Positive/preservation: P1, B1, P2, P3, P4 and blank R1 post and create one row in each of Sales, CustomerBalance, InventoryInWarehouses and InventoryCost.
- Negative: N1, N2, N3 and N4 remain unposted; all four recorder row counts are zero; inventory, cost, sales and customer state equal pre-posting values; entered due date survives draft write/reread.
- Existing failure R2 remains unposted with zero movements and unchanged balances because stock is insufficient.

Machine-readable cases are in `behavior-summary.json`; the task-specific deterministic oracle is `oracle.py`.

## Patch and instrumentation boundaries

- `production-patch.diff.gz` contains the minimal LF-normalized two-file production patch against the immutable snapshot export. After deterministic gzip decompression, applying it requires normalizing those two text files to UTF-8/LF first; this was done on a fresh repeat copy after exact pre-normalization SHA checks, and reconstructed the byte-identical GREEN production files.
- `instrumentation.diff.gz` contains only the task-specific ManagedApplication entrypoint and JetServerCall probe. It is not production logic.
- `source-identity.json` binds source, production, patch and instrumentation hashes.

## Cost

From fresh-executor start to packaged candidate: `4602` seconds. Native attempts and `run-prepared` calls: `4`; owner interventions: `0`; manual native lifecycle actions outside the supported command: `0`; changed production files: `2`; common harness/skill changes: `0`. See `cost-ledger.json`.

## Limitations

Evidence is limited to a disposable file IB on 1C:Enterprise `8.5.1.1150`, direct server posting and the explicit case matrix. It does not prove GUI/form exposure, migration of existing production data, deployment, compatibility with other platform/client modes, localized user messages or business-owner acceptance. The immutable source configuration, source CF and live IB were not modified.
