# Independently auditing a claimed 1C write-cycle proof (critic's checklist)

Use this when you are asked to **verify / critically review someone's claimed
write-cycle proof** (issue-10 style: "understand → patch → load into isolated 1C →
prove new behaviour"). You are the reviewer, not the author. Do NOT trust the
report (`docs/…` / `EVIDENCE.md`) or a prior agent's summary — re-measure every
claim yourself with your own reads/commands, and record for each point whether it is
a **confirmed fact**, an **inference from several facts**, or **unknown/not proven**.

The author-side "how to do the cycle" is in `native-write-cycle-runtime.md`; this
file is the acceptance/audit discipline on top of it.

## The 7-point audit template (each point → verdict)

### 1. Immutable source untouched
- CF: `sha256sum <dist>/<src>.cf` vs `sha256sum <run>/work-config/original.cf` → must be
  equal. Record both hashes.
- Snapshot: `cd <snapshot_dir> && sha256sum -c ../snapshot.manifest`. Line format is
  `<sha256>  <relative/path>`. Report entries / OK / FAILED-as-missing /
  FAILED-as-mismatch. Goal: `0` missing + `0` mismatch (exit 0 = all matched).
- Record `stat -c '%y %A %n'` on the source CF and snapshot dir — mtime/mode must
  predate the run and be unchanged.

### 2. Minimal, work-copy-only change — prove it, don't claim it
- The change file: `CommonModules/.../Ext/Module.bsl` must contain the patch. Show the
  changed function with line numbers.
- **CRLF-normalized diff** (1C `.bsl` is CRLF; a raw `diff` explodes into whole-file
  spurious output). Use process substitution:
  `diff -u <(tr -d '\r' < "$SNAP") <(tr -d '\r' < "$WORK")`
  → expect exactly one hunk, N added lines, 0 removed. If it dumps the ENTIRE file, the
  other path was wrong (bad cwd/relative path) — re-run from the correct dir with
  absolute or correctly-relative paths.
- **Prove *nothing else* changed** across the whole dump tree:
  `diff -rq "$SNAP" "$WORK"` → list must be exactly the expected files
  (production module + probe module). Also verify the A/B pair differ in exactly the
  feature file: `diff -rq <red-config>/files <work-config>/files`.

### 3. Probe is test harness, NOT production
- Find the probe module (`Ext/ManagedApplicationModule.bsl`): the `Procedure` +
  call in `OnStart`.
- Concurrency check: the production function body must have NO file/terminal I/O
  (only `StrReplace`/`AdjustValue`/`Return`). If the feature itself writes a receipt,
  the runtime proof is contaminated — flag it.

### 4. Real runtime execution vs. constants/parse — the hard part
Independently confirm 1C actually executed, not that someone hard-coded the receipt.
Corroborators, in rough strength order:
- **Real platform runtime-error strings in run `.log`**: e.g.
  `{ManagedApplicationModule(NN,2)}: Procedure or function ... not defined (X)`,
  `Training version limitation reached`, `Infobase connections limitation reached`.
  These only come from live BSL execution.
- **BOM signature** `EF BB BF` (od -c: `357 273 277`) at receipt start — TextWriter
  UTF-8 writes a BOM. Absence of BOM ≠ fake, but presence is consistent with real output.
- **Receipt values match expected function output** (a value like `1234` for
  `"1"+TAB+"234"` can only be produced by the platform's real parse after the strip).
- **Distinct session dirs & causality**: `.1C/.1cv8t` created per run, and receipt
  `mtime` right after the run / before the evidence copy.
- `/DumpResult` **lives in the `.result` file** passed to `/DumpResult <file>`, NOT in
  the `.log` — "DumpResult==0" means the `.result` file contains `0`, not that the
  string "DumpResult" appears in the log. Don't grep for it in `.log`.

### 5. Scenario coverage + mutation power
- GREEN receipt must show the feature input now parses (e.g. `tab###1234`); RED receipt
  must show it empty/Undefined (`tab###`). They must DIFFER on the feature input.
- Control inputs (negative `invalid###`, unchanging `decimal###`, `space###`) must be
  IDENTICAL green vs red. If the two sides match everywhere, the test is tautological
  and has **no mutation power** — say so plainly.
- Verify RED used the ORIGINAL code: red-config module must be byte-identical to the
  source snapshot (`diff <(tr -d '\r' < "$SNAP") <(tr -d '\r' < "$RED")` → identical).

### 6. No source write / no parse-substitution
- Confirm an ENTERPRISE/log artifact (not just a re-parsed dump) stands as the runtime
  evidence; check source CF/snapshot mtime/mode unchanged.

### 7. No new dependencies / repo pollution
- `git status --porcelain` and `git log --oneline` on the branch. Expect AT MOST the
  documented markdown doc. If run artifacts (probe, receipts, configs, logs) show up in
  git, the `.local/` ignore is broken — verify with `git check-ignore .local/...`.
  Workspace artifacts belong under git-ignored `.local/runs/`.

## Discipline: confirmed / inferred / unknown
Write the verdict as three buckets so a reader knows the confidence:
- **Confirmed facts** — you measured them yourself (hashes, line numbers, diff hunks,
  receipt bytes, mtimes, git status).
- **Inferences from facts** — e.g. "red==source+probe, green!=red ⇒ test distinguishes
  versions" or "runtime errors ⇒ live BSL execution".
- **Unknown / not proven** — anything you could not reproduce (e.g. a receipt whose
  encoding you cannot regenerate from the probe as written) must be flagged openly,
  with exactly what is missing, never smoothed over.

## Repo hygiene for the audit yourself
- Run read-only. Never launch 1C or write to the source/snapshot during an audit.
- Guard against the cwd trap: relative paths make `diff`/`diff -rq` treat a file as
  missing and dump the whole file. Always `cd` to a known base or use absolute paths.
- If `xxd` is absent, use `od -c` (portable) for byte-level checks.
