from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue12-narrow-context-20260826"
MANIFEST = "package-manifest.json"

JET_CONTENT_ID = "sha256:70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
SDMS_CONTENT_ID = "sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((PACKAGE / relative).read_text(encoding="utf-8"))


def validate_manifest(root: Path = PACKAGE) -> None:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    } - {MANIFEST}
    expected = set(manifest["artifacts"])
    if actual != expected:
        raise AssertionError(
            f"package closure mismatch: extra={sorted(actual - expected)} "
            f"missing={sorted(expected - actual)}"
        )
    for relative, digest in manifest["artifacts"].items():
        path = root / relative
        if not path.is_file() or sha256(path) != digest:
            raise AssertionError(f"artifact mismatch: {relative}")


def fragment_paths(context: dict) -> set[str]:
    fragments = context.get("fragments", context.get("used_fragments", []))
    return {str(fragment["path"]).replace("\\", "/") for fragment in fragments}


def validate_context_boundary(kind: str, context: dict, content_id: str) -> None:
    bound = context.get("snapshotContentId") or context.get("binding", {}).get("content_id")
    if bound != content_id:
        raise AssertionError(f"stale or foreign content identity: {bound}")
    paths = fragment_paths(context)
    if kind == "sdms":
        required_suffixes = {
            "HTTPServices/API.xml",
            "HTTPServices/API/Ext/Module.bsl",
            "CommonModules/API/Ext/Module.bsl",
            "Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl",
        }
        forbidden_suffixes = {"Reports/ЗадачиПоЗаявкам.xml"}
    elif kind == "jet":
        required_suffixes = {"Catalogs/Warehouses.xml"}
        forbidden_suffixes = {
            "Configuration.xml",
            "ConfigDumpInfo.xml",
        }
        if any("/Forms/" in path or path.endswith(".bsl") for path in paths):
            raise AssertionError("Jet context crossed the frozen metadata-only boundary")
    else:
        raise AssertionError(f"unknown context kind: {kind}")
    for suffix in required_suffixes:
        if not any(path.endswith(suffix) for path in paths):
            raise AssertionError(f"insufficient context: missing {suffix}")
    for suffix in forbidden_suffixes:
        if any(path.endswith(suffix) for path in paths):
            raise AssertionError(f"distractor or forbidden source selected: {suffix}")


