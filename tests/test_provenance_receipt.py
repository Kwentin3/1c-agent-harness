from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("provenance_receipt", ROOT / "scripts/managed_probe_prepare.py")
assert SPEC and SPEC.loader
N = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(N)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sample() -> dict[str, object]:
    identity = {"files": 3, "directories": 2, "bytes": 19, "sha256": "a" * 64}
    request = {"runId": "11111111-1111-4111-8111-111111111111", "nonce": "22222222-2222-4222-8222-222222222222"}
    client = b"client-current\n"
    server = b"server-business\n"
    payload = {"posted": "No", "movements": 0}
    return N.build_provenance_receipt(
        preparation={
            "canonicalBase": {"files": 5099, "sha256": "b" * 64},
            "patches": [
                {"role": "production", "sha256": "c" * 64},
                {"role": "instrumentation", "sha256": "d" * 64},
            ],
            "changedPaths": ["A.bsl", "B.bsl"],
            "runnerInput": identity,
        },
        request=request,
        runner={
            "status": "runtime_contract_completed",
            "preparedInvocation": {
                "sourceBefore": identity,
                "sourceAfter": identity,
                "copiedBeforeFreeze": identity,
                "frozenInput": {"identity": identity},
            },
            "inputAfter": identity,
            "runtime": {"completed": True, "receiptSha256": sha(client), "receiptBytes": len(client)},
            "storageCompaction": {"status": "completed", "manualCleanupActions": 0},
        },
        client_receipt=client,
        server_receipt=server,
        business_payload=payload,
        oracle={"status": "PASS"},
        prepared_cleanup="discarded",
    )


