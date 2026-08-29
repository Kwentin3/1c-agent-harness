from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "semantic_preflight.py"
ISSUE29 = ROOT / "experiments" / "issue31-semantic-preflight" / "issue29-plan.json"
CONTROL = ROOT / "experiments" / "issue31-semantic-preflight" / "positive-control.json"
FRESH = ROOT / "experiments" / "issue31-semantic-preflight" / "fresh-discount-plan.json"


def run_preflight(plan: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), str(plan)], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )


def temporary_plan(plan: dict, receipt: str | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    local_root = ROOT / ".local"
    local_root.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(dir=local_root)
    root = Path(temporary.name)
    if "receipts" in plan:
        for phase, declared in plan["receipts"]["phases"].items():
            source = CONTROL.parent / declared["path"]
            target = root / f"{phase}.txt"
            target.write_bytes(source.read_bytes())
            declared["path"] = target.name
    if receipt is not None:
        (root / "green.txt").write_text(receipt, encoding="utf-8")
    path = root / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return temporary, path


class SemanticPreflightTests(unittest.TestCase):
    def test_issue29_is_blocked_by_all_required_defect_classes(self) -> None:
        completed = run_preflight(ISSUE29)
        self.assertEqual(completed.returncode, 1, completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["verdict"], "CONTRACT BLOCKED")
        codes = {item["code"] for item in result["findings"]}
        self.assertTrue({
            "SURVIVING_COUNTERMODEL", "RECEIPT_EXTRA_OBSERVATIONS",
            "UNSUPPORTED_ACCEPTANCE_CLAUSE", "NON_SCALAR_OBSERVATION",
        }.issubset(codes), result)
        self.assertIn("last-row-only", result["survivingCountermodels"])

    def test_consistent_synthetic_control_is_ready(self) -> None:
        completed = run_preflight(CONTROL)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["verdict"], "FORMAL COHERENCE READY")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["survivingCountermodels"], [])

    def test_fresh_discount_challenge_has_formal_coherence(self) -> None:
        completed = run_preflight(FRESH)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["verdict"], "FORMAL COHERENCE READY")

    def test_fresh_discount_challenge_kills_retained_threshold_countermodels(self) -> None:
        plan = json.loads(FRESH.read_text(encoding="utf-8"))
        self.assertEqual([case["id"] for case in plan["cases"]], ["amount99", "amount100", "amount101"])
        models = {model["id"]: model["predictions"] for model in plan["countermodels"]}
        self.assertEqual(models["strictly-over-100"]["amount100"], {"discountAccepted": "No"})
        self.assertEqual(models["exactly-100"]["amount101"], {"discountAccepted": "No"})
        self.assertEqual(models["always-discount"]["amount99"], {"discountAccepted": "Yes"})
        self.assertEqual(models["never-discount"]["amount100"], {"discountAccepted": "No"})
        self.assertEqual(models["at-most-100"]["amount101"], {"discountAccepted": "No"})

    def test_blocks_owner_false_positive_task_provenance_and_omission_shapes(self) -> None:
        mutations = {
            "opposite-task": lambda plan: plan.update(task="Reject every quantity, including positive quantities."),
            "unproven-domain": lambda plan: plan["clauses"][0].update(basis="established-domain"),
            "no-countermodels": lambda plan: plan.update(countermodels=[]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8")); mutate(plan)
                temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")

    def test_reports_uncovered_clause_as_structured_finding(self) -> None:
        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        plan["clauses"].append({"id": "uncovered", "statement": "An unmeasured claim.", "basis": "user-task", "taskQuote": "Accept positive quantities"})
        temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
        result = json.loads(run_preflight(path).stdout)
        self.assertEqual(result["verdict"], "CONTRACT BLOCKED")
        self.assertIn("UNCOVERED_CLAUSE", {item["code"] for item in result["findings"]})

    def test_documents_task_quote_negation_limit(self) -> None:
        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        plan["task"] = "Do not follow the instruction ‘Accept positive quantities and reject zero quantities.’ Reject every quantity."
        temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
        self.assertEqual(json.loads(run_preflight(path).stdout)["verdict"], "FORMAL COHERENCE READY")

    def test_validates_established_domain_quote_at_declared_line(self) -> None:
        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        clause = plan["clauses"][0]
        clause.clear(); clause.update({"id": "positive-only", "statement": "A quantity is accepted exactly when it is greater than zero.", "basis": "established-domain", "source": {"path": "README.md", "locator": "line:1", "quote": "1C Agent Harness"}})
        temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
        self.assertEqual(run_preflight(path).returncode, 0)
        clause["source"]["locator"] = "line:999999"
        path.write_text(json.dumps(plan), encoding="utf-8")
        result = json.loads(run_preflight(path).stdout)
        self.assertEqual(result["verdict"], "CONTRACT BLOCKED")
        self.assertIn("UNVERIFIED_DOMAIN_SOURCE", {item["code"] for item in result["findings"]})

        clause["source"].update(locator="line:1", quote="")
        path.write_text(json.dumps(plan), encoding="utf-8")
        result = json.loads(run_preflight(path).stdout)
        self.assertEqual(result["verdict"], "CONTRACT BLOCKED")
        self.assertEqual(result["findings"][0]["code"], "INVALID_PLAN")

    def test_exact_receipt_policy_rejects_mutations(self) -> None:
        mutations = {
            "missing": ("case###synthetic-green\npositiveAccepted###Yes\ncomplete###true\n", "RECEIPT_MISSING_OBSERVATIONS"),
            "extra": ("case###synthetic-green\nzeroAccepted###No\npositiveAccepted###Yes\ncomplete###true\nextra###x\n", "RECEIPT_EXTRA_OBSERVATIONS"),
            "duplicate": ("case###synthetic-green\nzeroAccepted###No\npositiveAccepted###Yes\npositiveAccepted###Yes\ncomplete###true\n", "RECEIPT_DUPLICATE_OBSERVATION"),
            "wrong": ("case###synthetic-green\nzeroAccepted###Yes\npositiveAccepted###Yes\ncomplete###true\n", "RECEIPT_WRONG_VALUE"),
        }
        for name, (receipt, expected_code) in mutations.items():
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8"))
                temporary, path = temporary_plan(plan, receipt)
                self.addCleanup(temporary.cleanup)
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout)
                codes = {item["code"] for item in json.loads(completed.stdout)["findings"]}
                self.assertIn(expected_code, codes)

    def test_incomplete_plan_fails_closed(self) -> None:
        temporary, path = temporary_plan({"schemaVersion": 1})
        self.addCleanup(temporary.cleanup)
        completed = run_preflight(path)
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["findings"][0]["code"], "INVALID_PLAN")

    def test_rejects_incomplete_semantic_vectors(self) -> None:
        mutations = {
            "empty-clause": lambda plan: plan["clauses"][0].update(id=""),
            "partial-case": lambda plan: plan["cases"][0]["expected"].clear(),
            "partial-countermodel": lambda plan: plan["countermodels"][0]["predictions"]["zero"].clear(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8")); mutate(plan)
                temporary, path = temporary_plan(plan)
                self.addCleanup(temporary.cleanup)
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")

    def test_requires_red_green_and_receipt_contract_linkage(self) -> None:
        mutations = {
            "missing-red": lambda plan: plan["receipts"]["phases"].pop("red"),
            "missing-binding": lambda plan: (
                plan["receipts"]["phases"]["green"]["bindings"].pop(),
                plan["receipts"]["phases"]["green"]["controls"].append("positiveAccepted"),
            ),
            "unclassified-key": lambda plan: plan["receipts"]["phases"]["green"]["expected"].append(["mystery", "x"]),
            "non-string-path": lambda plan: plan["receipts"]["phases"]["green"].update(path=7),
            "duplicate-cell": lambda plan: plan["receipts"]["phases"]["green"]["bindings"].append(["zero", "accepted", "positiveAccepted"]),
            "green-semantic-lie": lambda plan: plan["receipts"]["phases"]["green"]["expected"][1].__setitem__(1, "Yes"),
            "red-equals-green": lambda plan: plan["receipts"]["phases"]["red"]["expected"].__setitem__(1, "No"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8"))
                temporary, path = temporary_plan(plan)
                self.addCleanup(temporary.cleanup)
                copied = json.loads(path.read_text(encoding="utf-8")); mutate(copied)
                path.write_text(json.dumps(copied), encoding="utf-8")
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")

    def test_confines_receipts_to_repo_owned_evidence_root(self) -> None:
        paths = [
            ("absolute", "/etc/passwd", "must be relative"),
            ("traversal", "../../../../etc/passwd", "escapes its approved root"),
        ]
        for name, receipt_path, message in paths:
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8"))
                temporary, path = temporary_plan(plan)
                self.addCleanup(temporary.cleanup)
                copied = json.loads(path.read_text(encoding="utf-8"))
                copied["receipts"]["phases"]["green"]["path"] = receipt_path
                path.write_text(json.dumps(copied), encoding="utf-8")
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["verdict"], "CONTRACT BLOCKED")
                self.assertIn(message, result["findings"][0]["message"])

        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        temporary, path = temporary_plan(plan)
        self.addCleanup(temporary.cleanup)
        green = path.parent / "green.txt"
        green.unlink()
        green.symlink_to("/etc/passwd")
        completed = run_preflight(path)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")

    def test_rejects_empty_values_and_symlink_loop_plan(self) -> None:
        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        plan["cases"][0]["expected"]["accepted"] = ""
        temporary, path = temporary_plan(plan)
        self.addCleanup(temporary.cleanup)
        completed = run_preflight(path)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)

        loop = Path(temporary.name) / "loop.json"
        loop.symlink_to("loop.json")
        completed = run_preflight(loop)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")

    def test_issue29_receipt_copies_preserve_frozen_bytes(self) -> None:
        frozen = ROOT / "experiments" / "issue29-inventory-increase-price-core-loop"
        for phase in ("red", "green"):
            self.assertEqual(
                (ISSUE29.parent / f"issue29-{phase}-receipt.txt").read_bytes(),
                (frozen / f"{phase}-receipt.txt").read_bytes(),
            )

    def test_rejects_fifo_plan_symlink_boolean_schema_and_duplicate_model(self) -> None:
        mutations = {
            "boolean-schema": lambda plan: plan.update(schemaVersion=True),
            "duplicate-model": lambda plan: plan["countermodels"].append(plan["countermodels"][0]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                plan = json.loads(CONTROL.read_text(encoding="utf-8")); mutate(plan)
                temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
                completed = run_preflight(path)
                self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)

        plan = json.loads(CONTROL.read_text(encoding="utf-8"))
        temporary, path = temporary_plan(plan); self.addCleanup(temporary.cleanup)
        alias = path.parent / "alias.json"; alias.symlink_to(path.name)
        completed = run_preflight(alias)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)

        outside_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temporary.cleanup)
        outside = Path(outside_temporary.name)
        nested = outside / "nested"; nested.mkdir()
        external_plan = nested / "plan.json"; external_plan.write_bytes(path.read_bytes())
        (nested / "red.txt").write_bytes((path.parent / "red.txt").read_bytes())
        (nested / "green.txt").write_bytes((path.parent / "green.txt").read_bytes())
        alias_root = path.parent / "alias-root"; alias_root.symlink_to(outside, target_is_directory=True)
        completed = run_preflight(alias_root / "nested" / "plan.json")
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)

        fifo = path.parent / "green.txt"; fifo.unlink(); os.mkfifo(fifo)
        completed = subprocess.run(
            [sys.executable, str(CLI), str(path)], cwd=ROOT, text=True,
            capture_output=True, check=False, timeout=2,
        )
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["verdict"], "CONTRACT BLOCKED")


if __name__ == "__main__":
    unittest.main()
