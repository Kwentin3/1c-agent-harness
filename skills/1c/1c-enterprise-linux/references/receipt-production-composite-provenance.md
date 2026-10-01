# Binding a retained native receipt to a narrow patch

## Use when

A native receipt is valid and no new runtime budget is desired, but it names a hash for a composite production input while the review PR publishes only the task-specific fragment.

## Minimal data-only closure

Publish three tracked artifacts:

1. the unchanged narrow business patch, named `exact-production.patch` (or the repository's established exact-patch name);
2. the exact composite production patch whose SHA is recorded by the receipt, named under the existing `exact-*.patch` binary/CRLF rule;
3. the receipt itself.

Add a short Markdown provenance note, not a script or validator. It must state composite size/hash, business-patch size/hash, the literal suffix/range (or a deterministic composition), and a fresh-clone verification command.

## Fresh-clone check

For a suffix beginning at zero-based offset `O`:

```bash
D=experiments/<task>
sha256sum "$D/exact-receipt-production-composite.patch" \
          "$D/exact-production.patch" "$D/receipt.json"
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('experiments/<task>/receipt.json').read_text(encoding='utf-8'))
print(next(p['sha256'] for p in r['patches'] if p['role'] == 'production'))
PY
tail -c +$((O + 1)) "$D/exact-receipt-production-composite.patch" \
  | cmp - "$D/exact-production.patch"
```

Pass conditions:

- the receipt `production` SHA equals the composite `sha256sum`;
- the final `cmp` is silent with exit code 0.

This proves byte identity and receipt binding only. It does not recreate a prepared tree, prove resistance to coordinated artifact replacement, or substitute for a missing receipt.

## Guardrails

- Never replace or normalize the business patch while correcting packaging.
- Restore the base repository's shared `.gitattributes` exactly; do not add a task-specific binary rule when a generic exact-patch rule already exists.
- If exact composite bytes are unavailable, say the binding is unproven. Run native software only if the owner explicitly grants the one allowed final-path attempt.
- Do not introduce a replay framework, validator, or external reviewer merely to express this two-hash-plus-byte-range relationship.
