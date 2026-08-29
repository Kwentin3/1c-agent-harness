---
name: 1c-enterprise-linux
description: "Use when running or automating 1C:Enterprise on Linux."
version: 1.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [1c, 1c-enterprise, linux, designer, config-dump, infobase]
    related_skills: [systematic-debugging, semantic-contract-testing]
---

# 1C:Enterprise on Linux

Working knowledge for standing up and driving the 1C:Enterprise 8.3 platform
(«1С:Предприятие») on Linux — e.g. for the `1c-agent-harness` project, a read-only
harness that lets a coding agent explore 1C configurations via a native file snapshot.

## When to Use

- Setting up, running, or automating the 1C:Enterprise platform on Linux (server/client/Designer).
- Producing a native file snapshot of a 1C config (`/DumpConfigToFiles`) without GUI automation.
- Choosing a platform version, acquiring a distribution, or diagnosing headless/batch startup.

## Component map — what "1C on Linux" actually means

| Component | Binary | Purpose | Needed for native config dump? |
|---|---|---|---|
| Сервер (cluster) | `ragent` / `rmngr` / `rphost` | client-server mode | No |
| Тонкий клиент | `1cv8c` | connect to bases, **no Designer** | No |
| Полный клиент + Конфигуратор | `1cv8` | thick client + Designer | **Yes** |
| Утилита `ibcmd` | `ibcmd` | create/dump/restore infobase, export config — **license-free** | **Yes (license-free path; in server64, not client distr)** |

Key consequences:
- A **file infobase does not need the server** — the full client (Designer) works on it directly.
- The **Конфигуратор (Designer) batch mode** is the native, no-GUI way to dump a config:

```bash
1cv8 DESIGNER /F"/path/to/ib" /N"user" /P"pass" /DisableStartupMessages \
  /DumpConfigToFiles "/out/dir" -Format Hierarchical /Out"/tmp/dump.log" -NoTruncate
```

- The Linux full client (with Designer) exists since ~8.3.22; confirmed for 8.3.27
  (`setup-full-8.3.27.1606-x86_64.run` installs конфигуратор + толстый + тонкий клиент).

## Version pinning

Pin the platform to the config's compatibility mode. The `1Ci-Company/Jet` smoke fixture is
built on `Version8_3_24`, so the platform must be **≥ 8.3.24** (8.3.27/8.3.28 current as of
2026-08). Old 8.3.10 / 8.3.13 builds will not open a 8.3.24 config.

## Distribution & acquisition

- **8.3.x < 8.3.20**: separate `.deb`/`.rpm` packages (`1c-enterprise83-client`, `-server`,
  `-thin-client`, `-common`, `-ws`, `-nls`) → extract WITHOUT root: `dpkg-deb -x pkg.deb dir/`.
- **8.3.20+** (incl. 8.3.24–8.3.28 AND the «учебная»/training version): the «единый
  дистрибутив» — a single InstallBuilder `.run` (`setup-full-…-x86_64.run`,
  `all-clients-distr-…-x86_64.run`) that **requires root** (hardcoded check + `installAsRoot`
  ELF helper). It is an ELF self-extractor, NOT `.deb`/zip/tar (embedded makeself/bzip2 blobs).
- **No rootless path to a Jet-compatible (8.3.24+) platform**: rootless `.deb` is pre-8.3.20,
  which won't open an 8.3.24 config. Root is needed for INSTALL only — running/dumping are rootless.
- `all-clients-distr` `.run` is client-only and cannot provide Designer. Do not infer server
  components from an installer filename such as `setup-full`: the verified 8.5.1.1150 package
  provided the thick client and Designer but no `ibcmd`, `ragent`, `rmngr`, or `rphost`. Inspect
  the actual installer/component manifest and verify installed binaries before choosing a path;
  `ibcmd` requires a server distribution that explicitly contains it.
- Installs to `/opt/1cv8/` by default; keep a self-contained lab under git-ignored
  `.local/platform/`. In a non-root container with a root-SSH VPS, prefer a one-off
  `docker exec -u root` over installing sudo + NOPASSWD (least-privilege, no persistent change).
- After a root install, do not execute or recursively move/chown through a user-writable Workspace
  from a privileged shell. Stage and verify the installer in a root-owned directory, complete the
  vendor install under `/opt`, establish ownership there, then let the unprivileged Workspace user
  copy the verified tree into `.local/platform/`. Removing the `/opt` duplicate is a separate,
  explicit root action after the local copy has been verified. See the privileged boundary in
  `references/training-edition-lab.md`.
- **Official channels are gated** behind a personal login + license acceptance: `online.1c.ru`,
  `my.1ci.com`, 1C:DN Community License. There is no public GitHub release asset.
