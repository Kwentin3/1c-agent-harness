#!/usr/bin/python3
"""Fixed SSH capability for one admitted demo journal; no shell or path input."""
import base64, datetime, hashlib, json, os, re, signal, stat, subprocess, sys, time, uuid
from pathlib import Path

REFERENCE = 'd2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c'
REFERENCE_IMAGE = 'sha256:69f919497cada9a8611f3de61df902d9f94bf20f84552ef5bd93125c38608ef9'
WORKER_IMAGE = 'sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488'
RUNTIME_HOST = os.environ.get('CURRENT_JOURNAL_RUNTIME_ROOT','')
RUNTIME_TARGET = '/opt/admitted-ibcmd'
BINARY_SHA256 = '62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7'
VRD_SHA256 = 'e5406c8e7352b43c6499e2ff4fe189c9b239fe045eb0ac46de2960555850ac7d'
LOCK_FILE = str(Path(__file__).resolve().with_name('access.lock'))
ACCOUNTING_EXECUTOR = '2b5cf583d41f24bd4b4dde0d3678f3d3ad1b5e16293e03a5b43ea96258b0e5d7'
CONTRACT_SHA256 = '9ddb68dba6c8eb365c682e4f51dd71105d4659fde5bae0b7bafe8c0414a401e6'

# Runs only in the existing executor/file owner's namespace, never in the UID33 worker.
# This replaces export_research.py's per-capture accounting, not its ledger.
ACCOUNTING = r'''
import datetime,fcntl,hashlib,json,math,os,pathlib,re,stat,sys,tempfile,uuid
ROOT=pathlib.Path('/workspace/1c-agent-harness/.local/issue90-current-source-rnd')

def store(path,rows):
 original=path.lstat()
 fd,name=tempfile.mkstemp(prefix='.ledger-',dir=path.parent)
 try:
  os.fchmod(fd,stat.S_IMODE(original.st_mode))
  with os.fdopen(fd,'w',encoding='utf8') as out:
   fd=None;out.write(json.dumps(rows,indent=2));out.flush();os.fsync(out.fileno())
  os.replace(name,path)
  directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if fd is not None:os.close(fd)
  if os.path.exists(name):os.unlink(name)

def transaction(command):
 lock=os.open(ROOT/'issue94-ledger.lock',os.O_RDWR|os.O_NOFOLLOW)
 try:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('budget_busy') from None
  for name in ('contract.json','ledger.json','issue94-ledger.lock'):
   if not stat.S_ISREG((ROOT/name).lstat().st_mode):raise ValueError('budget_unavailable')
  raw=(ROOT/'contract.json').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=command['contractSha256']:raise ValueError('budget_unavailable')
  limits=json.loads(raw)['limits'];path=ROOT/'ledger.json';rows=json.loads(path.read_bytes())
  if (set(limits)!={'help','export','sessionCycles','callSeconds','nativeTotalSeconds'}
      or any(type(n) is not int or n<=0 for n in limits.values()) or limits['callSeconds']!=30
      or not isinstance(rows,list)):raise ValueError('budget_unavailable')
  for n,row in enumerate(rows,1):
   if (not isinstance(row,dict) or type(row.get('n')) is not int or row['n']!=n
       or row.get('kind') not in ('help','export','session','engineering-runtime-smoke')
       or row.get('status') not in ('STARTED','COMPLETED','FAILED','FAILED_NO_RETRY')):raise ValueError('budget_unavailable')
   for key in ('durationSeconds','nativeBudgetReservedSeconds'):
    value=row.get(key,0)
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('budget_unavailable')
   if row['status']!='STARTED' and ('durationSeconds' not in row or row.get('nativeBudgetReservedSeconds',0)!=0):raise ValueError('budget_unavailable')
  if command['action']=='reserve':
   kind=command['kind']
   if kind not in ('export','session'):raise ValueError('budget_unavailable')
   if any(row['status']=='STARTED' for row in rows):raise ValueError('budget_busy')
   if (sum(r['kind']=='help' for r in rows)>limits['help']
       or sum(r['kind']=='export' for r in rows)+(kind=='export')>limits['export']
       or sum(r['kind']=='session' for r in rows)+(kind=='session')>limits['sessionCycles']
       or math.fsum(r.get('durationSeconds',0) for r in rows)+(30 if kind=='export' else 0)>limits['nativeTotalSeconds']):raise ValueError('budget_exhausted')
   entry={'n':len(rows)+1,'kind':kind,'attemptId':str(uuid.uuid4()),
          'operation':'current-journal-v1' if kind=='export' else 'operator-session-cycle',
          'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status':'STARTED','nativeBudgetReservedSeconds':30 if kind=='export' else 0,
          'purpose':'fixed-current-journal' if kind=='export' else 'approved-session-cycle'}
   if kind=='export':
    request=command['request'];entry.update(request=request,requestSha256=hashlib.sha256((json.dumps(request,separators=(',',':'))+'\n').encode()).hexdigest())
   rows.append(entry)
  elif command['action']=='settle':
   matches=[r for r in rows if r.get('attemptId')==command['attemptId']]
   if len(matches)!=1 or matches[0]['status']!='STARTED':raise ValueError('budget_unavailable')
   entry=matches[0];result=command.get('result')
   if result is not None and (not isinstance(result,dict) or set(result)-{'status','nativeInvocations','exitCode','durationSeconds','outputBytes','outputSha256'}):raise ValueError('budget_unavailable')
   receipt=command['receiptSha256']
   if not isinstance(receipt,str) or re.fullmatch('[0-9a-f]{64}',receipt) is None:raise ValueError('budget_unavailable')
   wall=command['wallSeconds']
   if type(wall) not in (int,float) or not math.isfinite(wall) or wall<0:raise ValueError('budget_unavailable')
   duration=result.get('durationSeconds') if isinstance(result,dict) else None
   proven=(isinstance(result,dict) and result.get('nativeInvocations')==1
           and type(result.get('exitCode')) is int and type(duration) in (int,float)
           and math.isfinite(duration) and 0<=duration<=31)
   success=proven and result.get('status')=='EXPORTED' and result['exitCode']==0
   if entry['kind']=='session':
    success=command['completed'] is True;duration=0;proven=True
   entry.update(status='COMPLETED' if success else 'FAILED_NO_RETRY',nativeBudgetReservedSeconds=0,
                durationSeconds=duration if proven else 30,controllerWallSeconds=command['wallSeconds'],
                nativeInvocations=result.get('nativeInvocations','UNKNOWN') if result else (0 if entry['kind']=='session' else 'UNKNOWN'),
                exit=result.get('exitCode') if result else None,
                receiptSha256=receipt,
                sshExit=0 if result is not None else None,
                outputBytes=result.get('outputBytes') if result else None,outputSha256=result.get('outputSha256') if result else None,
                errorCategory=None if success else 'capability_failed')
  else:raise ValueError('budget_unavailable')
  store(path,rows)
  if json.loads(path.read_bytes())!=rows:raise ValueError('budget_unavailable')
  return {'attemptId':entry['attemptId'],'status':entry['status']}
 finally:os.close(lock)

if __name__=='__main__':
 try:print(json.dumps(transaction(json.loads(sys.stdin.buffer.read(16384)))))
 except (ValueError,KeyError,TypeError,OSError) as error:
  reason=str(error) if isinstance(error,ValueError) and str(error) in ('budget_busy','budget_exhausted') else 'budget_unavailable'
  print(json.dumps({'reasonCode':reason}));sys.exit(2)
'''


