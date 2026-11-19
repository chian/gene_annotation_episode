"""Private original native attempt file, scratch and identity helpers."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.local_job_worker import allocated_bytes
from gene_annotation_episode.episodic_workflow.episode_support.records.local_execution.native_record_identity import finite_json_copy, native_record_digest

_IDENTITY_FIELDS = {"run_id", "episode_id", "resource_id", "execution_id",
    "attempt_id", "operation_key", "requested_job_sha256"}

def _now():
    return datetime.now(timezone.utc).isoformat()

def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
        allow_nan=False, indent=2) + "\n").encode("utf-8")

def _atomic_new(path, value):
    """Publish fully written bytes without replacing an existing record."""
    temporary = path.with_name("." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(_encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _regular_reader(path):
    # O_NONBLOCK prevents a FIFO supplied as a file from hanging validation.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("native_infernal_regular_file_required")
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise

def _read_json(path, *, sealed=False):
    with _regular_reader(path) as stream:
        raw = stream.read()
    value = finite_json_copy(json.loads(raw))
    if sealed and raw != _encoded(value):
        raise ValueError("native_infernal_sealed_record_bytes_changed")
    return value

def _digest_file(path):
    hasher, size = hashlib.sha256(), 0
    with _regular_reader(path) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            hasher.update(block)
    return size, hasher.hexdigest()

def _absolute_directory(value):
    if (type(value) is not str or not Path(value).is_absolute()
            or str(Path(value)) != value or ".." in Path(value).parts
            or value == "/" or any(c in value for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_infernal_absolute_attempt_directory_required")
    root = Path(value)
    if root.resolve() != root or root.is_symlink():
        raise ValueError("native_infernal_attempt_symlink_forbidden")
    if root.exists() and not root.is_dir():
        raise ValueError("native_infernal_attempt_directory_required")
    return root

def _validate_identity(identity, request):
    if (type(identity) is not dict or set(identity) != _IDENTITY_FIELDS
            or any(type(v) is not str or not v or "\0" in v for v in identity.values())):
        raise ValueError("native_infernal_complete_attempt_identity_required")
    if identity["requested_job_sha256"] != native_record_digest(request):
        raise ValueError("native_infernal_requested_job_digest_mismatch")
    if identity["attempt_id"] != native_record_digest(identity["operation_key"]):
        raise ValueError("native_infernal_attempt_operation_identity_conflict")

def _confined_file(root, relative):
    if (type(relative) is not str or not relative or PurePosixPath(relative).is_absolute()
            or str(PurePosixPath(relative)) != relative or relative == "."
            or ".." in relative.split("/") or any(c in relative for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_infernal_artifact_path_escape")
    path = root / relative
    if path.resolve() != path or path.is_symlink() or not path.is_relative_to(root):
        raise ValueError("native_infernal_artifact_path_escape")
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("native_infernal_artifact_not_regular_file")
    return path

class _ScratchLimit(Exception):
    def __init__(self, observed, limit):
        self.observed, self.limit = observed, limit
        super().__init__("native_infernal_scratch_limit")

def _scratch(root, policy, additional=0):
    observed = allocated_bytes(root) + additional
    if observed > policy["scratch_bytes"]:
        raise _ScratchLimit(observed, policy["scratch_bytes"])

def _environment(job, root):
    return {**job["environment"], "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"),
        "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache")}

def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None

