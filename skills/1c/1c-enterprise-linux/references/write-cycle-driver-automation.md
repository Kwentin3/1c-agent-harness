# Automating the write-cycle: a committed, testable driver (not a one-off experiment)

`references/native-write-cycle-runtime.md` covers the *manual/native* write-cycle commands and their
traps. This reference is the **automation layer**: how to turn that one-off experiment into a committed,
*re-runnable* driver whose pure logic is unit-tested without 1C, so a future session (or another agent)
can reproduce the whole RED→GREEN proof from a clean state instead of trusting a description.

Guideline: PURE logic goes in imported functions (testable with plain `unittest`, no platform);
platform orchestration lives only in a `run` command. Verify the driver actually executes the full cycle
once (`driver run`) before declaring it "reproducible" — a driver that only lints is not proof.

**A driver is a PARTING NOT the destination: the smallest safe deliverable wins.** A committed driver
is justified only when the same experiment must be re-run repeatedly by a machine across environments.
When an owner review says "не латать бесконечно драйвер — выбери минимальное безопасное решение",
the correct resolution is: **delete the driver**, keep a frozen evidence package (sanitized contract +
diffs + receipts + hashes) plus a fail-closed validator test, and describe reproduction as a precise
executable runbook. This session's 498-line driver accumulated reproducible unsafety because a runner
must decide about rmtree, stale files, receipts and process trees — and every one of those decisions
was a new attack surface:

- **`rmtree` on a user-supplied path can delete the immutable source.** Never delete anything outside
  a fresh unique run dir; refuse to run if the run dir already exists.
- **Stale receipts/results/logs must make the run FAIL, not be accepted.** A guard that only
  `Path.exists()` accepts yesterday's evidence; require the artifact to be absent before the step and
  only read it after the step that produces it.
- **`check` without evidence must fail closed.** Missing/incomplete/extra evidence → non-zero.
- **Snapshot verification must include extra files and symlinks**, not just `sha256sum -c` (which
  only checks manifest entries, never surprises). Count missing/mismatch/extra/symlink all = 0.
- **Mutation-power analysis must require exact expected values AND types**, not "RED differs from
  GREEN" (that accepts `banana/pear`-style noise as mutation).
- **Sanitize committed evidence**: no private absolute paths (`/workspace/...`), no CF, no IB, no raw
  logs, no secrets — replace with `<RUN_DIR>` / `<REPO_ROOT>` placeholders, and add a test that
  scans the package for `/workspace/` leaks.

## Split the logic so it's testable without 1C

Keep these as standalone functions (import them in the test module via `importlib.util.spec_from_file_location`):

- `parse_receipt(path)` → `dict[label, value]` (split on `label###value`).
- `analyze_mutation(green, red) → {feature_flipped, control_changed, mutation_power}`. Mutation power is
  TRUE only when the feature cases flip AND the control/unchanged cases do NOT flip. A test that also
  flips its controls is tautologically weak → `mutation_power=False`.
- `verify_snapshot(snapshot_dir, manifest) → {entries, ok, missing, mismatch}` per-file against the
  `<sha256>  <relative/path>` manifest.
- `verify_cf(cf)` re-asserts the source CF hash against the pinned constant.
- `inject_probe(module, receipt_path)` / `apply_production_patch(module)` — the BSL mutation helpers.

Only the `run` command drives `CREATEINFOBASE` / `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` /
`ENTERPRISE`, so tests import the pure functions and never need the platform.

## Pitfalls in the automation layer (each cost real time this session)

- **`Path.read_text()` destroys CRLF.** Python's `read_text()` uses universal-newline mode and converts
  `\r\n` → `\n`, so a BSL anchor string written with explicit `\r\n` **never matches** and the injection
  silently no-ops (or raises "anchor not found"). Fix: read with `open(path, "r", encoding="utf-8-sig",
  newline="")` and write with `open(path, "w", encoding="utf-8-sig", newline="")` so line endings are
  preserved. Keep the BOM through `utf-8-sig` on both sides.
