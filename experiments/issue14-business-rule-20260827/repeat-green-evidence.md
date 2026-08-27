# Repeat GREEN evidence from a clean run

This repeat run started from a new physical run root and reapplied the published production patch to a fresh disposable copy of the immutable Jet snapshot.

- Local run root: `.local/runs/issue14-business-rule-repeat/repeat-full-b8b623837201433d`
- Production patch: `production-patch.diff`
- Production patch SHA-256: `73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3`
- Published repeat receipt: `repeat-green-receipt.txt`
- Published repeat receipt SHA-256: `7ad3eabca42d387f0c9472f1542bd31ae7a15841cfecd63e6ffc60b952495dad`
- Raw local repeat receipt SHA-256: `b9e82b37f7bc3ceb1871bb84793f5a9c5c1fb39c2bda4f902e3e1bf4434642d6`
- Snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- Source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- Snapshot file count observed: `5099`

Native verification repeated successfully: `CREATEINFOBASE`, `DESIGNER /LoadConfigFromFiles /UpdateDBCfg`, `DumpResult=0`, `Configuration successfully updated`, runtime receipt `complete###true`.

The meaningful observation vector matches the primary GREEN receipt. Ignored differences are only the run nonce and platform-generated document numbers/timestamps embedded in error text.

## Repeat observations

- `negative_single`, `zero_single`, `mixed_same_product`: draft save succeeds; posting fails; `Posted=false`; product A/B balances stay `10`; zero movement rows in both registers.
- `insufficient_stock_positive`: still rejected atomically by existing stock control; product A stays `10`.
- `normal_positive`: posts; product A `10 -> 6`.
- `minimum_positive`: posts; product A `10 -> 9.999`; cost amount remains `10` due two-decimal cost rounding.
- `all_positive_multi_duplicate`: posts; product A `10 -> 6`, product B `10 -> 8`, one aggregated recorder row per product.
