# Official 1C training-edition Linux lab

Validated 2026-08 with official training edition 8.5.1.1150 on Debian 13 x86_64. Use this reference for a minimal native Designer lab, not as a mandate to build a universal installer or process supervisor.

## Proven artifact shape

- Training tree: `.local/platform/1cv8t/x86_64/8.5.1.1150/`; binary is `1cv8t`, not `1cv8`.
- Official acquisition page: `https://online.1c.ru/catalog/programs/program/36179915/` (personal form + license acceptance; never persist its temporary signed URL).
- Installer SHA-256 observed: `396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28`.
- Verified public fixture: `1Ci-Company/Jet` release `v1.0.3.1-tr`, asset `1.0.3.1.cf`, SHA-256 `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`.
- Native sequence: `CREATEINFOBASE` → `DESIGNER /LoadCfg` → `DESIGNER /DumpConfigToFiles -Format Hierarchical`, with `/Out`, `/DumpResult`, `/DisableStartupDialogs`, and `/DisableStartupMessages`.
- Verified output: 5,099 files, 1,258 `.bsl` files; repeated direct dumps and a `cc-1c-skills` full dump had identical path/content hashes. Canonical manifest content ID: `sha256:70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.

Treat hashes as provenance for these exact artifacts, not universal values for future releases.

## Preferred KISS workflow

When the task is to prove a native lab, prefer standard tools over custom orchestration:

1. Make the Git root the actual Hermes Workspace.
2. Keep platform, fixture, bases, logs, snapshots, and external checkout under ignored `.local/`.
3. Copy the fixture into a fresh run directory; never pass the source CF to 1C.
4. Set the workspace-local `PATH`, `LD_LIBRARY_PATH`, `FONTCONFIG_FILE`, and isolated HOME/TMP/XDG paths.
5. Invoke the bundled `xvfb-run -a` separately for `CREATEINFOBASE`, `/LoadCfg`, and full `/DumpConfigToFiles`.
6. Require process success, `/DumpResult=0`, root `Configuration.xml`, root `ConfigDumpInfo.xml`, several metadata domains, and nonzero BSL files.
7. Compare source/copy SHA-256 before and after as observed endpoint evidence.
8. Repeat from a second fresh infobase and compare relative paths plus each file's SHA-256.
9. Test the pinned external adapter against the same snapshot; keep it isolated rather than globally activating mutating skills.

A verified direct sequence using `xvfb-run` is preferable to committing a new shell wrapper, manifest utility, or process supervisor. Issue-level lab work should not silently turn into a security-sensitive harness.

## Environment pattern

```bash
ROOT=/path/to/git-root
V="$ROOT/.local/platform/1cv8t/x86_64/8.5.1.1150"
L="$ROOT/.local/platform/libs"
RUN="$ROOT/.local/runs/new-run-id"
export PATH="$L/usr/bin:$PATH"
export LD_LIBRARY_PATH="$V:$L/usr/lib/x86_64-linux-gnu"
export FONTCONFIG_FILE="$ROOT/.local/platform/fonts.conf"
export HOME="$RUN/home" TMPDIR="$RUN/tmp"
export XDG_CACHE_HOME="$RUN/xdg-cache"
export XDG_CONFIG_HOME="$RUN/xdg-config"
export XDG_DATA_HOME="$RUN/xdg-data"
```

Then run each platform operation with:

```bash
"$L/usr/bin/xvfb-run" -a -e "$RUN/logs/<step>-xvfb.log" \
  "$V/1cv8t" <native arguments> \
  /Out "$RUN/logs/<step>.log" /DumpResult "$RUN/logs/<step>.result"