- **`/DumpResult` has a UTF-8 BOM.** The result file reads back as `\ufeff0` (or `\xef\xbb\xbf0`), so a
  naive `result != "0"` check fails on the BOM prefix. Decode with `utf-8-sig` (or `read_bytes()` +
  `.decode("utf-8-sig")`) then `.strip()`, and compare to `"0"`. Do NOT rely on `xvfb-run`'s shell rc —
  the result file is the exit status.
- **The managed-app module has TWO `#EndRegion`. A first-match `str.replace("#EndRegion", ...)` inserts
  the probe into the WRONG region** (the top `#Region Variables` closer) instead of the bottom
  `#Region EventHandlers` closer. Use the **last** occurrence: `text.rfind("#EndRegion")` and splice there.
  Similarly insert the OnStart call at the exact `Procedure OnStart()` anchor; verify the call lands
  *before* the `// StandardSubsystems` comment.
- **Double-patch guard must match the EXACT block, not a bare substring.** Guarding with
  `'Chars.NBSp' in text` false-positives because an unrelated function (e.g. `StringToDate`) legitimately
  uses `Chars.NBSp`. Check `PRODUCTION_PATCH_LINES in text` (the full block) instead.
- **Kill the whole process tree, not just the wrapper.** `xvfb-run` is a shell wrapper; `proc.kill()` on
  it leaves the real `1cv8t ENTERPRISE` child alive → it holds the educational-edition connection slot.
  Launch with `start_new_session=True` and tear down with `os.killpg(os.getpgid(proc.pid), SIGKILL)` so
  the child dies too. Poll for the receipt, then kill; the platform client idles after the probe `Return`s
  rather than exiting on its own.
- **`revert_production_patch` is usually dead code.** When building the RED variant you copy the snapshot
  (original) fresh, so there is no patch to revert — assert the patch block is ABSENT instead of trying
  to strip it. Remove dead functions; don't leave a stub "for symmetry".
- **Chmod the work copy** after `copytree` (the snapshot is read-only), or the Designer load and receipt
  write will hit permission errors on inherited read-only files/modes.
- **Diff files must APPLY — generate them in byte mode, not text mode.** `subprocess.run(..., text=True)`
  (or `capture_output=True` with text) decodes with universal newlines and strips `\r` from CRLF
  sources, so a `.diff` produced this way looks correct but fails `git apply` (context lines no longer
  match). Generate patches from a scratch git repo (`git init; core.autocrlf=false; commit snapshot
  files; overwrite with modified; git diff`) using **byte capture** (`capture_output=True` without
  `text=True`), or with `git diff --no-index -a/… -b/…` from a `tmp/a`/`tmp/b` layout. Then VERIFY:
  `git apply -p1 --check` against a fresh snapshot copy must pass for every diff file, and applying
  `full-work-copy.diff` must reproduce the work copy byte-for-byte (module) or modulo the sanitized
  receipt placeholder (instrumentation). A reviewer running `git apply` is a legitimate acceptance
  test — do not ship a diff that only renders.
- **Recommit everything after regenerating evidence.** Any file regeneration (diff, receipt, manifest
  rebuild) changes hashes; rebuild `package-manifest.json` (exclude the manifest itself from its own
  artifact list — circular hash), re-run the validator, and the full suite before committing.
- **Keep `diff --check` / `py_compile` + the full existing suite green** before committing a driver. In a
  file-mode training lab the platform step can't run in a plain CI without the platform, so the unit tests
  should cover pure logic and not assert on 1C execution.

## Idempotent-probe example (byte-clean against a known-good artifact)

After building, diff the generated work copy against the *known-good* `.local` artifact to prove the
helpers reproduce exactly what ran:
`diff <(normalized generated)/Module.bsl <(normalized known-good)/Module.bsl`. With CRLF normalized
(`sed 's/\r$//'` or compare `bytes.replace(b'\r\n', b'\n')`), the ONLY difference should be the
parameterized receipt path — everything else (OnStart call, probe procedure, production patch) must be
byte-identical.

## Scope note

The driver reproduces ONE scenario and is deliberately not a general write-framework, patch-engine, parser,
RAG, MCP, graph, or plugin system. It only orchestrates the native platform commands and verifies output.
Keep it that narrow — expanding it into infrastructure "for the future" is the exact anti-pattern the
issue contract warns against.
