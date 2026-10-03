---
name: 1c-enterprise-linux
description: "Use for 1C XML/BSL analysis and Linux platform automation."
version: 1.6.2
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [1c, 1c-enterprise, linux, xml, bsl, configuration-analysis, designer, config-dump, infobase]
    related_skills: [systematic-debugging, semantic-contract-testing]
---

# 1C:Enterprise on Linux

Working knowledge for standing up and driving the 1C:Enterprise 8.3 platform
(«1С:Предприятие») on Linux — e.g. for the `1c-agent-harness` project, a read-only
harness that lets a coding agent explore 1C configurations via a native file snapshot.

## User-facing status updates

When reporting progress, a blocker, or the outcome of a 1C lab task to this user, start in plain Russian without internal jargon. Lead with: **what currently works**, **the one concrete blocker**, **why it prevents the next step**, and **the smallest action that unblocks it**. Keep exact paths, hashes, process names, and chronology as optional supporting detail rather than the main explanation. Do not bury a simple answer under a review timeline or repeat a long technical receipt unless the user asks for it.

## When to Use

- Setting up, running, or automating the 1C:Enterprise platform on Linux (server/client/Designer).
- Investigating or planning a 1C configuration/business-rule change from XML/BSL before any platform launch or production edit.
- Producing a native file snapshot of a 1C config (`/DumpConfigToFiles`) without GUI automation.
- Choosing a platform version, acquiring a distribution, or diagnosing headless/batch startup.

### Discovery-routing maintenance

This skill has two complementary front doors: **XML/BSL investigation or change planning** and **Linux platform running/automation**. When revising its front-matter description, preserve both triggers in one additive description. `When to Use` inside the body does not replace metadata-based discovery, which may be the only routing information inspected by a fresh agent.

### Fresh-agent evaluation boundary

When evaluating whether ordinary user language routes a new agent to sufficient 1C context, keep skills **enabled** and let normal discovery choose them. Do not name the desired skill, module, source locator, expected patch, prior answer, or reviewer countermodel in the fresh task prompt. A coordinator may provide only non-semantic environment access needed to reach the canonical target.

Before dispatching the fresh agent, freeze a source-derived task-selection note: canonical target identity and readiness, the real XML/BSL locators used to select the task, why it differs from previously evaluated scenario families, the intended business observation, closest bypass/preservation surfaces, and the bounded native budget if native work may later be admitted. Publish the ordinary-language task separately from that note.

If the experiment requires the **same** fresh agent to do both a scored preflight and a later native phase, preserve its execution continuity before dispatch: use a single runner that can pause at an explicit review gate and resume only after admission. A bounded leaf/subagent that terminates after returning its preflight cannot truthfully become that same executor later. Do not feed its preflight or review back to a replacement agent and label the continuation autonomous; either rerun the full scenario end-to-end with one retained executor, or record first-pass evaluation and native continuation as separate evidence lanes.

When a goal-style issue explicitly supersedes an older step-by-step thread, keep the coordinator and fresh-executor inputs separate. The coordinator may read the live goal, land accepted prerequisites, create a clean exact-base task-owned worktree, and prove generic target/runtime readiness. The fresh executor should receive only the ordinary business request plus non-semantic access facts (repository/worktree location, authenticated route, immutable/disposable boundaries). Do not pass the issue number, historical comments, earlier preflight, locators, expected patch, skill names, or review conclusions merely because the coordinator needed them for orchestration. Record exact base commit/tree before dispatch, and retain that same executor through implementation and native acceptance.

For an accepted stacked prerequisite, land it in dependency order, retarget the upper PR to the updated base, and verify the final base tree equals the accepted head tree before dispatching the fresh executor. A green component PR is not enough: read back the final default-branch commit/tree and CI for that exact merge result. This is prerequisite admission, not semantic assistance to the fresh task.

When a successor Goal is conditional on that landing, treat the transition as one fail-closed admission sequence: verify the accepted PR head/tree and exact-head checks, merge only under the explicit owner decision, require the merge commit's tree to equal the accepted content tree, wait for post-merge CI on that merge SHA, complete any required predecessor issue verdict/closure, and only then create the successor branch or start its clock. Keep merge authorization scoped to the predecessor; it never carries forward to the successor PR.

Do not assume `git fetch origin main` updated `refs/remotes/origin/main`: repositories may have a deliberately narrow `remote.origin.fetch` refspec, in which case only `FETCH_HEAD` moves. Inspect the configured refspec and, when an exact tracking ref is required for identity checks, fetch explicitly as `refs/heads/main:refs/remotes/origin/main`; cross-check the merge SHA/tree through the authenticated GitHub API before acting. A stale local tracking ref is a local verification defect, not evidence that GitHub merged the wrong content.

If the canonical target lives on a remote executor, verify the configured pinned remote route and run the project readiness command there before declaring the target unavailable. Do not infer a remote outage from a failed local-loopback connection or substitute a similar local fixture. The fresh agent can receive the established access route as environment access, but not task-specific source facts.

