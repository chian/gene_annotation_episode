"""Private A110 native file capture and retained-byte verification."""
import hashlib
import os
from pathlib import Path
import tempfile
from .domain import ContractError


def artifact_file(store, path, media_type="application/octet-stream"):
    """Capture a file with bounded memory before attempting its representation."""
    digest, size = hashlib.sha256(), 0
    fd, temporary = tempfile.mkstemp(dir=store.path / "artifacts", prefix=".capture-")
    try:
        with os.fdopen(fd, "wb") as output, Path(path).open("rb") as original:
            for chunk in iter(lambda: original.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        checksum = digest.hexdigest()
        directory = store.path / "artifacts" / checksum[:2]
        directory.mkdir(exist_ok=True)
        destination = directory / checksum
        if not destination.exists():
            os.replace(temporary, destination)
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        ref = "artifact_" + checksum
        store.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?)", (ref, checksum, media_type, size))
        return ref
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _verified_artifact_path(store, ref):
    """Verify retained byte identity only; callers own access authority."""
    artifact = store._require(ref, {"artifact"})
    path = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != artifact["sha256"]:
        raise ContractError("artifact_digest_mismatch")
    return path


