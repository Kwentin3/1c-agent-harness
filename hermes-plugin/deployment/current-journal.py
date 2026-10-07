#!/usr/bin/python3
"""Fixed SSH capability for one admitted demo journal; no shell or path input."""
import base64, datetime, hashlib, json, os, re, signal, subprocess, sys, uuid
from pathlib import Path

REFERENCE = 'd2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c'
REFERENCE_IMAGE = 'sha256:69f919497cada9a8611f3de61df902d9f94bf20f84552ef5bd93125c38608ef9'
WORKER_IMAGE = 'sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488'
RUNTIME_HOST = os.environ.get('CURRENT_JOURNAL_RUNTIME_ROOT','')
RUNTIME_TARGET = '/opt/admitted-ibcmd'
BINARY_SHA256 = '62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7'
VRD_SHA256 = 'e5406c8e7352b43c6499e2ff4fe189c9b239fe045eb0ac46de2960555850ac7d'
LOCK_FILE = str(Path(__file__).resolve().with_name('access.lock'))

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
assert os.getuid()==10001 and os.getgid()==33
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

def docker_args(pid, name):
    source = f'/proc/{pid}/root/var/lib/1c/ib/1Cv8Log'
    return ['/usr/bin/docker', 'run', '-i', '--rm', '--pull', 'never', '--name', name,
            '--label', 'one-c-access=issue94', '--network', 'none', '--read-only',
            '--user', '10001:33', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--pids-limit', '128', '--memory', '256m', '--cpus', '1', '--log-driver', 'none',
            '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=33554432,uid=10001,gid=33,mode=0700',
            '--mount', f'type=bind,src={source},dst=/source/journal,readonly,bind-recursive=disabled',
            '--mount', f'type=bind,src={RUNTIME_HOST},dst={RUNTIME_TARGET},readonly,bind-recursive=disabled',
            '--env', 'TZ=UTC', '--env', 'HOME=/work/home', '--env', 'TMPDIR=/work/tmp',
            '--entrypoint', '/usr/bin/python3', WORKER_IMAGE, '-I', '-B', '-c', WORKER]

def main():
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    match = re.fullmatch(r'current-journal-v1 ([A-Za-z0-9+/=]{1,4096})', command)
    if not match:
        raise ValueError('invalid_request')
    try:
        value = admit(json.loads(base64.b64decode(match[1], validate=True)))
    except (ValueError,UnicodeError):
        raise ValueError('invalid_request') from None
    runtime=Path(RUNTIME_HOST)
    # Docker resolves this trusted root-owned binding; SSH UID need not traverse it.
    if not runtime.is_absolute() or ',' in RUNTIME_HOST:
        raise ValueError('binding_unavailable')
    import fcntl
    lock = os.open(LOCK_FILE,os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('access_busy') from None
    inspected = json.loads(subprocess.check_output(['/usr/bin/docker', 'inspect', REFERENCE], timeout=5))[0]
    if inspected['Id'] != REFERENCE or inspected['Image'] != REFERENCE_IMAGE or not inspected['State']['Running']:
        raise ValueError('binding_unavailable')
    pid = inspected['State']['Pid']
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
    name = 'issue94-journal-' + uuid.uuid4().hex
    process = None
    def interrupted(signum, frame):
        raise SystemExit(128+signum)
    for signum in [signal.SIGTERM, signal.SIGHUP, signal.SIGINT]:
        signal.signal(signum, interrupted)
    try:
        process = subprocess.Popen(docker_args(pid, name), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(json.dumps(value).encode(), timeout=40)
        if process.returncode:
            raise ValueError('capability_failed')
        result = json.loads(stdout)
        if result['sourceDirectory'] != source['journalDirectory']:
            raise ValueError('binding_unavailable')
        result['sourceBinding'] = {'referenceId':REFERENCE,'referenceImage':REFERENCE_IMAGE,
            'referenceHostPid':pid,'referenceStartedAt':inspected['State']['StartedAt'],
            'vrdSha256':VRD_SHA256,'currentIbPath':'/var/lib/1c/ib','journalPath':'/var/lib/1c/ib/1Cv8Log','sourceProbe':source}
        print(json.dumps(result,sort_keys=True))
    finally:
        # Docker owns the task cgroup. Remove this unique helper only, never the reference.
        subprocess.run(['/usr/bin/docker','rm','--force',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        if process is not None and process.poll() is None:
            process.kill();process.wait(timeout=5)

if __name__ == '__main__':
    try:
        main()
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        reason=str(error) if isinstance(error,ValueError) and str(error) in ['invalid_request','binding_unavailable','capability_failed','access_busy'] else 'capability_unavailable'
        result={'schemaVersion':1,'status':'blocked','reasonCode':reason}
        if reason in ['invalid_request','binding_unavailable','access_busy']:result['nativeInvocations']=0
        else:result['nativeInvocations']='UNKNOWN_IF_EXPORT_REQUESTED'
        print(json.dumps(result),file=sys.stderr)
        sys.exit(2)