A remote executor checkout is also an identity boundary. Before a fresh executor uses it, verify that its Git `HEAD` and tree equal the successor's admitted current `main`, and that it is clean. An old or dirty checkout may have a ready CF, snapshot, and platform but cannot evidence the current task. Preserve that checkout; create a separate task-owned remote worktree at the exact current `main`, copy only the required canonical target assets into its task-owned `.local/`, and rerun the project readiness command there. Give the fresh executor only the isolated route and target location—not historic locators, patches, probes, or oracle design.

## 1C pre-native context gathering

For a new business-rule task, load `semantic-contract-testing` and investigate the real XML/BSL snapshot before launching 1C. Keep the search bounded by the task and feed only relevant 1C facts into the generic pre-native Markdown gate:

1. Identify the actual execution layer: form/client handler, server common module, object or record-set module, manager module, posting handler, or background/integration entry point. A name match is only a lead.
2. Trace one current scenario from its callable entry point through normalization, predicates, reads/writes and observable business state. Cite repository-relative paths and line ranges for every material step. For every distinguishing case feed the semantic gate an explicit **pre-state → input/action → expected persisted/business post-state**.
3. Trace omitted/default values and their normalization to the predicate that consumes them. A default branch without a relevant pre-state is not a distinguishing case.
4. Inspect the nearest bypass and preservation surfaces: direct server calls that bypass UI checks, transaction and lock boundaries, write/posting hooks, existing validations, and one similar neighboring object or caller when it can change the conclusion. Limit the conclusion to the actually investigated API/execution layer and name nearby writers it does not cover.
5. Validate every proposed observation against the actual target metadata, especially tabular sections. `FillPropertyValues` can receive a selection containing fields that exist on the document header but not on a tabular-row target; it does not prove that every selected field is present or populated in every target. Cite the relevant child attributes in XML and, for native work, invoke the actual fill route and observe only real fields. Do not infer a row field from a similarly named document header field.
6. Include types, units, rounding, tax, currency, dates, posting movements, or register balances only when the task or sources make them relevant. For persisted behavior, observe the resulting object/register state rather than only messages or process exit. If task language requires no physical write or side effect, identify a reproducible witness or a static acceptance constraint; unchanged scalar alone does not prove that no-op.
7. Stop when the current path, two plausible wrong implementations, distinguishing observations, preserved behavior, required no-op witnesses or constraints, and material unknowns are supported. Do not survey the whole configuration and do not invent a requirement from an object name.
8. For a fresh read-only first pass, return publication-ready Markdown rather than a discovery transcript. Include the selected skills; `native attempts`, modified-file, and owner-intervention counts; the exact `project_target.py` payload; duration measured by a tool; and snapshot-relative line locators. Keep facts, expected post-states, and unknowns separate. Do not claim a native result when `native attempts=0`.
9. When rejected posting must leave no movements, bind the acceptance observation to recorder-scoped records in every declared target register. Before native work, identify the earliest validation point before record-set preparation, reflection, and writes; a late `Cancel` is not enough unless its no-write semantics are evidenced.

If the apparent rule exists only in a form while a server path can still write the data, report that gap and use `CONTEXT BLOCKED` unless the task explicitly concerns UI behavior. Likewise, if a required no-write/no-side-effect no-op lacks a witness or static acceptance constraint, retain it as unknown and use `CONTEXT BLOCKED`; do not redefine no-op as unchanged persisted state. This gate authorizes only the next bounded native experiment; it does not authorize a production patch or claim semantic correctness.

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
  **Check the exact build's dependencies**, not a blanket 8.5 rule. The historical lab used
  GTK3 and a WebKit2GTK 4.0 bundle, but inspection of the retained 8.5.1.1150 training
  `libwx_gtk3u-3.0.so.0` now shows a required `libwebkit2gtk-4.1.so.0` through `ldd`.
  Do not prescribe a cross-release 4.0 bundle or change the OS from that old recipe
  without checking the admitted binaries. Neither dependency inspection nor clean `ldd`
  proves web-client readiness. Do not chase GTK2 merely because older releases used it.
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
- **Historical Debian 13 lab caveat:** `libgtk-3-0` was renamed `libgtk-3-0t64`,
  and the old WebKit2GTK 4.0 package bundle came from bookworm. That is a retained
  laboratory recipe, not a requirement for every 8.5 binary or a default web bootstrap.
  Check the actual required SONAME and prefer the prepared OS package environment;
  use the old pinned bundle only in its explicitly admitted historical scenario.
- **fontconfig**: 1cv8 segfaults (`Fontconfig error: Cannot load default config file` + core
  dump) without a font config. Rootless fix: extract `fonts-dejavu-core` + `fontconfig-config`
  debs, then set `FONTCONFIG_FILE` to a minimal config with a `<dir>` at the fonts + a writable
  `<cachedir>`. Also expect `sh: /sbin/ip: not found` noise — the platform calls `/sbin/ip`
  during license checks (absent in minimal containers; harmless).