def _budget_transaction(command):
    command['contractSha256'] = CONTRACT_SHA256
    try:
        reply = subprocess.run(['/usr/bin/docker', 'exec', '-i', '--user', '10001:10001', ACCOUNTING_EXECUTOR,
                                '/usr/bin/python3', '-I', '-B', '-c', ACCOUNTING],
                               input=json.dumps(command).encode(), capture_output=True, timeout=5)
        result = json.loads(reply.stdout)
        if not isinstance(result, dict) or (not reply.returncode and set(result) != {'attemptId', 'status'}):
            raise ValueError('budget_unavailable')
        if reply.returncode:
            raise ValueError(result.get('reasonCode', 'budget_unavailable'))
        return result
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) and str(error) in ('budget_busy', 'budget_exhausted') else 'budget_unavailable'
        raise ValueError(reason) from None


def reserve_budget(kind, request=None):
    """Same ledger owner; session is an operator-only seam, never an SSH action."""
    return _budget_transaction({'action': 'reserve', 'kind': kind, 'request': request})['attemptId']


def settle_budget(attempt_id, result=None, wall_seconds=0, completed=False):
    # The forced capture owner hashes its complete, immutable receipt. Accounting
    # receives only bounded technical fields, never journal payload/inventories.
    receipt = (json.dumps(result, sort_keys=True) + '\n').encode() if result is not None else b''
    summary = {key: result[key] for key in ('status', 'nativeInvocations', 'exitCode',
               'durationSeconds', 'outputBytes', 'outputSha256') if key in result} if result is not None else None
    return _budget_transaction({'action': 'settle', 'attemptId': attempt_id, 'result': summary,
                                'receiptSha256': hashlib.sha256(receipt).hexdigest(),
                                'wallSeconds': wall_seconds, 'completed': completed})

