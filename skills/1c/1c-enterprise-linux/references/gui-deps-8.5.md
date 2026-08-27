# 1C 8.5.x GUI dependency stack (verified for 8.5.1.1150 on Debian 13 container)

1C 8.5 full/training clients (`1cv8` / `1cv8t`, including Designer) link GTK3 +
WebKit2GTK 4.0. In a minimal container none of these are present. This package bank is a verified
starting point, not a substitute for closure checks: pull packages rootlessly with user-space apt,
extract with `dpkg-deb -x` into `.local/platform/libs/`, then run `ldd` on `1cv8`/`1cv8t`, Xvfb,
and `xkbcomp` until every target is free of `not found` entries.

## Release pinning

- `libgtk-3-0` is renamed `libgtk-3-0t64` in Debian 13 (t64 transition).
- WebKit2GTK **4.0** (`libwebkit2gtk-4.0-37`, `libjavascriptcoregtk-4.0-18`) is **bookworm-only**;
  trixie carries only 4.1 (`libwebkit2gtk-4.1-0`), which 8.5 does NOT link against.
- Do not mix arbitrary package versions. On Debian 13 the verified closure required trixie's GTK
  package naming plus bookworm-only WebKit2GTK 4.0 and its ABI-matched dependencies (for example
  ICU 72). Pin each coherent dependency family, record package versions/hashes, and let complete
  `ldd` checks—not a presumed package list—decide whether the resulting local runtime is closed.

## Package list

Core GUI:
```
libgtk-3-0t64  libgdk-pixbuf-2.0-0  libcairo-gobject2  libpangocairo-1.0-0
libsoup-2.4-1  libglu1-mesa
```

WebKit2GTK 4.0 (bookworm only):
```
libwebkit2gtk-4.0-37  libjavascriptcoregtk-4.0-18
```

Transitive (bookworm):
```
libopengl0 libxcursor1 libxinerama1 libavif15 libcloudproviders0 libenchant-2-2
libepoxy0 libflite1 libgstreamer1.0-0 libgstreamer-plugins-base1.0-0
libharfbuzz-icu0 libhyphen0 libicu72 libjpeg62-turbo libmanette-0.2-0
libpangoft2-1.0-0 libsecret-1-0 libwayland-cursor0 libwayland-egl1
libwebp7 libwebpdemux2 libwebpmux3 libwoff1 libxslt1.1
libsvtav1enc1 libaom3 libdav1d6 libdw1 libevdev2 libgav1-1
libgstreamer-gl1.0-0 libgudev-1.0-0 liborc-0.4-0 librav1e0 libyuv0
libegl1 libegl-mesa0 libglvnd0 libabsl20220623 libunwind8
```

Virtual display (Xvfb):
```
xvfb xserver-xorg-core xserver-common xauth   # Xvfb + xvfb-run
x11-xkb-utils                                   # provides /usr/bin/xkbcomp (REQUIRED by Xvfb)
xkb-data                                        # keymap data -> /usr/share/X11/xkb
```

## Mapping a missing `.so` to a package

`ldd "$V/1cv8" | grep -i 'not found'` lists names like `libwebkit2gtk-4.0.so.37`. Map:
- `libwebkit2gtk-4.0.so.37` → `libwebkit2gtk-4.0-37`
- `libicu*.so.72` → `libicu72` (major = version = package suffix)
- `libavif.so.15` → `libavif15` (NOT `libavif16` = trixie)
- `libgst*.so.0` → `libgstreamer1.0-0` + `libgstreamer-plugins-base1.0-0` (+ `libgstreamer-gl1.0-0` for `libgstgl`)
- `libwoff2dec.so.1.0.2` → `libwoff1`
- `libEGL.so.1` → `libegl1` (GLVND dispatcher) + `libegl-mesa0` — `libegl-mesa0` alone only
  provides `libEGL_mesa.so.0`, not the `libEGL.so.1` dispatcher
- `libabsl_synchronization.so.20220623` → `libabsl20220623`

If unsure of a name: `apt-cache $O search <soname-stem>`.

## Xvfb: the `xkbcomp` blocker (diagnosed, requires one-off root)

Xvfb runs the external keymap compiler at a **hardcoded** `/usr/bin/xkbcomp` (compile-time
`XKB_BIN_DIRECTORY`). Symptom chain:

```
sh: 1: /usr/bin/xkbcomp: not found
XKB: Failed to compile keymap
Keyboard initialization failed. This could be a missing or incorrect setup of xkeyboard-config.
(EE) Fatal server error:
(EE) Failed to activate virtual core keyboard: 2
```

- `-kb` is **not** a valid flag (→ `Unrecognized option: -kb`). Prefer atomic display allocation
  with `-displayfd` and Xauthority. If an isolated container must use `-ac`, pair it with
  `-nolisten tcp`. Retain and verify the Xvfb PID/socket; in a supervising gateway, terminate only
  child processes proven to belong to the run (see `training-edition-lab.md`), never the caller's
  process group.
- `-xkbdir <dir>` overrides the keymap DATA dir only — NOT the xkbcomp binary path.
- Rootless socket dir: `mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix` (Xvfb refuses to
  create it itself when euid != 0).
- `/usr/bin`, `/usr/share`, `/usr/local/bin` are not writable without root, and `strings` on the
  Xvfb binary shows only `xkbcomp` (path is assembled from `XKB_BIN_DIRECTORY`), so there is no
  rootless escape hatch. On a fresh Debian container, provision these paths from exact artifacts
  obtained through a signed, timestamped Debian snapshot. Do not run an unpinned `apt-get install`
  as the published reproduction recipe, and do not copy a workspace executable directly into
  `/usr/bin` as root.
- The validated boundary stages `x11-xkb-utils` and `xkb-data` `.deb` files in a random root-owned
  directory, verifies their exact SHA-256 after staging, extracts them without maintainer scripts,
  and publishes only absent `/usr/bin/xkbcomp` and `/usr/share/X11/xkb` destinations. It refuses
  regular existing paths and dangling symlinks, constrains cleanup to the staging root, and
  normalizes `/tmp/.X11-unix` to root ownership with mode `01777`.
- Exact 2026-08 artifact hashes and the clean-rebuild sequence are in
  `reproducible-debian-runtime.md`. Recompute hashes and rerun the full smoke for any changed
  package version or snapshot.

If either destination is already present, do not delete or replace it automatically. Identify its
owner with `dpkg-query -S /usr/bin/xkbcomp /usr/share/X11/xkb` when applicable, verify packaged
content with `dpkg -V x11-xkb-utils xkb-data`, and resolve any non-package owner explicitly.

For users copying commands through Windows PowerShell and SSH, keep this as one actual line after
substituting fixed paths. If quoting becomes difficult, enter an interactive root shell and run
short commands one at a time instead of sending a multiline quoted `bash -c` payload.

xkbcomp's own libs (libX11, libxkbfile, libxcb, libXau, libXdmcp) are satisfied by the same
`LD_LIBRARY_PATH` used to launch Xvfb, because the spawned subprocess inherits it.
