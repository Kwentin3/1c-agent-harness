# Frozen evidence package + fail-closed validator (the KISS delivery shape)

When the deliverable for a 1C write-cycle R&D task is reviewable by a human/owner (PR + issue), the
proven default is NOT a runner script. It is a small **sanitized, frozen evidence package** in Git
plus a **fail-closed validator test**, with reproduction described as an executable runbook. This is
the shape that survived an owner review that rejected a large driver as "латать бесконечно".

## Package layout (`experiments/<pkg-id>/`)

```
experiments/<pkg-id>/
  README.md               # what the package is, RED/GREEN table, reproduction steps, validator cmd
  task-contract.json      # frozen BEFORE the patch: task, locators, boundary paths, safety rules,
                          #   expected RED/GREEN (value AND type per case), native acceptance,
                          #   immutable identities, scope limits
  production-patch.diff   # ONLY the feature change (e.g. +4/-0 for one function)
  instrumentation.diff    # ONLY the test probe (e.g. +35/-0 in the managed app module)
  full-work-copy.diff     # both files concatenated == the complete difference vs the snapshot
  evidence/green-receipt.txt
  evidence/red-receipt.txt
  native-results.md       # DumpResult=0 + log tails per step, <RUN_DIR>-sanitized
  package-manifest.json   # sha256 of every artifact + immutable source identities
tests/test_<pkg>_evidence.py   # fail-closed validator (mirrors tests/test_review_package.py style)
```

## Hard rules

- **Sanitize everything**: no `/workspace/...` (or any absolute private path), no CF, no snapshot,
  no IB, no raw big logs, no secrets. Replace with `<RUN_DIR>` / `<REPO_ROOT>`. Add a validator test
  that regex-scans every file for `/workspace/[^\s"']+` and fails on any hit.
- **`package-manifest.json` must EXCLUDE itself** from its artifact list (circular hash). Rebuild it
  after ANY regeneration of a packaged file; then verify closure (each hash == disk bytes) and, for
  any text artifact, that git's blob (which equals `sha1('blob ' + len + '\0' + bytes)`) matches the
  raw bytes — no EOL conversion must be in effect (`core.autocrlf` unset).
- **Receipts must declare their byte policy**: either keep raw platform CRLF + UTF-8 BOM bytes, or
  publish an LF-normalized receipt for Git hygiene **while also recording the raw local receipt hash**.
  The validator must decode `utf-8-sig`, tolerate the declared line-ending policy, and bind each
  summary hash to the published receipt bytes. Never silently normalize without a field that says so.
- **Validator tests assert exact value+type or exact key/value per case**, the FULL label set,
  no duplicates/extras, exact diff statistics (+4/-0, +35/-0, full == parts where that artifact is
  present), manifest closure, immutable identities, and no private paths. Asserting mere
  "RED differs from GREEN" is not enough.
- **Diffs must `git apply`** (see write-cycle-driver-automation.md byte-mode pitfall); verify with
  `git apply -p1 --check` from a clean snapshot copy before publishing.

## Post-review hardening pattern

When owner/reviewer acceptance reproduces a false positive in an evidence package, do not answer with the old report. Create a new commit that closes the exact false positive and then re-review the new tree.

Useful bounded additions (still KISS, no framework):

1. A closed-set manifest/equivalent listing exactly the package files, excluding itself.
2. A fail-closed validator test that checks hashes **and** semantics. Include a negative test that performs the reproduced mutation, refreshes the manifest hashes, and still expects validation to fail.
3. A published instrumentation artifact separate from the production patch. For native 1C probes, publish either exact per-run instrumentation or a sanitized template with **real** placeholders for receipt/stage/mode/nonce, then bind sanitized command argv, key environment, run nonce/mode, published receipt file + SHA-256, raw local receipt SHA-256, base/patched production-file SHA-256, applied instrumentation file SHA-256 values, DumpResult values, log/result-json hashes, and completion marker in a compact JSON file. The validator must compare those output identities against frozen expected values and recomputed published receipt hashes; checking only field presence, argv prefix/mode, loose argv shape, or `DumpResult=0` is fail-open. If the package claims exact native commands, freeze and compare the **entire argv array** for every step (length, order, required flags, expected `<RUN_DIR>` paths, and no unexpected flags).
4. A negative mutation for every reviewer-reproduced false positive. If a reviewer changes a native output identity such as `runtimeResultJsonSha256` to 64 zeroes and refreshes the package manifest, the focused evidence test must still fail with an identity mismatch. If a reviewer removes `/UpdateDBCfg`, redirects `/Out` to another path, or inserts an unexpected runtime flag, the focused evidence test must fail with an argv mismatch.
5. Canonical production-byte identity: if a first GREEN run used semantically equivalent but byte-different line endings, pick a canonical representation by applying the published patch to a fresh source copy, record the patched-file SHA-256, and run another clean GREEN with the same patched-file hash.
6. A short final report with method cost, reuse from earlier issues, manual steps, instrumentation size, and explicit non-claims.

Do not add new semantic cases, runtime approaches, pytest/framework dependencies, or broad hardening if the owner asked for bounded evidence closure only.

## The honest-limits section

Every such package ends with explicit non-claims: one config, one platform edition, client-side
probe only, one function, no proof of lifecycle/server context, no portability to other configs /
old platforms / other agent clients. Where the source is only convention-immutable (same-uid agent
can rewrite `.local/`), say so. Sync README/ROADMAP; leave AGENTS.md etc. alone if they are
protected files requiring owner approval — note the gap instead of working around the block.
