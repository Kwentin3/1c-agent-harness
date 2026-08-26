#!/usr/bin/env python3
"""Reproducible driver for the issue #10 write-cycle experiment.

Proves on a clean run the full loop:

    immutable source -> writable work copy -> minimal BSL patch
    -> native DESIGNER load/UpdateDBCfg -> ENTERPRISE runtime probe
    -> RED (original) vs GREEN (changed) receipts -> mutation power
    -> immutable source hashes unchanged.

The driver is intentionally narrow: it reproduces ONE scenario (the Jet
`StringFunctionsClientServer.StringToNumber` whitespace change). It does NOT
create a write framework, a general patch engine, a parser, or any extension
system. It only orchestrates the exact native platform commands from
docs/lab.md (CREATEINFOBASE, DESIGNER LoadConfigFromFiles + UpdateDBCfg,
ENTERPRISE) and verifies output.

Workspace convention: everything it writes lands under a single --work-root
(default .local/runs/issue10-jet-string-whitespace-driven). The immutable source
CF and the immutable snapshot are only read, never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

SOURCE_CF_SHA256 = "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a"

# The writable work-copy split-dump directory is recreated under the base name.
WORK_FILES_REL = "files"  # split-dump directory copied from snapshot

# Minimal production patch (added after the existing regular-space strip).
# Lines are inserted verbatim into StringFunctionsClientServer/Ext/Module.bsl.
PRODUCTION_PATCH_LINES = (
    "\t// Digits are commonly separated by tab or a non-breaking space in copied\r\n"
    "\t// text. Strip those as well, not just the regular space.\r\n"
    "\tValue  = StrReplace(Value, Chars.Tab, \"\");\r\n"
    "\tValue  = StrReplace(Value, Chars.NBSp, \"\");\r\n"
)
PRODUCTION_ANCHOR = '\tValue  = StrReplace(Value, " ", "");\r\n'

# Cases exercised by the runtime probe. Label -> BSL expression that calls the
# production StringToNumber. `invalid` and the decimal/space controls must stay
# unchanged between RED and GREEN; only tab and nbsp flip from Undefined->number.
PROBE_CASES = (
    ("tab",     'StringFunctionsClientServer.StringToNumber("1" + Chars.Tab + "234")'),
    ("nbsp",    'StringFunctionsClientServer.StringToNumber("1" + Chars.NBSp + "234")'),
    ("invalid", 'StringFunctionsClientServer.StringToNumber("12x3")'),
    ("decimal", 'StringFunctionsClientServer.StringToNumber("1234.56")'),
    ("space",   'StringFunctionsClientServer.StringToNumber(" 567 ")'),
)
PROBE_LABELS = [c[0] for c in PROBE_CASES]

# Files we expect to differ between the immutable snapshot and the work copy.
EXPECTED_DIFF = ("CommonModules/StringFunctionsClientServer/Ext/Module.bsl",
                 "Ext/ManagedApplicationModule.bsl")

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


class DriverError(RuntimeError):
    """A hard, fail-closed failure. We never paper over a contract violation."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_manifest(path: Path) -> list[tuple[str, str]]:
    entries = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        entries.append((digest, rel))
    return entries


def verify_snapshot(snapshot_dir: Path, manifest: Path) -> dict:
    """Return counts for the per-file manifest check (airtight unchanged-proof)."""
    entries = parse_manifest(manifest)
    ok = missing = mismatch = 0
    for digest, rel in entries:
        p = snapshot_dir / rel
        if not p.exists():
            missing += 1
            continue
        if sha256(p) == digest:
            ok += 1
        else:
            mismatch += 1
    return {"entries": len(entries), "ok": ok, "missing": missing,
            "mismatch": mismatch}


def verify_cf(cf: Path) -> None:
    if sha256(cf) != SOURCE_CF_SHA256:
        raise DriverError(
            f"source CF hash mismatch: expected {SOURCE_CF_SHA256[:16]}…, "
            f"got {sha256(cf)[:16]}…")


