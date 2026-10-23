"""Registration policy tests: real state/locks, only native Get/Set is replaced."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

from one_c_harness import registration_logging as registration

TARGET = "target:" + "a" * 64
OTHER_TARGET = "target:" + "b" * 64


class NativeApi:
    """External Get/Set oracle, including a policy change between Get and CAS Set."""
    def __init__(self, levels):
        self.levels = sorted(levels)
        self.calls = []
        self.before_set = None
        self.after_set = None
        self.get_conflict = False

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        if request["action"] == "get":
            result = {"status": "conflict" if self.get_conflict else "ok", "levels": self.levels[:]}
        else:
            if self.before_set:
                self.before_set(request)
            if sorted(request["expectedLevels"]) != self.levels:
                result = {"status": "conflict", "levels": self.levels[:]}
            else:
                self.levels = sorted(request["levels"])
                if self.after_set:
                    self.after_set(request)
                result = {"status": "ok", "levels": self.levels[:]}
        return result


class NativeSettingsContractTests(unittest.TestCase):
    def test_native_get_conflict_is_not_accepted_as_observed_policy(self):
        api = NativeApi(["Warning"])
        api.get_conflict = True
        with self.assertRaises(ValueError):
            registration.native(api, {"action": "get"})
        self.assertEqual(api.levels, ["Warning"])

    def test_native_compare_set_cannot_overwrite_a_foreign_current_policy(self):
        api = NativeApi(["Warning"])
        observed = registration.native(api, {"action": "get"})
        api.levels = ["Information"]  # Another actor changed policy after Get.
        result = registration.native(api, {"action": "set", "expectedLevels": observed["levels"],
                                           "levels": ["Error", "Warning"]})
        self.assertEqual(result, {"status": "conflict", "levels": ["Information"]})
        self.assertEqual(api.levels, ["Information"])

    def test_native_false_success_without_requested_readback_is_refused(self):
        invoke = Mock(return_value={"status": "ok", "levels": ["Warning"]})
        with self.assertRaisesRegex(ValueError, "native_readback_mismatch"):
            registration.native(invoke, {"action": "set", "expectedLevels": ["Warning"],
                                         "levels": ["Error", "Warning"]})

    def test_invalid_request_is_rejected_before_native_callback(self):
        for request in (None, [], {"action": "get", "levels": []},
                        {"action": "set", "levels": [], "expectedLevels": ["Other"]},
                        {"action": "set", "levels": ["Error", "Error"], "expectedLevels": []},
                        {"action": "set", "levels": [], "expectedLevels": [], "path": "/caller"}):
            with self.subTest(request=request):
                invoke = Mock()
                with self.assertRaises(ValueError):
                    registration.native(invoke, request)
                invoke.assert_not_called()

    def test_callback_must_return_closed_observed_settings_not_transport_payload(self):
        for result in (b'{"status":"ok","levels":[]}', None,
                       {"status": "ok", "levels": [], "cookie": "not-policy"},
                       {"status": "ok", "levels": ["Error", "Error"]},
                       {"status": "ok", "levels": ["Other"]},
                       {"status": "blocked", "reasonCode": "native_settings_failed"}):
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    registration.native(Mock(return_value=result), {"action": "get"})


@unittest.skipUnless(sys.platform.startswith("linux"), "state transactions use real Linux flock/O_NOFOLLOW")
class RegistrationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "control"
        self.api = NativeApi(["Warning", "Note"])

    def control(self, action, **kwargs):
        return registration.control(action, self.api, self.root, kwargs.pop("target_ref", TARGET), **kwargs)

    def state(self):
        return json.loads((self.root / "registration.json").read_bytes())

    def state_bytes(self):
        return (self.root / "registration.json").read_bytes()

    def test_profiles_add_levels_and_stop_restores_every_original_level(self):
        original = self.api.levels[:]
        for profile, required in (("errors", {"Error"}),
                                  ("diagnostic", {"Error", "Warning", "Information", "Note"})):
            with self.subTest(profile=profile):
                started = self.control("start", profile=profile)
                self.assertEqual(started["status"], "ok")
                self.assertEqual(set(self.api.levels), set(original) | required)
                self.assertEqual(self.state()["before"], original)
                stopped = self.control("stop", capture_ref=started["captureRef"])
                self.assertEqual((stopped["status"], stopped["configurationState"]), ("ok", "restored"))
                self.assertEqual(self.api.levels, original)

    def test_recoverable_baseline_is_on_disk_before_first_native_set(self):
        original = self.api.levels[:]
        observed = []
        def before_set(request):
            retained = self.state()
            self.assertEqual(retained["phase"], "prepared")
            self.assertEqual(retained["before"], original)
            self.assertEqual(self.api.levels, original)
            self.assertEqual(request["expectedLevels"], original)
            observed.append(retained["captureRef"])
        self.api.before_set = before_set
        result = self.control("start", profile="errors")
        self.assertEqual(observed, [result["captureRef"]])
        self.assertEqual(self.state()["phase"], "applied")

    def test_start_cas_conflict_and_stop_preserve_intervening_foreign_policy(self):
        def foreign_change(request):
            self.api.levels = ["Information"]
        self.api.before_set = foreign_change
        result = self.control("start", profile="errors")
        self.assertEqual((result["status"], result["reasonCode"]), ("conflict", "configuration_conflict"))
        self.assertEqual(self.api.levels, ["Information"])
        retained = self.state_bytes()
        self.api.before_set = None
        stopped = self.control("stop", capture_ref=self.state()["captureRef"])
        self.assertEqual(stopped["status"], "conflict")
        self.assertEqual(self.api.levels, ["Information"])
        self.assertEqual(self.state_bytes(), retained)

    def test_get_conflict_refuses_start_before_state_or_policy_mutation(self):
        self.api.get_conflict = True
        before = self.api.levels[:]
        try:
            result = self.control("start", profile="errors")
        except ValueError:
            result = {"status": "blocked"}
        self.assertIn(result["status"], ("blocked", "conflict", "unavailable"))
        self.assertEqual(self.api.levels, before)
        self.assertFalse((self.root / "registration.json").exists())
        self.assertEqual([request["action"] for request in self.api.calls], ["get"])

    def test_active_capture_reports_foreign_policy_without_overwriting_it(self):
        started = self.control("start", profile="errors")
        self.api.levels = ["Information"]
        retained = self.state_bytes()
        for action in ("status", "stop"):
            result = self.control(action, **({"capture_ref": started["captureRef"]} if action == "stop" else {}))
            self.assertEqual((result["status"], result["configurationState"]), ("conflict", "conflict"))
            self.assertEqual(self.api.levels, ["Information"])
            self.assertEqual(self.state_bytes(), retained)

    def test_crash_after_native_apply_recovers_stop_from_prepared_baseline(self):
        class InterruptedNativeReply(RuntimeError):
            pass
        original = self.api.levels[:]
        def crash_after_apply(request):
            raise InterruptedNativeReply("lost native reply after policy changed")
        self.api.after_set = crash_after_apply
        with self.assertRaises(InterruptedNativeReply):
            self.control("start", profile="errors")
        state = self.state()
        self.assertEqual(state["phase"], "prepared")
        self.assertEqual(state["before"], original)
        self.assertEqual(set(self.api.levels), set(original) | {"Error"})
        self.api.after_set = None
        result = self.control("stop", capture_ref=state["captureRef"])
        self.assertEqual(result["configurationState"], "restored")
        self.assertEqual(self.api.levels, original)
        self.assertEqual(self.state()["phase"], "restored")

    def test_stopped_capture_then_external_change_returns_truthful_restore_conflict(self):
        started = self.control("start", profile="errors")
        self.control("stop", capture_ref=started["captureRef"])
        self.api.levels = ["Information"]
        retained = self.state_bytes()
        result = self.control("stop", capture_ref=started["captureRef"])
        self.assertEqual((result["status"], result["configurationState"]), ("conflict", "conflict"))
        self.assertEqual(self.api.levels, ["Information"])
        self.assertEqual(self.state_bytes(), retained)

    def test_target_mismatch_and_corrupt_capture_ref_refuse_before_native_mutation(self):
        self.control("start", profile="errors")
        retained = self.state_bytes()
        levels = self.api.levels[:]
        self.api.calls.clear()
        with self.assertRaises(ValueError):
            self.control("status", target_ref=OTHER_TARGET)
        self.assertEqual(self.state_bytes(), retained)
        self.assertEqual(self.api.calls, [])
        corrupted = self.state()
        corrupted["captureRef"] = "capture:" + "!" * 32
        (self.root / "registration.json").write_text(json.dumps(corrupted))
        corrupt_bytes = self.state_bytes()
        with self.assertRaises(ValueError):
            self.control("status")
        self.assertEqual(self.state_bytes(), corrupt_bytes)
        self.assertEqual(self.api.levels, levels)
        self.assertEqual(self.api.calls, [])

    def test_same_capture_start_and_stop_are_idempotent_and_profile_cannot_switch(self):
        original = self.api.levels[:]
        started = self.control("start", profile="errors")
        again = self.control("start", profile="errors")
        self.assertEqual(started["captureRef"], again["captureRef"])
        retained = self.state_bytes()
        switched = self.control("start", profile="diagnostic")
        self.assertEqual(switched["status"], "conflict")
        self.assertEqual(self.state_bytes(), retained)
        self.assertEqual(self.state()["before"], original)
        for _ in range(2):
            result = self.control("stop", capture_ref=started["captureRef"])
            self.assertEqual(result["configurationState"], "restored")
            self.assertEqual(self.api.levels, original)
        self.assertEqual(sum(request["action"] == "set" for request in self.api.calls), 2)

    def test_existing_os_lock_prevents_any_native_policy_call(self):
        import fcntl
        self.root.mkdir(mode=0o700)
        with (self.root / "control.lock").open("wb") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "access_busy"):
                self.control("start", profile="errors")
        self.assertFalse((self.root / "registration.json").exists())
        self.assertEqual(self.api.calls, [])


if __name__ == "__main__":
    unittest.main()
