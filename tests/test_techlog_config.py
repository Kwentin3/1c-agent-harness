"""Real temporary XML/files, native process locks, and interrupted publication."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from one_c_harness import techlog_config as tc


class TechlogConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = self.root / "logcfg.xml"
        self.logs = self.root / "collected"
        self.state = self.root / "control"
        self.manager = self.make()

    def make(self, **overrides):
        values = dict(config_path=self.config, log_directory=self.logs,
                      state_directory=self.state, target_ref="allowed-runtime-A")
        values.update(overrides)
        return tc.TechlogConfig(**values)

    def test_preserves_existing_namespaced_settings_adds_only_narrow_log_and_restores_exact_bytes(self):
        original = (b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\r\n'
                    b'<config xmlns="http://v8.1c.ru/v8/tech-log">\r\n'
                    b'<!-- operator setting -->\r\n'
                    b'<log location="/operator/log" history="24"><event><eq property="name" value="EXCP"/></event>'
                    b'<property name="duration"/></log><dump location="/operator/dump" create="false"/>'
                    b'</config>\r\n')
        self.config.write_bytes(original)
        before = ET.fromstring(original)
        result = self.manager.start()
        applied = self.config.read_bytes()
        root = ET.fromstring(applied)
        ns = "{" + tc.NAMESPACE + "}"
        self.assertEqual(root.tag, ns + "config")
        self.assertEqual([ET.tostring(x) for x in list(root)[:-1]], [ET.tostring(x) for x in before])
        own = root[-1]
        self.assertEqual(own.tag, ns + "log")
        self.assertEqual(own.attrib, {"location": str(self.logs), "history": "1"})
        self.assertEqual([e.find(ns + "eq").attrib for e in own.findall(ns + "event")],
                         [{"property": "name", "value": event} for event in ("EXCP", "EXCPCNTX")])
        self.assertEqual([p.attrib for p in own.findall(ns + "property")], [{"name": "all"}])
        self.assertEqual(len(root.findall(ns + "dump")), 1)
        self.assertIn(b"operator setting", applied)
        self.assertTrue(result["configurationApplied"])
        self.assertEqual(result["platformObservation"], "not_performed")
        self.assertEqual((self.state / "original.bin").read_bytes(), original)
        self.assertEqual(self.manager.stop()["status"], "inactive")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.state / "state.json").exists())

    def test_absent_empty_and_unnamespaced_configs_restore_their_distinct_originals(self):
        for original in (None, b"", b" \n\t", b'<config><dump create="false"/></config>'):
            with self.subTest(original=original):
                if original is None:
                    self.config.unlink(missing_ok=True)
                else:
                    self.config.write_bytes(original)
                self.manager.start()
                self.assertEqual(ET.fromstring(self.config.read_bytes()).tag.split("}")[-1], "config")
                self.manager.stop()
                self.assertEqual(self.config.read_bytes() if self.config.exists() else None, original)

    def test_profiles_are_narrow_and_cannot_change_an_active_collection(self):
        with self.assertRaises(tc.TechlogConfigError):
            self.manager.start("dumpall")
        self.assertFalse(self.state.exists())
        self.manager.start("diagnostic")
        applied = self.config.read_bytes()
        root = ET.fromstring(applied)
        self.assertEqual([item.get("value") for item in root.iter("{" + tc.NAMESPACE + "}eq")],
                         ["EXCP", "EXCPCNTX", "CONN"])
        with self.assertRaises(tc.TechlogConfigError) as changed:
            self.manager.start("errors")
        self.assertEqual(changed.exception.code, "profile_in_use")
        self.assertEqual(self.config.read_bytes(), applied)
        self.assertTrue(self.manager.start("diagnostic")["alreadyActive"])
        self.manager.stop()
        self.manager.start("errors")
        self.assertNotIn(b"CONN", self.config.read_bytes())
        self.manager.stop()

    def test_status_is_nonmutating_start_is_idempotent_and_stop_can_repeat(self):
        self.assertEqual(self.manager.status()["status"], "inactive")
        self.assertFalse(self.state.exists())
        self.assertFalse(self.logs.exists())
        self.manager.start()
        snapshot = self.config.read_bytes()
        backup = (self.state / "original.bin").read_bytes()
        self.assertTrue(self.manager.start()["alreadyActive"])
        self.assertEqual(self.config.read_bytes(), snapshot)
        self.assertEqual((self.state / "original.bin").read_bytes(), backup)
        self.assertEqual(self.manager.status()["status"], "active")
        self.manager.stop()
        self.assertEqual(self.manager.stop()["status"], "inactive")
        self.assertFalse(self.config.exists())

    def test_capture_ref_is_persisted_and_foreign_stop_cannot_restore(self):
        result = self.manager.start()
        capture = result['captureRef']
        applied = self.config.read_bytes()
        self.assertEqual(json.loads((self.state / 'state.json').read_bytes())['captureRef'], capture)
        self.assertEqual(self.make().status()['captureRef'], capture)
        with self.assertRaises(tc.TechlogConfigError) as foreign:
            self.manager.stop(capture_ref='capture:' + 'f' * 32)
        self.assertEqual(foreign.exception.code, 'capture_not_found')
        self.assertEqual(self.config.read_bytes(), applied)
        self.manager.stop(capture_ref=capture)
        self.assertFalse(self.config.exists())

    def test_foreign_edit_and_deletion_are_preserved_with_backup_and_state(self):
        for foreign in (b'<config><log location="foreign" history="7"/></config>', None):
            with self.subTest(foreign=foreign), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve()
                config = root / "logcfg.xml"
                config.write_bytes(b"<config/>")
                manager = tc.TechlogConfig(config, root / "logs", root / "state", target_ref="same")
                manager.start()
                if foreign is None:
                    config.unlink()
                else:
                    config.write_bytes(foreign)
                self.assertEqual(manager.status()["status"], "conflict")
                self.assertEqual(manager.stop()["status"], "conflict")
                self.assertEqual(manager.start()["status"], "conflict")
                self.assertEqual(config.read_bytes() if config.exists() else None, foreign)
                self.assertEqual((root / "state/original.bin").read_bytes(), b"<config/>")
                self.assertTrue((root / "state/state.json").is_file())

    def test_durable_prepared_state_exists_before_config_publish_and_can_resume(self):
        self.config.write_bytes(b'<config><dump create="false"/></config>')
        real_atomic = tc._atomic

        def fail_publication(path, data, *args):
            if path == self.config:
                state = json.loads((self.state / "state.json").read_bytes())
                self.assertEqual(state["phase"], "prepared")
                self.assertEqual((self.state / "original.bin").read_bytes(), self.config.read_bytes())
                raise OSError("simulated interruption before publication")
            return real_atomic(path, data, *args)

        with mock.patch.object(tc, "_atomic", side_effect=fail_publication):
            with self.assertRaises(OSError):
                self.manager.start()
        self.assertEqual(self.manager.status()["status"], "prepared")
        self.assertTrue(self.manager.start()["configurationApplied"])
        self.manager.stop()
        self.assertEqual(self.config.read_bytes(), b'<config><dump create="false"/></config>')

    def test_interruption_after_publication_recovers_without_adding_a_second_log(self):
        real_save = self.manager._save

        def fail_active(value):
            if value["phase"] == "active":
                raise OSError("simulated interruption after publication")
            return real_save(value)

        with mock.patch.object(self.manager, "_save", side_effect=fail_active):
            with self.assertRaises(OSError):
                self.manager.start()
        applied = self.config.read_bytes()
        self.assertEqual(self.manager.status()["status"], "active")
        self.assertTrue(self.manager.start()["alreadyActive"])
        self.assertEqual(self.config.read_bytes(), applied)
        self.manager.stop()
        self.assertFalse(self.config.exists())

    def test_binding_and_backup_tampering_cannot_restore_another_target(self):
        self.config.write_bytes(b"<config/>")
        self.manager.start()
        for manager in (self.make(target_ref="other-runtime"), self.make(log_directory=self.root / "other-logs"),
                        self.make(config_path=self.root / "other.xml")):
            with self.assertRaises(tc.TechlogConfigError):
                manager.stop()
        applied = self.config.read_bytes()
        (self.state / "original.bin").write_bytes(b"forged backup")
        with self.assertRaises(tc.TechlogConfigError):
            self.manager.stop()
        self.assertEqual(self.config.read_bytes(), applied)

    def test_invalid_xml_or_preexisting_same_location_is_not_adopted(self):
        for original in (b"<broken", b"<unrelated/>", b'<!DOCTYPE config [<!ENTITY x "boom">]><config/>',
                         ('<config><log location="' + str(self.logs) + '"/></config>').encode()):
            with self.subTest(original=original):
                self.config.write_bytes(original)
                with self.assertRaises(tc.TechlogConfigError):
                    self.manager.start()
                self.assertEqual(self.config.read_bytes(), original)
                self.assertFalse((self.state / "state.json").exists())

    def test_unsafe_paths_and_overlaps_are_refused(self):
        for changes in ({"config_path": Path("relative.xml")}, {"config_path": self.root / ".." / "escape.xml"},
                        {"log_directory": self.root}, {"state_directory": self.logs},
                        {"state_directory": self.logs / "state"}):
            with self.subTest(changes=changes), self.assertRaises(tc.TechlogConfigError):
                self.make(**changes)
        missing_parent = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            self.make(state_directory=missing_parent / "state").start()
        self.assertFalse(missing_parent.exists())

    def test_symlink_paths_and_hardlinked_config_are_refused(self):
        external = self.root / "external.xml"
        external.write_bytes(b"<config/>")
        try:
            self.config.symlink_to(external)
        except OSError as error:
            self.skipTest("native symlink creation unavailable: " + type(error).__name__)
        with self.assertRaises(tc.TechlogConfigError):
            self.make()
        self.config.unlink()
        os.link(external, self.config)
        with self.assertRaises(tc.TechlogConfigError):
            self.manager.start()
        self.assertEqual(external.read_bytes(), b"<config/>")

    def test_native_lock_in_another_process_blocks_change_and_releases(self):
        self.manager.start()
        before = self.config.read_bytes()
        code = """import os,sys
fd=os.open(sys.argv[1],os.O_RDWR)
if os.name=='posix':
 import fcntl
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
else:
 import msvcrt
 msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
print('LOCKED',flush=True)
sys.stdin.readline()
os.close(fd)
"""
        child = subprocess.Popen([sys.executable, "-u", "-c", code, str(self.state / "lock")],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline().rstrip(b"\r\n"), b"LOCKED")
            with self.assertRaises(tc.TechlogConfigError) as blocked:
                self.manager.stop()
            self.assertEqual(blocked.exception.code, "busy")
            self.assertEqual(self.config.read_bytes(), before)
        finally:
            child.communicate(b"\n", timeout=5)
        self.assertEqual(child.returncode, 0)
        self.assertEqual(self.manager.stop()["status"], "inactive")
