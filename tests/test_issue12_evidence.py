from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "issue12-narrow-context-20260826"
MANIFEST = "package-manifest.json"

JET_CONTENT_ID = "sha256:70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
SDMS_CONTENT_ID = "sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d"
NATIVE_EVIDENCE_ANCHORS = {
    "baseline": {
        "receipt": "df23b8e745ded9ba5148bd9c5a870327dade1842f7be84d4e4d46e4e5d52d90e",
        "createLog": "d2113b46662b4711cbaba99b57fdfacfbd1a38ddeb3d73cd806daf464e9bbf13",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "dumpResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
    },
    "candidate": {
        "receipt": "79a5a4de238aeb28484285b18f29d381c20212767fc381cb51cef22367620084",
        "createLog": "b3313dd7bb728e36103bc2f6a58c627a5831e588dbfbcc0270e4450e2b5f3e1b",
        "loadLog": "4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86",
        "dumpResult": "e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083",
    },
}


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


def parse_single_file_unified_diff(data: bytes) -> list[bytes]:
    records = data.splitlines()
    if not data.endswith(b"\n") or len(records) < 6:
        raise AssertionError("invalid unified diff framing")
    if not records[0].startswith(b"diff --git a/"):
        raise AssertionError("invalid unified diff header")
    if not records[1].startswith(b"index "):
        raise AssertionError("invalid unified diff index")
    if not records[2].startswith(b"--- a/") or not records[3].startswith(b"+++ b/"):
        raise AssertionError("invalid unified diff file headers")
    match = re.fullmatch(rb"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?", records[4])
    if match is None:
        raise AssertionError("invalid unified diff hunk header")
    old_count = int(match.group(2) or b"1")
    new_count = int(match.group(4) or b"1")
    old_seen = 0
    new_seen = 0
    for record in records[5:]:
        if not record or record[:1] not in {b" ", b"-", b"+"}:
            raise AssertionError("invalid unified diff body record")
        if record[:1] in {b" ", b"-"}:
            old_seen += 1
        if record[:1] in {b" ", b"+"}:
            new_seen += 1
    if (old_seen, new_seen) != (old_count, new_count):
        raise AssertionError("invalid unified diff hunk counts")
    return records


def apply_single_hunk_patch(original: bytes, patch: bytes) -> bytes:
    parse_single_file_unified_diff(patch)
    lines = patch.splitlines(keepends=True)
    hunk_index = next(index for index, line in enumerate(lines) if line.startswith(b"@@ "))
    match = re.fullmatch(rb"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?\n", lines[hunk_index])
    if match is None:
        raise AssertionError("unsupported patch hunk header")
    source_lines = original.splitlines(keepends=True)
    source_index = int(match.group(1)) - 1
    output = source_lines[:source_index]
    for line in lines[hunk_index + 1:]:
        marker, payload = line[:1], line[1:]
        if marker == b" ":
            if source_lines[source_index] != payload:
                raise AssertionError("patch context does not match source bytes")
            output.append(payload)
            source_index += 1
        elif marker == b"-":
            if source_lines[source_index] != payload:
                raise AssertionError("patch removal does not match source bytes")
            source_index += 1
        elif marker == b"+":
            output.append(payload)
        else:
            raise AssertionError("invalid unified diff body record")
    output.extend(source_lines[source_index:])
    expected = b"".join(output)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        owner = root / "Catalogs/Warehouses.xml"
        owner.parent.mkdir(parents=True)
        owner.write_bytes(original)
        patch_path = root / "change.patch"
        patch_path.write_bytes(patch)
        common = ["git", "-c", "core.autocrlf=false", "apply", "--whitespace=nowarn"]
        checked = subprocess.run([*common, "--check", str(patch_path)], cwd=root, capture_output=True, check=False)
        if checked.returncode != 0:
            raise AssertionError("invalid unified diff: git apply --check rejected it")
        applied = subprocess.run([*common, str(patch_path)], cwd=root, capture_output=True, check=False)
        if applied.returncode != 0 or owner.read_bytes() != expected:
            raise AssertionError("invalid unified diff: git apply result mismatch")
    return expected


