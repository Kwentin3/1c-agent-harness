#!/usr/bin/env python3
"""Replay Issue #43 patches on the canonical snapshot; never launches 1C."""
from __future__ import annotations

import hashlib
import json
import shutil
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
SNAPSHOT = REPO / ".local/runs/training-jet-review-final/snapshot"
WORK = REPO / ".local/issue43-input-reconstruction"
CHANGED = [
    "Documents/InventoryTransfer/Ext/ObjectModule.bsl",
    "CommonModules/JetServerCall/Ext/Module.bsl",
    "Ext/ManagedApplicationModule.bsl",
]
sys.path.insert(0, str(REPO / "scripts"))
from native_cycle import tree_identity  # type: ignore  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_patch(tree: Path, patch_path: Path) -> None:
    text = patch_path.read_text(encoding="utf-8")
    # The captured difflib patch follows a BSL file with no final newline.
    text = text.replace("#EndRegion--- a/", "#EndRegion\n--- a/")
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        assert lines[index].startswith("--- a/")
        relative = lines[index][6:].rstrip("\r\n")
        index += 1
        assert lines[index].rstrip("\r\n") == f"+++ b/{relative}"
        index += 1
        path = tree / relative
        original = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        output: list[str] = []
        cursor = 0
        while index < len(lines) and not lines[index].startswith("--- a/"):
            header = lines[index]
            assert header.startswith("@@ ")
            old_start = int(header.split()[1].split(",")[0][1:])
            output.extend(original[cursor:old_start - 1])
            cursor = old_start - 1
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@ ", "--- a/")):
                marker, payload = lines[index][0], lines[index][1:]
                if marker == " ":
                    expected = original[cursor]
                    assert expected == payload or (
                        not expected.endswith(("\n", "\r"))
                        and expected == payload.rstrip("\r\n")
                    )
                    output.append(expected)
                    cursor += 1
                elif marker == "-":
                    assert original[cursor] == payload
                    cursor += 1
                elif marker == "+":
                    output.append(payload)
                elif marker != "\\":
                    raise AssertionError(f"bad hunk marker: {marker!r}")
                index += 1
        output.extend(original[cursor:])
        path.write_text("\ufeff" + "".join(output), encoding="utf-8", newline="")


def reconstruct(lane: int) -> dict:
    name = f"bound-green-{lane}"
    tree = WORK / name
    shutil.copytree(SNAPSHOT, tree)
    canonical = {relative: sha(tree / relative) for relative in CHANGED}
    for relative in CHANGED:
        path = tree / relative
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    production = PACKAGE / "production.patch"
    instrumentation = PACKAGE / f"{name}-instrumentation.patch"
    apply_patch(tree, production)
    apply_patch(tree, instrumentation)
    prepared = tree_identity(tree)
    patched = {relative: sha(tree / relative) for relative in CHANGED}
    for path in (tree, *tree.rglob("*")):
        path.chmod(path.lstat().st_mode & ~0o222)
    frozen = tree_identity(tree)
    return {
        "schemaVersion": 1,
        "lane": name,
        "canonicalManifestSha256": "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691",
        "productionPatchSha256": sha(production),
        "instrumentationPatchSha256": sha(instrumentation),
        "changedFiles": {
            path: {"canonicalSha256": canonical[path], "patchedSha256": patched[path]}
            for path in CHANGED
        },
        "preparedTree": prepared,
        "frozenTree": frozen,
    }


def main() -> None:
    if WORK.exists():
        raise SystemExit(f"refusing pre-existing work root: {WORK}")
    WORK.mkdir(parents=True)
    try:
        for lane in (1, 2):
            actual = reconstruct(lane)
            expected = json.loads(
                (PACKAGE / f"bound-green-{lane}-input-binding.json").read_text(encoding="utf-8")
            )
            assert actual == expected, f"lane {lane} reconstruction mismatch"
            print(f"PASS {actual['lane']} {actual['preparedTree']['sha256']} {actual['frozenTree']['sha256']}")
    finally:
        for tree in WORK.glob("*"):
            if tree.is_dir():
                for path in (tree, *tree.rglob("*")):
                    path.chmod(path.lstat().st_mode | (stat.S_IRWXU if path.is_dir() else stat.S_IWUSR))
        shutil.rmtree(WORK)


if __name__ == "__main__":
    main()
