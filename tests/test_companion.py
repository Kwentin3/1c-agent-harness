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

    def test_observation_info_and_expansion_modes_are_closed_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            source = Path(temporary) / "techlog"
            log = source / "1cv8t_1" / "26091812.log"
            project.mkdir(); log.parent.mkdir(parents=True)
            log.write_text("\n".join([
                "00:00.000001-0,EXCP,1,Exception=First,Descr='first detail',SrcName=core",
                "00:00.000002-0,EXCP,1,Exception=Second,Descr='second detail',SrcName=db",
            ]) + "\n", encoding="utf-8")
            previous = os.environ.get("ONE_C_HARNESS_TECHLOG_ROOT")
            previous_zone = os.environ.get("ONE_C_HARNESS_TECHLOG_TIME_ZONE")
            os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = str(source)
            os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = "UTC"
            try:
                info = companion.execute(_request("observation_info", {}), project)
                observed = companion.execute(_request("observe", {
                    "start": "2026-09-18T12:00:00", "end": "2026-09-18T12:00:01",
                    "events": ["EXCP"], "filters": {"sourceComponent": "db"}, "limit": 1,
                }), project)
                groups = companion.execute(_request("expand_observation", {
                    "observationRef": observed["observationRef"], "offset": 0, "limit": 1,
                }), project)
                records = companion.execute(_request("expand_observation", {
                    "groupRef": groups["groups"][0]["ref"], "offset": 0, "limit": 1,
                }), project)
                neighbors = companion.execute(_request("expand_observation", {
                    "recordRef": records["records"][0]["recordRef"], "before": 1, "after": 1,
                }), project)
            finally:
                if previous is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT", None)
                else: os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = previous
                if previous_zone is None: os.environ.pop("ONE_C_HARNESS_TECHLOG_TIME_ZONE", None)
                else: os.environ["ONE_C_HARNESS_TECHLOG_TIME_ZONE"] = previous_zone

        self.assertEqual(info["status"], "ok")
        self.assertEqual(observed["summary"]["recordCount"], 1)
        self.assertEqual(groups["level"], "observation")
        self.assertEqual(records["level"], "group")
        self.assertEqual(neighbors["level"], "record")
        self.assertEqual(neighbors["scope"], "retainedFilteredSelection")

    def test_registration_log_select_page_and_record_are_closed_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"; project.mkdir()
            exporter = Path(temporary) / "exporter.py"
            exporter.write_text("""#!/usr/bin/env python3
import sys
sys.stdin.buffer.read()
sys.stdout.write('<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog"><v8e:Event><v8e:Level>Error</v8e:Level><v8e:Date>2026-09-22T06:44:16</v8e:Date><v8e:Event>_$Data$_.Update</v8e:Event><v8e:User>alice</v8e:User><v8e:Metadata>Document.Invoice</v8e:Metadata></v8e:Event></v8e:EventLog>')
""", encoding="utf-8")
            exporter.chmod(0o755)
            previous_command = os.environ.get("ONE_C_HARNESS_EVENTLOG_COMMAND")
            previous_zone = os.environ.get("ONE_C_HARNESS_EVENTLOG_TIME_ZONE")
            os.environ["ONE_C_HARNESS_EVENTLOG_COMMAND"] = str(exporter)
            os.environ["ONE_C_HARNESS_EVENTLOG_TIME_ZONE"] = "UTC"
            try:
                selected = companion.execute(_request("eventlog_select", {
                    "start": "2026-09-22T06:44:00", "end": "2026-09-22T06:45:00",
                    "filters": {"level": "Error"}, "maximumCount": 100, "limit": 20,
                }), project)
                page = companion.execute(_request("eventlog_page", {
                    "selectionRef": selected["selectionRef"], "offset": 0, "limit": 20,
                    "filters": {"level": "Error"},
                }), project)
                record = companion.execute(_request("eventlog_record", {
                    "recordRef": page["records"][0]["recordRef"],
                }), project)
            finally:
                if previous_command is None: os.environ.pop("ONE_C_HARNESS_EVENTLOG_COMMAND", None)
                else: os.environ["ONE_C_HARNESS_EVENTLOG_COMMAND"] = previous_command
                if previous_zone is None: os.environ.pop("ONE_C_HARNESS_EVENTLOG_TIME_ZONE", None)
                else: os.environ["ONE_C_HARNESS_EVENTLOG_TIME_ZONE"] = previous_zone

        self.assertEqual(selected["operation"], "eventlog_select")
        self.assertEqual(page["operation"], "eventlog_page")
        self.assertEqual(page["summary"]["countScope"], "refinedRetainedSelection")
        self.assertEqual(record["operation"], "eventlog_record")
        self.assertEqual(record["record"]["metadata"]["name"], "Document.Invoice")

    def test_registration_log_requests_reject_unknown_fields(self) -> None:
        result = companion.execute(_request("eventlog_record", {"recordRef": "x", "path": "/tmp/raw"}), self.root if hasattr(self, "root") else Path.cwd())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasonCode"], "invalid_request")

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