```

`xvfb-run` uses Xauthority and automatic display allocation. This was validated in the prepared single-user lab and produced the same Jet snapshot as the earlier direct Xvfb path.

## Running a pinned Python adapter with the training binary

`cc-1c-skills` `db-dump-xml.py` accepts the full training binary through `-V8Path`, even though its human-readable status line labels the command as `1cv8.exe`. That label is not evidence of which executable ran; bind the claim to the supplied absolute path and pinned checkout commit.

The adapter does not allocate a display itself. Wrap the **Python invocation** in the same `xvfb-run` environment so its `1cv8t` child inherits `DISPLAY`:

```bash
OUT="$RUN/cc-adapter-dump"
test ! -e "$OUT" && test ! -L "$OUT"
"$L/usr/bin/xvfb-run" -a -e "$RUN/logs/cc-adapter-xvfb.log" \
  "$ROOT/.local/tools/cc-1c-skills-venv/bin/python" \
  "$ROOT/.local/tools/cc-1c-skills/.claude/skills/db-dump-xml/scripts/db-dump-xml.py" \
  -V8Path "$V/1cv8t" \
  -InfoBasePath "$RUN/ib" \
  -ConfigDir "$OUT" \
  -Mode Full -Format Hierarchical
```

Use the same fresh working infobase as the direct native comparison, a fresh output directory, the workspace-local library/font/HOME/TMP/XDG environment, and an isolated venv. Recompute path/content manifests for both outputs and require byte equality; a success message or matching file count alone is insufficient. Then run the pinned `cf-info.py` on the fresh dump and compare name, version, vendor, compatibility mode, and direct `ChildObjects` count with `Configuration.xml`.

## Evidence semantics

Be precise about what was proved:

- `/DumpConfigToFiles` without `-update`, `-force`, or `-listFile`, targeting a fresh output directory, is the native full operation.
- Required files, object domains, and BSL counts are structural evidence that output is nonempty and suitable for the next stage; they are not a generic proof of semantic completeness for every possible configuration.
- Matching endpoint SHA-256 values prove observed content equality at the checkpoints, not absence of a malicious mutation-and-restoration race by another same-uid process.
- `read-only` normally means workflow discipline plus removed Unix write bits, not filesystem immutability; the owner can restore permissions.
- A line-oriented SHA-256 manifest is acceptable evidence for the controlled filename set emitted by 1C, but it is not automatically a safe generic format for arbitrary Linux filenames.

## Threat model and when automation becomes a separate project

The minimal lab assumes a trusted single-user Workspace with no adversarial same-uid process racing filesystem paths. State that assumption explicitly.

If the deliverable must resist hostile concurrent processes, do not improvise a shell hardening layer. A publishable multi-tenant harness needs a separately reviewed architecture, including:

- descriptor-relative traversal and publication (`openat`/dirfds, `O_NOFOLLOW`, atomic bundle publication);
- pinned source/snapshot identities across the native run;
- pidfds or equivalent immutable process identity, not numeric PID snapshots;
- established child supervision and reliable descendant cleanup;
- trusted lock and output parent directories;
- protected X socket directory, authenticated display allocation, and stale-resource cleanup;
- fault-injection tests for every failure boundary.

That scope is larger than proving a native 1C lab. Prefer narrowing the contract or using an established supervisor/container runtime instead of writing a bespoke subreaper.

## Privileged provisioning boundary

The official installer requires root. Do not publish a root command that executes an installer directly from a user-writable Workspace or recursively moves/chowns through untrusted parents.

For a clean rebuild, an administrator should:

1. copy the installer as data into root-owned staging;
2. verify the staged SHA-256 immediately before execution;
3. run the exact staged regular file;
4. use a root-controlled transition for installed output;
5. establish ownership before any unprivileged workspace copy;
6. avoid replacing existing system XKB paths until package/owner provenance is known.

Xvfb invokes `/usr/bin/xkbcomp`; keymap data is normally under `/usr/share/X11/xkb`. Prefer authenticated distro packages on a fresh container. If current paths were copied manually from extracted packages, document that fact and their hashes rather than presenting them as dpkg-owned.

Keep root commands short and genuinely single-line for PowerShell/SSH copy-paste. If quoting becomes complex, enter an interactive root container shell and run short commands one at a time.

## Training-edition constraints

Use only for learning, development, testing, and fixtures permitted by the training license. The training edition is file-mode oriented and excludes production accounting, client-server operation, configuration repository workflows, COM, distributed infobases, and other documented commercial capabilities.