- Always pass `/Out ... -NoTruncate`: the Designer writes the real error cause to that log.
- Installer/message output is cp1251 (shows as `????` under UTF-8). Decode with
  `iconv -f cp1251 -t utf-8` or pass `--installer-language en` for readable diagnostics.

## Read-only feasibility audits for Test Manager / Test Client

When assessing whether Test Manager/Test Client can become a headless transport, keep three conclusions separate: **documented platform capability**, **historical/runtime inventory**, and **what the current executor can launch**. Do not infer the third from either of the first two.

1. Read the issue contract and existing lifecycle runner before inspecting binaries. A normal single-`ENTERPRISE` runner may own a process group and a receipt safely but still be unsuitable for a two-client, TCP-port-bound arm.
2. Inspect actual executable paths and testing components in the current executor; also run the project-target preflight. A missing target asset or unavailable binary is a current-executor block, not evidence that the platform feature is unsupported. Do not launch 1C during a read-only audit.
3. Official sources establish only the limited mechanics: `/TESTMANAGER` launches a Test Manager; `/TESTCLIENT` launches a Test Client; automated testing is manager/client interaction. The historical ITS example documents manager launch as `ENTERPRISE /F <IB> /TESTMANAGER` and a client `/TESTCLIENT` launch. A testing port (`-TPort`) is documented for their interaction, but **verify exact manager-side syntax against restored exact-version help/docs before freezing argv**; do not guess option placement from a different release. The flag pair is not a generic command-line RPC or external-script runner: official material describes the manager as running a 1C test algorithm while the test client reproduces its interactive actions.
4. Before admitting a smoke, require a disposable manager-side BSL test algorithm and a corresponding target/test-client task route. They must consume the fresh request identity, direct the one test case, reach the requested server layer, and produce the declared client response plus server witness. A component inventory (for example `test*.so` and launch binaries) removes only the missing-runtime-component block; without the task algorithm/instrumentation it is **CONTEXT BLOCKED**, not platform-unsupported or a scored capability failure. Do not assert that dedicated testing metadata is inherently required when docs show an authored BSL algorithm is sufficient; either form of absent task asset is nevertheless an admission block.
5. Treat the pair as an admissible capability candidate, not a generic externally documented RPC. Its one smoke must prove current-run request binding, required server-layer reach, and a no-manual-GUI response; otherwise report capability failure rather than silently falling back to an OnStart probe. Automated testing may avoid manual interaction once authored, but it operates against a client logical model/forms; do not claim an exact Linux training runtime works display-free until that exact headless condition has been evidenced.
6. Use a dedicated **one-shot supervisor, not a persistent service**. Predeclare one fresh high loopback port, exact manager/client argv, each leader PID plus `/proc` start time, and a unique run marker. On terminal response or fixed timeout, terminate/reap only processes/listeners matching that marker and PID/start-time, wait for port release, and record cleanup failure even if late cleanup succeeds. Never kill an unmarked survivor: report an external collision.
7. Use fresh non-reused run/case/nonce identities. Accept success only from strict fresh client and server receipts whose matching token is generated after server entry and differs from the nonce. Process exit, Designer load, stale receipt, or client echo never proves server execution. Keep the smoke harmless: generated instrumentation contains no object creation/write/posting or `Execute`/`Eval`; static source closure must prove the server-only witness writer.

When reporting, state the executor/date for historical inventories, explicitly say that embedded `test*.so` files do not prove a headless round trip, and list current prerequisites as blockers without turning them into permanent platform limitations.

## Project-target open boundaries

When one public command must reuse, admit, or materialize a project-declared 1C source into a persistent data-only `SnapshotRef`, read `references/project-target-open-boundary.md`. It covers single-owner admission, source binding, directory-lock serialization, atomic retained publication, typed blockers, capability/process cleanup, warm determinism, and exact-tree CI wording without creating a source/plugin framework. For the concrete no-escape cleanup invariant and sentinel regression proof, also read `references/project-target-owned-cleanup.md`.

### Runtime ownership and final-canary discipline

Keep the CF lifecycle algorithm (`CREATEINFOBASE` → `/LoadCfg` → `/DumpConfigToFiles`, exit/`DumpResult` checks, isolated HOME/TMP, process/work-root cleanup and snapshot construction) inside the harness. The external boundary is only a pre-provisioned 1C/Xvfb/libs/license runtime; never replace this with an executor-owned `cf_to_hierarchical_snapshot` executable.

A generic materializer must not embed a fixture name, platform version, or guessed remote route. Use exactly one simple executor-level runtime locator (one environment variable, one local ignored contract, or one established convention), selected autonomously; do not add fallback chains, discovery frameworks, registries, providers, or runtime data to the project contract or `SnapshotRef`.

