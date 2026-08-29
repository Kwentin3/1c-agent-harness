from __future__ import annotations

import hashlib
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
FINAL_FRESH = ROOT / "experiments" / "issue31-semantic-preflight" / "final-fresh-attempt-20260829-reservation"


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

    def test_final_fresh_attempt_receipt_is_bound_and_honest_failure(self) -> None:
        manifest = json.loads((FINAL_FRESH / "manifest.json").read_text(encoding="utf-8"))
        expected_files = {
            path.relative_to(FINAL_FRESH).as_posix()
            for path in FINAL_FRESH.rglob("*") if path.is_file()
        } - {"manifest.json"}
        self.assertEqual(set(manifest["artifacts"]), expected_files)
        self.assertEqual(manifest["artifactInventory"], "all package files except this self-describing manifest")
        self.assertEqual(manifest["verdict"], "PREFLIGHT FAIL / FORMAL TOOL ONLY")
        self.assertEqual(manifest["formalVerdict"], "CONTRACT BLOCKED")
        self.assertEqual(manifest["formalExitCode"], 1)
        self.assertEqual(manifest["nativeAttempts"], 0)
        self.assertEqual(manifest["ownerInterventions"], 0)
        for name, digest in manifest["artifacts"].items():
            self.assertEqual(hashlib.sha256((FINAL_FRESH / name).read_bytes()).hexdigest(), digest)
        report = json.loads((FINAL_FRESH / "verbatim-result.json").read_text(encoding="utf-8"))
        retained = run_preflight(FINAL_FRESH / "issue31-reservation-plan.json")
        self.assertEqual(retained.returncode, report["formal_exit_code"])
        self.assertEqual(retained.stdout.rstrip(), report["formal_stdout"])
        self.assertEqual(retained.stderr, report["formal_stderr"])
        self.assertEqual(json.loads(retained.stdout)["verdict"], report["verdict"])
        self.assertEqual(report["task"], manifest["task"])
        self.assertEqual(report["candidate_identity"]["head"], manifest["candidateAtAttemptStart"]["head"])
        self.assertEqual(report["candidate_identity"]["tree"], manifest["candidateAtAttemptStart"]["tree"])
        self.assertEqual(report["candidate_identity"]["skill_name"], manifest["skill"]["name"])
        self.assertEqual(report["candidate_identity"]["skill_version"], manifest["skill"]["version"])
        self.assertEqual(report["candidate_identity"]["skill_manifest_sha256"], manifest["skill"]["resourceManifestSha256"])
        self.assertTrue(report["executor_identity"])
        self.assertTrue(report["allowed_context"])
        self.assertTrue(report["forbidden_context"])
        self.assertTrue(report["semantic_challenge"]["clauses"])
        self.assertTrue(report["semantic_challenge"]["observations"])
        self.assertTrue(report["semantic_challenge"]["cases"])
        self.assertTrue(report["semantic_challenge"]["countermodels"])
        plan = json.loads((FINAL_FRESH / "issue31-reservation-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["task"], report["task"])
        self.assertEqual(
            plan["observations"],
            [{"id": "reservation_status", "clauseIds": ["C1"], "kind": "scalar", "description": "The externally observable scalar reservation status after the request: confirmed or rejected."}],
        )
        self.assertEqual(
            [(case["id"], case["inputs"], case["expected"]["reservation_status"]) for case in plan["cases"]],
            [("below-availability", {"requested_units": 4, "available_units": 5}, "confirmed"),
             ("at-availability", {"requested_units": 5, "available_units": 5}, "confirmed"),
             ("above-availability", {"requested_units": 6, "available_units": 5}, "rejected")],
        )
        models = {model["id"]: model["predictions"] for model in plan["countermodels"]}
        self.assertEqual(set(models), {"strict-less-than", "unconditional-confirm", "equality-only-confirm"})
        self.assertEqual(models["strict-less-than"]["at-availability"], {"reservation_status": "rejected"})
        self.assertEqual(models["unconditional-confirm"]["above-availability"], {"reservation_status": "confirmed"})
        self.assertEqual(models["equality-only-confirm"]["below-availability"], {"reservation_status": "rejected"})
        self.assertEqual(report["end_monotonic_ns"] - report["start_monotonic_ns"], round(report["elapsed_ms"] * 1_000_000))
        self.assertEqual(report["verdict"], "CONTRACT BLOCKED")
        self.assertEqual(report["formal_exit_code"], 1)
        self.assertIn('"verdict": "CONTRACT BLOCKED"', report["formal_stdout"])
        self.assertEqual(report["formal_stderr"], "")
        self.assertEqual(report["native_attempts"], 0)
        self.assertEqual(report["owner_interventions"], 0)
        transcript = (FINAL_FRESH / "executor-transcript.log").read_text(encoding="utf-8")
        self.assertEqual(transcript.count("python3 scripts/semantic_preflight.py"), 2)
        self.assertEqual(transcript.count("-> patch("), 1)
        self.assertIn("renderer-truncated/ellipsized", (FINAL_FRESH / "README.md").read_text(encoding="utf-8"))

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
