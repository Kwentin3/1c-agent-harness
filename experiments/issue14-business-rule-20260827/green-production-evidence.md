# GREEN evidence after minimal production patch

Native GREEN was collected from a disposable work copy with the minimal production patch in `Documents/InventoryWriteOff/Ext/ObjectModule.bsl` plus probe-only instrumentation outside the production file.

- Local run root: `.local/runs/issue14-business-rule-primary/green-full-7d54ba68acb84d6a`
- Production patch: `production-patch.diff`
- Production patch SHA-256: `73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3`
- Published receipt: `green-production-receipt.txt`
- Published receipt SHA-256: `4bc33c9a99ea99b0025dd12c5069664f661f83fad4e4a8beafb28ecf51e0dab1`
- Raw local receipt SHA-256: `e9a29799bd40a5524a8885fd756c517b43cd41c9b03d65a17d47da6cfa47ce25`
- Source logic base SHA-256: `86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c`
- Patched production file SHA-256: `aac9b1b60a16c3aa57cab1e5e050e0cf526d9d941cc43c2a079269e72ae4f3ef`

## Minimal patch

The patch changes one production file and inserts one guard before posting movement initialization:

- reject posting if any `Inventory` tabular-section row has `Quantity <= 0`;
- set `Cancel = True` and return before any register movement construction or recordset writes.

Patch statistics: `+6, -0`, one file. The zero-context patch applies to a disposable copy of the CRLF snapshot with `git apply --ignore-space-change --unidiff-zero`; applying the text patch normalizes the touched file's line endings, so byte hashes are not compared across that apply check.

## GREEN observations

Invalid quantity-rule cases are rejected while unposted draft saving remains allowed:

| Case | Draft saved | Posting call succeeded | Posted after | Balances/movements |
|---|---:|---:|---:|---|
| `negative_single` | true | false | false | product A/B quantity+cost unchanged at `10`; zero movement rows |
| `zero_single` | true | false | false | product A/B quantity+cost unchanged at `10`; zero movement rows |
| `mixed_same_product` | true | false | false | product A/B quantity+cost unchanged at `10`; zero movement rows |

Controls and valid preservation cases:

| Case | Observation |
|---|---|
| `insufficient_stock_positive` | still rejected atomically by existing stock control; product A stayed `10` |
| `normal_positive` | posted; product A quantity/cost `10 -> 6` |
| `minimum_positive` | posted; product A quantity `10 -> 9.999`; cost quantity `10 -> 9.999`; cost amount stayed `10` due two-decimal cost rounding |
| `all_positive_multi_duplicate` | posted; product A `10 -> 6`, product B `10 -> 8`, one aggregated recorder row per product |

The full machine-readable GREEN receipt is preserved in `green-production-receipt.txt`; `green-production-summary.json` binds the key observations and hashes.