Historical native receipts prove a route was valid then, not that the current executor is capable. If no current capable executor/route has been provided, finish all source-only correction and no-1C process-seam tests, publish exact draft HEAD/TREE and CI, and retain one blocker only for the final canary. Do not ask the owner repeated architecture questions or launch a native attempt against an incapable executor.

For that final canary, use the exact pinned CF directly and read-only unless the platform demonstrates a technical blocker. The acceptance sequence is one cold public `open` (successful platform exits and `DumpResult`, source SHA unchanged, declared admitted identity/file count, disposable roots/processes cleaned) immediately followed by one warm `open` (same `SnapshotRef`, `action=reused`, no native launch, ≤10 seconds). The warm call is not a second native attempt.

## Read-only snapshot search routes

When adding a daily text search command over an admitted hierarchical snapshot, keep the route as `project_target.py open → SnapshotRef → search`:

1. `open` remains the single owner of source selection, contract, retained-storage layout, and admission. The search CLI must accept only the data-only `SnapshotRef`; never add a public raw-directory alternative.
2. Put any required consumer resolver in the target domain. It should validate the exact reference and perform one retained-target admission, then return only the manifest-declared read surface required by consumers. The search command must not duplicate contract/layout parsing or call target admission both before and after an otherwise read-only scan.
3. Keep daily product behavior separate from acceptance measurement. Do not hard-code a canary SLA/deadline into the search protocol merely because an issue has a performance threshold. Measure the full `open → search` route externally in the exact-head canary; preserve fail-closed validation, deterministic output, and byte bounds in product code.
4. Begin V1 with only observed formats (normally `.bsl` and `.xml`), deterministic lexicographic ordering, relative paths and line numbers, literal/regex modes, safe relative prefix filtering, and a bounded stdout contract that includes the final newline. Expand formats only after a demonstrated task need.
5. Document a copy-paste `open → search` example in the repository README, including saving `project_target.py open` JSON as a task-local `SnapshotRef` file and passing it to search. This is the discoverable fresh-executor front door.
6. A compact static canary must run without system `rg`, network, or native 1C; use a retained warm SnapshotRef, real BSL plus XML surfaces, repeated byte-identical stdout, and unchanged manifest/process witnesses. The ≤10-second acceptance criterion belongs to this external measurement, not a product timer.

Do not add an index, cache, graph, parser, MCP, service, registry, framework, or reviewer cycle merely to implement this route.

## Read-only Document context inspectors

When adding a bounded inspector over an admitted hierarchical snapshot, preserve the existing project-target boundary rather than accepting a second raw-directory route:

1. The public CLI accepts only a data-only `SnapshotRef` produced by `project_target.py open` (a file or explicit serialized input). Compare it to the current project contract and delegate retained-target validation to the existing admission owner. Do not duplicate manifest/admission logic, expose `--snapshot <directory>` as a parallel public contract, or embed native/runtime knowledge in the inspector.
2. Treat `confirmed` relations as structural XML facts, not token matches. Freeze a small allowlist of source positions appropriate to the claimed relation type (for example, a configuration child object, a role object/name entry, an event source, or subsystem content item). A comment, description, or arbitrary text node containing the same metadata token is a candidate or unknown, never confirmed.
3. Support both ordinary English and Russian BSL procedure/function delimiters in a lightweight outline. This is not a BSL AST. If the outline grammar cannot recognize a common construct, distinguish unknown/incomplete extraction from a truly empty module.
4. Locator generation must be occurrence-aware: repeated `Name`, `DataPath`, or handler values in one XML file must not all cite the first matching line. Keep locators snapshot-relative and deterministic.
5. Measure the whole agent route, not just the front-door JSON. Compare aggregate-to-aggregate against the frozen baseline; include every necessary subsequent source read/search used to establish owner, procedure, dependencies, and patch boundary. A locator is navigation, not the procedure body. If an external precedent is required, account for its read too. Never multiply a baseline that already aggregates the evaluation tasks, and do not shrink useful output or omit required reads merely to reach a threshold. If the honest route misses the product threshold, return `NO MATERIAL WIN`.
6. The read-only canary is static: run on an exact frozen head through `SnapshotRef`, make no native 1C invocation, require deterministic repeated output and unchanged admitted manifest, and run Python deprecation warnings as errors when ElementTree truthiness may be involved.

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

For a **frozen multi-arm comparison of context front doors** (direct source, index, or a narrowly admitted external skill), read `references/frozen-context-frontdoor-comparison.md`. It covers candidate admission before score, immutable-copy index boundaries, one hashed blind protocol, fresh isolated executors, accounting cold setup separately from task time, and winner-only native follow-up.

For the simpler **direct-source baseline** variant, read
`references/blind-metadata-arm-freeze.md`. It focuses on temporary handling of copied read-only
modes, byte-preserving minimal edits, exact one-file hash/diff closure, contract context and metric
accounting, removal of construction helpers, derived-byte recomputation, and the final
immutable/git continuity pass.

### Restricted direct-rg comparison lanes

