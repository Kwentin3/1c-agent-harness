# RED evidence before production patch

Native RED was collected from source logic before any production patch.

- Pre-RED commit: `9d8229b2868736154658c93227e9d148ba2edb96`
- Pre-RED tree: `77fe41ecbb01f7c5983f30ce8430c9639b3cbd98`
- Local run root: `.local/runs/issue14-business-rule-primary/red-full-7e9c5a00437242c2`
- Receipt: `red-source-receipt.txt`
- Published receipt SHA-256: `0960822c0fa4a30df0314d74d545a8f8814faa1131bd1336d499de5492cb77ad`
- Source logic file: `Documents/InventoryWriteOff/Ext/ObjectModule.bsl`
- Source logic SHA-256: `86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c`

`Documents/InventoryWriteOff/Ext/ObjectModule.bsl` in the disposable RED work copy was byte-identical to the immutable Jet snapshot.

## RED observations

These cases violate the new rule but posted successfully on the unpatched source logic:

| Case | Draft saved | Posted | Quantity/cost observation |
|---|---:|---:|---|
| `negative_single` | true | true | product A quantity/cost `10 -> 11`, recorder quantity `-1` |
| `zero_single` | true | true | product A stayed `10`, but zero recorder rows were written |
| `mixed_same_product` | true | true | product A quantity/cost `10 -> 7`, aggregate recorder quantity `3` |

Controls behaved as expected on the source logic:

| Case | Observation |
|---|---|
| `insufficient_stock_positive` | posting failed; product A quantity/cost stayed `10` |
| `normal_positive` | posted; product A quantity/cost `10 -> 6` |
| `minimum_positive` | posted; product A quantity `10 -> 9.999`; cost amount stayed `10` due two-decimal cost rounding |
| `all_positive_multi_duplicate` | posted; product A `10 -> 6`, product B `10 -> 8`, one aggregated recorder row per product |

The machine-readable receipt is preserved in LF-normalized form in `red-source-receipt.txt`; `red-source-summary.json` binds the key observations plus the raw local receipt SHA-256 `24410de9c97a71be96037914634159476631f4641a6c0648ff95d0101348225e`.
