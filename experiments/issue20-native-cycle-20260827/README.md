# Issue #20 — native lifecycle entrypoint

Status: prior exact candidate `a2d38c569a035f2296e3ca9acb6e1cce0b5404b9` passed independent review; fresh PR #21 correction evidence is captured and a new exact-tree review is pending.

## Claim

After a task-specific probe and work tree have been prepared, one command owns the trusted training-lab lifecycle:

```bash
python3 scripts/native_cycle.py run --spec .local/native-cycle-spec.json
```

The runner copies a declared read-only input into a new disposable run root, creates a file infobase, loads and updates the configuration, waits for an exact stable runtime completion line, terminates every owned process group and writes a structured result. It does **not** patch BSL, create a probe, parse business observations or pronounce semantic PASS.

The exact interface and preparation rules are documented in [`docs/issue-20-native-cycle.md`](../../docs/issue-20-native-cycle.md).

## Evidence

[`native-results.json`](native-results.json) binds deterministically path-sanitized runner results together with reproducibly compressed raw `result.json` bytes, exact raw native receipts, exact `/DumpResult` files, exact load logs, path-sanitized create logs, and machine-captured post-run `/proc` checks. The validator decompresses each raw result, checks its immutable SHA-256 anchor, reruns sanitization, and requires byte-for-byte equality with the published sanitized object. [`candidate-code-identity.json`](candidate-code-identity.json) binds those native runs to the exact runner and lifecycle-test bytes. The package records three first-attempt native runs on training platform 8.5.1.1150:

| Run | State | Wall time | Key evidence |
|---|---|---:|---|
| success | `runtime_contract_completed` | 125.046 s | source/copy identity plus distinct post-`chmod` load identity; create/load `DumpResult=0`; terminal receipt; exact runtime log state; no remaining native process |
| clean repeat | `runtime_contract_completed` | 164.740 s | same mechanical contract and exact observation parity with success |
| bounded failure | `runtime_timeout` | 128.231 s | process return `-15`; absent receipt and `run.result` explicit; empty `run.log` identity preserved; no remaining native process |

Both successful runs reused the issue #18 task-specific probe and accepted GREEN observation vector. That external acceptance observed totals `34` and `40`; it is evidence that the common lifecycle did not hard-code one exact receipt. The runner itself claims only completion-contract success.

The immutable snapshot was checked after the final runs: 5,099 declared/actual files, with missing, extra, mismatch and symlink counts all zero. Its manifest SHA-256 remained `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.

## Budget

[`cost-ledger.json`](cost-ledger.json) records both the bounded native executor and the caller-owned preparation needed before every new input binding.

The native execution command has one stable entrypoint, zero path substitutions inside the process and no manual cleanup on nominal success. However, the caller must still freeze the prepared tree, invoke the internal fingerprint calculation and author a new spec/run-root binding; repeat requires those binding actions again. There is no supported preparation CLI in this capability and no preparation wall-time measurement.

Verdict: **BOUNDED NATIVE EXECUTOR / PREPARATION REMAINS MANUAL / LOW-COST NOT CLAIMED**. Native platform wall time and all manual preparation/review costs remain visible rather than being hidden behind an after-preparation lifecycle claim.

## Fail-closed surface

Unit tests reproduce and reject:

- duplicate JSON keys and unknown spec fields;
- path traversal and run roots outside `.local/runs`;
- writable, identity-mismatched, symlinked or non-regular input, while separately binding the byte-identical copy and the post-`chmod` tree actually loaded by Designer;
- missing Linux child-subreaper/procfs-children prerequisites through an explicit preflight diagnostic;
- existing run roots and stale output artifacts;
- non-zero/missing `DumpResult` and missing native success markers;
- batch and runtime timeouts, including a runtime-created FIFO receipt that must be classified without blocking and still trigger owned-process cleanup;
- substring-only, malformed or unstable completion receipts;
- children surviving wrapper success or timeout;
- input identity changes during a run.

## Limitations

- Fixed to the repository's trusted Linux training-edition profile; this is not a multi-platform abstraction.
- Ordinary physical copy is used because the workspace filesystem rejected reflink cloning.
- Filesystem read-only mode plus before/after identity checks are the trusted single-user lab boundary, not a hostile same-UID security boundary.
- The runner does not clean old run roots and never overwrites one.
- Semantic assertions and task-specific preparation remain separate responsibilities.
- Raw infobases, platform files and full runtime logs stay untracked under `.local/`. Exact compressed runner results are tracked for deterministic sanitization verification; they contain lab-local absolute paths but no credentials or source payloads.

`package-manifest.json` closes this package; `tests/test_issue20_evidence.py` checks closure, hashes, private-path exclusion and the concrete lifecycle claims.