When a frozen comparison lane permits only a wrapper around `rg` plus a wrapper around ranged
file reads, treat that wrapper as the complete source front door: do not substitute normal file,
Git, index, browser, or repository-history tools. Search first, then ranged-read only paths found by
those searches, and account distinct files per business task against the stated cap.

When the allowed front door instead includes `search`, `collect`, and `read`, run one cheap
task-derived seed search first. As soon as that yields a probable canonical `Document.<Name>`, call
`collect` immediately with schema version 1, task-derived focus strings, candidate metadata/term
seeds, and the declared limit; do not continue broad discovery. Treat the packet's locators as the
read authorization, and read only those paths/ranges or locators returned by a subsequent permitted
narrow wrapper search. Do not inspect wrapper caches, terminal-output files, Git, or the snapshot
directly. Once the coordinator closes discovery, make no further source calls: serialize the
required machine schema from the evidence already obtained.

With an absolute snapshot root, wrapper-forwarded ripgrep globs may need a leading `**/` (for
example `**/Documents/Example/**`); a snapshot-relative-looking glob can validly return zero even
when the object exists. In the restricted wrapper, place `--glob GLOB` **before** the one PATTERN
argument (`search --glob "**/Documents/Example/**" "Posting"`): a trailing glob may be parsed as
a second pattern and fail with `one pattern required`. Broad alternations may also report a large
total while displaying only a prefix. Resolve both cases by narrowing to object-specific paths and
owner/module patterns rather than widening into unrelated source. For posting invariants, establish
the owner from document metadata plus the object-module posting entry, identify the earliest point
before record-set preparation/reflection/write, and keep native no-movement behavior explicitly
unknown unless it was actually exercised. When that entry unconditionally calls record-set
preparation or writing, a rejection branch must set `Cancel = True` **and immediately return**
before those calls; passing `Cancel` only to reflection helpers can still leave a subsequent
unconditional record-set write (or clearing of prior recorder records) reachable. Keep the
comparison in `Posting`, not a form `BeforeWrite` hook, when the rejected object must remain saved
as an unposted draft.

If the coordinator or user says to finish without opening new search directions, stop discovery
immediately, serialize the required machine-readable result from evidence already gathered, and
return only the requested compact handoff. Do not add a verification read that violates the
closed-search instruction merely to produce a more elaborate receipt. When the required handoff is
strict JSON, emit exactly one parseable JSON object with no Markdown or explanatory prose; include
a snapshot-relative locator for each material conclusion and classify unexercised runtime behavior
as `unknowns`, rather than turning static inference into a claimed native result.

### Collector-gated task-driven context passes

When an isolated lane admits only `search`, `collect`, and `read`, those wrappers are the complete
source boundary. Start with a cheap task-derived seed search; once it reveals a plausible canonical
`Document.<Name>`, immediately call `collect` with that exact `metadata` seed and only a small set
of task-derived focus terms. Do not keep broad-searching after the document candidate exists. A
collector that requires a `Document.<Name>` metadata seed will not accept lexical terms as a
substitute, so preserve the specified JSON schema and seed state exactly.

Read only wrapper-returned locators. Keep the collector payload separate from the reader invocation: where `read` exposes the positional contract `read SNAPSHOT_RELATIVE_PATH START END`, pass the packet locator as those three arguments rather than as JSON. An artifact locator at line 1 proves that a module exists, but it does not authorize reading an unreturned procedure body or prove posting order. In that case, name the smallest owner/seam only as a candidate and leave the posting handler, transaction/order of record-set writes, draft-save route, and no-movement behavior explicitly unknown. When the handoff schema asks for `surfaces`, attach `path`, `startLine`, `endLine`, and a source-bounded reason to each entry; never imply runtime proof from collector metadata alone.

### Frozen read-only indexed context passes

When a review task authorizes only a prebuilt code index over a separate source copy, treat the index as a navigation aid and bind every material locator back to the canonical snapshot before reporting. Run the project-target verifier first and again as the final continuity check. At the end, verify all of the following exactly as the task declares: the canonical manifest/hash and file count, the required Git full SHA (not merely a shared prefix), and a clean Git status. If the indexed copy has an index sidecar such as `.code-index`, compare its remaining source tree byte-for-byte with the canonical snapshot; do not treat a ready snapshot or clean status as a substitute for the specified Git identity. A mismatch in any required frozen identity means `CONTEXT BLOCKED`: report the evidence-backed read-only plan as non-authorized for implementation, without editing, launching 1C, or attempting to reconcile the baseline. For a strict index-only or admitted-tool context lane, follow `references/index-only-readonly-context-pass.md`: its restricted-tool and machine-schema requirements override normal exploratory practice.

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
`references/data-backed-document-write-probes.md`.

When a headless probe must cross from early managed-client `OnStart` into an exported
server-call common module, or when a loaded configuration exits before producing a receipt,
read `references/headless-server-probe-observability.md`. It covers the verified bounded
client→server route, per-case receipt observability, and the fact that Designer load acceptance
does not necessarily compile an instrumentation path reached only at ENTERPRISE runtime.