def run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=env, capture_output=True, text=True,
                          timeout=1200)


# ---------------------------------------------------------------------------
# Probe injection
# ---------------------------------------------------------------------------


def probe_bsl(receipt_path: Path) -> str:
    """The test-only BSL that drives the production function and writes a receipt."""
    lines = [
        "// Probe-only: runs the production StringToNumber for the issue-10 whitespace",
        "// contract and writes a receipt. This code is NOT part of the implementation",
        "// and exists only in the throwaway instrumented work copy.",
        "Procedure Issue10WriteRuntimeReceipt()",
        "\t",
        f'\tReceipt = New TextWriter("{receipt_path}", TextEncoding.UTF8);',
        "\t",
    ]
    for label, expr in PROBE_CASES:
        lines.append(f'\tReceipt.Write("{label}###" + String({expr}) + Chars.LF);')
    lines += ["\t", "\tReceipt.Close();", "\t", "EndProcedure", "", ""]
    return "\r\n".join(lines)


def read_bsl(path: Path) -> str:
    """Read a BSL file preserving its exact line endings (no newline translation)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def write_bsl(path: Path, text: str) -> None:
    """Write BSL preserving line endings (no newline translation), keep UTF-8 BOM."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(text)


def inject_probe(module: Path, receipt_path: Path) -> None:
    """Insert the OnStart call + the probe procedure into ManagedApplicationModule."""
    text = read_bsl(module)
    on_start_anchor = "Procedure OnStart()\r\n\t\r\n\t// StandardSubsystems"
    if on_start_anchor not in text:
        raise DriverError("OnStart anchor not found in ManagedApplicationModule.bsl")
    call = "Procedure OnStart()\r\n\t\r\n\tIssue10WriteRuntimeReceipt();\r\n\tReturn;\r\n\t\r\n\t// StandardSubsystems"
    text = text.replace(on_start_anchor, call, 1)

    proc = probe_bsl(receipt_path)
    region_anchor = "#EndRegion"
    # Insert before the LAST #EndRegion (the EventHandlers region), not the
    # first one which closes Variables at the top of the module.
    pos = text.rfind(region_anchor)
    if pos == -1:
        raise DriverError("#EndRegion anchor not found in ManagedApplicationModule.bsl")
    text = text[:pos] + proc + text[pos:]
    write_bsl(module, text)


def apply_production_patch(module: Path) -> None:
    """Add the two StrReplace lines after the existing regular-space strip."""
    text = read_bsl(module)
    if PRODUCTION_ANCHOR not in text:
        raise DriverError("StringToNumber regular-space anchor not found")
    if PRODUCTION_PATCH_LINES in text:
        raise DriverError("StringToNumber already contains the patch — refusing to double-patch")
    text = text.replace(PRODUCTION_ANCHOR,
                        PRODUCTION_ANCHOR + PRODUCTION_PATCH_LINES, 1)
    write_bsl(module, text)


# ---------------------------------------------------------------------------
# Native platform step
# ---------------------------------------------------------------------------


def make_env(root: Path, onecv: Path, libs: Path, fonts: Path, home: Path) -> dict:
    v = onecv  # directory containing 1cv8t
    l = libs / "usr/lib/x86_64-linux-gnu"
    env = os.environ.copy()
    env["PATH"] = f"{libs / 'usr/bin'}:{env['PATH']}"
    env["LD_LIBRARY_PATH"] = f"{v}:{l}"
    env["FONTCONFIG_FILE"] = str(fonts)
    env["HOME"] = str(home)
    env["TMPDIR"] = str(root / "tmp")
    env["XDG_CACHE_HOME"] = str(home / "xdg-cache")
    env["XDG_CONFIG_HOME"] = str(home / "xdg-config")
    env["XDG_DATA_HOME"] = str(home / "xdg-data")
    return env