- **License reality (verified 2026-08):** the commercial/full `1cv8` can run
  `CREATEINFOBASE` license-free, but its **Designer config ops need a CLIENT license** —
  `1cv8 DESIGNER /LoadCfg` (and `/DumpConfigToFiles`, `/DumpCfg`) fail with `License not found`
  without one. There are two legal license-free lab paths:
  1. **Official training edition** (best for file-infobase development/smoke fixtures): the Linux
     8.5.1.1150 installer is `setup-training-8.5.1.1150-x86_64.run`, installs to `/opt/1cv8t/`,
     and uses suffixed binaries `1cv8t`, `1cv8ct`, `chdbflt`. `1cv8t DESIGNER /LoadCfg` and
     `/DumpConfigToFiles` work without a software license or HASP key. Verified with Jet 1.0.3.1:
     process exit 0, `/DumpResult=0`, 5,099 files / 1,258 BSL files, repeated dumps byte-identical.
     Official page: `https://online.1c.ru/catalog/programs/program/36179915/`; personal form +
     license acceptance yields a one-day download link. Limitations include training/testing only,
     file mode, one session, data-volume caps, no client-server, config repository, COM, or
     distributed infobases.
  2. **`ibcmd`** (console admin tool, ships in the **server64** distr, NOT client `.run`s): per 1C
     docs, `ibcmd infobase create --load=<file.cf>` + `ibcmd infobase config export` work without
     a server license and can produce dumps byte-identical to `/DumpConfigToFiles`.
  Paid/HASP licenses gate commercial `1cv8` Designer operations and running commercial configs.
- Training-edition relocation differs from commercial: after root install, move `/opt/1cv8t`
  to `.local/platform/1cv8t` (moving avoids a 2.5 GiB duplicate), chown it to the workspace user,
  and invoke `.local/platform/1cv8t/x86_64/<version>/1cv8t`. The same GTK/Xvfb/fontconfig stack
  applies. Keep training and commercial trees separate; do not rename `1cv8t` to `1cv8`.
  The verified Jet smoke procedure, provenance, evidence semantics, minimal `xvfb-run`
  workflow, and exact pinned-Python-adapter invocation are in
  `references/training-edition-lab.md`. Read that reference before adding code: for an
  issue-level lab, direct native commands are preferred to a bespoke wrapper/supervisor.
  For documentation-only issue closure, staged-artifact review, post-merge tree binding,
  required provenance, clean-bootstrap claims, and stale-contract checks, use
  `references/lab-spec-compliance-review.md`. After the user authorizes publication, use
  `references/github-closure-handoff.md` to bind the reviewed commit to
  the PR, merge, issue closure, branch cleanup, and preserved `.local/` handoff evidence.
- **HASP key emulators (e.g. HASPEMUL) are license circumvention — decline to install/use them.**
  They conflict with the project's «законно доступная» requirement and aren't needed to dump.
- Non-official acquisition (torrent/mirror) is a **user decision**. Provenance posture: record
  source + SHA-256, but there is **no vendor signature** — never present it as official provenance.

## Rootless GUI dependency provisioning (no `apt install`)

Minimal containers lack the GUI stack the Конфигуратор needs even in batch mode. Fetch the
`.deb`s into a local lib root WITHOUT root and load them via `LD_LIBRARY_PATH` (verified → `ldd`
clean for 1C 8.5). Dependency mapping is in `references/gui-deps-8.5.md`; the clean-rebuild method,
signed timestamped snapshots, APT-hook isolation, extraction-order rule, XKB publication boundary,
and validated smoke evidence are in `references/reproducible-debian-runtime.md`.

The snippet below is an exploratory dependency-discovery pattern, not a reproducible release
recipe. For issue closure or a clean-workspace promise, use fixed HTTPS Debian snapshots, exact
`name=version` arrays, isolated APT dirs, and explicitly neutralize both inherited
`APT::Update::Post-Invoke` hooks. Rebuild into a new empty runtime and rerun full native smoke after
any package/source/order change.

```bash
APTBASE=.local/tools/aptroot
mkdir -p "$APTBASE"/{etc/apt,state/lists/partial,cache/archives/partial}
cat > "$APTBASE/etc/apt/sources.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] http://deb.debian.org/debian bookworm main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] http://deb.debian.org/debian-security bookworm-security main
EOF
O="-o Dir::Etc::sourcelist=$APTBASE/etc/apt/sources.list -o Dir::Etc::sourceparts=- \
   -o Dir::State::lists=$APTBASE/state/lists -o Dir::Cache::archives=$APTBASE/cache/archives \
   -o APT::Get::List-Cleanup=0"
apt-get $O update
apt-get $O -t bookworm download <pkg>...     # .debs land in cwd
LIBS=.local/platform/libs
for d in *.deb; do dpkg-deb -x "$d" "$LIBS"; done
export LD_LIBRARY_PATH="$V:$LIBS/usr/lib/x86_64-linux-gnu:$CR/root/usr/lib/x86_64-linux-gnu:$CR/root/usr/lib"
```