Before freezing any business RED/GREEN cycle that reuses a managed-client probe, perform a
**whole-probe callable audit**: enumerate every added client and server procedure, including
`Except` branches that are not expected to execute, and compare every called helper against the
exact platform/runtime or a prior exact-runtime receipt. Include global-method language aliases:
never infer an English BSL name by translating a Russian method name. Bind the admitted alias and
signature to the exact installed `shcntx_*.hbk` identity or another exact-version primary source;
an unknown method in a server common module can prevent entry before the first body marker.
Designer acceptance is insufficient:
managed-client code may compile only when ENTERPRISE starts. Prefer literal, grammar-safe error
labels in diagnostic receipts; do not normalize exception text with unverified helpers. If the
probe has not been proven as a whole on the exact runtime, first freeze one harmless compile-canary
that uses no business fixture or production patch. **Budget admission is mandatory:** when the
owner authorizes exactly two native attempts and those are contractually RED and GREEN, an
unproven probe cannot consume RED as an implicit transport canary. Obtain separate canary budget
or a prior exact-runtime callable receipt; otherwise freeze `CONTEXT BLOCKED` before any native
invocation. Also inspect the candidate common-module metadata: `Server=true` does not establish a
managed-client call path; require `ServerCall=true` or an already-proven bridge.

For generated managed-application instrumentation, audit the **rendered module structure**, not
only the insertion template. Inject the probe body *inside* the existing `OnStart` procedure; never
insert another `Procedure OnStart()` declaration at an anchor that already includes the original
declaration. Before launching 1C, assert exactly one `OnStart` declaration, balanced
`Procedure`/`EndProcedure` structure, the probe call before the preserved startup body, exactly one
terminal receipt write, and the complete generated changed-path closure. A runtime error such as
`Keyword EndProcedure expected` after create/load is a probe compile/admission failure, not RED.
Retain its result and runtime log separately, remove only the owned prepared tree, and do not rerun
that failed contract.

When an external agent has a hard deadline shorter than a full RED/GREEN/repeat cycle, split work
at durable native boundaries rather than repeatedly assigning the whole route. After every runner
return, immediately copy the exact result plus client/server receipts into a task-owned evidence
root and run the lane oracle before doing analysis, packaging, or tests. A safe continuation should
consume retained receipts, execute only the next unfinished lane, and keep compile/admission
failures separate from the product-lane count. Prefer phases `contract + static preparation` →
`RED` → `GREEN + conditional repeat` → `package/commit/PR`; this preserves expensive native work
across coordinator timeouts without weakening the original business oracle.

For a packaging-only continuation on a separately named executor, freeze the execution boundary
before editing: verify that the admitted route reaches the expected repository, task branch, base
identity, and retained candidate files. A local checkout with the same repository name is not a
substitute when its branch or candidate state differs. If the named executor is temporarily
unreachable, do not reconstruct receipts from a transcript or commit against the local substitute;
preserve the durable remote state and report the smallest access prerequisite. After access is
restored, continue from the retained files rather than rebuilding or rerunning native lanes.

**Forensic differential controls:** when a known-good short probe and a newly generated probe differ,
do not infer a platform limitation from a timeout alone. Build a compact, source-backed comparison of
the client call signature and argument count, server signature, pre-call receipt writes, common-module
metadata, runner argv/environment, and the complete added-code diff. Then run one harmless control that
changes **one observable variable** while retaining the known-good receipt grammar and lifecycle. A
successful control supports only that difference; it does not prove a general platform limit without a
separately frozen differential. Keep every such control free of business-object creation, document
writes, posting, and production changes.

When a Python preparation script captures `git diff --no-index`, treat exit code `1` as the expected
"files differ" result and retain its stdout as the audit diff; only other nonzero results are failures.
This avoids discarding a valid static preflight before a platform attempt.

For an **exact generated patch**, prefer `git diff --no-index --no-ext-diff` over a
line-oriented Python diff generator. Preserve the emitted bytes, normalize only the two
known work-copy path prefixes to `a/` and `b/`, then run `git apply --no-index --check`
with `--directory=<canonical-snapshot-relative-root>`. This preserves CRLF source context
and gives the same patch parser that the shared route will use. Do not treat a successful
ad-hoc diff rendering or a check from the repository root as admission: a patch can look
plausible yet name paths relative to the wrong tree or have corrupt hunk counts.

When exact unified patches are applied inside a repository-ignored `.local/prepared/...` tree,
`git apply` may discover the enclosing worktree and silently report success while skipping ignored
paths; `--no-index` alone does not prevent this. Run patch check/application with
`GIT_CEILING_DIRECTORIES` set to the prepared tree's parent so Git treats the disposable tree as
standalone, then require a non-empty exact changed-path closure and expected post-apply hashes.
Keep a regression fixture that is demonstrably ignored by an enclosing worktree.

