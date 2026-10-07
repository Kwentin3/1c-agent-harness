"""Exercise CF descendant collection with real Linux processes, without 1C."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

# The outer process owns orphans when the materializer fails to adopt them.
# It holds zombies until observation, making the regression independent of
# whether CI's PID 1 would otherwise collect them, then cleans up every child.
PROBE = r'''
import ctypes,json,os,pathlib,signal,subprocess,sys,tempfile
libc=ctypes.CDLL(None,use_errno=True)
assert libc.prctl(36,1,0,0,0)==0
wrapper="""import os,sys,time
from pathlib import Path
ready_read,ready_write=os.pipe()
child=os.fork()
if child==0:
 os.close(ready_read)
 if sys.argv[3]=='detached':os.setsid()
 os.write(ready_write,b'ready');os.close(ready_write)
 time.sleep(60)
 os._exit(0)
os.close(ready_write);os.read(ready_read,5);os.close(ready_read)
Path(sys.argv[1]).write_text(str(child))
Path(sys.argv[2]).write_text('1' if sys.argv[3]=='nonzero' else '0')
if sys.argv[3]=='timeout':time.sleep(60)
os._exit(0)
"""
inner="""import json,os,pathlib,subprocess,sys
sys.path.insert(0,sys.argv[1])
from one_c_harness import cf_materializer
result=pathlib.Path(sys.argv[3]);pidfile=pathlib.Path(sys.argv[4]);mode=sys.argv[5]
# Allow interpreter/fork startup under full-suite load before testing timeout.
# The wrapper and its child still sleep 60s; no production timeout is changed.
if mode=='timeout':cf_materializer.TIMEOUT_SECONDS=2
try:
 cf_materializer._run_step([sys.executable,sys.argv[2],str(pidfile),str(result),mode],dict(os.environ),result,runner=subprocess.run)
 outcome={'status':'PASS'}
except BaseException as exc:
 outcome={'status':'FAIL','errorType':type(exc).__name__,'message':str(exc)}
pid=int(pidfile.read_text());p=pathlib.Path('/proc')/str(pid)
outcome['residualChildExists']=p.exists()
if p.exists():outcome['residualState']=(p/'stat').read_text().rsplit(')',1)[1].split()[0]
outcome['dumpResult']=result.read_text()
print(json.dumps(outcome))
"""
with tempfile.TemporaryDirectory() as folder:
 root=pathlib.Path(folder);(root/'wrapper.py').write_text(wrapper)
 try:
  completed=subprocess.run([sys.executable,'-c',inner,sys.argv[1],str(root/'wrapper.py'),str(root/'result'),str(root/'pid'),sys.argv[2]],capture_output=True,text=True,timeout=20)
  assert completed.returncode==0,completed.stderr
  outcome=json.loads(completed.stdout)
 finally:
  children=pathlib.Path(f'/proc/{os.getpid()}/task/{os.getpid()}/children')
  for value in children.read_text().split():
   pid=int(value)
   try:os.kill(pid,signal.SIGKILL)
   except ProcessLookupError:pass
   os.waitpid(pid,0)
 print(json.dumps(outcome))
'''


@unittest.skipUnless(sys.platform == "linux", "Linux process ownership contract")
class CFMaterializerProcessTests(unittest.TestCase):
    def probe(self, mode: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, str(ROOT), mode],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_success_reaps_adopted_child_instead_of_rejecting_a_zombie(self) -> None:
        result = self.probe("success")
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["dumpResult"], "0")
        self.assertFalse(result["residualChildExists"], result)

    def test_success_collects_a_child_that_started_a_new_session(self) -> None:
        result = self.probe("detached")
        self.assertEqual(result["status"], "PASS", result)
        self.assertFalse(result["residualChildExists"], result)

    def test_timeout_still_fails_and_collects_descendants(self) -> None:
        result = self.probe("timeout")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["errorType"], "MaterializationFailed")
        self.assertIn("timed out", result["message"])
        self.assertFalse(result["residualChildExists"], result)

    def test_nonzero_result_still_fails_after_descendant_collection(self) -> None:
        result = self.probe("nonzero")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["errorType"], "MaterializationFailed")
        self.assertIn("nonzero result", result["message"])
        self.assertFalse(result["residualChildExists"], result)


if __name__ == "__main__":
    unittest.main()