def normalize_jet_diff(diff: bytes, arm: str) -> bytes:
    records = parse_single_file_unified_diff(diff)
    diff = b"\n".join(records) + b"\n"
    replacements = {
        b"a/.local/runs/training-jet-review-final/snapshot/Catalogs/Warehouses.xml": b"a/Catalogs/Warehouses.xml",
        f"b/.local/experiments/issue12/arms/jet-{arm}/work-copy/Catalogs/Warehouses.xml".encode(): b"b/Catalogs/Warehouses.xml",
    }
    for old, new in replacements.items():
        if diff.count(old) != 2:
            raise AssertionError(f"unexpected frozen diff path count for {arm}: {old!r}")
        diff = diff.replace(old, new)
    normalized = b"\n".join(diff.splitlines()) + b"\n"
    parse_single_file_unified_diff(normalized)
    return normalized


def validate_native_source_binding(root: Path, arm: str) -> None:
    wrapper_path = root / f"evidence/native-jet-{arm}.json"
    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
    receipt_bytes = base64.b64decode((root / wrapper["encodedSanitizedExecutionReceipt"]).read_bytes())
    anchors = NATIVE_EVIDENCE_ANCHORS[arm]
    retained = wrapper["retainedOutputs"]
    anchored_payloads = {
        "receipt": receipt_bytes,
        "createLog": base64.b64decode((root / retained["createLog"]).read_bytes()),
        "loadLog": base64.b64decode((root / retained["loadLog"]).read_bytes()),
        "dumpResult": base64.b64decode((root / retained["dumpResult"]).read_bytes()),
    }
    if any(hashlib.sha256(payload).hexdigest() != anchors[name] for name, payload in anchored_payloads.items()):
        raise AssertionError("immutable evidence anchor mismatch")
    receipt = json.loads(receipt_bytes)
    published = wrapper["publishedChangeBindingBeforeInvocation"]
    if receipt.get("publishedChangeBindingBeforeInvocation") != published:
        raise AssertionError("receipt binding mismatch")
    task = json.loads((root / "tasks/jet.json").read_text(encoding="utf-8"))
    if published["taskId"] != task["task_id"]:
        raise AssertionError("task binding mismatch")
    expected_content_id = f"sha256:{task['snapshot']['identity']['manifest_sha256']}"
    if published["snapshotContentId"] != expected_content_id:
        raise AssertionError("snapshot binding mismatch")
    patch = (root / published["publishedPatch"]).read_bytes()
    diff = (root / published["adjudicatedDiff"]).read_bytes()
    if hashlib.sha256(patch).hexdigest() != published["publishedPatchSha256"]:
        raise AssertionError("patch binding mismatch")
    if hashlib.sha256(diff).hexdigest() != published["adjudicatedDiffSha256"]:
        raise AssertionError("diff binding mismatch")
    normalized = normalize_jet_diff(diff, arm)
    patch_records = b"\n".join(patch.splitlines()) + b"\n"
    if normalized != patch_records or hashlib.sha256(normalized).hexdigest() != published["normalizedDiffSha256"]:
        raise AssertionError("patch/diff semantic binding mismatch")
    source = wrapper["sourceBindingBeforeInvocation"]
    if published["changedFile"] != "Catalogs/Warehouses.xml":
        raise AssertionError("changed-file path binding mismatch")
    changed_bytes = base64.b64decode((root / wrapper["sourceArtifacts"]["changed"]).read_bytes())
    if hashlib.sha256(changed_bytes).hexdigest() != source["changedFileSha256"]:
        raise AssertionError("changed-file artifact binding mismatch")
    if published["changedFileSha256"] != source["changedFileSha256"]:
        raise AssertionError("changed-file identity binding mismatch")
    if published["workCopyManifestSha256"] != source["manifestSha256"]:
        raise AssertionError("work-copy identity binding mismatch")


