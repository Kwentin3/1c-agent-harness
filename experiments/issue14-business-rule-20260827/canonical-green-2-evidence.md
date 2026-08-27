# Canonical GREEN #2 evidence

This run is the byte-canonical confirmation requested after review of PR #15. It starts from a fresh physical run root, reapplies the published `production-patch.diff`, and uses the same probe-only instrumentation as the previous repeat GREEN.

- Local run root: `.local/runs/issue14-business-rule-repeat/canonical-green-2-d5db4eaef975447b`
- Published receipt: `canonical-green-2-receipt.txt`
- Published receipt SHA-256: `55dfbb2dd6c81a28d0270c2a942bda35d48f39bb30092a43141856f1af4b0120`
- Raw local receipt SHA-256: `2221d1b82259e95ae27d2bacd02e212cf67e78a1c68d43f77e5567d45c8c2f0d`
- Production patch SHA-256: `73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3`
- Patched production file SHA-256: `d8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a`

The patched production file hash equals canonical GREEN #1 (`repeat-green-summary.json`): `True`. The meaningful observation vector also matches canonical GREEN #1; ignored differences are only run nonce and platform-generated document numbers/timestamps in error text.

Native verification: `CREATEINFOBASE` `DumpResult=0`; `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` `DumpResult=0`; load log contains `Configuration successfully updated`; runtime receipt contains final `complete###true`.
