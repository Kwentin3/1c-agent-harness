from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "project_target.py"
sys.path.insert(0, str(ROOT / "scripts"))
import cf_materializer


def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def manifest(root: Path) -> bytes:
    return "".join(f"{digest(p.read_bytes())}  {p.relative_to(root).as_posix()}\n" for p in sorted(root.rglob("*")) if p.is_file()).encode()

def export(root: Path, name="Sample", version="2.0") -> Path:
    source=root/".local/source/export"; source.mkdir(parents=True)
    (source/"Configuration.xml").write_bytes(f"<MetaDataObject><Configuration><Properties><Name>{name}</Name><Version>{version}</Version></Properties></Configuration></MetaDataObject>".encode())
    p=source/"Documents/Order.xml"; p.parent.mkdir(); p.write_text("<MetaDataObject/>")
    return source

def contract(root: Path, source: dict[str, object], content: str, count=2) -> None:
    value={"schemaVersion":2,"configuration":{"name":"Sample","version":"2.0"},"source":source,"snapshot":{"root":".local/targets/sample/snapshot","manifest":".local/targets/sample/snapshot.manifest","contentId":f"sha256:{content}","fileCount":count},"dailyNativeRoute":"scripts/shared_task_route.py run"}
    (root/"project-target.json").write_text(json.dumps(value))

def hierarchical(root: Path) -> Path:
    source=export(root); payload=manifest(source); contract(root,{"kind":"hierarchical","path":".local/source/export","contentId":f"sha256:{digest(payload)}","fileCount":2},digest(payload)); return source

def open_(root: Path, command="open") -> subprocess.CompletedProcess[str]:
    argv=[sys.executable,str(CLI),"--repo-root",str(root)] if command == "alias" else [sys.executable,str(CLI),command,"--repo-root",str(root)]
    return subprocess.run(argv,text=True,capture_output=True,check=False)

def result(cp): return json.loads(cp.stdout)