def admit(value):
    if not isinstance(value, dict) or type(value.get('schemaVersion')) is not int or value['schemaVersion'] != 1:
        raise ValueError('invalid_request')
    action = value.get('operation')
    if action == 'probe' and set(value) == {'schemaVersion', 'operation'}:
        return value
    if action != 'export' or set(value) != {'schemaVersion', 'operation', 'start', 'end', 'format', 'followMilliseconds'}:
        raise ValueError('invalid_request')
    timestamps = []
    for field in ['start', 'end']:
        raw = value[field]
        if not isinstance(raw, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', raw):
            raise ValueError('invalid_request')
        timestamps.append(datetime.datetime.fromisoformat(raw))
    if not 0 <= (timestamps[1]-timestamps[0]).total_seconds() <= 86400:
        raise ValueError('invalid_request')
    if value['format'] not in ['json', 'xml'] or type(value['followMilliseconds']) is not int or not 0 <= value['followMilliseconds'] <= 1000:
        raise ValueError('invalid_request')
    return value

WORKER = r'''
import base64,errno,hashlib,json,os,pathlib,resource,signal,stat,subprocess,sys,time
request=json.load(sys.stdin)
journal=pathlib.Path('/source/journal')
binary=pathlib.Path('/opt/admitted-ibcmd/ibcmd')
expected='62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7'
# Rotated journal segments may be owner-only (0600). Use the source owner
# inside the isolated read-only worker; group readability is not guaranteed.
assert os.getuid()==33 and os.getgid()==33
assert hashlib.sha256(binary.read_bytes()).hexdigest()==expected
mounts=pathlib.Path('/proc/mounts').read_text().splitlines()
for mount in ['/','/source/journal','/opt/admitted-ibcmd']:
 assert any(line.split()[1]==mount and 'ro' in line.split()[3].split(',') for line in mounts)
assert not pathlib.Path('/var/lib/1c/ib/1Cv8.1CD').exists()
assert not pathlib.Path('/var/run/docker.sock').exists()
assert pathlib.Path('/proc/self/status').read_text().split('CapEff:')[1].splitlines()[0].strip()=='0000000000000000'
def inventory():
 result=[];total=0
 for p in sorted(journal.iterdir()):
  s=p.lstat()
  assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
  assert p.name=='1Cv8.lgf' or p.name.endswith('.lgp')
  total+=s.st_size
  assert len(result)<128 and total<=67108864
  with p.open('rb') as stream: readable=len(stream.read(16))
  result.append({'name':p.name,'device':s.st_dev,'inode':s.st_ino,'bytes':s.st_size,'mtimeNs':s.st_mtime_ns,'readProbeBytes':readable})
 assert any(p['name']=='1Cv8.lgf' for p in result) and len(result)>=2
 return result
before=inventory()
denied=[]
for path in [journal/'1Cv8.lgf',pathlib.Path('/etc/passwd')]:
 try:
  fd=os.open(path,os.O_WRONLY)
 except OSError as error:
  assert error.errno in [errno.EROFS,errno.EACCES]
  denied.append({'path':str(path),'errno':error.errno})
 else:
  os.close(fd)
  raise RuntimeError('write boundary is not enforced')
directory=journal.stat()
result={'schemaVersion':1,'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'timeZone':'UTC','binarySha256':expected,'sourceDirectory':{'device':directory.st_dev,'inode':directory.st_ino},'sourceBefore':before,'sourceMountedReadOnly':True,'rootFilesystemReadOnly':True,'writeRoot':'/work','writeOpenDenials':denied,'acquisitionConsistency':'NOT_PROVEN_BY_ACCESS_CAPABILITY'}
work=pathlib.Path('/work');work.mkdir(exist_ok=True);(work/'home').mkdir();(work/'tmp').mkdir()
canary=work/'access-canary';canary.write_bytes(b'probe');assert canary.read_bytes()==b'probe';canary.unlink()
if request['operation']=='probe':
 result.update(status='ACCESS_PROBE_PASS',nativeInvocations=0)
else:
 resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 output=work/('eventlog.'+request['format'])
 args=[str(binary),'eventlog','export','--format='+request['format'],'--skip-root','--from='+request['start'],'--to='+request['end'],'--out='+str(output)]
 if request['followMilliseconds']:args.append('--follow='+str(request['followMilliseconds']))
 args.append(str(journal))
 started=time.monotonic();began=time.time();p=None
 def stop(signum,frame):
  if p is not None:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  raise SystemExit(124)
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGHUP,stop);signal.signal(signal.SIGALRM,stop)
 signal.alarm(31)
 stderr=work/'stderr';stdout=work/'stdout'
 with stderr.open('wb') as err,stdout.open('wb') as out:
  p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  try:code=p.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();code=124
 elapsed=time.monotonic()-started;signal.alarm(0)
 raw=output.read_bytes() if output.is_file() else b''
 assert len(raw)<=1048576
 result.update(status='EXPORTED' if code==0 else 'NATIVE_FAILED',nativeInvocations=1,exitCode=code,startedAtUnix=began,durationSeconds=elapsed,argv=args,outputBytes=len(raw),outputSha256=hashlib.sha256(raw).hexdigest(),outputBase64=base64.b64encode(raw).decode(),sourceAfter=inventory())
 for kind,file in [('stdout',stdout),('stderr',stderr)]:
  data=file.read_bytes();result[kind]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'payloadBase64':base64.b64encode(data[:65536]).decode(),'truncated':len(data)>65536}
print(json.dumps(result,sort_keys=True))
'''

def docker_args(merged, name):
    source = f'{merged}/var/lib/1c/ib/1Cv8Log'
    return ['/usr/bin/docker', 'run', '-i', '--rm', '--pull', 'never', '--name', name,
            '--label', 'one-c-access=issue94', '--network', 'none', '--read-only',
            '--user', '33:33', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--pids-limit', '128', '--memory', '256m', '--cpus', '1', '--log-driver', 'none',
            '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=33554432,uid=33,gid=33,mode=0700',
            '--mount', f'type=bind,src={source},dst=/source/journal,readonly,bind-recursive=disabled',
            '--mount', f'type=bind,src={RUNTIME_HOST},dst={RUNTIME_TARGET},readonly,bind-recursive=disabled',
            '--env', 'TZ=UTC', '--env', 'HOME=/work/home', '--env', 'TMPDIR=/work/tmp',
            '--entrypoint', '/usr/bin/python3', WORKER_IMAGE, '-I', '-B', '-c', WORKER]

class CaptureAttemptError(ValueError):
    """A reserved capture failed; its native execution cannot be called zero."""


def main(argv=None):
    argv = [] if argv is None else argv
    if argv == ['--request-stdin']:
        print(json.dumps(execute_product(sys.stdin.buffer.read(16385)), sort_keys=True))
        return
    if argv:
        raise ValueError('invalid_request')
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    if command.startswith('current-harness-v1 '):
        print(json.dumps(_product_command(command), sort_keys=True))
        return
    match = re.fullmatch(r'current-journal-v1 ([A-Za-z0-9+/=]{1,4096})', command)
    if not match:
        raise ValueError('invalid_request')
    try:
        value = admit(json.loads(base64.b64decode(match[1], validate=True)))
    except (ValueError,UnicodeError):
        raise ValueError('invalid_request') from None
    if value['operation'] == 'probe':
        result = _capture(value)
    else:
        attempt_id = reserve_budget('export', value)
        began = time.monotonic()
        result = None
        try:
            result = _capture(value)
        except ValueError as error:
            raise CaptureAttemptError(str(error)) from None
        finally:
            try:
                settle_budget(attempt_id, result, time.monotonic() - began)
            except ValueError:
                # Reservation remains charged; never claim pre-launch rejection now.
                raise ValueError('capability_failed') from None
    print(json.dumps(result, sort_keys=True))


def _capture(value, *, binding=None):
    runtime=Path(RUNTIME_HOST)
    # Docker resolves this trusted root-owned binding; SSH UID need not traverse it.
    if not runtime.is_absolute() or ',' in RUNTIME_HOST:
        raise ValueError('binding_unavailable')
    if binding is None:
        import fcntl
        lock = os.open(LOCK_FILE,os.O_RDWR|os.O_NOFOLLOW)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('access_busy') from None
        binding = _binding()
    inspected, driver, merged, source = binding
    pid = inspected['State']['Pid']
    name = 'issue94-journal-' + uuid.uuid4().hex
    process = None
    def interrupted(signum, frame):
        raise SystemExit(128+signum)
    for signum in [signal.SIGTERM, signal.SIGHUP, signal.SIGINT]:
        signal.signal(signum, interrupted)
    try:
        process = subprocess.Popen(docker_args(merged, name), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(json.dumps(value).encode(), timeout=40)
        if process.returncode:
            raise ValueError('capability_failed')
        result = json.loads(stdout)
        if result['sourceDirectory'] != source['journalDirectory']:
            raise ValueError('binding_unavailable')
        result['sourceBinding'] = {'referenceId':REFERENCE,'referenceImage':REFERENCE_IMAGE,
            'referenceHostPid':pid,'referenceStartedAt':inspected['State']['StartedAt'],
            'referenceStorageDriver':driver['Name'],'referenceMergedRoot':merged,
            'vrdSha256':VRD_SHA256,'currentIbPath':'/var/lib/1c/ib','journalPath':'/var/lib/1c/ib/1Cv8Log','sourceProbe':source}
        return result
    finally:
        # Docker owns the task cgroup. Remove this unique helper only, never the reference.
        subprocess.run(['/usr/bin/docker','rm','--force',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        if process is not None and process.poll() is None:
            process.kill();process.wait(timeout=5)


def _binding():
    """Single existing authority for both legacy capture and product control."""
    inspected = json.loads(subprocess.check_output(['/usr/bin/docker', 'inspect', REFERENCE], timeout=5))[0]
    if inspected['Id'] != REFERENCE or inspected['Image'] != REFERENCE_IMAGE or not inspected['State']['Running']:
        raise ValueError('binding_unavailable')
    pid = inspected['State']['Pid']
    driver = inspected['GraphDriver']
    merged = driver.get('Data', {}).get('MergedDir', '')
    if driver['Name'] != 'overlay2' or not isinstance(merged, str) or not Path(merged).is_absolute() or ',' in merged:
        raise ValueError('binding_unavailable')
    # The service and VRD own the source; no model-supplied source path exists.
    service = subprocess.run(['/usr/bin/systemctl', 'is-active', '1c-jet-demo.service'], capture_output=True, timeout=5)
    if service.returncode:
        raise ValueError('binding_unavailable')
    probe = """import hashlib,json,pathlib,re,xml.etree.ElementTree as ET
p=pathlib.Path('/var/www/jetcontrol/default.vrd');raw=p.read_bytes()
ibs=[]
for el in ET.fromstring(raw).iter():
 match=re.search(r'''File\\s*=\\s*["']([^"']+)["']''',el.attrib.get('ib',''),re.I)
 if match:ibs.append(match.group(1))
journal=pathlib.Path('/var/lib/1c/ib/1Cv8Log');s=journal.stat()
assert not journal.is_symlink()
print(json.dumps({'vrdSha256':hashlib.sha256(raw).hexdigest(),'ibBindings':ibs,'timeZonePath':str(pathlib.Path('/etc/localtime').resolve()),'journalDirectory':{'device':s.st_dev,'inode':s.st_ino}}))
"""
    source = json.loads(subprocess.check_output(['/usr/bin/docker', 'exec', '--user', '33:33', REFERENCE,
        '/usr/bin/python3', '-I', '-B', '-c', probe], timeout=5))
    if source['vrdSha256'] != VRD_SHA256 or source['ibBindings'] != ['/var/lib/1c/ib'] or source['timeZonePath'] != '/usr/share/zoneinfo/Etc/UTC':
        raise ValueError('binding_unavailable')
    return inspected, driver, merged, source


PRODUCT_BOOTSTRAP = r'''
import json,os,pathlib,stat,sys
root=pathlib.Path(sys.argv[1])
if not root.is_absolute() or root.resolve()!=root:raise SystemExit(2)
for path in (root,*root.parents):
 s=path.stat()
 if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022:raise SystemExit(2)
config=root/'deployment/goal91/current-logging.json'
s=config.lstat()
if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid!=0 or s.st_mode&0o022:raise SystemExit(2)
with config.open('rb') as stream:raw=stream.read(16385)
if len(raw)>16384:raise SystemExit(2)
python=pathlib.Path(json.loads(raw)['python'])
if not python.is_absolute() or '..' in python.parts:raise SystemExit(2)
for path in (python.resolve(),*python.parents):
 s=path.stat()
 if s.st_uid!=0 or s.st_mode&0o022:raise SystemExit(2)
if not python.is_file() or not os.access(python,os.X_OK):raise SystemExit(2)
if sys.executable!=str(python):os.execv(str(python),[str(python),'-I','-B','-c',sys.argv[2],str(root),sys.argv[2]])
sys.path.insert(0,str(root))
sys.argv=['current_logging']
from one_c_harness.current_logging import main
main()
'''


def _product_source():
    if 'CURRENT_HARNESS_SOURCE' in os.environ:
        source = os.environ['CURRENT_HARNESS_SOURCE']
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+', source) or '..' in Path(source).parts:
            raise ValueError('binding_unavailable')
        return source
    if os.name != 'posix':
        raise ValueError('binding_unavailable')
    try:
        handler = Path(__file__).absolute()
        pin_path = handler.with_name('one-c-source.json')
        if any(path.is_symlink() for path in (pin_path, handler, *pin_path.parents)):
            raise ValueError
        fd = os.open(pin_path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != 0
                    or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o444):
                raise ValueError
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        pin = json.loads(raw)
        if (not isinstance(pin, dict) or set(pin) != {'repository', 'commit', 'artifact_id', 'source_directory', 'files'}
                or pin['repository'] != 'https://github.com/Kwentin3/1c-agent-harness.git'
                or not isinstance(pin['commit'], str) or not re.fullmatch('[0-9a-f]{40}', pin['commit'])
                or not isinstance(pin['artifact_id'], str) or not re.fullmatch('sha256:[0-9a-f]{64}', pin['artifact_id'])
                or pin['source_directory'] != '.' or not isinstance(pin['files'], dict)):
            raise ValueError
        info = handler.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError
        digest = pin['files']['deployment/goal91/current-journal.py']
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError
        if hashlib.sha256(handler.read_bytes()).hexdigest() != digest:
            raise ValueError
        return '/opt/one-c-harness/' + pin['commit']
    except (ValueError, TypeError, KeyError, OSError):
        raise ValueError('binding_unavailable') from None


def _product_command(command):
    match = re.fullmatch(r'current-harness-v1 ([A-Za-z0-9+/=]{1,24576})', command)
    if not match:
        raise ValueError('invalid_request')
    try:
        raw = base64.b64decode(match[1], validate=True)
    except (ValueError, UnicodeError):
        raise ValueError('invalid_request') from None
    return execute_product(raw)


def execute_product(raw):
    """Closed local/SSH product seam; binding, lock and backend keep one owner."""
    try:
        if len(raw) > 16384:
            raise ValueError
        value = json.loads(raw)
        if (not isinstance(value, dict) or set(value) != {'schemaVersion', 'operation', 'arguments'}
                or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
                or value['operation'] not in ('logging_control','observation_info','observe','expand_observation','eventlog_capture')
                or not isinstance(value['arguments'], dict)):
            raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError('invalid_request') from None
    capture = None
    if value['operation'] == 'eventlog_capture':
        capture = admit(value['arguments'])
        if capture['operation'] != 'export':
            raise ValueError('invalid_request')
    import fcntl
    lock = os.open(LOCK_FILE, os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0))
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('access_busy') from None
        source = _product_source()
        binding = _binding()
        _, _, _, bound = binding
        if capture is not None:
            return _capture(capture, binding=binding)
        # Canonical technical identity; neither caller targetRef nor a model path owns it.
        identity = {'referenceId': REFERENCE, 'image': REFERENCE_IMAGE, 'vrd': VRD_SHA256,
                    'ibPath': '/var/lib/1c/ib', 'journalDevice': bound['journalDirectory']['device'],
                    'journalInode': bound['journalDirectory']['inode']}
        target_ref = 'target:' + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        reply = subprocess.run(['/usr/bin/docker', 'exec', '-i', '--user', '0:0',
            '--env', 'ONE_C_HARNESS_CURRENT_TARGET_REF=' + target_ref,
            '--env', 'ONE_C_HARNESS_CURRENT_SOURCE=' + source,
            '--env', 'ONE_C_HARNESS_CURRENT_IB_PATH=' + bound['ibBindings'][0],
            REFERENCE, '/usr/bin/python3', '-I', '-B',
            '-c', PRODUCT_BOOTSTRAP, source, PRODUCT_BOOTSTRAP], input=raw, capture_output=True, timeout=56)
        if reply.returncode or len(reply.stdout) > 16384 or len(reply.stderr) > 1024:
            raise ValueError('capability_failed')
        result = json.loads(reply.stdout)
        if not isinstance(result, dict):
            raise ValueError('capability_failed')
        return result
    finally:
        os.close(lock)

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        reason=str(error) if isinstance(error,ValueError) and str(error) in ['invalid_request','binding_unavailable','capability_failed','access_busy','budget_busy','budget_exhausted','budget_unavailable'] else 'capability_unavailable'
        result={'schemaVersion':1,'status':'blocked','reasonCode':reason}
        if not isinstance(error,CaptureAttemptError) and reason in ['invalid_request','binding_unavailable','access_busy','budget_busy','budget_exhausted','budget_unavailable']:result['nativeInvocations']=0
        else:result['nativeInvocations']='UNKNOWN_IF_EXPORT_REQUESTED'
        print(json.dumps(result),file=sys.stderr)
        sys.exit(2)