def read_result(path: Path) -> str:
    """Read a /DumpResult value, tolerating the UTF-8 BOM the platform writes."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return text.strip()


def create_ib(onecv_bin: Path, xvfb_run: Path, env: dict, ib: Path, out: Path) -> None:
    cmd = [str(xvfb_run), "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp",
           "-e", str(out.with_suffix(".xvfb.log")),
           str(onecv_bin), "CREATEINFOBASE", f"File={ib}",
           "/DisableStartupDialogs", "/DisableStartupMessages",
           "/Out", str(out.with_suffix(".log")),
           "/DumpResult", str(out.with_suffix(".result"))]
    r = run(cmd, env)
    res = read_result(out.with_suffix(".result")) if out.with_suffix(".result").exists() else "NONE"
    if r.returncode != 0 or res != "0":
        raise DriverError(f"CREATEINFOBASE failed: rc={r.returncode} result={res!r}")


def load_config(onecv_bin: Path, xvfb_run: Path, env: dict, ib: Path,
                files_dir: Path, out: Path) -> None:
    cmd = [str(xvfb_run), "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp",
           "-e", str(out.with_suffix(".xvfb.log")),
           str(onecv_bin), "DESIGNER", "/F", str(ib),
           "/LoadConfigFromFiles", str(files_dir), "/UpdateDBCfg",
           "/DisableStartupDialogs", "/DisableStartupMessages",
           "/Out", str(out.with_suffix(".log")),
           "/DumpResult", str(out.with_suffix(".result"))]
    r = run(cmd, env)
    res = read_result(out.with_suffix(".result")) if out.with_suffix(".result").exists() else "NONE"
    logtxt = out.with_suffix(".log").read_text(encoding="utf-8-sig", errors="replace")
    if r.returncode != 0 or res != "0" or "Configuration successfully updated" not in logtxt:
        raise DriverError(
            f"DESIGNER load/UpdateDBCfg failed: rc={r.returncode} result={res!r} "
            f"logtail={logtxt[-400:]!r}")


def run_enterprise(onecv_bin: Path, xvfb_run: Path, env: dict, ib: Path,
                   out: Path, receipt: Path, timeout: float = 120.0) -> None:
    cmd = [str(xvfb_run), "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp",
           "-e", str(out.with_suffix(".xvfb.log")),
           str(onecv_bin), "ENTERPRISE", "/F", str(ib),
           "/DisableStartupDialogs", "/DisableStartupMessages",
           "/DisplayManager", "none",
           "/Out", str(out.with_suffix(".log"))]
    # The probe performs its work in OnStart and returns; on a file infobase the
    # client then idles rather than exiting on its own. So we poll for the
    # receipt the probe writes, then terminate the whole process tree so the
    # educational-edition connection slot is released and the next run can start.
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if receipt.exists():
                break
            if proc.poll() is not None:
                break
            time.sleep(1.0)
    finally:
        _terminate_tree(proc)
    # The exit code is informational: an educational-edition limitation or an
    # idle client can end non-zero even though the probe ran (the receipt is the
    # source of truth, checked by the caller).


def _terminate_tree(proc: subprocess.Popen) -> None:
    """Terminate a process and its whole group without leaking a session slot."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Receipt parsing / mutation-power analysis
# ---------------------------------------------------------------------------


