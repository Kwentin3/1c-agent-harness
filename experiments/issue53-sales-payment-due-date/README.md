# Issue #53 — SalesInvoice payment due date

## Terminal verdict

**`PRODUCT PASS / COST FAIL — READY FOR OWNER REVIEW`**

The business feature works through the one shared daily route. The active elapsed target of 10 minutes was missed: local terminal receipt was obtained after **1,035 s** from the admitted start.

## Narrow `rg` context

The packet used for the change was five source areas, not a configuration-wide read:

1. `Documents/SalesInvoice.xml:1061-1066` — document attribute insertion boundary.
2. `Documents/SalesInvoice/Ext/ObjectModule.bsl:14-56` — server/external-connection `Posting`; validation must return before initialization and four movement writers.
3. `Documents/SalesInvoice/Ext/ObjectModule.bsl:74-82` — `BeforeWrite`; unchanged so invalid dates can still be saved as drafts.
4. `Documents/SalesInvoice/Forms/DocumentForm/Ext/Form.xml:271-315` — explicit Number/Date header controls and smallest form placement.
5. `Documents/BankPayment.xml:568-612` — existing optional date-only metadata precedent.

Context size: **5 files / 148 ranged source lines**. The nearest bypass is direct server/external-connection posting, so the rule is owned only by the SalesInvoice object `Posting`, not by the form. The four affected recorder registers are Sales, CustomerBalance, InventoryInWarehouses and InventoryCost.

## Production patch

`exact-production.patch` changes exactly three SalesInvoice-owned files:

- adds optional date-only `PaymentDueDate` metadata;
- exposes `Object.PaymentDueDate` beside the existing document date in the main form;
- rejects a filled due date whose calendar day is earlier than the document calendar day, with an immediate return before posting initialization or movements.

`BeforeWrite`, manager/common modules and register writers are unchanged.

## Native business result

The shared command produced [`receipt.json`](receipt.json) as its automatic output. Its oracle validated eleven data-backed cases:

- draft write succeeds with blank, same, later and earlier dates;
- blank, same calendar day and four later-date controls post successfully;
- four earlier-date cases remain unposted;
- rejected recorders have zero rows in all four movement registers and before/after balances are equal;
- the existing insufficient-stock failure remains rejected;
- metadata is optional, date-only and persisted.

The first native invocation reached the correct business result but the host oracle rejected the platform's localized date rendering. After a normal local parser correction, the final shared-route invocation returned oracle `PASS` and wrote the receipt. This was not a business or 1C retry.

## Cost

| Phase | Active elapsed |
|---|---:|
| `rg` context and source contract | 509 s |
| production/instrumentation/oracle + static admission | 262 s |
| shared native route, parser correction and final receipt | 264 s |
| **Total to local terminal receipt** | **1,035 s** |

The dominant miss was pre-native adaptation of the older payment-date probe to the new shared client/server receipt boundary. No new generic component was added; the adaptation stays task-owned.

## Cleanup and limits

- canonical CF/snapshot/manifest remained ready and unchanged;
- prepared tree discarded;
- runner compaction completed with `manualCleanupActions=0`;
- disposable IB/work-copy/HOME/TMP were removed;
- no `1cv8t`, `1cv8ct`, Xvfb or `shared-task-*` survivor remained;
- the proof is limited to JetTr 1.0.3.1 and training 1C 8.5.1.1150 in a disposable file IB;
- main-form XML load proves platform acceptance and binding, not pixel-level UI appearance.