def refresh_package_manifest_entry(root: Path, relative: str) -> None:
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = root / relative
    manifest["artifacts"][relative] = sha256(artifact)
    manifest["artifactStats"][relative] = artifact.stat().st_size
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_native_command_contract(receipt: dict, arm: str) -> None:
    repo = "${REPO}"
    expected_work_copy = f".local/experiments/issue12/arms/jet-{arm}/work-copy"
    run_relative = receipt.get("runRoot")
    work_relative = receipt.get("workCopy")
    run_pattern = rf"\.local/runs/issue12-jet-{arm}-\d{{8}}T\d{{6}}Z-[0-9a-f]{{8}}"
    if not isinstance(run_relative, str) or re.fullmatch(run_pattern, run_relative) is None:
        raise AssertionError("native run-root contract mismatch")
    if work_relative != expected_work_copy:
        raise AssertionError("native work-copy contract mismatch")
    run_root = f"{repo}/{run_relative}"
    work_copy = f"{repo}/{work_relative}"
    executable = f"{repo}/.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t"
    common = ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp", executable]
    expected_environment = {
        "LD_LIBRARY_PATH": (
            f"{repo}/.local/platform/1cv8t/x86_64/8.5.1.1150:"
            f"{repo}/.local/platform/libs/usr/lib/x86_64-linux-gnu"
        ),
        "FONTCONFIG_FILE": f"{repo}/.local/platform/fonts.conf",
        "HOME": f"{run_root}/home",
        "TMPDIR": f"{run_root}/tmp",
        "XDG_CACHE_HOME": f"{run_root}/home/xdg-cache",
        "XDG_CONFIG_HOME": f"{run_root}/home/xdg-config",
        "XDG_DATA_HOME": f"{run_root}/home/xdg-data",
    }
    if receipt.get("relevantEnvironment") != expected_environment:
        raise AssertionError("native environment contract mismatch")
    expected_steps = [
        [
            *common, "CREATEINFOBASE", f"File={run_root}/ib",
            "/DisableStartupDialogs", "/DisableStartupMessages",
            "/Out", f"{run_root}/logs/create.log",
            "/DumpResult", f"{run_root}/logs/create.result",
        ],
        [
            *common, "DESIGNER", "/F", f"{run_root}/ib",
            "/LoadConfigFromFiles", work_copy, "/UpdateDBCfg",
            "/DisableStartupDialogs", "/DisableStartupMessages",
            "/Out", f"{run_root}/logs/load.log",
            "/DumpResult", f"{run_root}/logs/load.result",
        ],
    ]
    steps = receipt.get("steps", [])
    if len(steps) != 2:
        raise AssertionError("native step count mismatch")
    for step, expected_name, expected_argv, expected_marker in zip(
        steps,
        ("create", "load"),
        expected_steps,
        ("completed successfully", "Configuration successfully updated"),
    ):
        if step.get("step") != expected_name or step.get("argv") != expected_argv:
            raise AssertionError(f"native {expected_name} argv contract mismatch")
        if step.get("successMarker") != expected_marker:
            raise AssertionError(f"native {expected_name} marker contract mismatch")


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

    def test_no_unexpected_host_absolute_paths_including_base64(self) -> None:
        absolute = re.compile(r"(?<![A-Za-z0-9_$}])/(?:workspace|home|tmp|root|data|opt|var|mnt)/[^\s\"']+")
        allowed_frozen_paths = {
            "/workspace/1c-agent-harness/.local/runs/sdms-native-02/snapshot",
            "/workspace/1c-agent-harness/.local/runs/sdms-native-02/snapshot.manifest",
        }
        observed_frozen_paths: set[str] = set()
        for path in PACKAGE.rglob("*"):
            if not path.is_file():
                continue
            payloads = [("plain", path.read_bytes())]
            if path.suffix == ".b64":
                payloads.append(("decoded", base64.b64decode(path.read_bytes(), validate=False)))
            for representation, payload in payloads:
                matches = set(absolute.findall(payload.decode("utf-8", errors="replace")))
                relative = path.relative_to(PACKAGE).as_posix()
                if relative == "tasks/sdms-frozen-original.json.b64" and representation == "decoded":
                    observed_frozen_paths.update(matches)
                elif matches:
                    self.fail(f"unexpected host paths in {relative} ({representation}): {sorted(matches)}")
        self.assertEqual(observed_frozen_paths, allowed_frozen_paths)

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

    def test_jet_full_text_oracle_difference_is_non_blocking(self) -> None:
        baseline = (PACKAGE / "diffs/jet-baseline.diff").read_text(encoding="utf-8")
        candidate = (PACKAGE / "diffs/jet-candidate.diff").read_text(encoding="utf-8")
        self.assertIn("<FullTextSearch>DontUse</FullTextSearch>", baseline)
        self.assertIn("<FullTextSearch>Use</FullTextSearch>", candidate)
        public_task = load_json("tasks/jet.json")
        public_contract = " ".join([public_task["business_wording"], *public_task["acceptance"]])
        self.assertNotIn("FullTextSearch", public_contract)
        adjudication = load_json("adjudication/jet.json")
        # Frozen raw adjudication remains untouched as historical evidence.
        self.assertEqual(adjudication["armResults"]["baseline"]["fairnessAdjustedFieldsCorrect"], 11)
        self.assertEqual(adjudication["armResults"]["candidate"]["fairnessAdjustedFieldsCorrect"], 10)
        decision = load_json("decision.json")
        self.assertEqual(decision["publicSemanticContract"]["baseline"], "pass")
        self.assertEqual(decision["publicSemanticContract"]["candidate"], "pass")
        self.assertEqual(decision["fullTextSearchOracleDifference"]["effectOnDecision"], "non-blocking")

    def test_native_receipts_bind_exact_inputs_commands_and_outputs(self) -> None:
        for arm in ("baseline", "candidate"):
            validate_native_source_binding(PACKAGE, arm)
            receipt = load_json(f"evidence/native-jet-{arm}.json")
            published_receipt_bytes = base64.b64decode((PACKAGE / receipt["encodedSanitizedExecutionReceipt"]).read_bytes())
            published_receipt = json.loads(published_receipt_bytes)
            self.assertEqual(
                hashlib.sha256(published_receipt_bytes).hexdigest(),
                receipt["publishedSanitizedReceiptSha256"],
            )
            self.assertEqual(receipt["receiptSanitization"]["placeholder"], "${REPO}")
            self.assertIs(receipt["receiptSanitization"]["rawReceiptRetained"], False)
            self.assertIs(receipt["receiptSanitization"]["rawReceiptAuthenticityClaimed"], False)
            self.assertEqual(published_receipt["sourceBindingBeforeInvocation"], receipt["sourceBindingBeforeInvocation"])
            validate_native_command_contract(published_receipt, arm)
            self.assertEqual(published_receipt["status"], "ok")
            self.assertEqual(published_receipt["preSnapshot"], published_receipt["postSnapshot"])
            self.assertEqual(published_receipt["preSnapshot"], {
                "listed": 5099, "actual": 5099, "missing": 0,
                "extra": 0, "mismatch": 0, "symlinks": 0,
            })

            source = receipt["sourceArtifacts"]
            original = base64.b64decode((PACKAGE / source["original"]).read_bytes())
            changed = base64.b64decode((PACKAGE / source["changed"]).read_bytes())
            manifest_bytes = base64.b64decode((PACKAGE / source["snapshotManifest"]).read_bytes())
            binding = receipt["sourceBindingBeforeInvocation"]
            self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), receipt["snapshotManifestSha256"])
            self.assertEqual(hashlib.sha256(original).hexdigest(), binding["originalChangedFileSha256"])
            self.assertEqual(hashlib.sha256(changed).hexdigest(), binding["changedFileSha256"])
            rows = {}
            for line in manifest_bytes.decode("utf-8-sig").splitlines():
                digest, relative = line.split(maxsplit=1)
                rows[relative] = digest
            self.assertEqual(len(rows), binding["fileCount"])
            rows["Catalogs/Warehouses.xml"] = binding["changedFileSha256"]
            work_copy_manifest = "".join(
                f"{rows[name]}  {name}\n" for name in sorted(rows)
            ).encode("utf-8")
            self.assertEqual(hashlib.sha256(work_copy_manifest).hexdigest(), binding["manifestSha256"])

            patch_bytes = (PACKAGE / source["patch"]).read_bytes()
            self.assertEqual(apply_single_hunk_patch(original, patch_bytes), changed)

            encoded_logs = receipt["retainedOutputs"]
            create_log = base64.b64decode((PACKAGE / encoded_logs["createLog"]).read_bytes())
            load_log = base64.b64decode((PACKAGE / encoded_logs["loadLog"]).read_bytes())
            dump_result = base64.b64decode((PACKAGE / encoded_logs["dumpResult"]).read_bytes())
            for step, log in zip(published_receipt["steps"], (create_log, load_log)):
                self.assertEqual(step["processExit"], 0)
                self.assertIs(step["dumpResultZero"], True)
                self.assertEqual(hashlib.sha256(log).hexdigest(), step["logSha256"])
                self.assertIn(step["successMarker"], log.decode("utf-8-sig", errors="replace"))
                self.assertEqual(hashlib.sha256(dump_result).hexdigest(), step["dumpResultSha256"])
            self.assertEqual(dump_result.decode("utf-8-sig").replace("\r", "").replace("\n", ""), "0")

    def test_native_source_binding_mutations_fail_closed_after_manifest_refresh(self) -> None:
        mutations = ("patch", "diff", "work-copy", "receipt")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "package"
                shutil.copytree(PACKAGE, root)
                wrapper_relative = "evidence/native-jet-baseline.json"
                wrapper_path = root / wrapper_relative
                wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
                receipt_relative = wrapper["encodedSanitizedExecutionReceipt"]
                if mutation == "patch":
                    relative = "patches/jet-baseline.patch"
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"# changed after native run\n")
                    refresh_package_manifest_entry(root, relative)
                elif mutation == "diff":
                    relative = "diffs/jet-baseline.diff"
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"# changed after adjudication\n")
                    refresh_package_manifest_entry(root, relative)
                elif mutation == "work-copy":
                    relative = wrapper["sourceArtifacts"]["changed"]
                    path = root / relative
                    changed = bytearray(base64.b64decode(path.read_bytes()))
                    changed[-1] ^= 1
                    path.write_text(base64.b64encode(changed).decode() + "\n", encoding="ascii")
                    refresh_package_manifest_entry(root, relative)
                else:
                    receipt_path = root / receipt_relative
                    receipt_bytes = base64.b64decode(receipt_path.read_bytes())
                    receipt = json.loads(receipt_bytes)
                    receipt["publishedChangeBindingBeforeInvocation"]["taskId"] = "foreign-task"
                    changed_receipt = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
                    receipt_path.write_text(base64.b64encode(changed_receipt).decode() + "\n", encoding="ascii")
                    wrapper["publishedSanitizedReceiptSha256"] = hashlib.sha256(changed_receipt).hexdigest()
                    wrapper_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    refresh_package_manifest_entry(root, receipt_relative)
                    refresh_package_manifest_entry(root, wrapper_relative)
                validate_manifest(root)
                with self.assertRaisesRegex(AssertionError, "(?:binding|anchor) mismatch"):
                    validate_native_source_binding(root, "baseline")

    def test_coordinated_receipt_and_output_rewrites_fail_after_manifest_refresh(self) -> None:
        for mutation in ("work-copy-traversal", "create-log-rewrite"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "package"
                shutil.copytree(PACKAGE, root)
                wrapper_relative = "evidence/native-jet-baseline.json"
                wrapper_path = root / wrapper_relative
                wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
                receipt_relative = wrapper["encodedSanitizedExecutionReceipt"]
                receipt_path = root / receipt_relative
                receipt = json.loads(base64.b64decode(receipt_path.read_bytes()))
                if mutation == "work-copy-traversal":
                    receipt["workCopy"] = "../../outside-run"
                    operand = receipt["steps"][1]["argv"].index("/LoadConfigFromFiles") + 1
                    receipt["steps"][1]["argv"][operand] = "${REPO}/../../outside-run"
                else:
                    log_relative = wrapper["retainedOutputs"]["createLog"]
                    log_path = root / log_relative
                    rewritten = base64.b64decode(log_path.read_bytes()) + b"fabricated post-run bytes\n"
                    log_path.write_text(base64.b64encode(rewritten).decode() + "\n", encoding="ascii")
                    receipt["steps"][0]["logSha256"] = hashlib.sha256(rewritten).hexdigest()
                    refresh_package_manifest_entry(root, log_relative)
                changed_receipt = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
                receipt_path.write_text(base64.b64encode(changed_receipt).decode() + "\n", encoding="ascii")
                wrapper["publishedSanitizedReceiptSha256"] = hashlib.sha256(changed_receipt).hexdigest()
                wrapper_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                refresh_package_manifest_entry(root, receipt_relative)
                refresh_package_manifest_entry(root, wrapper_relative)
                validate_manifest(root)
                with self.assertRaisesRegex(AssertionError, "immutable evidence anchor mismatch"):
                    validate_native_source_binding(root, "baseline")

    def test_malformed_unified_diff_hunk_counts_are_rejected(self) -> None:
        wrapper = load_json("evidence/native-jet-baseline.json")
        source = wrapper["sourceArtifacts"]
        original = base64.b64decode((PACKAGE / source["original"]).read_bytes())
        patch = (PACKAGE / source["patch"]).read_bytes()
        malformed = patch.replace(b"@@ -362,6 +362,46 @@", b"@@ -362,999 +362,999 @@")
        self.assertNotEqual(patch, malformed)
        with self.assertRaisesRegex(AssertionError, "invalid unified diff"):
            apply_single_hunk_patch(original, malformed)

    def test_native_command_contract_rejects_mutations(self) -> None:
        wrapper = load_json("evidence/native-jet-baseline.json")
        encoded = (PACKAGE / wrapper["encodedSanitizedExecutionReceipt"]).read_bytes()
        original = json.loads(base64.b64decode(encoded))
        mutations = []

        changed = copy.deepcopy(original)
        changed["steps"][0]["argv"][4] = "definitely-not-1c"
        mutations.append(changed)

        changed = copy.deepcopy(original)
        changed["steps"][0]["argv"][5] = "FABRICATEDMODE"
        mutations.append(changed)

        changed = copy.deepcopy(original)
        changed["steps"][1]["argv"].remove("/UpdateDBCfg")
        mutations.append(changed)

        changed = copy.deepcopy(original)
        out_index = changed["steps"][1]["argv"].index("/Out") + 1
        changed["steps"][1]["argv"][out_index] = "${REPO}/wrong/load.log"
        mutations.append(changed)

        changed = copy.deepcopy(original)
        changed["relevantEnvironment"]["LD_LIBRARY_PATH"] = "${REPO}/wrong/runtime"
        mutations.append(changed)

        for invalid in ("", "/absolute/work-copy", "../../outside-run", ".local/experiments/issue12/arms/jet-candidate/work-copy"):
            changed = copy.deepcopy(original)
            changed["workCopy"] = invalid
            mutations.append(changed)

        for invalid in ("", "/absolute/run", "../../outside-run", ".local/runs/issue12-jet-baseline-not-a-run-id"):
            changed = copy.deepcopy(original)
            changed["runRoot"] = invalid
            mutations.append(changed)

        for mutation in mutations:
            with self.assertRaisesRegex(AssertionError, "contract mismatch"):
                validate_native_command_contract(mutation, "baseline")

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