Loop: `ldd "$V/1cv8" | grep -i 'not found'` → map each missing `.so` to its Debian package
(watch `.so.N` suffixes and t64 renames) → download → re-run until clean. `apt-get download`
does NOT resolve dependencies, so the loop is mandatory. Pin `-t bookworm` so the whole
ABI-matched set (e.g. ICU 72) comes from one release instead of mixing trixie/bookworm.

## Headless / batch pitfalls

- The Конфигуратор pulls GUI libraries even in batch mode and needs a display (GTK must
  initialize) → run under `xvfb-run` or a manual Xvfb. **8.3.x links GTK2** (`libgtk-x11-2.0.so.0`);
  **8.5.x links GTK3** (`libgtk-3.so.0`) + WebKit2GTK 4.0 — do NOT chase `libgtk2.0` for 8.5.
- **Xvfb needs `xkbcomp`**: it shells out to a hardcoded `/usr/bin/xkbcomp` (compiled-in
  `XKB_BIN_DIRECTORY`; `strings` shows only `xkbcomp`, not the full path). Missing it →
  `Fatal server error: Failed to activate virtual core keyboard`. `xkbcomp` is in `x11-xkb-utils`,
  keymap data in `xkb-data`; both normally live under `/usr`. `-kb` is NOT a valid Xvfb flag.
  For a trusted single-user lab, prefer the bundled `xvfb-run -a` with `xauth` and `-nolisten tcp`;
  it was validated with the training edition and avoids bespoke display/PID orchestration. Do not
  probe guessed display sockets manually. If hostile same-uid races are in scope, treat process,
  filesystem, and X isolation as a separate reviewed architecture (pidfds/dirfds or an established
  supervisor), not a shell-script hardening exercise. `-xkbdir <dir>` overrides only the DATA dir,
  not the xkbcomp binary path. Child library dependencies resolve through inherited
  `LD_LIBRARY_PATH`.
- **Debian 13 (trixie) is newer than what 1C ships against** — expect lib conflicts. Two real
  traps: `libgtk-3-0` was renamed `libgtk-3-0t64` (t64 transition), and WebKit2GTK 4.0
  (`libwebkit2gtk-4.0-37`, `libjavascriptcoregtk-4.0-18`) was dropped from trixie (only 4.1
  remains). Pin those deps to **bookworm** with `apt-get download -t bookworm`.
- **fontconfig**: 1cv8 segfaults (`Fontconfig error: Cannot load default config file` + core
  dump) without a font config. Rootless fix: extract `fonts-dejavu-core` + `fontconfig-config`
  debs, then set `FONTCONFIG_FILE` to a minimal config with a `<dir>` at the fonts + a writable
  `<cachedir>`. Also expect `sh: /sbin/ip: not found` noise — the platform calls `/sbin/ip`
  during license checks (absent in minimal containers; harmless).
- Always pass `/Out ... -NoTruncate`: the Designer writes the real error cause to that log.
- Installer/message output is cp1251 (shows as `????` under UTF-8). Decode with
  `iconv -f cp1251 -t utf-8` or pass `--installer-language en` for readable diagnostics.

## Static snapshot evidence audits

When auditing a hierarchical configuration dump with metadata and BSL indexes, read
`references/static-snapshot-index-audits.md`. It defines immutable-output boundaries, source
cross-checks, handling of partial AST outlines/false negatives, exact declaration counting,
and the rule that usages are navigation candidates rather than a call graph. Stop additional
rebuilds and broad searches once material facts are independently verified and the user says
the evidence is sufficient.

For a dual-agent or second-human acceptance lane where independence from existing answers,
oracle, ledger, and primary-review notes is contractual, also read
`references/independent-frozen-snapshot-acceptance.md`. It defines the independent-first reading
boundary, an outside-repository hashed view checkpoint, bidirectional package comparison,
oracle/task construct-mismatch handling, dangerous-claim additions, and the final no-more-reads
snapshot continuity gate.

When a smoke/demo fixture is not representative enough, read
`references/representative-config-selection.md`. It defines license/NOTICE checks, pinned-SHA
complexity measurement without large downloads, oracle grading, compatibility-mode versus
old-runtime boundaries, and a researched shortlist of public business configurations.

When freezing a smallest-possible synthetic split-source metadata benchmark without running 1C
at selection time, read `references/minimal-synthetic-metadata-task-freeze.md`. It covers immutable
snapshot identity, narrow public contracts, exact private oracles, deterministic UUIDs, deferred
native acceptance, dangerous distractors, and checksum closure.