**Lifecycle admission audit:** before freezing the canary contract or allocating a native-attempt
number, inspect the actual runner's static path/admission validation as well as its `--help` text.
Verify that the planned immutable/prepared input location, task-owned run root, receipt location,
location,and copy/cleanup lifecycle are all admissible together. A runner may advertise an output run-root
convention while separately restricting its input tree to a different approved subtree. If those
constraints conflict with the authorized isolation boundary, record raw precheck evidence and stop
`CONTEXT BLOCKED` before any platform process; do not relocate an input outside the contract,
create a compatibility wrapper/service, or relabel that static rejection as a RED/CANARY runtime
result. See `references/managed-client-probe-compile-hardening.md` and, for this project's
runner-admitted disposable bridge layout, `references/native-cycle-prepared-input-bridge.md`.

When the question is **which transport should become the repeatable headless interface**—for
example `OnStart` receipts versus `/Execute` EPF versus Test Manager/Test Client—read
`references/headless-transport-selection.md` *before any native invocation*. It defines the
transport-neutral state contract, independent server witness, strict response grammar, bounded
one-smoke-per-arm comparison, and deterministic KISS selection without treating the most native
mechanism as a presumed winner. For a read-only admission decision specifically about an external
EPF launched by `ENTERPRISE /Execute`, also read
`references/external-epf-execute-feasibility.md`: it separates platform command syntax from the
repository runner's actual argv surface and from the stronger server-witness evidence requirement. For the tight final review lane over a completed
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

## Owner HOLD and post-hoc evidence corrections

When an owner review places a native transport/evidence PR on HOLD **after** native
runs, treat the review as a new boundary rather than permission to quietly repair
history or consume another smoke:

1. Stop native invocations. Correct pure validators, source-only adapters, tests,
and documentation first; do not reinterpret the hold as permission for a clean
repeat or a comparison arm.
2. State the strongest honest verdict supported by the published chronology. If
only one arm has native evidence or pre-run freezes/selection data were not
published, report a baseline partial proof / no clear winner, not a tournament
winner. Do not synthesize timing, roots, scores, or a pre-run chronology from
local artifacts afterward.
3. Revalidate every claimed execution layer after tightening receipt grammar. A
legacy client-only receipt that claimed a server-side task exception is historical
evidence only if the corrected contract requires a server-authored failure witness;
it cannot remain a current pass merely because the old parser accepted it.
4. For an existing success receipt, a compact tracked evidence packet may contain
exact receipt bytes, a minimal runner-result summary, and their hashes. If CRLF or
BOM bytes would make `git diff --check` noisy, store the exact bytes as Base64 and
make a unit test decode, hash, and validate them. If the original request file was
not retained, label any reconstructed request as reconstructed and do not claim
byte-level original-request provenance.
5. A minimal repeatable front door may be added without spending a native budget:
its `prepare` phase should generate a fresh request outside the immutable input,
make only its declared disposable BSL closure, and unit-test that closure. Its
`run` phase may delegate to the existing bounded lifecycle and validate the
current receipts, but must be documented as HOLD-prohibited until separately
authorized.
6. Any correction changes the review artifact. Run an exact-artifact follow-up
review and adjudicate concrete findings against code/tests; reviewer agreement
never lifts the HOLD, authorizes a run, merge, or issue closure.

### Canary failure classification

When a runner proves only lifecycle setup (for example, file-IB creation and configuration load) but the canary `ENTERPRISE` process exits before its required receipt, classify the result as **`NATIVE FAIL` for the probe/runtime route**, not as RED evidence and not as a conclusion about the business rule. Preserve the runner result and raw runtime log, record that no business witness was obtained, stop the current RED/GREEN sequence if its contract requires a successful canary, and re-check canonical identity and owned-process cleanup. A later correction needs a newly frozen contract and a new attempt budget; never consume the remaining RED/GREEN attempts under the failed contract.

## Reviewable GitHub delivery boundary

When a native 1C product task must culminate in owner review, read `references/reviewable-github-native-delivery.md`. It defines early publication of the first coherent candidate, exact local/remote/PR/tree identity checks, GitHub read-back and exact-head CI, approval-gate handling under a live pre-authorization, compact evidence publication, and the rule that merge remains a separate owner decision. A local worktree, local tests, or local reviewer verdict is progress—not a reviewable delivery.

When owner review requires replacing task-specific preparation/lifecycle glue with one reusable task-owned patch → runner → oracle → receipt route, read `references/shared-task-native-route.md`. It covers strict ownership, exact CRLF patch retention, static reconstruction without another native run, honest full-layer counting, and functional-versus-complexity verdicts.

### Late provenance closure for an existing native receipt

