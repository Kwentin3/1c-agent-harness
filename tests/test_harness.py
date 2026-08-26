from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "harness.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_harness(name: str = "harness_under_test") -> object:
    module_spec = importlib.util.spec_from_file_location(name, CLI)
    if module_spec is None or module_spec.loader is None:
        raise AssertionError("cannot load harness module")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


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
        self.candidate = self.root / "candidate.json"
        self.candidate.write_bytes(self.answer.read_bytes())
        self.oracle = self.root / "oracle.json"
        self.oracle.write_text(json.dumps({
            "schemaVersion": 1,
            "experimentId": "fixture",
            "preparedBeforeRuns": True,
            "independentSources": [],
            "answers": {
                "Q1": {
                    "expected": ["Demo is exported."],
                    "locators": ["CommonModules/Demo/Ext/Module.bsl:1-1"],
                },
            },
        }) + "\n", encoding="utf-8")
        self.ledger = self.root / "adjudication-ledger.json"
        self.ledger.write_text(json.dumps({
            "schemaVersion": 1,
            "experimentId": "fixture",
            "reviewer": "human-approved-fixture",
            "questions": [{
                "questionId": "Q1",
                "items": [{
                    "index": 1,
                    "expected": "Demo is exported.",
                    "arms": {
                        "baseline": {"correct": True, "rationale": "Matches source.", "citedLocators": ["CommonModules/Demo/Ext/Module.bsl:1-1"]},
                        "candidate": {"correct": True, "rationale": "Matches source.", "citedLocators": ["CommonModules/Demo/Ext/Module.bsl:1-1"]},
                    },
                }],
            }],
            "dangerousClaims": {
                "baseline": {"count": 0, "claims": [], "rationale": "None."},
                "candidate": {"count": 0, "claims": [], "rationale": "None."},
            },
        }) + "\n", encoding="utf-8")
        self.adjudication = self.root / "adjudication.json"
        self.write_adjudication()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CLI), *(str(x) for x in args)], text=True, capture_output=True, check=False)

    def run_compare(self, output: Path) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "compare", "--experiment", self.spec,
            "--baseline", self.answer, "--candidate", self.candidate,
            "--oracle", self.oracle, "--ledger", self.ledger,
            "--adjudication", self.adjudication, "--output", output,
        )

    def write_adjudication(self, **identity_overrides: str) -> None:
        identity = {
            "snapshotContentId": f"sha256:{sha256(self.manifest)}",
            "questionSetSha256": sha256(self.questions),
            "oracleSha256": sha256(self.oracle),
            "ledgerSha256": sha256(self.ledger),
            "baselineAnswerSha256": sha256(self.answer),
            "candidateAnswerSha256": sha256(self.candidate),
        }
        identity.update(identity_overrides)
        self.adjudication.write_text(json.dumps({
            "schemaVersion": 2,
            "experimentId": "fixture",
            "identity": identity,
            "arms": {
                "baseline": {"factsCorrect": 1, "factsTotal": 1, "dangerousFalseClaims": 0},
                "candidate": {"factsCorrect": 1, "factsTotal": 1, "dangerousFalseClaims": 0},
            },
            "reviewer": "human-approved-fixture",
        }) + "\n", encoding="utf-8")

    def test_preflight_and_verify_answer(self) -> None:
        preflight = self.outputs / "preflight.json"
        result = self.run_cli("preflight", "--experiment", self.spec, "--output", preflight)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(preflight.read_text())["status"], "ok")
        verified = self.outputs / "verified.json"
        result = self.run_cli("verify-answer", "--experiment", self.spec, "--answer", self.answer, "--output", verified)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(verified.read_text())["locatorCount"], 1)

    def test_verify_rejects_fact_without_locator(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"] = []
        self.answer.write_text(json.dumps(answer) + "\n")
        output = self.outputs / "fact-without-locator.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fact", result.stderr.lower())
        self.assertIn("locator", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_verify_rejects_inference_without_locator(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["inferences"] = [{"id": "I1", "text": "Demo is available to callers."}]
        self.answer.write_text(json.dumps(answer) + "\n")
        output = self.outputs / "inference-without-locator.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inference", result.stderr.lower())
        self.assertIn("locator", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_verify_allows_assumptions_and_unknowns_without_locators(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["assumptions"] = [{"id": "A1", "text": "The module may be used."}]
        answer["answers"][0]["unknowns"] = [{"id": "U1", "text": "Runtime use is unknown."}]
        self.answer.write_text(json.dumps(answer) + "\n")
        output = self.outputs / "uncertainty-without-locators.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.exists())

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

    def test_verify_rejects_duplicate_json_keys_without_output(self) -> None:
        raw = self.answer.read_text()
        self.answer.write_text(raw.replace('"schemaVersion": 1,', '"schemaVersion": 1, "schemaVersion": 1,', 1))
        output = self.outputs / "duplicate-json-key.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_verify_rejects_non_finite_json_without_output(self) -> None:
        raw = self.answer.read_text()
        self.answer.write_text(raw.replace('"durationSeconds": 1.0', '"durationSeconds": NaN', 1))
        output = self.outputs / "non-finite-json.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-finite", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_contract_keys_reject_non_string_keys(self) -> None:
        module_spec = importlib.util.spec_from_file_location("harness_contract_keys", CLI)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        with self.assertRaises(module.ContractError):
            module.require_contract_keys({"name": "ok", 1: "bad"}, ("name",), ("name",), "fixture")

    def test_output_below_symlinked_ancestor_is_rejected(self) -> None:
        real = self.root / "real-output"
        (real / "nested").mkdir(parents=True)
        alias = self.root / "alias-output"
        alias.symlink_to(real, target_is_directory=True)
        spec = json.loads(self.spec.read_text())
        spec["outputRoot"] = str(alias)
        self.spec.write_text(json.dumps(spec) + "\n")
        output = alias / "nested" / "receipt.json"

        result = self.run_cli("preflight", "--experiment", self.spec, "--output", output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_snapshot_race_after_manifest_read_is_rejected(self) -> None:
        module = load_harness("harness_snapshot_race")
        spec = module.load_experiment(self.spec)
        original = module.read_file_stable
        changed = False

        def raced_read(path: Path, label: str) -> bytes:
            nonlocal changed
            data = original(path, label)
            if label == "snapshot manifest" and not changed:
                changed = True
                target = self.snapshot / "Configuration.xml"
                old_hash = sha256(target)
                target.write_text("<Configuration>\n<Name>Evil</Name>\n</Configuration>\n", encoding="utf-8")
                self.manifest.write_text(self.manifest.read_text().replace(old_hash, sha256(target)))
            return data

        with mock.patch.object(module, "read_file_stable", side_effect=raced_read):
            with self.assertRaises(module.ContractError):
                module.verify_snapshot(spec)

    def test_output_directory_replacement_cannot_escape_descriptor_root(self) -> None:
        module = load_harness("harness_output_race")
        outside = self.root / "outside"
        outside.mkdir()
        parked = self.root / "parked-output"
        original = module._open_path_fd
        replaced = False

        def raced_open(path: Path, *, directory: bool, label: str) -> int:
            nonlocal replaced
            fd = original(path, directory=directory, label=label)
            if label == "outputRoot" and not replaced:
                replaced = True
                self.outputs.rename(parked)
                self.outputs.symlink_to(outside, target_is_directory=True)
            return fd

        with mock.patch.object(module, "_open_path_fd", side_effect=raced_open):
            module.write_new_json(self.outputs / "receipt.json", {"status": "ok"}, self.outputs)

        self.assertFalse((outside / "receipt.json").exists())
        self.assertTrue((parked / "receipt.json").exists())

    def test_keyboard_interrupt_during_write_leaves_no_final_or_temporary_output(self) -> None:
        module = load_harness("harness_interrupted_output")
        output = self.outputs / "partial.json"
        original = module.os.write

        def interrupted_write(fd: int, data: bytes) -> int:
            original(fd, data[:1])
            raise KeyboardInterrupt()

        with mock.patch.object(module.os, "write", side_effect=interrupted_write):
            with self.assertRaises(KeyboardInterrupt):
                module.write_new_json(output, {"status": "must-not-publish"}, self.outputs)

        self.assertFalse(output.exists())
        self.assertEqual(list(self.outputs.glob(".partial.json.tmp-*")), [])

    def test_temporary_name_collision_does_not_unlink_existing_file(self) -> None:
        module = load_harness("harness_temporary_collision")
        output = self.outputs / "collision.json"
        existing = self.outputs / f".collision.json.tmp-{os.getpid()}-fixed"
        existing.write_text("keep", encoding="utf-8")

        with mock.patch.object(module.secrets, "token_hex", return_value="fixed"):
            with self.assertRaises(module.ContractError):
                module.write_new_json(output, {"status": "must-not-publish"}, self.outputs)

        self.assertFalse(output.exists())
        self.assertEqual(existing.read_text(), "keep")

    def test_seal_rejects_artifact_path_replaced_after_stable_read(self) -> None:
        module = load_harness("harness_seal_race")
        artifact = self.outputs / "artifact.json"
        artifact.write_text("old", encoding="utf-8")
        original = module.read_file_stable_identity

        def raced_read(path: Path, label: str) -> tuple[bytes, tuple[int, int, int, int, int, int]]:
            data, identity = original(path, label)
            if label == "artifact":
                replacement = path.with_suffix(".replacement")
                replacement.write_text("new", encoding="utf-8")
                replacement.replace(path)
            return data, identity

        with mock.patch.object(module, "read_file_stable_identity", side_effect=raced_read):
            with self.assertRaises(module.ContractError):
                module.seal(SimpleNamespace(experiment=self.spec, artifact=[artifact]))

    def test_verify_rejects_non_string_locator_claim_id_without_traceback(self) -> None:
        answer = json.loads(self.answer.read_text())
        answer["answers"][0]["locators"][0]["claimIds"] = [{"bad": "id"}]
        self.answer.write_text(json.dumps(answer) + "\n")
        output = self.outputs / "non-string-claim-id.json"

        result = self.run_cli(
            "verify-answer", "--experiment", self.spec, "--answer", self.answer,
            "--output", output,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[error]", result.stderr.lower())
        self.assertIn("claimids", result.stderr.lower())
        self.assertNotIn("traceback", result.stderr.lower())
        self.assertFalse(output.exists())

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

    def test_published_schemas_require_bound_adjudication_and_review_ledger(self) -> None:
        adjudication_schema = json.loads((ROOT / "contracts" / "adjudication.schema.json").read_text())
        ledger_schema = json.loads((ROOT / "contracts" / "adjudication-ledger.schema.json").read_text())
        oracle_schema = json.loads((ROOT / "contracts" / "oracle.schema.json").read_text())

        self.assertEqual(adjudication_schema["properties"]["schemaVersion"], {"const": 2})
        self.assertIn("identity", adjudication_schema["required"])
        self.assertEqual(
            set(adjudication_schema["properties"]["identity"]["required"]),
            {
                "snapshotContentId", "questionSetSha256", "oracleSha256", "ledgerSha256",
                "baselineAnswerSha256", "candidateAnswerSha256",
            },
        )
        self.assertEqual(ledger_schema["properties"]["schemaVersion"], {"const": 1})
        self.assertIn("questions", ledger_schema["required"])
        self.assertEqual(ledger_schema["$defs"]["verdict"]["properties"]["citedLocators"]["minItems"], 1)
        self.assertEqual(oracle_schema["properties"]["preparedBeforeRuns"], {"const": True})
        self.assertEqual(oracle_schema["$defs"]["oracleAnswer"]["properties"]["locators"]["minItems"], 1)

    def test_compare_and_seal(self) -> None:
        compared = self.outputs / "comparison.json"
        result = self.run_compare(compared)
        self.assertEqual(result.returncode, 0, result.stderr)
        comparison = json.loads(compared.read_text())
        self.assertEqual(comparison["status"], "ok")
        self.assertIn("exactOracleCoverage", comparison["scores"]["baseline"])
        self.assertNotIn("factAccuracy", comparison["scores"]["baseline"])
        sealed = self.outputs / "sealed.json"
        result = self.run_cli("seal", "--experiment", self.spec, "--artifact", self.answer, "--artifact", compared, "--output", sealed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(sealed.read_text())["artifacts"]), 2)
        # Source integrity remains unchanged after all operations.
        self.assertEqual(sha256(self.manifest), self.spec_content_id())

    def test_compare_rejects_different_answer_bytes_without_output(self) -> None:
        candidate = json.loads(self.candidate.read_text())
        candidate["metrics"]["mutationProbe"] = "not reviewed"
        self.candidate.write_text(json.dumps(candidate) + "\n")
        output = self.outputs / "stale-answer-adjudication.json"

        result = self.run_compare(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate answer", result.stderr.lower())
        self.assertIn("sha-256", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_compare_rejects_every_wrong_identity_field(self) -> None:
        fields = (
            "snapshotContentId",
            "questionSetSha256",
            "oracleSha256",
            "ledgerSha256",
            "baselineAnswerSha256",
            "candidateAnswerSha256",
        )
        for index, field in enumerate(fields):
            with self.subTest(field=field):
                wrong = "sha256:" + "0" * 64 if field == "snapshotContentId" else "0" * 64
                self.write_adjudication(**{field: wrong})
                output = self.outputs / f"wrong-identity-{index}.json"

                result = self.run_compare(output)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("identity", result.stderr.lower())
                self.assertFalse(output.exists())
        self.write_adjudication()

    def test_oracle_locator_requires_manifest_path_range_and_hash(self) -> None:
        module = load_harness("harness_oracle_locator")
        spec = module.load_experiment(self.spec)
        state = module.verify_snapshot(spec)
        root = spec["_snapshotRoot"]
        locator = "CommonModules/Demo/Ext/Module.bsl:1-1"

        with self.assertRaises(module.ContractError):
            module.validate_oracle_locator(root, state, "CommonModules/Missing/Ext/Module.bsl:1-1")
        with self.assertRaises(module.ContractError):
            module.validate_oracle_locator(root, state, "CommonModules/Demo/Ext/Module.bsl:1-999")

        source = self.snapshot / "CommonModules" / "Demo" / "Ext" / "Module.bsl"
        source.write_text("Function Changed() Export\nEndFunction\n", encoding="utf-8")
        with self.assertRaises(module.ContractError):
            module.validate_oracle_locator(root, state, locator)

    def test_compare_rejects_oracle_ledger_item_mismatch(self) -> None:
        ledger = json.loads(self.ledger.read_text())
        ledger["questions"][0]["items"] = []
        self.ledger.write_text(json.dumps(ledger) + "\n")
        self.write_adjudication()
        output = self.outputs / "oracle-ledger-mismatch.json"

        result = self.run_compare(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("oracle", result.stderr.lower())
        self.assertIn("ledger", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_compare_rejects_schema_invalid_oracle_source_and_boolean_index(self) -> None:
        oracle = json.loads(self.oracle.read_text())
        oracle["independentSources"] = ["schema-invalid"]
        self.oracle.write_text(json.dumps(oracle) + "\n")
        self.write_adjudication()
        output = self.outputs / "invalid-oracle-source.json"
        result = self.run_compare(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

        oracle["independentSources"] = []
        self.oracle.write_text(json.dumps(oracle) + "\n")
        ledger = json.loads(self.ledger.read_text())
        ledger["questions"][0]["items"][0]["index"] = True
        self.ledger.write_text(json.dumps(ledger) + "\n")
        self.write_adjudication()
        output = self.outputs / "boolean-ledger-index.json"
        result = self.run_compare(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_compare_rejects_arbitrary_adjudication_denominator(self) -> None:
        adjudication = json.loads(self.adjudication.read_text())
        adjudication["arms"]["candidate"]["factsTotal"] = 2
        self.adjudication.write_text(json.dumps(adjudication) + "\n")
        output = self.outputs / "arbitrary-denominator.json"

        result = self.run_compare(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ledger", result.stderr.lower())
        self.assertIn("totals", result.stderr.lower())
        self.assertFalse(output.exists())

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
