"""Portable checks of the source-owned skill recovery contract; no Hermes install required."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillSourceTests(unittest.TestCase):
    def test_all_three_non_plugin_domains_are_recoverable(self):
        manifest = json.loads((ROOT / "skills/manifest.json").read_text())
        self.assertEqual({p["name"] for p in manifest["packages"]}, {
            "1c-enterprise-linux", "headless-1c-probing", "semantic-contract-testing",
        })

    def test_manifest_closes_exact_resource_sets_and_identities(self):
        manifest = json.loads((ROOT / "skills/manifest.json").read_text())
        for package in manifest["packages"]:
            with self.subTest(package=package["name"]):
                root = ROOT / package["source_root"]
                actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
                declared = [r["path"] for r in package["resources"]]
                self.assertEqual(len(declared), len(set(declared)))
                self.assertEqual(actual, set(declared))
                for resource in package["resources"]:
                    data = (root / resource["path"]).read_bytes()
                    self.assertEqual(len(data), resource["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), resource["sha256"])
                lines = "".join(r["sha256"] + "  " + r["path"] + "\n"
                                for r in sorted(package["resources"], key=lambda r: r["path"]))
                self.assertEqual(hashlib.sha256(lines.encode()).hexdigest(), package["resource_manifest_sha256"])
                body = (root / "SKILL.md").read_text()
                self.assertEqual(re.search(r"^version: (.+)$", body, re.M)[1], package["version"])
                for resource in package["resources"]:
                    for reference in re.findall(r"references/[a-z0-9-]+\.md", (root / resource["path"]).read_text()):
                        self.assertTrue((root / reference).is_file(), reference)

    def test_main_1c_skill_preserves_both_discovery_triggers(self):
        text = (ROOT / "skills/1c/1c-enterprise-linux/SKILL.md").read_text()
        description = re.search(r"^description: (.+)$", text, re.M)[1].lower()
        self.assertIn("xml/bsl", description)
        self.assertIn("linux", description)


if __name__ == "__main__":
    unittest.main()