If a retained native receipt records only `SHA-256(production composite)` while the PR publishes only one narrower business-patch fragment, do not claim the fragment was used merely because both hashes are known. Close the seam statically before considering any new native attempt: publish the exact composite bytes as a data-only `exact-*.patch` artifact (so the repository's existing binary/CRLF contract applies), retain the receipt, and publish a compact provenance note that identifies the fragment's literal byte range or a deterministic composition. On a fresh clone, verify (1) the receipt's `production` hash equals `sha256sum` of the published composite and (2) `cmp` of the stated byte range against the current business patch succeeds. Keep the business patch bytes unchanged, restore shared `.gitattributes` from the base rather than adding a task-specific rule, and avoid a validator, replay framework, reviewer cycle, or native rerun when these retained bytes close the chain. See `references/receipt-production-composite-provenance.md`.

For a time-boxed product Goal that starts from ordinary business language and must finish at a local shared-route receipt plus an open exact-head PR, read `references/fast-product-vertical-slice.md`. It covers predecessor admission before the clock, narrow `rg` context, task-only inputs, elapsed accounting without telemetry infrastructure, authoritative route receipts, safe correction of localized-date oracle parsing, honest `PRODUCT PASS / COST FAIL`, and compact terminal reporting. If owner review then authorizes one bounded product/reporting correction on the same open PR, also read `references/time-boxed-owner-correction.md`; it covers localized message-boundary proof, one replacement native run, preserved original timing/verdict, honest requalification, and stale synthetic-merge refs after a PR head update.

### Concurrent document invariants in a bounded product slice

A sequential `SELECT`-then-post check does **not** prove a uniqueness invariant: two postings can both observe no existing document before either commits. When an owner requires concurrent uniqueness and permits only one additional native run, first look for the configuration's existing `DataLock` and `BackgroundJobs.Execute` patterns. Prefer the smallest domain-owned lock placed in the document's `Posting` path **before** the duplicate read and before record-set preparation; it must be held by the platform posting transaction. Do not add a shared lock framework, service, runner feature, or dependency merely to make this test convenient.

A single task-owned instrumentation run may launch two background jobs for two distinct draft documents with the same key *before waiting for either*. Bind the receipt to both job attempts and require: two jobs started; exactly one posting succeeded; exactly one document is rejected; the rejected recorder has zero records in every declared target register; and the final count of posted documents for the key is one. Keep adjacent preservation cases in that same run rather than spending separate repeats. If the exact runtime cannot execute the existing background-job route or cannot produce these witnesses without widening the architecture, stop as `PRODUCT GAP` rather than relabeling a sequential result as concurrency proof.

An explicit owner prohibition on a reviewer cycle overrides the default dual-review policy for that task: do not initiate, repeat, or rely on external review as a gate. CI/read-back and the owner-authorized native receipt remain sufficient task mechanics; reviewer output never authorizes merge in any case.

### Reviewable stop checkpoints

A chat-only report is not a review surface. When a substantive 1C task stops for owner verification, budget renewal, or a bounded correction, publish a compact live GitHub checkpoint before the next native attempt: create a task branch and draft PR containing only the reviewable task-owned request, exact patches, oracle, and any already-generated receipt; exclude run roots and raw logs. Read the PR back for exact base/head/tree and file closure, then leave one concise issue comment linking the PR, stating the current product/cost verdict, exact causes of prior attempt failures, and measured cost without resetting the original clock.

After the final authorized run, update that same PR with the receipt, wait for exact-head CI, and leave one terminal issue report. Distinguish retained measured runtime/lifecycle durations from wall-clock time and never invent a missing continuous active timer. Keep the PR open for owner review; neither a checkpoint, CI success, nor reviewer output authorizes merge.

## Workspace convention (this project)

- Dedicated project folder = the Hermes **workspace** = the **git root** (no nested workspace).
  Do not move the git root up into a shared `/workspace` that also holds Hermes-internal dirs.
- Machine-local data lives under git-ignored `.local/`: `dist/ platform/ fixtures/ tools/ runs/ cache/`.
- Read-only relative to the source config and infobase — changing the source is a failed experiment.
- A metadata-preserving copy can retain the snapshot's read-only mode bits. Before injecting a probe, grant owner-write permission **only** to the explicitly allowed files inside the named disposable copy. Never recursively relax permissions on the canonical snapshot or broad work-copy tree. If cleanup of an owned prepared copy fails because copied directories are read-only, first verify that no task process remains, then grant `u+rwx` to **directories only** below that exact task-owned copy and remove only that copy. Do not recursively change file modes and do not apply this to the canonical snapshot.
- When a user executes root operations through Windows PowerShell → SSH → `docker exec`, provide
  either one genuinely single-line command or an interactive container shell followed by short
  commands one at a time. Never present a visually multiline quoted `bash -c` payload as though it
  were safely copyable; broken quote boundaries can leave the remote shell waiting for more input.

## No-sudo tooling

`references/acquisition-and-tooling.md` has verified recipes: a no-sudo static `aria2c` install
(torrent downloads) and a no-sudo headless-Chromium lib-bundling setup, plus the Cloudflare
handoff pattern for gated logins.
