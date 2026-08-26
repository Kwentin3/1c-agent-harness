from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "sdms-product-eval-20260825-review"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrozenReviewPackageTests(unittest.TestCase):
    def test_manifest_closes_over_review_artifacts(self) -> None:
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text())
        expected_paths = {
            "questions.json",
            "oracle.json",
            "answers/baseline.json",
            "answers/candidate.json",
            "adjudication-ledger.json",
            "adjudication.json",
            "comparison.json",
        }
        self.assertEqual(set(manifest["artifacts"]), expected_paths)
        for relative, expected_hash in manifest["artifacts"].items():
            self.assertEqual(sha256(PACKAGE / relative), expected_hash, relative)

    def test_adjudication_is_bound_to_exact_package_bytes(self) -> None:
        adjudication = json.loads((PACKAGE / "adjudication.json").read_text())
        identity = adjudication["identity"]
        self.assertEqual(identity["questionSetSha256"], sha256(PACKAGE / "questions.json"))
        self.assertEqual(identity["oracleSha256"], sha256(PACKAGE / "oracle.json"))
        self.assertEqual(identity["ledgerSha256"], sha256(PACKAGE / "adjudication-ledger.json"))
        self.assertEqual(identity["baselineAnswerSha256"], sha256(PACKAGE / "answers" / "baseline.json"))
        self.assertEqual(identity["candidateAnswerSha256"], sha256(PACKAGE / "answers" / "candidate.json"))

    def test_frozen_denominator_and_totals_recompute(self) -> None:
        oracle = json.loads((PACKAGE / "oracle.json").read_text())
        ledger = json.loads((PACKAGE / "adjudication-ledger.json").read_text())
        adjudication = json.loads((PACKAGE / "adjudication.json").read_text())
        question_ids = list(oracle["answers"])
        self.assertEqual([item["questionId"] for item in ledger["questions"]], question_ids)
        counts = {"baseline": 0, "candidate": 0}
        total = 0
        for question in ledger["questions"]:
            expected = oracle["answers"][question["questionId"]]["expected"]
            self.assertEqual([item["expected"] for item in question["items"]], expected)
            total += len(expected)
            for item in question["items"]:
                for arm in counts:
                    counts[arm] += int(item["arms"][arm]["correct"])
        self.assertEqual(total, 47)
        self.assertEqual(counts, {"baseline": 45, "candidate": 44})
        for arm in counts:
            self.assertEqual(adjudication["arms"][arm]["factsTotal"], total)
            self.assertEqual(adjudication["arms"][arm]["factsCorrect"], counts[arm])
            self.assertEqual(
                adjudication["arms"][arm]["dangerousFalseClaims"],
                ledger["dangerousClaims"][arm]["count"],
            )

    def test_answer_claims_and_ledger_locators_are_traceable(self) -> None:
        ledger = json.loads((PACKAGE / "adjudication-ledger.json").read_text())
        answers = {
            arm: json.loads((PACKAGE / "answers" / f"{arm}.json").read_text())
            for arm in ("baseline", "candidate")
        }
        locator_sets: dict[str, dict[str, set[str]]] = {}
        for arm, answer in answers.items():
            locator_sets[arm] = {}
            for entry in answer["answers"]:
                located = {claim_id for locator in entry["locators"] for claim_id in locator["claimIds"]}
                required = {claim["id"] for key in ("facts", "inferences") for claim in entry[key]}
                self.assertLessEqual(required, located, f"{arm} {entry['questionId']}")
                locator_sets[arm][entry["questionId"]] = {
                    f"{locator['path']}:{locator['startLine']}-{locator['endLine']}"
                    for locator in entry["locators"]
                }
        for question in ledger["questions"]:
            for item in question["items"]:
                for arm in answers:
                    self.assertLessEqual(
                        set(item["arms"][arm]["citedLocators"]),
                        locator_sets[arm][question["questionId"]],
                    )


if __name__ == "__main__":
    unittest.main()
