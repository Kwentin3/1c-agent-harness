from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "managed_probe_prepare.py"
MANAGED = Path("Ext/ManagedApplicationModule.bsl")
SERVER = Path("CommonModules/JetServerCall/Ext/Module.bsl")


def load_tool() -> object:
    spec = importlib.util.spec_from_file_location("managed_probe_prepare_under_test", TOOL)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load managed probe preparation tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_snapshot(root: Path, *, onstart: bool = True, initial_vars: str = "") -> None:
    (root / "Ext").mkdir(parents=True)
    (root / "CommonModules" / "JetServerCall" / "Ext").mkdir(parents=True)
    managed = (
        "#Region EventHandlers\n"
        "Procedure BeforeStart()\n"
        "\tStandardSubsystemsClient.BeforeStart();\n"
        "EndProcedure\n\n"
    )
    if onstart:
        managed += (
            "Procedure OnStart()\n"
            f"{initial_vars}"
            "\t// StandardSubsystems\n"
            "\tStandardSubsystemsClient.OnStart();\n"
            "\t// End StandardSubsystems\n"
            "EndProcedure\n\n"
        )
    managed += "Procedure BeforeExit(Cancel, WarningText)\n\tReturn;\nEndProcedure\n#EndRegion\n"
    (root / MANAGED).write_text(managed, encoding="utf-8")
    (root / SERVER).write_text(
        "#Region Public\nFunction ExistingServerHelper() Export\n\tReturn True;\nEndFunction\n#EndRegion\n",
        encoding="utf-8",
    )
    (root / "CommonModules" / "JetServerCall.xml").write_text(
        "<CommonModule><Server>true</Server><ServerCall>true</ServerCall></CommonModule>\n",
        encoding="utf-8",
    )
    (root / "Configuration.xml").write_text("<Configuration/>\n", encoding="utf-8")


def client_block() -> bytes:
    return (
        b"\tIf Not IsBlankString(LaunchParameter) Then\n"
        b"\t\tReturn;\n"
        b"\tEndIf;\n\n"
    )


def server_block() -> bytes:
    return (
        b"#Region TestManagedProbe\n"
        b"Function TestManagedProbe() Export\n"
        b"\tReturn True;\n"
        b"EndFunction\n"
        b"#EndRegion\n"
    )


class ManagedProbePreparationTests(unittest.TestCase):
    def prepare(self, tool: object, repo: Path, snapshot: Path, prepared: Path) -> dict[str, object]:
        return tool.prepare_probe(
            repo_root=repo,
            snapshot_root=snapshot,
            prepared_root=prepared,
            client_block=client_block(),
            server_block=server_block(),
        )

    def test_preparation_preserves_full_module_closure_and_freezes_tree(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-a"
            write_snapshot(snapshot)
            source_before = {
                path.relative_to(snapshot).as_posix(): path.read_bytes()
                for path in snapshot.rglob("*") if path.is_file()
            }

            audit = self.prepare(tool, repo, snapshot, prepared)

            self.assertEqual(audit["changedPaths"], [SERVER.as_posix(), MANAGED.as_posix()])
            self.assertEqual(audit["staticCheck"], "pass")
            self.assertEqual(audit["forbiddenAddedMatches"], [])
            self.assertEqual(
                {
                    path.relative_to(snapshot).as_posix(): path.read_bytes()
                    for path in snapshot.rglob("*") if path.is_file()
                },
                source_before,
            )
            client = (prepared / MANAGED).read_bytes()
            server = (prepared / SERVER).read_bytes()
            self.assertIn(b"Procedure BeforeStart()", client)
            self.assertIn(b"Procedure BeforeExit(Cancel, WarningText)", client)
            self.assertIn(client_block(), client)
            self.assertIn(b"Function ExistingServerHelper() Export", server)
            self.assertTrue(server.endswith(server_block()))
            self.assertEqual(audit["client"]["addedSha256"], sha256(client_block()))
            self.assertEqual(audit["server"]["addedSha256"], sha256(server_block()))
            self.assertTrue(all(not (path.stat().st_mode & 0o222) for path in (prepared, *prepared.rglob("*"))))

    def test_preparation_leaves_read_only_snapshot_modes_unchanged(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-read-only"
            write_snapshot(snapshot)
            for path in sorted((snapshot, *snapshot.rglob("*")), key=lambda item: len(item.parts), reverse=True):
                path.chmod(path.stat().st_mode & ~0o222)
            source_modes = {
                path.relative_to(snapshot).as_posix(): stat.S_IMODE(path.stat().st_mode)
                for path in (snapshot, *snapshot.rglob("*"))
            }

            self.prepare(tool, repo, snapshot, prepared)

            self.assertEqual(
                {
                    path.relative_to(snapshot).as_posix(): stat.S_IMODE(path.stat().st_mode)
                    for path in (snapshot, *snapshot.rglob("*"))
                },
                source_modes,
            )

    def test_preparation_rejects_dangling_symlink_output(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            parent = repo / ".local" / "prepared"
            parent.mkdir(parents=True)
            prepared = parent / "case-link"
            escaped = parent / "escaped"
            prepared.symlink_to(escaped, target_is_directory=True)
            write_snapshot(snapshot)

            with self.assertRaisesRegex(ValueError, "symlink"):
                self.prepare(tool, repo, snapshot, prepared)
            self.assertTrue(prepared.is_symlink())
            self.assertFalse(escaped.exists())

    def test_preparation_rejects_dynamic_or_business_generated_block(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-unsafe"
            write_snapshot(snapshot)

            with self.assertRaisesRegex(ValueError, "forbidden"):
                tool.prepare_probe(
                    repo_root=repo,
                    snapshot_root=snapshot,
                    prepared_root=prepared,
                    client_block=b"\tExecute(\"unsafe\");\n",
                    server_block=server_block(),
                )
            self.assertFalse(prepared.exists())

    def test_preparation_inserts_after_initial_var_declarations(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-var"
            write_snapshot(snapshot, initial_vars="\tVar StartupValue;\n")

            self.prepare(tool, repo, snapshot, prepared)

            client = (prepared / MANAGED).read_bytes()
            self.assertLess(client.index(b"Var StartupValue;"), client.index(client_block()))

    def test_preparation_handles_multiline_var_comment_semicolon(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-multiline-var"
            write_snapshot(snapshot, initial_vars="\tVar\n\t\tStartupValue, // comment ;\n\t\tAnotherValue;\n")

            self.prepare(tool, repo, snapshot, prepared)

            client = (prepared / MANAGED).read_bytes()
            self.assertLess(client.index(b"AnotherValue;"), client.index(client_block()))

    def test_preparation_rejects_missing_onstart_without_output(self) -> None:
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / "snapshot"
            prepared = repo / ".local" / "prepared" / "case-no-onstart"
            write_snapshot(snapshot, onstart=False)

            with self.assertRaisesRegex(ValueError, "OnStart"):
                self.prepare(tool, repo, snapshot, prepared)
            self.assertFalse(prepared.exists())


if __name__ == "__main__":
    unittest.main()