class ProvenanceReceiptTests(unittest.TestCase):
    def test_shared_preparation_applies_exact_patch_bytes_and_freezes_the_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("before-a\n", encoding="utf-8")
            (source / "B.txt").write_text("before-b\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            patch_a = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-before-a\n+after-a\n"
            patch_b = b"--- a/B.txt\n+++ b/B.txt\n@@ -1 +1 @@\n-before-b\n+after-b\n"

            audit = N.prepare_patched_tree(
                repo_root=repo,
                snapshot_root=source,
                prepared_root=prepared,
                patches=[("production", patch_a), ("instrumentation", patch_b)],
            )

            self.assertEqual((prepared / "A.txt").read_text(), "after-a\n")
            self.assertEqual((prepared / "B.txt").read_text(), "after-b\n")
            self.assertEqual(audit["changedPaths"], ["A.txt", "B.txt"])
            self.assertEqual(audit["patches"], [
                {"role": "production", "sha256": sha(patch_a)},
                {"role": "instrumentation", "sha256": sha(patch_b)},
            ])
            self.assertNotEqual(audit["canonicalBase"], audit["preparedInput"])
            self.assertTrue(all(not (path.stat().st_mode & 0o222) for path in (prepared, *prepared.rglob("*"))))

    def test_shared_preparation_rejects_a_patch_that_does_not_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / "snapshot"
            source.mkdir()
            (source / "A.txt").write_text("actual\n", encoding="utf-8")
            prepared = repo / ".local/prepared/task"
            stale = b"--- a/A.txt\n+++ b/A.txt\n@@ -1 +1 @@\n-stale\n+changed\n"
            with self.assertRaises(ValueError):
                N.prepare_patched_tree(
                    repo_root=repo,
                    snapshot_root=source,
                    prepared_root=prepared,
                    patches=[("production", stale)],
                )
            self.assertFalse(prepared.exists())

    def test_compact_receipt_binds_the_complete_shared_chain(self) -> None:
        receipt = sample()
        self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")
        self.assertEqual(receipt["schemaVersion"], 1)
        self.assertEqual(receipt["business"]["payload"], {"posted": "No", "movements": 0})
        self.assertEqual(base64.b64decode(receipt["business"]["rawReceipt"]["base64"]), b"server-business\n")

    def test_stale_foreign_partial_patch_input_runtime_and_cleanup_are_rejected(self) -> None:
        mutations = [
            ("stale request", lambda r: r["request"].__setitem__("sha256", "0" * 64)),
            ("duplicate patch", lambda r: r["patches"].append(copy.deepcopy(r["patches"][0]))),
            ("input mismatch", lambda r: r["input"]["frozen"].__setitem__("sha256", "0" * 64)),
            ("runtime status", lambda r: r["runtime"].__setitem__("status", "runtime_timeout")),
            ("runtime completion", lambda r: r["runtime"].__setitem__("completed", False)),
            ("cleanup", lambda r: r["cleanup"]["runner"].__setitem__("status", "failed")),
            ("prepared cleanup", lambda r: r["cleanup"].__setitem__("preparedTree", "retained")),
            ("raw receipt", lambda r: r["business"]["rawReceipt"].__setitem__("sha256", "0" * 64)),
            ("oracle", lambda r: r["oracle"].__setitem__("status", "FAIL")),
            ("partial", lambda r: r.pop("patches")),
        ]
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                receipt = copy.deepcopy(sample())
                mutate(receipt)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    N.validate_provenance_receipt(receipt)

    def test_oracle_binding_rejects_wrong_identity_or_business_payload(self) -> None:
        for section in ("requestSha256", "businessPayloadSha256", "serverReceiptSha256"):
            receipt = sample()
            receipt["oracle"][section] = "0" * 64
            with self.subTest(section=section), self.assertRaises(ValueError):
                N.validate_provenance_receipt(receipt)
    def test_task_oracle_rejects_coordinated_identity_and_business_lies(self) -> None:
        task_dir = ROOT / "experiments/issue48-kiss-receipt"
        oracle_spec = importlib.util.spec_from_file_location("issue48_task_oracle", task_dir / "oracle.py")
        assert oracle_spec and oracle_spec.loader
        oracle = importlib.util.module_from_spec(oracle_spec)
        oracle_spec.loader.exec_module(oracle)
        original = json.loads((task_dir / "receipt.json").read_text(encoding="utf-8"))
        oracle.validate(original)
        mutations = []
        identity = copy.deepcopy(original)
        identity["request"]["payload"]["runId"] = "99999999-9999-4999-8999-999999999999"
        identity["request"]["sha256"] = N._canonical_sha256(identity["request"]["payload"])
        identity["oracle"]["requestSha256"] = identity["request"]["sha256"]
        mutations.append(identity)
        business = copy.deepcopy(original)
        business["business"]["payload"]["activePosted"] = "No"
        business["business"]["payloadSha256"] = N._canonical_sha256(business["business"]["payload"])
        business["oracle"]["businessPayloadSha256"] = business["business"]["payloadSha256"]
        mutations.append(business)
        for receipt in mutations:
            self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")
            with self.assertRaises(ValueError):
                oracle.validate(receipt)

    def test_frozen_issue46_red_green_repeat_project_to_the_same_contract(self) -> None:
        package = ROOT / "experiments/issue46-supplier-warehouse-core-loop"
        validate_spec = importlib.util.spec_from_file_location("issue46_frozen", package / "validate.py")
        assert validate_spec and validate_spec.loader
        frozen = importlib.util.module_from_spec(validate_spec)
        validate_spec.loader.exec_module(frozen)
        self.assertEqual(frozen.validate(package)["status"], "PASS")
        evidence = json.loads((package / "evidence.json").read_text(encoding="utf-8"))
        for lane_name in ("red", "green", "repeat"):
            lane = evidence["lanes"][lane_name]
            patches = [{"role": "instrumentation", "sha256": lane["binding"]["instrumentationPatchSha256"]}]
            if lane["binding"]["productionPatchSha256"] is not None:
                patches.insert(0, {"role": "production", "sha256": lane["binding"]["productionPatchSha256"]})
            runner = dict(lane["runner"])
            runner["preparedInvocation"] = {
                "sourceBefore": lane["runner"]["sourceBefore"],
                "sourceAfter": lane["runner"]["sourceAfter"],
                "copiedBeforeFreeze": lane["runner"]["copiedBeforeFreeze"],
                "frozenInput": {"identity": lane["runner"]["frozenInput"]},
            }
            receipt = N.build_provenance_receipt(
                preparation={
                    "canonicalBase": {
                        "files": evidence["contract"]["snapshotFiles"],
                        "sha256": evidence["contract"]["snapshotManifestSha256"],
                    },
                    "patches": patches,
                    "changedPaths": lane["request"]["changedPaths"],
                    "runnerInput": lane["binding"]["runnerInput"],
                },
                request=lane["request"],
                runner=runner,
                client_receipt=base64.b64decode(lane["clientReceipt"]["base64"]),
                server_receipt=base64.b64decode(lane["serverReceipt"]["base64"]),
                business_payload=lane["business"],
                oracle={"status": "PASS", "task": "issue46", "lane": lane_name},
                prepared_cleanup="discarded",
            )
            with self.subTest(lane=lane_name):
                self.assertEqual(N.validate_provenance_receipt(receipt)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
