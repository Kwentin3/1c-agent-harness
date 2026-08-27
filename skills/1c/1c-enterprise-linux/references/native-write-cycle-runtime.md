# Native config change + runtime verification (write-cycle) on the training edition

Goal: prove, on the official **training edition** (`1cv8t`, Linux), that a config change actually
executes inside 1C — not just that files imported. For the issue-10 class R&D task ("understand →
patch → load into isolated 1C → prove new behaviour"), the required evidence is three *distinct*
levels, and proving each one has its own trap.

## The three evidence levels (a single "1C didn't complain" is NOT enough)

1. **Platform accepted the change** — Designer loads the config and brings the disposable IB to an
   executable state. Proof: `/DumpResult` = `0` + `Configuration successfully updated`.
2. **New behaviour actually runs** — the target BSL executes inside 1C and yields the expected
   observable result.
3. **The test is not tautological** — it fails (or yields a different result) WITHOUT the change, and
   distinguishes a positive and a negative/unchanged scenario. This is the RED→GREEN/mutation-power
   requirement.

## Commands (verified on training edition 8.5.x, file mode)

```bash
V=.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t
L=.local/platform/libs
RUN=.local/runs/<run-id>

# 1) disposable file IB
xvfb-run -a -s "-screen 0 1280x1024x8 -nolisten tcp" \
  "$V" CREATEINFOBASE "File=$RUN/instr-ib" /DisableStartupDialogs /DisableStartupMessages \
  /Out $RUN/logs/create.log /DumpResult $RUN/logs/create.result

# 2) load the CHANGED config dump into the disposable IB (must match the dump layout)
xvfb-run -a -s "-screen 0 1280x1024x8 -nolisten tcp" \
  "$V" DESIGNER /F $RUN/instr-ib \
  /LoadConfigFromFiles $RUN/work-config/files /UpdateDBCfg \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out $RUN/logs/load.log /DumpResult $RUN/logs/load.result
#   → check load.result == 0 and log contains "Configuration successfully updated"

# 3) execute a runtime scenario inside the disposable IB
xvfb-run -a -s "-screen 0 1280x1024x8 -nolisten tcp" \
  "$V" ENTERPRISE /F $RUN/instr-ib \
  /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" /Out $RUN/logs/run.log
```

- `CREATEINFOBASE` takes `File=<path>` (not `/CreateIB`); `DESIGNER` uses `/LoadConfigFromFiles <dir>`
  (the dir must be the config-dump dir that CONTAINS `Configuration.xml`, e.g. `work-config/files`),
  followed by `/UpdateDBCfg`. Both accept `/Out <log>` + `/DumpResult <file>`.
- The IB here is disposable and lives under `.local/runs/<run-id>/`. Source CF/snapshot stay read-only.

## Prove BSL actually ran: inject a probe, don't parse files

An external processing / report that you also open can crash or require interactive open. The cheap,
reliable way to run config code headlessly and emit a machine-readable receipt is a **probe in the
managed-application module**: add a `Procedure <Name>()` that calls the *production* function and
writes a `TextWriter` receipt, then call it from `OnStart` and `Return` before the subsystem handlers:

```bsl
Procedure OnStart()
    Issue10WriteRuntimeReceipt();
    Return;
    // StandardSubsystems...
EndProcedure

Procedure Issue10WriteRuntimeReceipt()
    Receipt = New TextWriter("/abs/path/to/run/home/issue10-runtime-receipt.txt", TextEncoding.UTF8);
    WriteProbeCase(Receipt, "tab", StringFunctionsClientServer.StringToNumber("1" + Chars.Tab + "234"));
    ...
    Receipt.Close();
EndProcedure

Procedure WriteProbeCase(Receipt, Label, Result)
    TypeMarker = String(TypeOf(Result));
    ValueText  = ?(TypeMarker = "Number", String(Result), "");
    Receipt.Write(Label + "###" + ValueText + "###" + TypeMarker + Chars.LF);
EndProcedure
```

- **Encode value AND type per line (`label###value###type`).** A bare `label###value` receipt CANNOT
  distinguish `Undefined` from the empty string `""` (both print as nothing) — a 2026-08 owner review
  flagged this exact gap. With the type marker the receipt is unambiguous: `tab######Undefined` is
  `Undefined`, `tab###1234###Number` is a Number, and a blank value with a non-Undefined type is a
  formatting error. The validator must assert exact value+type per case (not just "RED differs from
  GREEN" — that accepts `banana/pear` nonsense as "mutation power"), the full label set, and no
  duplicates/extras.

- The probe is test instrumentation, NOT the feature. It lives only in the throwaway work copy and must
  not be part of the shipped production function. Keep the production function pure (no file I/O).
- **Scope honesty:** calling the probe from `OnStart` then `Return`-ing proves the *target function*
  executes, NOT the full application lifecycle (startup dialogs, subsystem handlers, shutdown). State this
  explicitly as a boundary — a reviewer will (correctly) flag a claim of "the app's lifecycle" when you
  only proved one function. It's an intentional narrowing: you want to prove the function runs, nothing more.
- **Receipt bytes are platform-produced.** 1C's `TextWriter` normalizes `Chars.LF` to `\r\n` on write, so the
  persisted receipt contains CRLF even though the BSL wrote `Chars.LF`. Copy the receipt out byte-for-byte
  (`shutil.copyfile` / `cp`) and do NOT re-encode — the CRLF is what the platform emitted, and this is the
  machine-readable evidence. A reviewer may probe "why CRLF if you wrote LF?" — the answer is the platform's
  `TextWriter`, and the raw runtime errors in `/Out` (e.g. `Object method not found`) are the independent
  proof BSL actually executed, independent of receipt byte details.
- Write the receipt to a path under the run's `HOME` (a path 1C owns), not a speculative absolute path;
  and create the `tmp/` dir `xvfb-run` needs (`xvfb-run` errors `mktemp: failed to create directory via
  template ... /tmp/xvfb-run.XXXXXX` if `TMPDIR`'s target doesn't exist).
- **`TextWriter.WriteString` is NOT a valid method** on this platform (raises
  `Object method not found (WriteString)`). Use `.Write(...)`. `TextEncoding.UTF8` is fine.
- **Receipt readiness must be semantic, not `-s`/nonempty.** Constructing a UTF-8 `TextWriter`
  can create a 3-byte BOM-only file before the business scenario finishes. A poller that treats any
  nonempty file as success can kill ENTERPRISE mid-transaction and publish a false result. Require a
  unique terminal marker (for example `complete###true`), the exact scenario ID and case cardinality,
  no error marker, then confirm the full-file hash is stable across two delayed reads. Only after all
  checks pass may the process group be stopped. A BOM-only or structurally incomplete receipt is a
  failed attempt; preserve it diagnostically and use a fresh disposable IB because partial side
  effects are unknown.
- Run RED (original code) and GREEN (patched code) with the SAME probe into two persisted receipts, then
  diff them. That is the mutation-power evidence.
- For data-backed document posting probes, also see `references/data-backed-document-write-probes.md`.
  It captures the issue-14 lessons: explicitly set `Document.Date` before `Write()`/posting, record
  draft-vs-posting state plus register movements/balances, wait for `complete###true`, and handle CRLF/LF
  patch/receipt publication without overstating byte equality.

## Pitfalls that cost real time

- **Training-edition connection cap.** `Training version limitation reached / Infobase connections
  limitation reached` == the educational edition's connection allowance is exhausted. The usual cause is
  an **orphaned client child**: killing only the `xvfb-run` wrapper leaves the actual `1cv8t ENTERPRISE`
  child alive, holding a connection slot. `ps`/`pgrep` may be absent — scan `/proc/*/cmdline` instead;
  a hung session may show as a `Z` (zombie) re-parented to PID 1 that SIGKILL does not reap, but a
  **live** `1cv8t ... ENTERPRISE` child is the real slot holder. Fix: SIGKILL the `1cv8t` child directly
  (not the wrapper), and/or **recreate the disposable IB fresh** (`rm -rf` + `CREATEINFOBASE` +
  reload) to clear the stuck session record. This affects timing, not results.
- **Xvfb renderer segfault.** At the default depth 24, a software-rendered container can segfault in
  pixman/cairo (backtrace in `libpixman-1.so.0` → `cairo_mask`). Workaround: `-screen 0 1280x1024x8`
  (depth 8). This only affects the headless display, not BSL logic; if the app then appears to hang,
  it usually means the receipt was written and the client is still up — poll for the receipt and kill.
- **`/DumpResult` is the exit status** — read it from the result file, not the shell rc of `xvfb-run`.
- **Locator drift between source and changed files.** When you add N lines to a module, the same logical
  function's line range shifts: a locator of `Module.bsl:797-828` on the *immutable source* becomes
  `:810-832` in the *changed work copy*. Always state which file a locator refers to, and give both when a
  reviewer may diff them. Recommend giving the immutable-source locator (the contract) and note the offset.
- **Read the actual issue/contract BEFORE choosing a feature.** This session's costliest mistake was starting
  to implement a self-invented feature (extend `StringToNumber`) before reading the real issue body. The
  issue IS the contract: fetch it first (`gh issue view <n> --repo <repo> --comments`), confirm the actual
  scope/acceptance criteria, and pick a feature that genuinely satisfies the stated evidence levels — not one
  that merely feels convenient. Never assume scope from a neighboring issue's content or from the project's
  prior work. A frozen `task-contract.json` (or equivalent) written BEFORE the patch is the contract anchor;
  align the feature and absolute boundaries to it explicitly.
- **Keep the diff to the immutable source minimal and provable**: compare the *whole* work-copy module
  against the snapshot module with `diff` (normalize CRLF) so the "exactly these N lines" claim is
  airtight, and verify source + snapshot hashes with `sha256sum`/`sha256sum -c` (manifest line format is
  `<sha256>  <relative/path>`).
- A fresh `HOME` per run helps isolate session accounting, but the *IB* holds the stuck session, so a
  fresh home alone does not clear the connection cap.
- **Reset persistent terminal environment after native runs.** Hermes terminal exports persist between
  calls. If a 1C command sets `HOME`, `TMPDIR`, `XDG_*`, or `FONTCONFIG_FILE` to a disposable run root,
  later Python tests may create `tempfile.TemporaryDirectory()` under `.local/runs/...` inside the Git
  worktree. `git apply` probes that are intended to run in an isolated temp repository can then resolve
  paths against the parent worktree and fail with misleading patch mismatches. After native runs, restore
  at least `HOME=/home/hermeswebui`, `TMPDIR=/tmp`, and unset `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`,
  `XDG_DATA_HOME`, `FONTCONFIG_FILE`; or pass a clean env explicitly to validation commands.

## Evidence to keep (`.local/runs/<run-id>/evidence/`)

Persist each receipt to a distinct file (a single overwritten path loses one side):
`green-receipt.txt`, `red-receipt.txt`, plus an `EVIDENCE.md` with the exact commands, both receipts,
source/snapshot hashes, the patch locator, and the boundaries (immutable source / writable work copy /
disposable IB / evidence). `task-contract.json` frozen BEFORE the patch records the absolute paths,
expected RED/GREEN behaviour, and forbidden writes — the issue contracts on this.

## "Immutable" is convention + permissions, not a mechanism (verified 2026-08)

A same-uid agent process CAN delete or rewrite `.local/runs/.../snapshot.manifest` (and other source
artifacts): the protection is read-only modes and convention, not a user namespace or immutable FS.
This was demonstrated when an independent reviewer's write-safety probe accidentally deleted the
manifest, then restored it from a byte-identical copy in another run (`training-jet-final/...` showed
the same `70972b5e…` identity) and re-verified 5099/5099 clean.

Consequences for how you run and review:

- **Manifest identity is the truth, not the in-place file.** The SHA-256 of the manifest bytes is
  reproducible across runs (the same dump produces the same identity). If the in-place manifest is
  ever damaged, a byte-identical copy from any run with the same identity is a valid restore — and
  after restore you MUST re-run the full verification (missing/mismatch/extra/symlink = 0) before
  continuing.
- **Give independent reviewers read-only boundaries explicitly** («read-only, не трогайте source»)
  and instruct them to restore-and-reverify if they ever modify anything; then verify the source
  yourself after their pass, before trusting their verdict.
- **Report this as an honest limitation**, never as "source is cryptographically protected". In
  `.local/`, "immutable" means "the agent's discipline keeps it unchanged", and a review finding
  that calls this out is correct — record it in the evidence README / task contract rather than
  arguing it away.
- After ANY external pass (reviewer, another agent, a re-run) re-assert source integrity: CF hash +
  manifest identity + full snapshot sweep, and state the values in the final report.