For a **blind candidate arm** that must solve a minimal metadata task without oracle, prior-attempt,
history, or network leakage, read `references/bounded-frontier-metadata-candidate.md`. It defines
task/content/manifest binding, logged self-derived searches, byte-addressed source fragments,
bounded sibling expansion, sufficiency gates, a physically separate work copy, binary-safe diff,
changed-file closure, final manifest continuity, and read-only evidence freezing.

For the simpler **direct-source baseline** variant, read
`references/blind-metadata-arm-freeze.md`. It focuses on temporary handling of copied read-only
modes, byte-preserving minimal edits, exact one-file hash/diff closure, contract context and metric
accounting, removal of construction helpers, derived-byte recomputation, and the final
immutable/git continuity pass.

## Write-cycle: change a config and prove it runs (not just dumps)

Generic business-rule semantics and evidence-tier policy belong to the separate
`semantic-contract-testing` skill. Load it before choosing cases or implementation. This skill does
not duplicate that method; it owns only the 1C/Linux execution boundary and 1C-specific observation
adaptations. For document posting, those adaptations are in
`references/data-backed-document-write-probes.md`: draft versus posting state, explicit `Date`,
`Posted`, recorder movements, register balances, and platform-produced receipts.

For the issue-10-style R&D task (understand → patch → load into an isolated IB → prove new
behaviour), read `references/native-write-cycle-runtime.md`. It covers the three evidence levels
(platform accepted / behaviour runs / test not tautological), the exact `CREATEINFOBASE` +
`DESIGNER /LoadConfigFromFiles /UpdateDBCfg` + `xvfb-run ENTERPRISE` commands on the training
edition, the **probe-in-managed-app-module** pattern for executing config BSL headlessly and
emitting a machine-readable receipt, and the pitfalls that cost time: the stale-client-child cause
of `Infobase connections limitation reached`, the depth-8 Xvfb workaround for the pixman/cairo
segfault, `TextWriter.Write` vs the invalid `WriteString`, and keeping the diff-to-source minimal
and provable. For data-backed document posting probes (draft vs posting, explicit `Date`, recorder
movements/balances, patch/receipt line-ending hygiene, and repeat-run comparison), also read
`references/data-backed-document-write-probes.md`. For the tight final review lane over a completed
tracked evidence package at an exact HEAD/TREE, read
`references/final-bounded-evidence-review.md` before broadening into native reruns or `.local/`
exploration.

To turn that experiment into a committed, unit-tested, re-runnable driver rather than a one-off,
read `references/write-cycle-driver-automation.md`. It covers splitting pure logic (receipt parse /
mutation-power analysis / snapshot verify / patch-probe injection) so it tests without 1C, the
driver-automation pitfalls that cost real time — `Path.read_text()` silently swallowing CRLF so
`\r\n` anchors never match, `/DumpResult` carrying a UTF-8 BOM (decode `utf-8-sig`), the managed-app
module having TWO `#EndRegion` (use `rfind`, first-match inserts the probe in the wrong region),
guarding a double-patch against the exact block instead of a bare substring, killing the whole
process tree (`start_new_session` + `os.killpg`) so the `xvfb-run` wrapper's child doesn't hold the
connection slot, generating diff files in byte mode (text mode strips CR and `git apply` then fails),
and the guideline that a driver must be verified to actually run the cycle once, not just lint.

A driver is NOT the default deliverable, though: when an owner review rejects a big driver
("не латать бесконечно"), the resolution is to delete it and ship a **frozen evidence package +
fail-closed validator**. Read `references/frozen-evidence-package.md` for that shape: sanitized
task contract, production/instrumentation/full diffs, receipts with value AND type, native-result
excerpts, hash manifest excluding itself, exact-statistics validator, private-path scan, and the
honest-limits section. The evidence-package pattern also applies to `tests/test_review_package.py`-
style public review packages beyond 1C.

## Workspace convention (this project)

- Dedicated project folder = the Hermes **workspace** = the **git root** (no nested workspace).
  Do not move the git root up into a shared `/workspace` that also holds Hermes-internal dirs.
- Machine-local data lives under git-ignored `.local/`: `dist/ platform/ fixtures/ tools/ runs/ cache/`.
- Read-only relative to the source config and infobase — changing the source is a failed experiment.
- When a user executes root operations through Windows PowerShell → SSH → `docker exec`, provide
  either one genuinely single-line command or an interactive container shell followed by short
  commands one at a time. Never present a visually multiline quoted `bash -c` payload as though it
  were safely copyable; broken quote boundaries can leave the remote shell waiting for more input.

## No-sudo tooling

`references/acquisition-and-tooling.md` has verified recipes: a no-sudo static `aria2c` install
(torrent downloads) and a no-sudo headless-Chromium lib-bundling setup, plus the Cloudflare
handoff pattern for gated logins.
