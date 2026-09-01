# Issue 46 — supplier invoice / deleted warehouse

Frozen, re-runnable evidence for the server-side rule: a supplier-invoice draft may reference a warehouse marked for deletion, but posting must stop before preparation and register writes. Active-warehouse posting remains unchanged.

## Contents

- `production.patch` — minimal production change at the start of `Posting`.
- `semantic-contract.md` — pre-native cases, wrong implementations, scope.
- `prepare.py` — retained deterministic disposable-tree preparer (not executed by validation).
- `instrumentation.json` — exact Base64 patches for RED, GREEN, repeat.
- `evidence.json` — requests, runner bindings, exact receipts, business vectors, durations and cleanup.
- `manifest.json` — SHA-256 closure for every package file except itself.
- `validate.py` — fail-closed package and semantic validator.

## Validate

```bash
python3 experiments/issue46-supplier-warehouse-core-loop/validate.py
python3 -m unittest tests.test_issue46_evidence
```

Validation binds the package to `origin/main`, its Git tree, `scripts/native_cycle.py`, exact production/instrumentation bytes, prepared identities and runner inputs. It requires fresh canonical UUIDv4 identities, independent response tokens, exact RED/GREEN business vectors, positive durations, completed cleanup, and GREEN=repeat.

The retained admission failure is explicitly not RED. No native command is run by this package or validator. The package proves one fresh disposable JetTr route only; limitations remain as stated in `semantic-contract.md`.
