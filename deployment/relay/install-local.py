#!/usr/bin/env python3
"""Preview/apply the fixed local adapters; source owners are installed separately."""
import argparse
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import tempfile

CONFIG = Path('/etc/one-c-harness/relay-local.json')
SUDOERS = Path('/etc/sudoers.d/one-c-harness-relay-local')
CONTROLLER = Path('/usr/local/libexec/one-c-harness-local-controller')
EXECUTABLES = [Path('/usr/local/bin') / name for name in (
    'one-c-harness-local', 'one-c-harness-local-capture', 'one-c-harness-local-logging',
    'one-c-harness-local-exporter')] + [CONTROLLER]
SCRIPT = 'deployment/relay/one-c-harness-local'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe file path')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('expected regular single-link file')
    return path.read_bytes(), info


def state(path):
    if not path.exists() and not path.is_symlink():
        return None
    raw, info = read(path)
    return {'data': base64.b64encode(raw).decode(), 'sha256': sha(raw),
            'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}


def image(raw, mode):
    return {'data': base64.b64encode(raw).decode(), 'sha256': sha(raw), 'uid': 0, 'gid': 0, 'mode': mode}


def write(path, item):
    if item is None:
        path.unlink()
        return
    raw = base64.b64decode(item['data'], validate=True)
    if sha(raw) != item['sha256']:
        raise ValueError('receipt payload hash differs')
    fd, temporary = tempfile.mkstemp(prefix='.one-c-local-', dir=path.parent)
    try:
        os.fchown(fd, item['uid'], item['gid'])
        os.fchmod(fd, item['mode'])
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if state(path) != item:
            raise ValueError('installed readback differs')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_sudoers(raw):
    with tempfile.NamedTemporaryFile(prefix='one-c-local-sudoers-', delete=False) as stream:
        stream.write(raw)
        name = stream.name
    try:
        subprocess.run(['/usr/sbin/visudo', '-cf', name], check=True, capture_output=True)
    finally:
        os.unlink(name)


def load_adapter(path):
    loader = importlib.machinery.SourceFileLoader('one_c_relay_install_adapter', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def plan(bundle, lock_path, candidate, relay_user):
    lock = json.loads(read(lock_path)[0])
    if (lock.get('repository') != 'https://github.com/Kwentin3/1c-agent-harness.git'
            or not re.fullmatch('[0-9a-f]{40}', lock.get('commit', ''))):
        raise ValueError('invalid existing source lock')
    script = bundle / SCRIPT
    raw = read(script)[0]
    if sha(raw) != lock['files'][SCRIPT]:
        raise ValueError('adapter differs from existing source lock')
    config_raw = read(candidate)[0]
    # Reuse the adapter's configuration owner; no second config schema or pin
    # verifier. The maintained source installer must have finished beforehand.
    adapter = load_adapter(script)
    adapter.CONFIG = candidate
    config = adapter.configuration()
    for key, relative in (('journalControllerSha256', 'deployment/goal91/current-journal.py'),
                          ('engineeringControllerSha256', 'deployment/goal91/engineering-shell.py')):
        if config[key] != lock['files'][relative]:
            raise ValueError('installed owner differs from bundle lock')
    source_release = json.loads(read(Path(config['source']) / 'one_c_harness/release.json')[0])
    if source_release['artifactId'] != lock['artifact_id']:
        raise ValueError('host source generation differs from source lock')
    if not re.fullmatch('[a-z_][a-z0-9_-]*', relay_user):
        raise ValueError('invalid Relay account')
    user = pwd.getpwnam(relay_user)
    if user.pw_uid == 0:
        raise ValueError('Relay account must be unprivileged')
    sudoers = (relay_user + ' ALL=(root) NOPASSWD: NOSETENV: ' + str(CONTROLLER) + ' ""\n').encode()
    validate_sudoers(sudoers)
    desired = {str(path): image(raw, 0o555) for path in EXECUTABLES}
    desired[str(CONFIG)] = image(config_raw, 0o444)
    desired[str(SUDOERS)] = image(sudoers, 0o440)
    entries = [{'path': path, 'before': state(Path(path)), 'after': item} for path, item in desired.items()]
    cache = Path(config['workspace'])
    if cache.exists() or cache.is_symlink():
        info = cache.lstat()
        if cache.is_symlink() or not stat.S_ISDIR(info.st_mode) or (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (user.pw_uid, user.pw_gid, 0o700):
            raise ValueError('existing cache owner/mode differs')
    return {'schemaVersion': 1, 'status': 'PREVIEW', 'sourceCommit': lock['commit'],
            'adapterSha256': sha(raw), 'relayUser': relay_user,
            'cache': {'path': str(cache), 'uid': user.pw_uid, 'gid': user.pw_gid, 'created': not cache.exists()},
            'entries': entries, 'createdDirectories': []}


def save_receipt(path, receipt):
    write(path, image((json.dumps(receipt, indent=2) + '\n').encode(), 0o600))


def ensure_directory(path, receipt):
    if path.exists():
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('unsafe install directory')
        return
    ensure_directory(path.parent, receipt)
    path.mkdir(mode=0o755)
    os.chown(path, 0, 0)
    receipt['createdDirectories'].append(str(path))


def apply(receipt, receipt_path):
    if os.geteuid() != 0 or receipt_path.exists():
        raise ValueError('root and a new private receipt path required')
    parent = receipt_path.parent.stat()
    if (parent.st_uid, stat.S_IMODE(parent.st_mode)) != (0, 0o700):
        raise ValueError('receipt directory must be root0700')
    receipt['status'] = 'PREPARED'
    save_receipt(receipt_path, receipt)
    cache = receipt['cache']
    if cache['created']:
        path = Path(cache['path'])
        ensure_directory(path.parent, receipt)
        save_receipt(receipt_path, receipt)
        path.mkdir(mode=0o700)
        os.chown(path, cache['uid'], cache['gid'])
    for entry in receipt['entries']:
        target = Path(entry['path'])
        if state(target) != entry['before']:
            raise ValueError('target changed before installation')
        ensure_directory(target.parent, receipt)
        save_receipt(receipt_path, receipt)
        write(target, entry['after'])
    receipt['status'] = 'APPLIED'
    save_receipt(receipt_path, receipt)


def rollback(receipt, apply_changes=False):
    allowed = {str(path) for path in EXECUTABLES} | {str(CONFIG), str(SUDOERS)}
    if {entry['path'] for entry in receipt['entries']} != allowed:
        raise ValueError('receipt scope differs')
    for entry in receipt['entries']:
        if state(Path(entry['path'])) not in (entry['before'], entry['after']):
            raise ValueError('target changed since installation; preserve and inspect')
    if apply_changes:
        if os.geteuid() != 0:
            raise ValueError('rollback apply requires root')
        # Revoke only this entry, restore files, then restore any previous rule.
        previous_rule = next(entry['before'] for entry in receipt['entries'] if entry['path'] == str(SUDOERS))
        if SUDOERS.exists():
            SUDOERS.unlink()
        for entry in receipt['entries']:
            if entry['path'] == str(SUDOERS):
                continue
            if state(Path(entry['path'])) != entry['before']:
                write(Path(entry['path']), entry['before'])
        if previous_rule is not None:
            write(SUDOERS, previous_rule)
        # Preserve cache and retained results. Remove only empty task-created
        # parent directories; rmdir never removes nested contents.
        for name in reversed(receipt['createdDirectories']):
            try:
                Path(name).rmdir()
            except OSError:
                pass
    return {'status': 'ROLLED_BACK' if apply_changes else 'ROLLBACK_PREVIEW',
            'cacheRetained': receipt['cache']['path'], 'sourceCommit': receipt['sourceCommit']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--lock', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--relay-user')
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.rollback:
        raw, info = read(args.receipt)
        if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (0, 0, 0o600):
            raise ValueError('rollback receipt must be root0600')
        result = rollback(json.loads(raw), args.apply)
    else:
        if not all((args.bundle, args.lock, args.config, args.relay_user)):
            parser.error('install requires --bundle --lock --config --relay-user')
        receipt = plan(args.bundle, args.lock, args.config, args.relay_user)
        if args.apply:
            apply(receipt, args.receipt)
        result = {key: receipt[key] for key in ('status', 'sourceCommit', 'adapterSha256', 'relayUser')}
        result['files'] = [{'path': entry['path'], 'sha256': entry['after']['sha256'], 'mode': entry['after']['mode']} for entry in receipt['entries']]
        result['cache'] = receipt['cache']
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
