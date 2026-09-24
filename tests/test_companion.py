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

    def test_long_registration_log_text_is_bounded_and_recoverable_without_reexport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"; project.mkdir()
            source = root / "source.xml"
            calls = root / "calls"
            long_comment = "Ж" * 16423
            comments = [long_comment] + [f"{number}:" + "Я" * 2000 for number in range(1, 10)]
            events = "".join(
                "<v8e:Event><v8e:Level>Information</v8e:Level>"
                f"<v8e:Date>2026-09-22T06:44:{number:02d}</v8e:Date>"
                f"<v8e:Event>Long.{number}</v8e:Event><v8e:Comment>{comment}</v8e:Comment></v8e:Event>"
                for number, comment in enumerate(comments)
            )
            source.write_text(
                '<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog">'
                + events + '</v8e:EventLog>', encoding="utf-8",
            )
            exporter = root / "exporter.py"
            exporter.write_text(
                "#!/usr/bin/env python3\n"
                "import os,pathlib,sys\n"
                "sys.stdin.buffer.read()\n"
                "p=pathlib.Path(os.environ['CALLS']); p.write_text(p.read_text()+'x' if p.exists() else 'x')\n"
                "sys.stdout.buffer.write(pathlib.Path(os.environ['SOURCE_XML']).read_bytes())\n",
                encoding="utf-8",
            )
            exporter.chmod(0o755)
            previous = {name: os.environ.get(name) for name in (
                "ONE_C_HARNESS_EVENTLOG_COMMAND", "ONE_C_HARNESS_EVENTLOG_TIME_ZONE", "SOURCE_XML", "CALLS",
            )}
            os.environ.update({
                "ONE_C_HARNESS_EVENTLOG_COMMAND": str(exporter),
                "ONE_C_HARNESS_EVENTLOG_TIME_ZONE": "UTC",
                "SOURCE_XML": str(source), "CALLS": str(calls),
            })
            try:
                selected = companion.execute(_request("eventlog_select", {
                    "start": "2026-09-22T06:44:00", "end": "2026-09-22T06:45:00",
                    "filters": {}, "maximumCount": 100, "limit": 10,
                }), project)
                selected_wire = companion._dump(selected).encode("utf-8")
                page = companion.execute(_request("eventlog_page", {
                    "selectionRef": selected["selectionRef"], "offset": 0, "limit": 10,
                }), project)
                page_wire = companion._dump(page).encode("utf-8")
                record_ref = page["records"][0]["recordRef"]
                pieces: list[str] = []
                offset = 0
                while True:
                    record = companion.execute(_request("eventlog_record", {
                        "recordRef": record_ref, "commentOffset": offset, "commentMaxBytes": 16384,
                    }), project)
                    wire = companion._dump(record).encode("utf-8")
                    self.assertLessEqual(len(wire), companion.MAX_OUTPUT_BYTES)
                    self.assertNotEqual(json.loads(wire)["status"], "blocked")
                    pieces.append(record["record"]["comment"])
                    continuation = record["record"]["commentContinuation"]
                    if continuation["complete"]:
                        break
                    offset = continuation["nextOffsetBytes"]
                invalid = companion.execute(_request("eventlog_record", {
                    "recordRef": record_ref, "commentOffset": 1, "commentMaxBytes": 4096,
                }), project)
                call_receipt = calls.read_text()
            finally:
                for name, value in previous.items():
                    if value is None: os.environ.pop(name, None)
                    else: os.environ[name] = value

        self.assertEqual(selected["status"], "ok")
        self.assertEqual(page["total"], 10)
        self.assertEqual(len(page["records"]), 10)
        self.assertLessEqual(len(selected_wire), companion.MAX_OUTPUT_BYTES)
        self.assertLessEqual(len(page_wire), companion.MAX_OUTPUT_BYTES)
        self.assertNotEqual(json.loads(selected_wire)["status"], "blocked")
        self.assertNotEqual(json.loads(page_wire)["status"], "blocked")
        self.assertFalse(page["records"][0]["commentContinuation"]["complete"])
        self.assertEqual("".join(pieces), long_comment)
        self.assertEqual(invalid["reasonCode"], "invalid_request")
        self.assertEqual(call_receipt, "x")

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