def parse_receipt(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig").splitlines()
    out = {}
    for line in text:
        if "###" in line:
            label, val = line.split("###", 1)
            out[label.strip()] = val.strip()
    return out


def analyze_mutation(green: dict[str, str], red: dict[str, str]) -> dict:
    """Return per-case verdict and whether the test can detect the change."""
    rows = []
    for label in PROBE_LABELS:
        g = green.get(label)
        r = red.get(label)
        changed = (g != r)
        rows.append({"case": label, "red": r, "green": g, "changed": changed})
    flipped = [row for row in rows if row["changed"]]
    # The feature is proven only if tab and nbsp flip (Undefined -> number)
    # AND the controls (invalid/decimal/space) DO NOT flip.
    controls = ["invalid", "decimal", "space"]
    control_changed = [row for row in rows if row["case"] in controls and row["changed"]]
    feature_flipped = all(row["case"] in ("tab", "nbsp") and row["changed"] for row in rows
                          if row["case"] in ("tab", "nbsp"))
    mutation_power = bool(feature_flipped and not control_changed)
    return {"rows": rows, "feature_flipped": feature_flipped,
            "control_changed": bool(control_changed), "mutation_power": mutation_power}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build_work_copy(paths: dict, receipt_path: Path, patched: bool) -> Path:
    """Copy the immutable snapshot into a writable work copy and instrument it."""
    src = paths["snapshot"]
    work_root = paths["work_root"]
    files = work_root / WORK_FILES_REL
    if files.exists():
        shutil.rmtree(files)
    # Binary copy of the split dump; source stays untouched.
    shutil.copytree(src, files)
    # Ensure writability of the work copy only.
    for root, _, fnames in os.walk(files):
        for f in fnames:
            (Path(root) / f).chmod(0o600)
        Path(root).chmod(0o700)

    module = files / EXPECTED_DIFF[0]
    inject_probe(files / "Ext" / "ManagedApplicationModule.bsl", receipt_path)
    if patched:
        apply_production_patch(module)
    else:
        # RED variant: keep the probe, but the production change must be absent.
        if PRODUCTION_PATCH_LINES in read_bsl(module):
            raise DriverError("RED variant unexpectedly contains the production patch")
    return files


def cmd_run(args) -> int:
    paths = {
        "source_cf": Path(args.source_cf),
        "snapshot": Path(args.snapshot),
        "work_root": Path(args.work_root),
    }
    if not paths["source_cf"].exists():
        raise DriverError(f"source CF not found: {paths['source_cf']}")
    if not paths["snapshot"].exists():
        raise DriverError(f"snapshot not found: {paths['snapshot']}")

    # 0. Immutable source integrity before anything.
    verify_cf(paths["source_cf"])
    manifest_path = Path(args.manifest) if args.manifest else paths["snapshot"].parent / "snapshot.manifest"
    snap = verify_snapshot(paths["snapshot"], manifest_path)
    if snap["mismatch"] or snap["missing"]:
        raise DriverError(f"snapshot not clean before run: {snap}")
    print(f"[preflight] source CF sha256={sha256(paths['source_cf'])}")
    print(f"[preflight] snapshot {snap['ok']}/{snap['entries']} OK, "
          f"missing={snap['missing']} mismatch={snap['mismatch']}")

    # 1. Build disposable test IB from the same source CF (fresh each run).
    paths["work_root"].mkdir(parents=True, exist_ok=True)
    (paths["work_root"] / "tmp").mkdir(exist_ok=True)
    onecv_bin = Path(args.platform_dir) / "1cv8t"
    xvfb_run = Path(args.xvfb)
    all_env = make_env(paths["work_root"], Path(args.platform_dir), Path(args.libs_dir),
                       Path(args.fonts), paths["work_root"] / "home")

    evidence = paths["work_root"] / "evidence"
    evidence.mkdir(exist_ok=True)

    # 2. GREEN variant: probe + production patch.
    green_ib = paths["work_root"] / "green-ib"
    green_receipt = evidence / "green-receipt.txt"
    if green_ib.exists():
        shutil.rmtree(green_ib)
    green_files = build_work_copy(paths, green_receipt, patched=True)
    create_ib(onecv_bin, xvfb_run, all_env, green_ib, evidence / "create")
    load_config(onecv_bin, xvfb_run, all_env, green_ib, green_files, evidence / "green-load")
    run_enterprise(onecv_bin, xvfb_run, all_env, green_ib, evidence / "green-run", green_receipt)

    # 3. RED variant: probe, no production patch.
    red_ib = paths["work_root"] / "red-ib"
    red_receipt = evidence / "red-receipt.txt"
    if red_ib.exists():
        shutil.rmtree(red_ib)
    red_files = build_work_copy(paths, red_receipt, patched=False)
    create_ib(onecv_bin, xvfb_run, all_env, red_ib, evidence / "red-create")
    load_config(onecv_bin, xvfb_run, all_env, red_ib, red_files, evidence / "red-load")
    run_enterprise(onecv_bin, xvfb_run, all_env, red_ib, evidence / "red-run", red_receipt)

    # 4. Mutation power.
    if not green_receipt.exists() or not red_receipt.exists():
        raise DriverError("receipts missing — runtime may not have run")
    green = parse_receipt(green_receipt)
    red = parse_receipt(red_receipt)
    analysis = analyze_mutation(green, red)
    print(f"[mutation] green={green}")
    print(f"[mutation] red={red}")
    print(f"[mutation] feature_flipped={analysis['feature_flipped']} "
          f"control_changed={analysis['control_changed']} "
          f"mutation_power={analysis['mutation_power']}")
    if not analysis["mutation_power"]:
        raise DriverError("mutation power not demonstrated")

    # 5. Immutable source unchanged AFTER the whole cycle.
    verify_cf(paths["source_cf"])
    snap_after = verify_snapshot(paths["snapshot"], manifest_path)
    if snap_after["mismatch"] or snap_after["missing"]:
        raise DriverError(f"snapshot changed after run: {snap_after}")
    print(f"[postflight] source CF sha256={sha256(paths['source_cf'])}")
    print(f"[postflight] snapshot {snap_after['ok']}/{snap_after['entries']} OK, "
          f"missing={snap_after['missing']} mismatch={snap_after['mismatch']}")

    print("\nOK: full issue-#10 write cycle reproduced. Evidence in "
          f"{evidence.resolve()}")
    return 0


def cmd_check(args) -> int:
    """Read-only verification of an existing run without re-running 1C."""
    source_cf = Path(args.source_cf)
    snapshot = Path(args.snapshot)
    manifest_path = Path(args.manifest) if args.manifest else snapshot.parent / "snapshot.manifest"
    verify_cf(source_cf)
    snap = verify_snapshot(snapshot, manifest_path)
    print(f"source CF sha256={sha256(source_cf)} (expected {SOURCE_CF_SHA256[:16]}…)")
    print(f"snapshot {snap['ok']}/{snap['entries']} OK, missing={snap['missing']} "
          f"mismatch={snap['mismatch']}")
    evidence = Path(args.evidence)
    if evidence.exists():
        green = parse_receipt(evidence / "green-receipt.txt")
        red = parse_receipt(evidence / "red-receipt.txt")
        analysis = analyze_mutation(green, red)
        print(f"green={green}")
        print(f"red={red}")
        print(f"mutation_power={analysis['mutation_power']}")
        return 0 if analysis["mutation_power"] and not snap["mismatch"] else 1
    return 0 if not snap["mismatch"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--source-cf", default=".local/dist/Jet-1.0.3.1-tr.cf")
    common.add_argument("--snapshot", default=".local/runs/training-jet-review-final/snapshot")
    common.add_argument("--manifest", default=None)
    common.add_argument("--platform-dir", default=".local/platform/1cv8t/x86_64/8.5.1.1150")
    common.add_argument("--libs-dir", default=".local/platform/libs")
    common.add_argument("--fonts", default=".local/platform/fonts.conf")
    common.add_argument("--xvfb", default=".local/platform/libs/usr/bin/xvfb-run")

    r = sub.add_parser("run", parents=[common], help="reproduce the full cycle")
    r.add_argument("--work-root", default=".local/runs/issue10-jet-string-whitespace-driven")

    c = sub.add_parser("check", parents=[common], help="read-only verification of a run")
    c.add_argument("--work-root", default=".local/runs/issue10-jet-string-whitespace-driven")
    c.add_argument("--evidence", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            return cmd_run(args)
        if args.command == "check":
            if not args.evidence:
                args.evidence = str(Path(args.work_root) / "evidence")
            return cmd_check(args)
        raise DriverError(f"unknown command {args.command}")
    except DriverError as e:
        print(f"[driver] FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
