# Native receipt provenance — Issue #65

This is a data-only binding for the already executed native route. It adds no runner, replay tool, validator, or native invocation.

## Published bytes

| Artifact | Bytes | SHA-256 | Meaning |
| --- | ---: | --- | --- |
| `exact-receipt-production-composite.patch` | 4,934 | `efdb948d2f375e00918da8d1bf8dd56d4897d48f1c6e80882eb8d6e88074bb76` | Exact production input recorded by `receipt.json`. |
| `exact-production.patch` | 1,839 | `6061d1c1360a263c83793405f985b1524ef5fa719cd39f05b8d90f4069e7cbce` | The narrow SalesInvoice print-form business patch in this PR. |
| `receipt.json` | — | `aaf55b71b24be35402572e5f1ecda57da84262e6360f86d9ab27c2b85b222b87` | Machine-generated result of the existing native route. |

`receipt.json` names the production patch hash `efdb948d2f375e00918da8d1bf8dd56d4897d48f1c6e80882eb8d6e88074bb76`.

The composite begins with the already accepted prerequisite patch and its final **1,839 bytes** (byte offset **3,095**, zero-based) are exactly this PR's `exact-production.patch`. Thus the current business bytes are a literal suffix of the production input whose SHA is bound by the retained native receipt.

## Fresh-clone verification

From this PR head:

```bash
D=experiments/issue65-salesinvoice-payment-due-print
sha256sum "$D/exact-receipt-production-composite.patch" "$D/exact-production.patch" "$D/receipt.json"
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('experiments/issue65-salesinvoice-payment-due-print/receipt.json').read_text(encoding='utf-8'))
print(next(p['sha256'] for p in r['patches'] if p['role'] == 'production'))
PY
tail -c +3096 "$D/exact-receipt-production-composite.patch" | cmp - "$D/exact-production.patch"
```

Expected output hashes are the three values in the table; the final `cmp` is silent with exit code 0. This verifies only the byte relationship and existing receipt binding. It does not reconstruct or rerun the native route.
