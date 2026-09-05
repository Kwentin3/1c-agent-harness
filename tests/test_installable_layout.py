from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest

from one_c_harness import cf_materializer


ROOT = Path(__file__).resolve().parents[1]


class InstallableLayoutTests(unittest.TestCase):
    def test_core_uses_its_own_source_namespace_not_scripts(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertTrue((ROOT / "one_c_harness" / "companion.py").is_file())
        self.assertEqual(metadata["tool"]["setuptools"]["packages"], ["one_c_harness"])
        self.assertNotIn("package-dir", metadata["tool"]["setuptools"])

    def test_runtime_locator_is_executor_owned_not_a_project_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "business-project"
            project.mkdir()
            runtime = root / "executor-runtime"
            runtime.mkdir()
            files = {
                "platform": runtime / "1cv8t",
                "xvfb": runtime / "xvfb-run",
                "fontconfig": runtime / "fonts.conf",
                "libs": runtime / "libs",
            }
            for name in ("platform", "xvfb", "fontconfig"):
                files[name].write_text(name, encoding="utf-8")
            files["platform"].chmod(0o755)
            files["xvfb"].chmod(0o755)
            files["libs"].mkdir()
            config = root / "executor-runtime.json"
            config.write_text(json.dumps({
                "schemaVersion": 1,
                **{name: str(path) for name, path in files.items()},
            }), encoding="utf-8")
            previous = os.environ.get("ONE_C_HARNESS_RUNTIME_CONFIG")
            os.environ["ONE_C_HARNESS_RUNTIME_CONFIG"] = str(config)
            try:
                resolved = cf_materializer.require_runtime(project)
            finally:
                if previous is None:
                    os.environ.pop("ONE_C_HARNESS_RUNTIME_CONFIG", None)
                else:
                    os.environ["ONE_C_HARNESS_RUNTIME_CONFIG"] = previous

        self.assertEqual(resolved, files)
        self.assertFalse((project / ".local/one-c-runtime.json").exists())


if __name__ == "__main__":
    unittest.main()
