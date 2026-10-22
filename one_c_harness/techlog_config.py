"""Task-owned native logcfg.xml changes; paths/target are fixed by deployment.

One deployment-owned common state directory serializes this target's collector.
This writes configuration only: platform reload and observed logging are separate.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import xml.etree.ElementTree as ET

NAMESPACE = "http://v8.1c.ru/v8/tech-log"
PROFILES = {"errors": ("EXCP", "EXCPCNTX"), "diagnostic": ("EXCP", "EXCPCNTX", "CONN")}
MAX_CONFIG_BYTES = 1024 * 1024


class TechlogConfigError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _check_path(path):
    if not path.is_absolute() or ".." in path.parts or str(path).startswith("\\\\"):
        raise TechlogConfigError("unsafe_path")
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise TechlogConfigError("unsafe_path")


def _read_file(path, limit=MAX_CONFIG_BYTES):
    _check_path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None, None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
        raise TechlogConfigError("unsafe_file")
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise TechlogConfigError("file_changed")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise TechlogConfigError("unsafe_file")
    return data, info


def _sync_directory(path):
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _atomic(path, data, mode=0o600, owner=None):
    _check_path(path)
    fd, name = tempfile.mkstemp(prefix=".techlog-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            if os.name == "posix":
                if owner is not None:
                    os.fchown(stream.fileno(), *owner)
                os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(name, path)
        _sync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _profile(original, location, profile):
    if original and (b"<!DOCTYPE" in original.upper() or b"<!ENTITY" in original.upper()):
        raise TechlogConfigError("configuration_invalid")
    try:
        if original and original.strip():
            parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
            root = ET.fromstring(original, parser=parser)
        else:
            root = ET.Element("{" + NAMESPACE + "}config")
    except ET.ParseError:
        raise TechlogConfigError("configuration_invalid") from None
    if root.tag not in ("config", "{" + NAMESPACE + "}config"):
        raise TechlogConfigError("configuration_invalid")
    namespace = NAMESPACE if root.tag.startswith("{") else ""
    if namespace:
        ET.register_namespace("", namespace)
    tag = lambda name: "{" + namespace + "}" + name if namespace else name
    if any(child.tag == tag("log") and child.get("location") == location for child in root):
        raise TechlogConfigError("log_location_in_use")
    own = ET.SubElement(root, tag("log"), {"location": location, "history": "1"})
    for event in PROFILES[profile]:
        item = ET.SubElement(own, tag("event"))
        ET.SubElement(item, tag("eq"), {"property": "name", "value": event})
    ET.SubElement(own, tag("property"), {"name": "all"})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class TechlogConfig:
    def __init__(self, config_path, log_directory, state_directory, *, target_ref):
        self.config = Path(config_path)
        self.logs = Path(log_directory)
        self.directory = Path(state_directory)
        if not isinstance(target_ref, str) or not 1 <= len(target_ref) <= 256 or any(ord(c) < 32 for c in target_ref):
            raise TechlogConfigError("target_invalid")
        for path in (self.config, self.logs, self.directory):
            _check_path(path)
        if (self.config == self.logs or self.logs in self.config.parents
                or self.config == self.directory or self.directory in self.config.parents
                or self.logs == self.directory or self.logs in self.directory.parents
                or self.directory in self.logs.parents):
            raise TechlogConfigError("path_overlap")
        if not self.config.parent.is_dir():
            raise TechlogConfigError("configuration_parent_missing")
        for path in (self.logs, self.directory):
            if path.exists() and not path.is_dir():
                raise TechlogConfigError("unsafe_path")
        self.binding = {"targetRef": target_ref, "configPath": str(self.config),
                        "logDirectory": str(self.logs), "stateDirectory": str(self.directory)}
        self.state = self.directory / "state.json"
        self.backup = self.directory / "original.bin"
        self.lock = self.directory / "lock"

    @contextmanager
    def _locked(self, create=False):
        if create:
            for path in (self.directory, self.logs):
                _check_path(path)
                path.mkdir(mode=0o700, exist_ok=True)  # Never create unpassed parents.
        if not self.directory.exists():
            yield
            return
        _check_path(self.directory)
        info = self.directory.stat()
        if os.name == "posix" and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise TechlogConfigError("state_directory_unsafe")
        _check_path(self.lock)
        if not self.lock.exists() and not create:
            if self.state.exists() or self.backup.exists():
                raise TechlogConfigError("state_invalid")
            yield
            return
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | (os.O_CREAT if create else 0)
        fd = os.open(self.lock, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise TechlogConfigError("unsafe_file")
            try:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    raise TechlogConfigError("unsupported_lock_platform")
            except OSError:
                raise TechlogConfigError("busy") from None
            yield
        finally:
            os.close(fd)

    def _save(self, value):
        _atomic(self.state, (json.dumps(value, sort_keys=True) + "\n").encode())

    def _load(self):
        _check_path(self.backup)
        raw, _ = _read_file(self.state, 8192)
        if raw is None:
            if self.backup.exists():
                raise TechlogConfigError("orphaned_backup")
            return None, None
        try:
            value = json.loads(raw)
            if (value["schemaVersion"] != 1 or value["binding"] != self.binding
                    or value["phase"] not in ("prepared", "active", "restoring", "stopped")
                    or value["profile"] not in PROFILES or type(value["originalExists"]) is not bool
                    or not isinstance(value["captureRef"], str) or not re.fullmatch(r"capture:[0-9a-f]{32}", value["captureRef"])
                    or type(value["originalMode"]) is not int or not 0 <= value["originalMode"] <= 0o7777):
                raise ValueError
            for key in ("originalUid", "originalGid"):
                if value["originalExists"] and (type(value[key]) is not int or value[key] < 0):
                    raise ValueError
            for key in ("originalSha256", "appliedSha256"):
                if not isinstance(value[key], str) or len(value[key]) != 64:
                    raise ValueError
                int(value[key], 16)
            backup, _ = _read_file(self.backup)
            if backup is None and value["phase"] == "stopped":
                return value, None
            if backup is None or _digest(backup) != value["originalSha256"]:
                raise ValueError
            return value, backup
        except (KeyError, TypeError, ValueError):
            raise TechlogConfigError("state_invalid") from None

    def _current(self):
        return _read_file(self.config)

    def _matches(self, raw, value, which):
        if which == "original":
            return (raw is not None) == value["originalExists"] and _digest(raw or b"") == value["originalSha256"]
        return raw is not None and _digest(raw) == value["appliedSha256"]

    def _result(self, status, applied=False, **fields):
        return {"status": status, "targetRef": self.binding["targetRef"],
                "configurationApplied": applied, "platformObservation": "not_performed",
                "reloadPollHintSeconds": 60, **fields}

    def status(self):
        with self._locked():
            value, _ = self._load()
            raw, _ = self._current()
            if value is None or value["phase"] == "stopped":
                return self._result("inactive")
            if self._matches(raw, value, "applied"):
                return self._result("active", True, captureRef=value["captureRef"], profile=value["profile"])
            if value["phase"] in ("prepared", "restoring") and self._matches(raw, value, "original"):
                return self._result("prepared" if value["phase"] == "prepared" else "inactive",
                                    captureRef=value["captureRef"], profile=value["profile"])
            return self._result("conflict", reasonCode="configuration_changed",
                                captureRef=value["captureRef"], profile=value["profile"])

    def _cleanup(self, value):
        backup, _ = _read_file(self.backup)
        if backup is not None:
            if _digest(backup) != value["originalSha256"]:
                raise TechlogConfigError("state_invalid")
            self.backup.unlink()
        self.state.unlink()
        _sync_directory(self.directory)

    def start(self, profile="errors"):
        if not isinstance(profile, str) or profile not in PROFILES:
            raise TechlogConfigError("profile_invalid")
        with self._locked(create=True):
            value, backup = self._load()
            if value is not None and value["phase"] == "stopped":
                self._cleanup(value)
                value = None
            raw, info = self._current()
            if value is not None:
                if value["profile"] != profile:
                    raise TechlogConfigError("profile_in_use")
                if self._matches(raw, value, "applied") and value["phase"] in ("prepared", "active"):
                    return self._result("active", True, alreadyActive=True,
                                        captureRef=value["captureRef"], profile=value["profile"])
                if value["phase"] != "prepared" or not self._matches(raw, value, "original"):
                    return self._result("conflict", reasonCode="configuration_changed")
                applied = _profile(backup, str(self.logs), profile)
                if _digest(applied) != value["appliedSha256"]:
                    raise TechlogConfigError("state_invalid")
            else:
                applied = _profile(raw, str(self.logs), profile)
                value = {"schemaVersion": 1, "binding": self.binding, "phase": "prepared",
                         "profile": profile,
                         "captureRef": "capture:" + secrets.token_hex(16),
                         "originalExists": raw is not None, "originalSha256": _digest(raw or b""),
                         "appliedSha256": _digest(applied), "originalMode": stat.S_IMODE(info.st_mode) if info else 0o644,
                         "originalUid": info.st_uid if info else None, "originalGid": info.st_gid if info else None}
                _atomic(self.backup, raw or b"")
                self._save(value)  # Durable backup and intent BEFORE config publication.
            latest, _ = self._current()
            if not self._matches(latest, value, "original"):
                return self._result("conflict", reasonCode="configuration_changed")
            owner = (value["originalUid"], value["originalGid"]) if value["originalExists"] else None
            _atomic(self.config, applied, value["originalMode"], owner)
            value["phase"] = "active"
            self._save(value)
            return self._result("active", True, alreadyActive=False,
                                captureRef=value["captureRef"], profile=value["profile"])

    def stop(self, *, capture_ref=None):
        with self._locked():
            value, backup = self._load()
            if value is None:
                if capture_ref is not None:
                    raise TechlogConfigError("capture_not_found")
                return self._result("inactive")
            if capture_ref is not None and capture_ref != value["captureRef"]:
                raise TechlogConfigError("capture_not_found")
            raw, _ = self._current()
            original = self._matches(raw, value, "original")
            if value["phase"] == "stopped" or (value["phase"] in ("prepared", "restoring") and original):
                value["phase"] = "stopped"
                self._save(value)
                self._cleanup(value)
                return self._result("inactive")
            if not self._matches(raw, value, "applied"):
                return self._result("conflict", reasonCode="configuration_changed")
            value["phase"] = "restoring"
            self._save(value)
            latest, _ = self._current()
            if not self._matches(latest, value, "applied"):
                return self._result("conflict", reasonCode="configuration_changed")
            if value["originalExists"]:
                _atomic(self.config, backup, value["originalMode"], (value["originalUid"], value["originalGid"]))
            else:
                self.config.unlink()
                _sync_directory(self.config.parent)
            value["phase"] = "stopped"
            self._save(value)
            self._cleanup(value)
            return self._result("inactive")
