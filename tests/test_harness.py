from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "harness.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HarnessContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.snapshot = self.root / "snapshot"
        self.snapshot.mkdir()
        (self.snapshot / "Configuration.xml").write_text("<Configuration>\n<Name>Demo</Name>\n</Configuration>\n", encoding="utf-8")
        (self.snapshot / "ConfigDumpInfo.xml").write_text("<ConfigDumpInfo/>\n", encoding="utf-8")
        module = self.snapshot / "CommonModules" / "Demo" / "Ext" / "Module.bsl"
        module.parent.mkdir(parents=True)
        module.write_text("Function Demo() Export\n    Return True;\nEndFunction\n", encoding="utf-8")
        self.manifest = self.root / "snapshot.manifest"
        lines = []
        for path in sorted(p for p in self.snapshot.rglob("*") if p.is_file()):
            lines.append(f"{sha256(path)}  {path.relative_to(self.snapshot).as_posix()}\n")
        self.manifest.write_text("".join(lines), encoding="utf-8")
        self.questions = self.root / "questions.json"
        self.questions.write_text(json.dumps({"schemaVersion": 1, "questions": [{"id": "Q1", "text": "What is the demo?"}]}) + "\n", encoding="utf-8")
        self.spec = self.root / "experiment.json"
        self.outputs = self.root / "outputs"
        self.outputs.mkdir()
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.spec.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fixture",
            "snapshot": {
                "root": str(self.snapshot),
                "manifest": str(self.manifest),
                "contentId": f"sha256:{sha256(self.manifest)}",
            },
            "questions": {"path": str(self.questions), "sha256": sha256(self.questions)},
            "outputRoot": str(self.outputs),
            "cacheRoot": str(self.cache),
            "evaluation": {"minimumFactAccuracy": 0.9, "maxDangerousFalseClaims": 0, "maximumInvalidLocators": 0},
        }) + "\n", encoding="utf-8")
        self.answer = self.root / "answer.json"
        self.answer.write_text(json.dumps({
            "schemaVersion": 1,
            "experimentId": "fixture",
            "snapshotContentId": f"sha256:{sha256(self.manifest)}",
            "questionSetSha256": sha256(self.questions),
            "client": {"name": "fixture-client", "version": "1"},
            "answers": [{
                "questionId": "Q1",
                "answer": "The module exports Demo.",
                "facts": [{"id": "F1", "text": "Demo is exported."}],
                "inferences": [],
                "assumptions": [],
                "unknowns": [],
                "locators": [{"path": "CommonModules/Demo/Ext/Module.bsl", "startLine": 1, "endLine": 1, "claimIds": ["F1"]}],
            }],
            "metrics": {"durationSeconds": 1.0, "toolOperations": 1},
        }) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CLI), *(str(x) for x in args)], text=True, capture_output=True, check=False)

    def test_preflight_and_verify_answer(self) -> None:
        preflight = self.outputs / "preflight.json"
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", preflight)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(preflight.read_text())["status"], "ok")
        verified = self.outputs / "verified.json"
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", verified)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(verified.read_text())["locatorCount"], 1)

    def test_assemble_answer_uses_system_metadata_and_question_order(self) -> None:
        questions = {
            "schemaVersion": 1,
            "questions": [
                {"id": "Q1", "text": "What is the demo?"},
                {"id": "Q2", "text": "What is unknown?"},
            ],
        }
        self.questions.write_text(json.dumps(questions) + "\n", encoding="utf-8")
        spec = json.loads(self.spec.read_text())
        spec["questions"]["sha256"] = sha256(self.questions)
        self.spec.write_text(json.dumps(spec) + "\n", encoding="utf-8")

        q1 = self.root / "q1.json"
        q2 = self.root / "q2.json"
        base = json.loads(self.answer.read_text())["answers"][0]
        q1.write_text(json.dumps(base) + "\n", encoding="utf-8")
        q2.write_text(json.dumps({
            "questionId": "Q2",
            "answer": "The live state is not in the snapshot.",
            "facts": [],
            "inferences": [],
            "assumptions": [],
            "unknowns": [{"id": "U1", "text": "Live state is unknown."}],
            "locators": [],
        }) + "\n", encoding="utf-8")
        client = self.root / "client.json"
        client.write_text(json.dumps({"name": "second-client", "version": "2"}) + "\n")
        metrics = self.root / "metrics.json"
        metrics.write_text(json.dumps({"durationSeconds": 3, "toolOperations": 4}) + "\n")

        assembled = self.outputs / "assembled.json"
        result = self.run_cli(
            "assemble-answer", "--experiment", self.spec,
            "--unit", q2, "--unit", q1,
            "--client", client, "--metrics", metrics,
            "--output", assembled,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        answer = json.loads(assembled.read_text())
        self.assertEqual([item["questionId"] for item in answer["answers"]], ["Q1", "Q2"])
        self.assertEqual(answer["client"], {"name": "second-client", "version": "2"})
        self.assertEqual(answer["experimentId"], "fixture")
        self.assertNotIn("bundleId", answer)
        self.assertEqual(answer["metrics"]["toolOperations"], 4)

    def test_verify_unit_returns_receipt_without_publishing_an_answer(self) -> None:
        unit = self.root / "unit.json"
        unit.write_text(json.dumps(json.loads(self.answer.read_text())["answers"][0]) + "\n")
        receipt = self.outputs / "unit.verified.json"

        result = self.run_cli(
            "verify-unit", "--experiment", self.spec, "--unit", unit,
            "--output", receipt,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        verified = json.loads(receipt.read_text())
        self.assertEqual(verified["status"], "ok")
        self.assertEqual(verified["questionId"], "Q1")
        self.assertEqual(verified["locatorCount"], 1)
        self.assertEqual(verified["unitSha256"], sha256(unit))
        self.assertNotIn("answers", verified)

    def test_verify_unit_rejects_non_string_contract_key_without_traceback(self) -> None:
        harness = importlib.util.module_from_spec(importlib.util.spec_from_file_location("harness", CLI))
        assert harness.__spec__ is not None and harness.__spec__.loader is not None
        harness.__spec__.loader.exec_module(harness)
        unit = json.loads(self.answer.read_text())["answers"][0]
        unit["facts"][0][1] = "unexpected"

        with self.assertRaises(harness.ContractError):
            harness.verify_answer_entry(unit, self.snapshot)

    def test_assemble_answer_rejects_non_finite_metrics_without_output(self) -> None:
        unit = self.root / "unit.json"
        unit.write_text(json.dumps(json.loads(self.answer.read_text())["answers"][0]) + "\n")
        client = self.root / "client.json"
        client.write_text('{"name":"client","version":"1"}\n')
        metrics = self.root / "metrics.json"
        metrics.write_text('{"durationSeconds":NaN}\n')
        output = self.outputs / "must-not-exist-nan.json"

        result = self.run_cli(
            "assemble-answer", "--experiment", self.spec,
            "--unit", unit, "--client", client, "--metrics", metrics,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-finite", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_assemble_answer_refuses_incomplete_unit_set_without_output(self) -> None:
        unit = self.root / "wrong-unit.json"
        value = json.loads(self.answer.read_text())["answers"][0]
        value["questionId"] = "Q2"
        unit.write_text(json.dumps(value) + "\n")
        client = self.root / "client.json"
        client.write_text('{"name":"client","version":"1"}\n')
        metrics = self.root / "metrics.json"
        metrics.write_text("{}\n")
        output = self.outputs / "must-not-exist.json"

        result = self.run_cli(
            "assemble-answer", "--experiment", self.spec,
            "--unit", unit, "--client", client, "--metrics", metrics,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("question set mismatch", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_answer_unit_schema_is_the_same_contract_used_by_full_answers(self) -> None:
        answer_schema = json.loads((ROOT / "contracts" / "answer.schema.json").read_text())
        unit_schema = json.loads((ROOT / "contracts" / "answer-unit.schema.json").read_text())

        self.assertEqual(answer_schema["$defs"]["answerUnit"], unit_schema["allOf"][0])
        self.assertEqual(answer_schema["$defs"]["claim"], unit_schema["$defs"]["claim"])
        self.assertEqual(answer_schema["$defs"]["locator"], unit_schema["$defs"]["locator"])
        self.assertEqual(
            answer_schema["properties"]["answers"]["items"],
            {"$ref": "#/$defs/answerUnit"},
        )

    def test_preflight_rejects_tampered_snapshot(self) -> None:
        (self.snapshot / "Configuration.xml").write_text("tampered\n", encoding="utf-8")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest", result.stderr.lower())

    def test_preflight_requires_full_dump_roots(self) -> None:
        (self.snapshot / "ConfigDumpInfo.xml").unlink()
        lines = [line for line in self.manifest.read_text().splitlines() if not line.endswith("  ConfigDumpInfo.xml")]
        self.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        spec = json.loads(self.spec.read_text())
        spec["snapshot"]["contentId"] = f"sha256:{sha256(self.manifest)}"
        self.spec.write_text(json.dumps(spec) + "\n")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "incomplete.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required root", result.stderr.lower())

    def test_preflight_rejects_output_inside_snapshot(self) -> None:
        spec = json.loads(self.spec.read_text())
        spec["outputRoot"] = str(self.snapshot / "outputs")
        self.spec.write_text(json.dumps(spec) + "\n")
        output = self.snapshot / "outputs" / "out.json"
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertIn("disjoint", result.stderr.lower())

    def test_cli_output_must_be_inside_declared_output_root(self) -> None:
        forbidden = self.snapshot / "HARNESS_MUST_NOT_WRITE.json"
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", forbidden)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(forbidden.exists())
        self.assertIn("outputroot", result.stderr.lower())

    def test_preflight_rejects_output_root_containing_snapshot(self) -> None:
        spec = json.loads(self.spec.read_text())
        spec["outputRoot"] = str(self.root)
        self.spec.write_text(json.dumps(spec) + "\n")
        output = self.root / "outside-snapshot.json"
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertIn("disjoint", result.stderr.lower())

    def test_preflight_rejects_symlink_and_hardlink_snapshot_entries(self) -> None:
        link = self.snapshot / "extra-link"
        link.symlink_to(self.questions)
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())
        link.unlink()
        hardlink = self.snapshot / "hardlink.xml"
        os.link(self.snapshot / "Configuration.xml", hardlink)
        # Add the extra path to the manifest so the rejection tests link safety, not file-set drift.
        with self.manifest.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{sha256(hardlink)}  hardlink.xml\n")
        spec = json.loads(self.spec.read_text())
        spec["snapshot"]["contentId"] = f"sha256:{sha256(self.manifest)}"
        self.spec.write_text(json.dumps(spec) + "\n")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "out2.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hard link", result.stderr.lower())

    def test_preflight_rejects_lossy_question_mark_path(self) -> None:
        lossy = self.snapshot / "Catalogs" / "????.xml"
        lossy.parent.mkdir()
        lossy.write_text("<x/>\n", encoding="utf-8")
        with self.manifest.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{sha256(lossy)}  Catalogs/????.xml\n")
        spec = json.loads(self.spec.read_text())
        spec["snapshot"]["contentId"] = f"sha256:{sha256(self.manifest)}"
        self.spec.write_text(json.dumps(spec) + "\n")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "lossy.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lossy", result.stderr.lower())

    def test_verify_rejects_traversal_and_bad_line(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"][0]["path"] = "../questions.json"
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("locator", result.stderr.lower())
        answer["answers"][0]["locators"][0].update({"path": "CommonModules/Demo/Ext/Module.bsl", "startLine": 99, "endLine": 99})
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", self.outputs / "out2.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("line", result.stderr.lower())

    def test_verify_rejects_nul_locator_without_traceback(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"][0]["path"] = "bad\u0000name"
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", self.outputs / "nul-locator.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[error]", result.stderr.lower())
        self.assertNotIn("traceback", result.stderr.lower())

    def test_experiment_id_must_match_published_schema(self) -> None:
        spec = json.loads(self.spec.read_text())
        spec["id"] = "BAD ID"
        self.spec.write_text(json.dumps(spec) + "\n")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", self.outputs / "bad-id.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("experiment id", result.stderr.lower())

    def test_client_name_and_version_must_be_non_empty(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["client"]["name"] = ""
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", self.outputs / "empty-client.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("client", result.stderr.lower())

    def test_verify_rejects_symlink_locator(self) -> None:
        link = self.snapshot / "linked.bsl"
        link.symlink_to(self.snapshot / "CommonModules" / "Demo" / "Ext" / "Module.bsl")
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"][0]["path"] = "linked.bsl"
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())

    def test_verify_rejects_contract_mismatch(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["snapshotContentId"] = "sha256:" + "0" * 64
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot", result.stderr.lower())

    def test_verify_rejects_schema_extra_property(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["unexpected"] = True
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", self.outputs / "out.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected", result.stderr.lower())

    def test_verify_rejects_duplicate_locator_claim_ids(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"][0]["claimIds"] = ["F1", "F1"]
        self.answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", self.outputs / "duplicate-claims.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unique", result.stderr.lower())

    def test_verified_answer_hash_identifies_validated_bytes(self) -> None:
        module_spec = importlib.util.spec_from_file_location("harness_under_test", CLI)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        spec = module.load_experiment(self.spec)
        expected = sha256(self.answer)
        checked = module.verify_answer_doc(spec, self.answer)
        self.answer.write_text('{"changed":true}\n')
        self.assertEqual(checked["answerSha256"], expected)
        self.assertNotEqual(checked["answerSha256"], sha256(self.answer))

    def test_malformed_nested_contracts_fail_without_traceback(self) -> None:
        spec = json.loads(self.spec.read_text())
        spec["evaluation"] = []
        bad_spec = self.root / "bad-spec.json"
        bad_spec.write_text(json.dumps(spec) + "\n")
        result = self.run_cli("preflight", "--experiment", bad_spec, "--output", self.outputs / "bad-preflight.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[error]", result.stderr.lower())
        self.assertNotIn("traceback", result.stderr.lower())

        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["facts"] = "not-a-list"
        bad_answer = self.root / "bad-answer.json"
        bad_answer.write_text(json.dumps(answer) + "\n")
        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", bad_answer,
            "--output", self.outputs / "bad-verification.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[error]", result.stderr.lower())
        self.assertNotIn("traceback", result.stderr.lower())

    def test_compare_and_seal(self) -> None:
        candidate = self.root / "candidate.json"
        candidate.write_bytes(self.answer.read_bytes())
        adjudication = self.root / "adjudication.json"
        adjudication.write_text(json.dumps({
            "schemaVersion": 1,
            "experimentId": "fixture",
            "arms": {
                "baseline": {"factsCorrect": 1, "factsTotal": 1, "dangerousFalseClaims": 0},
                "candidate": {"factsCorrect": 1, "factsTotal": 1, "dangerousFalseClaims": 0},
            },
            "reviewer": "human-approved-fixture",
        }) + "\n")
        compared = self.outputs / "comparison.json"
        result = self.run_cli("compare", "--experiment", self.spec, "--baseline", self.answer, "--candidate", candidate, "--adjudication", adjudication, "--output", compared)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(compared.read_text())["status"], "ok")
        sealed = self.outputs / "sealed.json"
        result = self.run_cli("seal", "--experiment", self.spec, "--artifact", self.answer, "--artifact", compared, "--output", sealed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(sealed.read_text())["artifacts"]), 2)
        # Source integrity remains unchanged after all operations.
        self.assertEqual(sha256(self.manifest), self.spec_content_id())

    def spec_content_id(self) -> str:
        return json.loads(self.spec.read_text())["snapshot"]["contentId"].split(":", 1)[1]

    def test_refuses_existing_output(self) -> None:
        out = self.outputs / "out.json"
        out.write_text("keep\n")
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", out)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(out.read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
