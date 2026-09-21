from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import companion
import target_admission


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _project(root: Path) -> None:
    source = root / ".local/source/export"
    source.mkdir(parents=True)
    (source / "Configuration.xml").write_text(
        "<MetaDataObject><Configuration><Properties><Name>Sample</Name><Version>2.0</Version>"
        "</Properties></Configuration></MetaDataObject>", encoding="utf-8",
    )
    module = source / "Documents/Order/Ext/ObjectModule.bsl"
    module.parent.mkdir(parents=True)
    module.write_text("Procedure Posting(Cancel)\nEndProcedure\n", encoding="utf-8")
    manifest = target_admission.tree_manifest(source)
    contract = {
        "schemaVersion": 2,
        "configuration": {"name": "Sample", "version": "2.0"},
        "source": {
            "kind": "hierarchical", "path": ".local/source/export",
            "contentId": f"sha256:{_digest(manifest)}", "fileCount": 2,
        },
        "snapshot": {
            "root": ".local/targets/sample/snapshot",
            "manifest": ".local/targets/sample/snapshot.manifest",
            "contentId": f"sha256:{_digest(manifest)}", "fileCount": 2,
        },
        "dailyNativeRoute": "scripts/shared_task_route.py run",
    }
    (root / "project-target.json").write_text(json.dumps(contract), encoding="utf-8")


def _request(operation: str, arguments: dict[str, object]) -> bytes:
    return json.dumps({"schemaVersion": 1, "operation": operation, "arguments": arguments}).encode("utf-8")


class CompanionContractTests(unittest.TestCase):
    def test_open_then_narrow_uses_only_snapshot_ref_in_a_business_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "business-project"
            project.mkdir()
            _project(project)

            opened = companion.execute(_request("open", {}), project)
            narrow = companion.execute(_request("narrow", {
                "snapshotRef": opened["snapshotRef"],
                "query": "Procedure Posting",
                "mode": "literal",
                "limit": 10,
                "maxBytes": 4096,
            }), project)

            self.assertEqual(opened["status"], "ok")
            self.assertEqual(opened["snapshotRef"]["status"], "ready")
            self.assertEqual(opened["capabilityVersion"], companion.CAPABILITY_VERSION)
            self.assertEqual(narrow["status"], "ok")
            self.assertEqual(narrow["results"], [{
                "fragment": "Procedure Posting(Cancel)",
                "line": 1,
                "path": "Documents/Order/Ext/ObjectModule.bsl",
            }])
            self.assertFalse((project / "scripts").exists())

    def test_narrow_rejects_raw_snapshot_path_instead_of_bypassing_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            response = companion.execute(_request("narrow", {
                "snapshotRef": {"path": ".local/source/export"},
                "query": "Posting",
            }), project)

            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["reasonCode"], "snapshot_invalid")
            self.assertNotIn(str(project), json.dumps(response))

    def test_verify_rejects_an_unadmitted_snapshot_before_native_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            response = companion.execute(_request("verify", {
                "snapshotRef": {"path": ".local/source/export"},
                "request": "tasks/request.json",
                "productionPatch": "tasks/production.patch",
                "instrumentationPatch": "tasks/instrumentation.patch",
                "oracle": "tasks/oracle.py",
                "receipt": ".local/receipt.json",
                "timeoutSeconds": 480,
            }), project)

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "snapshot_invalid")

    def test_open_preserves_the_canonical_target_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _project(project)
            shutil.rmtree(project / ".local/source")
            response = companion.execute(_request("open", {}), project)

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "source_missing")
        self.assertNotIn(temporary, json.dumps(response))

    def test_invalid_request_is_one_bounded_blocker_without_stacktrace(self) -> None:
        response = companion.execute(b"{", Path.cwd())

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["reasonCode"], "invalid_request")
        self.assertNotIn("Traceback", json.dumps(response))
    def test_observe_then_expand_observation_uses_techlog_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            source = Path(temporary) / "techlog"
            log = source / "1cv8t_1" / "26091812.log"
            project.mkdir(); log.parent.mkdir(parents=True)
            log.write_text("00:00.000001-0,EXCP,1,process=1,Descr='private'\\n", encoding="utf-8")
            previous = os.environ.get("ONE_C_HARNESS_TECHLOG_ROOT")
            previous_zone = os.environ.get("ONE_C_HARNESS_TECHLOG_TIME_ZONE")
            os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = str(source)
            os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = "UTC"
            try:
                observed = companion.execute(_request("observe", {
                    "start": "2026-09-18T12:00:00", "end": "2026-09-18T12:00:01",
                    "events": ["EXCP"], "limit": 10,
                }), project)
                expanded = companion.execute(_request("expand_observation", {
                    "groupRef": observed["groups"][0]["ref"], "offset": 0, "limit": 10,
                }), project)
            finally:
                if previous is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT", None)
                else: os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = previous
                if previous_zone is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_TIME_ZONE", None)
                else: os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = previous_zone
        self.assertEqual(observed["status"], "ok")
        self.assertEqual(expanded["status"], "ok")
        self.assertEqual(expanded["records"][0]["event"], "EXCP")
        self.assertNotIn("private", json.dumps(expanded))

    def test_investigate_then_expand_exposes_bounded_runtime_receipt_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            point = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
            for number, status in enumerate(("runtime_contract_completed", "runtime_timeout", "runtime_timeout")):
                result = project / ".local/runs/native-cycle" / f"run-{number}" / "run/result.json"
                result.parent.mkdir(parents=True, exist_ok=True)
                result.write_text(json.dumps({
                    "status": status,
                    "totalDurationSeconds": 100 + number,
                    "environment": {"HOME": "/private/runtime/path"},
                }), encoding="utf-8")
                os.utime(result, (point.timestamp(), point.timestamp()))

            investigated = companion.execute(_request("investigate", {
                "incident": {"start": "2026-09-18T08:00:00Z", "end": "2026-09-18T08:00:00Z"},
                "focus": ["native_execution"],
                "limit": 10,
            }), project)
            finding = investigated["findings"][0]
            expanded = companion.execute(_request("expand", {
                "evidenceRef": finding["evidenceRefs"][0],
                "limit": 10,
            }), project)

        self.assertEqual(investigated["status"], "ok")
        self.assertEqual(investigated["summary"]["recordCount"], 3)
        self.assertEqual(finding["observed"]["status"], "runtime_timeout")
        self.assertEqual(expanded["status"], "ok")
        self.assertEqual(len(expanded["records"]), 2)
        self.assertNotIn("/private/runtime/path", json.dumps(expanded))
        self.assertNotIn(temporary, json.dumps(expanded))