class Issue12EvidenceTests(unittest.TestCase):
    def test_package_manifest_is_exactly_closed(self) -> None:
        validate_manifest()

    def test_no_host_absolute_paths(self) -> None:
        for path in PACKAGE.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertIsNone(re.search(r"/workspace/[^\s\"']+", text), path)

    def test_all_frozen_contexts_bind_to_expected_sources(self) -> None:
        validate_context_boundary("sdms", load_json("contexts/sdms-baseline.json"), SDMS_CONTENT_ID)
        validate_context_boundary("sdms", load_json("contexts/sdms-candidate.json"), SDMS_CONTENT_ID)
        validate_context_boundary("jet", load_json("contexts/jet-baseline.json"), JET_CONTENT_ID)
        candidate = load_json("contexts/jet-candidate.json")
        # Candidate uses the more explicit sha256-manifest spelling.
        validate_context_boundary("jet", candidate, JET_CONTENT_ID.replace("sha256:", "sha256-manifest:"))

    def test_jet_diffs_are_single_owner_metadata_changes(self) -> None:
        for name in ("jet-baseline.diff", "jet-candidate.diff"):
            text = (PACKAGE / "diffs" / name).read_text(encoding="utf-8")
            headers = [line for line in text.splitlines() if line.startswith("diff --git ")]
            self.assertEqual(len(headers), 1, name)
            self.assertIn("Catalogs/Warehouses.xml", headers[0])
            self.assertNotIn("/Forms/", text)
            self.assertNotIn(".bsl", text.lower())
            self.assertIn("AllowNegativeInventoryBalance", text)
            self.assertIn("Allow negative inventory balance", text)
            self.assertIn("xs:boolean", text)
            self.assertIn("<FillValue xsi:type=\"xs:boolean\">false</FillValue>", text)
            self.assertIn("<Use>ForItem</Use>", text)

    def test_sdms_task_identity_chain_is_closed(self) -> None:
        task = load_json("tasks/sdms.json")
        questions = load_json("tasks/sdms-questions.json")
        binding = load_json("tasks/sdms-binding.json")
        question_bytes = (PACKAGE / "tasks/sdms-questions.json").read_bytes()
        task_bytes = (PACKAGE / "tasks/sdms.json").read_bytes()
        encoded_original = (PACKAGE / binding["frozenSelection"]["encodedOriginalArtifact"]).read_bytes()
        original_bytes = base64.b64decode(encoded_original, validate=False)
        original = json.loads(original_bytes)
        self.assertEqual(binding["frozenSelection"]["publicTaskSha256"], hashlib.sha256(original_bytes).hexdigest())
        normalized_original = copy.deepcopy(original)
        normalized_original["snapshot"]["root"] = task["snapshot"]["root"]
        normalized_original["snapshot"]["manifest"] = task["snapshot"]["manifest"]
        self.assertEqual(normalized_original, task)
        self.assertEqual(task["taskText"], questions["questions"][0]["text"])
        self.assertEqual(binding["frozenSelection"]["publishedSanitizedTaskSha256"], hashlib.sha256(task_bytes).hexdigest())
        self.assertEqual(binding["canonicalQuestionSet"]["sha256"], hashlib.sha256(question_bytes).hexdigest())
        self.assertEqual(binding["canonicalQuestionSet"]["taskTextUtf8Sha256"], hashlib.sha256(task["taskText"].encode()).hexdigest())
        for arm in ("baseline", "candidate"):
            answer = load_json(f"answers/sdms-{arm}.json")
            self.assertEqual(answer["questionSetSha256"], hashlib.sha256(question_bytes).hexdigest())
            self.assertEqual(answer["experimentId"], binding["armBinding"]["bothExperimentIds"])
            self.assertEqual(answer["snapshotContentId"], binding["armBinding"]["bothSnapshotContentIds"])

    def test_jet_candidate_semantic_regression_is_detected(self) -> None:
        baseline = (PACKAGE / "diffs/jet-baseline.diff").read_text(encoding="utf-8")
        candidate = (PACKAGE / "diffs/jet-candidate.diff").read_text(encoding="utf-8")
        self.assertIn("<FullTextSearch>DontUse</FullTextSearch>", baseline)
        self.assertIn("<FullTextSearch>Use</FullTextSearch>", candidate)
        adjudication = load_json("adjudication/jet.json")
        self.assertEqual(adjudication["armResults"]["baseline"]["fairnessAdjustedFieldsCorrect"], 11)
        self.assertEqual(adjudication["armResults"]["candidate"]["fairnessAdjustedFieldsCorrect"], 10)
        self.assertIn("FullTextSearch", adjudication["armResults"]["candidate"]["semanticFailure"])
        self.assertIn("DontUse", adjudication["armResults"]["candidate"]["semanticFailure"])

    def test_native_receipts_are_exact_successes(self) -> None:
        for arm in ("baseline", "candidate"):
            receipt = load_json(f"evidence/native-jet-{arm}.json")
            self.assertEqual(receipt["status"], "ok")
            self.assertEqual(receipt["preSnapshot"], receipt["postSnapshot"])
            self.assertEqual(receipt["preSnapshot"], {
                "listed": 5099, "actual": 5099, "missing": 0,
                "extra": 0, "mismatch": 0, "symlinks": 0,
            })
            self.assertEqual([step["step"] for step in receipt["steps"]], ["create", "load"])
            for step in receipt["steps"]:
                self.assertEqual(step["processExit"], 0)
                self.assertIs(step["dumpResultZero"], True)
                self.assertRegex(step["logSha256"], r"^[0-9a-f]{64}$")

    def test_decision_is_fail_closed_and_scoped(self) -> None:
        decision = load_json("decision.json")
        self.assertEqual(decision["selectedApproach"], "direct-source-baseline")
        self.assertEqual(decision["candidateDecision"], "rejected")
        self.assertEqual(decision["newRuntimeComponents"], [])
        self.assertIn("one SDMS task", decision["scope"])
        self.assertIn("one Jet metadata task", decision["scope"])

    def test_negative_stale_context_is_rejected(self) -> None:
        context = load_json("contexts/sdms-baseline.json")
        context["snapshotContentId"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(AssertionError, "stale or foreign"):
            validate_context_boundary("sdms", context, SDMS_CONTENT_ID)

    def test_negative_insufficient_context_is_rejected(self) -> None:
        context = copy.deepcopy(load_json("contexts/sdms-baseline.json"))
        context["fragments"] = [
            fragment for fragment in context["fragments"]
            if not fragment["path"].endswith("Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl")
        ]
        with self.assertRaisesRegex(AssertionError, "insufficient context"):
            validate_context_boundary("sdms", context, SDMS_CONTENT_ID)

    def test_negative_same_term_distractor_is_rejected(self) -> None:
        context = copy.deepcopy(load_json("contexts/sdms-baseline.json"))
        context["fragments"].append({
            "path": "Reports/ЗадачиПоЗаявкам.xml", "startLine": 3,
            "endLine": 26, "fileSha256": "0" * 64,
            "byteCount": 1, "reason": "same-term distractor", "supports": ["X"],
        })
        with self.assertRaisesRegex(AssertionError, "distractor"):
            validate_context_boundary("sdms", context, SDMS_CONTENT_ID)

    def test_negative_jet_scope_expansion_is_rejected(self) -> None:
        context = copy.deepcopy(load_json("contexts/jet-baseline.json"))
        context["fragments"].append({
            "path": "Catalogs/Warehouses/Forms/ItemForm/Ext/Form/Module.bsl",
            "startLine": 1, "endLine": 1, "fileSha256": "0" * 64,
            "byteCount": 1, "reason": "unnecessary form code", "supports": ["X"],
        })
        with self.assertRaisesRegex(AssertionError, "metadata-only boundary"):
            validate_context_boundary("jet", context, JET_CONTENT_ID)


if __name__ == "__main__":
    unittest.main()