class ProjectTargetTests(unittest.TestCase):
    def test_hierarchical_cold_and_legacy_alias_use_one_contract_and_admission(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=hierarchical(root); cold=open_(root); alias=open_(root,"alias")
            self.assertEqual(cold.returncode,0,cold.stdout); self.assertEqual(alias.returncode,0,alias.stdout)
            self.assertEqual(result(cold)["action"],"materialized"); self.assertEqual(result(alias)["action"],"reused")
            ref=result(cold)["snapshot"]; self.assertIn(b"Sample",(root/ref["root"] / "Configuration.xml").read_bytes())
            self.assertEqual(manifest(source),manifest(root/ref["root"]))

    def test_warm_reuse_is_identical_without_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=hierarchical(root); self.assertEqual(open_(root).returncode,0); shutil.rmtree(source)
            one,two=open_(root),open_(root)
            self.assertEqual(one.stdout,two.stdout); self.assertEqual(result(one)["action"],"reused")

    def test_invalid_source_and_retained_target_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=hierarchical(root); (source/"Documents/Order.xml").write_text("bad")
            self.assertEqual(result(open_(root))["reasonCode"],"source_mismatch")
            self.assertFalse((root/".local/targets/sample").exists())
            (source/"Documents/Order.xml").write_text("<MetaDataObject/>")
            payload=manifest(source); contract(root,{"kind":"hierarchical","path":".local/source/export","contentId":f"sha256:{digest(payload)}","fileCount":2},digest(payload)); self.assertEqual(open_(root).returncode,0)
            f=root/".local/targets/sample/snapshot/Documents/Order.xml"; f.chmod(0o644); f.write_text("bad")
            self.assertEqual(result(open_(root))["reasonCode"],"snapshot_invalid")
            self.assertEqual(f.read_text(),"bad")

    def test_cf_open_uses_repo_owned_algorithm_and_fake_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); template=export(root); payload=manifest(template); shutil.rmtree(template)
            cf=root/".local/dist/sample.cf"; cf.parent.mkdir(parents=True); cf.write_bytes(b"cf")
            contract(root,{"kind":"cf","path":".local/dist/sample.cf","sha256":digest(b"cf")},digest(payload)); self.fake_runtime(root)
            cold,warm=open_(root),open_(root)
            self.assertEqual(cold.returncode,0,cold.stdout); self.assertEqual(result(cold)["action"],"materialized")
            self.assertEqual(result(warm)["action"],"reused")
            self.assertEqual(cf.read_bytes(),b"cf")
            self.assertEqual((root/".local/runtime-count").read_text(),"1\n1\n1\n")
            self.assertFalse(any((root/".local/targets").glob(".sample.staging-*")))

    def test_missing_runtime_is_only_cf_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cf=root/".local/dist/sample.cf"; cf.parent.mkdir(parents=True); cf.write_bytes(b"cf")
            contract(root,{"kind":"cf","path":".local/dist/sample.cf","sha256":digest(b"cf")},"0"*64)
            blocked=result(open_(root)); self.assertEqual(blocked["reasonCode"],"materializer_unavailable"); self.assertEqual(blocked["locator"],"docs/lab-bootstrap.md")

    def test_parallel_cold_cf_open_runs_one_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); template=export(root); payload=manifest(template); shutil.rmtree(template)
            cf=root/".local/dist/sample.cf"; cf.parent.mkdir(parents=True); cf.write_bytes(b"cf")
            contract(root,{"kind":"cf","path":".local/dist/sample.cf","sha256":digest(b"cf")},digest(payload)); self.fake_runtime(root)
            args=[sys.executable,str(CLI),"open","--repo-root",str(root)]
            a=subprocess.Popen(args,text=True,stdout=subprocess.PIPE); b=subprocess.Popen(args,text=True,stdout=subprocess.PIPE)
            ao,_=a.communicate(timeout=15); bo,_=b.communicate(timeout=15)
            self.assertEqual((a.returncode,b.returncode),(0,0)); self.assertEqual({json.loads(ao)["action"],json.loads(bo)["action"]},{"materialized","reused"})
            self.assertEqual((root/".local/runtime-count").read_text(),"1\n1\n1\n")

    def test_cf_materializer_checks_all_three_results_and_removes_bad_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cf=root/"source.cf"; cf.write_bytes(b"cf"); out=root/"output"; work=root/"work"; self.fake_runtime(root)
            def runner(argv, **kwargs):
                result=Path(argv[argv.index("/DumpResult")+1]); result.parent.mkdir(parents=True,exist_ok=True); result.write_text("1")
                return subprocess.CompletedProcess(argv,0)
            with self.assertRaises(cf_materializer.MaterializationFailed):
                cf_materializer.materialize_cf(repo_root=root,source=cf,output=out,work_root=work,runner=runner)
            self.assertFalse(out.exists())

    @staticmethod
    def fake_runtime(root: Path) -> None:
        binary=root/".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t"; xvfb=root/".local/platform/libs/usr/bin/xvfb-run"; font=root/".local/platform/fonts.conf"
        binary.parent.mkdir(parents=True,exist_ok=True); xvfb.parent.mkdir(parents=True,exist_ok=True); font.parent.mkdir(parents=True,exist_ok=True); binary.write_text("x"); font.write_text("<fontconfig/>")
        script=f'''#!/usr/bin/env python3
import sys
from pathlib import Path
args=sys.argv[1:]
root=Path({str(root)!r})
with (root/'.local/runtime-count').open('a') as f:f.write('1\\n')
result=Path(args[args.index('/DumpResult')+1]);result.parent.mkdir(parents=True,exist_ok=True);result.write_text('0')
if '/DumpConfigToFiles' in args:
 out=Path(args[args.index('/DumpConfigToFiles')+1]);out.mkdir();(out/'Configuration.xml').write_text('<MetaDataObject><Configuration><Properties><Name>Sample</Name><Version>2.0</Version></Properties></Configuration></MetaDataObject>');(out/'Documents').mkdir();(out/'Documents/Order.xml').write_text('<MetaDataObject/>')
'''
        xvfb.write_text(script); xvfb.chmod(0o755); binary.chmod(0o755)

if __name__ == "__main__": unittest.main()
