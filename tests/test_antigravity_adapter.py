from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "antigravity_adapter.py"


class AntigravityAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.output = self.root / "unit.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, task: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), "extract-unit", "--task-record", str(task), "--output", str(self.output)],
            text=True,
            capture_output=True,
            check=False,
        )

    def task_record(self, summary: str, **overrides: object) -> dict[str, object]:
        result: dict[str, object] = {
            "summary": summary,
            "findings": [],
            "risks": [],
            "recommendations": [],
            "sources": [],
        }
        result.update(overrides)
        return {"task_id": "task-1", "status": "completed", "result": result}

    def test_extracts_exact_small_unit_from_summary(self) -> None:
        unit = {
            "questionId": "Q1",
            "answer": "Confirmed.",
            "facts": [{"id": "F1", "text": "A fact."}],
            "inferences": [],
            "assumptions": [],
            "unknowns": [],
            "locators": [],
        }
        task = self.root / "task.json"
        task.write_text(json.dumps(self.task_record(json.dumps(unit, ensure_ascii=False))) + "\n")

        result = self.run_cli(task)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text()), unit)

    def test_refuses_competing_native_fields_without_output(self) -> None:
        task = self.root / "task.json"
        task.write_text(json.dumps(self.task_record("{}", findings=["extra"])) + "\n")

        result = self.run_cli(task)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be empty", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_refuses_malformed_summary_without_repair(self) -> None:
        task = self.root / "task.json"
        task.write_text(json.dumps(self.task_record('{"questionId":"Q1",}')) + "\n")

        result = self.run_cli(task)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid summary json", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_refuses_duplicate_summary_keys_without_output(self) -> None:
        task = self.root / "task.json"
        duplicate = '{"questionId":"Q1","questionId":"Q2"}'
        task.write_text(json.dumps(self.task_record(duplicate)) + "\n")

        result = self.run_cli(task)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate json key", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_refuses_output_below_symlinked_ancestor(self) -> None:
        task = self.root / "task.json"
        task.write_text(json.dumps(self.task_record("{}")) + "\n")
        real = self.root / "real"
        (real / "nested").mkdir(parents=True)
        alias = self.root / "alias"
        alias.symlink_to(real, target_is_directory=True)
        self.output = alias / "nested" / "unit.json"

        result = self.run_cli(task)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse((real / "nested" / "unit.json").exists())


if __name__ == "__main__":
    unittest.main()
