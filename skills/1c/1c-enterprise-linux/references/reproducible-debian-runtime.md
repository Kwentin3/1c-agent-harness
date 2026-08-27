# Reproducible Debian runtime for headless 1C

Use this reference when a clean Debian container must reconstruct the workspace-local GUI/Xvfb runtime for 1C Designer. It records a validated method, not a universal package list for every 1C release.

## Validated instance

For 1C training edition 8.5.1.1150 on Debian 13 x86_64, the 2026-08 lab used:

- signed Debian snapshots at `20260825T000000Z`;
- 106 exact `name=version` packages: 63 from trixie and 43 from bookworm;
- extraction in published order: trixie first, then bookworm, so the intended bookworm WebKit2GTK 4.0 ABI family wins;
- a new empty runtime directory of about 278 MiB;
- successful `ldd` closure for `1cv8t`, Xvfb, `xauth`, and `xkbcomp`;
- a full Jet smoke with process exits and `/DumpResult` values `0/0/0`, 5,099 files, 1,258 BSL files, and content ID `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.

The exact package array is project evidence, not a timeless skill default. In `1c-agent-harness`, read the committed `docs/lab-bootstrap.md`; do not reconstruct the list from memory.

## Rebuild pattern

1. Start with a new user-space APT root and a new empty extraction directory.
2. Use HTTPS `snapshot.debian.org` sources with a fixed timestamp and Debian archive keyring. Set `check-valid-until=no` because archived metadata is intentionally old.
3. Isolate `Dir::Etc::sourcelist`, `Dir::Etc::sourceparts`, `Dir::State::lists`, and `Dir::Cache::archives`.
4. Neutralize inherited host hooks explicitly: both `APT::Update::Post-Invoke=` and `APT::Update::Post-Invoke-Success=`. A user-space APT root does not by itself suppress `/etc/apt/apt.conf.d` hooks.
5. Express every package as exact `name=version`; reject duplicate package names and resolve the complete array against the pinned snapshot before download.
6. Download into a fresh cache, then extract with `dpkg-deb -x` in the documented release order. Extraction order is part of the experiment whenever releases overlap.
7. Generate `fonts.conf` from the actual absolute runtime font path and a writable cache path; XML-escape generated paths.
8. Run `ldd` on every executable boundary, not only `1cv8t`: include Xvfb, `xauth`, and `/usr/bin/xkbcomp`. Reject `not found` and unexpected Hermes/browser-runtime paths.
9. Run the readiness block and then the complete native smoke. Package resolution and clean `ldd` are necessary but not sufficient.
10. Record package count, extraction order, runtime size, snapshot timestamp, smoke exit codes, `/DumpResult`, fixture hash, file/BSL counts, and content ID.

After any package membership, version, source, or extraction-order edit, rebuild into another empty directory and rerun the full closure and smoke. Prior evidence no longer proves the edited recipe.

## XKB system exception

Xvfb invokes absolute `/usr/bin/xkbcomp` and expects XKB data under `/usr/share/X11/xkb`. For a clean single-user container:

- include `x11-xkb-utils`, `xkb-data`, and the local `libxkbfile1` dependency in the pinned package set;
- never publish a workspace-controlled executable directly as root;
- copy the two system `.deb` files into random root-owned staging, verify exact SHA-256 there, extract with `dpkg-deb -x`, and publish only absent destinations;
- refuse existing regular paths and dangling symlinks instead of replacing them;
- normalize `/tmp/.X11-unix` to root ownership and mode `01777` in the clean bootstrap;
- constrain cleanup to the known root-owned staging tree.

Hashes validated for the snapshot above:

- `x11-xkb-utils_7.7+9_amd64.deb`: `745e29c79bb435d057cdbf8bb59a35fa33e818e566cb754674f44d381ccd4317`;
- `xkb-data_2.42-1_all.deb`: `196ff18533382f64e057ea49df2bb486bd4275a4cc0917361edb560b8756dada`.

Treat these hashes as exact-artifact provenance only. A different snapshot or package version requires new hashes and a fresh smoke.

## Acquisition publication rule

For public fixtures or installers, do not download directly over an existing verified destination. Download to a fresh temporary file in the intended filesystem, verify its pinned digest, remove write bits if appropriate, then publish without clobbering (for example, same-filesystem hard-link publication when the destination must be absent). Clean temporary files with a trap.
