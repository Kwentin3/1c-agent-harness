from __future__ import annotations
import base64, hashlib, importlib.util, json, os, shutil, tempfile, unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments/issue46-supplier-warehouse-core-loop"
SPEC = importlib.util.spec_from_file_location("issue46_validate", PKG/"validate.py")
assert SPEC and SPEC.loader
V = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(V)

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def refresh(root: Path) -> None:
    files={p.relative_to(root).as_posix():digest(p) for p in root.rglob("*") if p.is_file() and p.name!="manifest.json"}
    (root/"manifest.json").write_text(json.dumps({"schemaVersion":1,"files":dict(sorted(files.items()))},sort_keys=True)+"\n")

class Issue46EvidenceTest(unittest.TestCase):
    def copy(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)/"package"; shutil.copytree(PKG,root); return td,root
    def rejected(self, mutate):
        td,root=self.copy()
        try:
            mutate(root); refresh(root)
            with self.assertRaises((ValueError,KeyError,TypeError,base64.binascii.Error)): V.validate(root,False)
        finally: td.cleanup()
    def test_package_is_closed_hashed_and_semantically_valid(self):
        result=V.validate(PKG,True); self.assertEqual(result["status"],"PASS"); self.assertEqual(result["lanes"],["red","green","repeat"])
    def test_shallow_context_requires_exact_github_pr_authority(self):
        with mock.patch.dict(os.environ,{},clear=True), self.assertRaises(ValueError):
            V.validate_shallow_pr_context(PKG,V.FROZEN_CONTRACT)
        with tempfile.TemporaryDirectory() as td:
            event=Path(td)/"event.json"; head=V.git(PKG,"rev-parse","HEAD")
            payload={"pull_request":{"base":{"ref":"main","sha":V.FROZEN_CONTRACT["baseCommit"]},"head":{"sha":head}}}
            event.write_text(json.dumps(payload))
            env={"GITHUB_EVENT_NAME":"pull_request","GITHUB_REPOSITORY":"Kwentin3/1c-agent-harness","GITHUB_EVENT_PATH":str(event)}
            with mock.patch.dict(os.environ,env,clear=True): V.validate_shallow_pr_context(PKG,V.FROZEN_CONTRACT)
            payload["pull_request"]["base"]["sha"]="0"*40; event.write_text(json.dumps(payload))
            with mock.patch.dict(os.environ,env,clear=True), self.assertRaises(ValueError): V.validate_shallow_pr_context(PKG,V.FROZEN_CONTRACT)
    def test_unmanifested_file_and_hash_tamper_are_rejected(self):
        td,root=self.copy()
        try:
            (root/"foreign.txt").write_text("x")
            with self.assertRaises(ValueError): V.validate(root,False)
            (root/"foreign.txt").unlink(); (root/"README.md").write_text("tampered")
            with self.assertRaises(ValueError): V.validate(root,False)
        finally: td.cleanup()
    def test_production_mutation_with_refreshed_manifest_is_rejected(self):
        self.rejected(lambda r:(r/"production.patch").write_bytes((r/"production.patch").read_bytes().replace(b"Warehouse.DeletionMark",b"Warehouse.Ref.DeletionMark")))
    def test_instrumentation_mutation_with_refreshed_manifest_is_rejected(self):
        def mutate(r):
            p=r/"instrumentation.json"; d=json.loads(p.read_text()); raw=base64.b64decode(d["lanes"]["green"]["base64"])+b"x"; d["lanes"]["green"]["base64"]=base64.b64encode(raw).decode(); d["lanes"]["green"]["sha256"]=hashlib.sha256(raw).hexdigest(); p.write_text(json.dumps(d))
        self.rejected(mutate)
    def test_coordinated_instrumentation_rewrite_is_rejected(self):
        def mutate(r):
            ip=r/"instrumentation.json"; ep=r/"evidence.json"
            i=json.loads(ip.read_text()); e=json.loads(ep.read_text())
            raw=base64.b64decode(i["lanes"]["green"]["base64"])+b"foreign"
            changed=hashlib.sha256(raw).hexdigest()
            i["lanes"]["green"].update(base64=base64.b64encode(raw).decode(),sha256=changed)
            e["lanes"]["green"]["binding"]["instrumentationPatchSha256"]=changed
            ip.write_text(json.dumps(i)); ep.write_text(json.dumps(e))
        self.rejected(mutate)
    def test_coordinated_production_rewrite_is_rejected(self):
        def mutate(r):
            pp=r/"production.patch"; ep=r/"evidence.json"; e=json.loads(ep.read_text())
            raw=pp.read_bytes().replace(b"\tIf Warehouse.DeletionMark Then",b"\t// If Warehouse.DeletionMark Then\r\n\tIf False Then")
            changed=hashlib.sha256(raw).hexdigest(); pp.write_bytes(raw); e["productionPatchSha256"]=changed
            for lane in ("green","repeat"): e["lanes"][lane]["binding"]["productionPatchSha256"]=changed
            ep.write_text(json.dumps(e))
        self.rejected(mutate)
    def test_stale_foreign_and_partial_evidence_are_rejected(self):
        def stale(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); d["lanes"]["red"]["request"]["treeIdentity"]="0"*64; p.write_text(json.dumps(d))
        def foreign(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); d["lanes"]["green"]["request"]["changedPaths"].append("Foreign.bsl"); p.write_text(json.dumps(d))
        def partial(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); del d["lanes"]["repeat"]; p.write_text(json.dumps(d))
        for mutation in (stale,foreign,partial): self.rejected(mutation)
    def test_noncanonical_or_reused_identity_is_rejected(self):
        def mutate(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); d["lanes"]["green"]["request"]["nonce"]=d["lanes"]["red"]["request"]["nonce"]; p.write_text(json.dumps(d))
        self.rejected(mutate)
    def test_business_wrong_and_bad_cleanup_are_rejected(self):
        def wrong(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); d["lanes"]["green"]["business"]["activePosted"]="No"; p.write_text(json.dumps(d))
        def cleanup(r):
            p=r/"evidence.json"; d=json.loads(p.read_text()); d["lanes"]["repeat"]["runner"]["storageCompaction"]["status"]="partial"; p.write_text(json.dumps(d))
        for mutation in (wrong,cleanup): self.rejected(mutation)
if __name__=="__main__": unittest.main()
