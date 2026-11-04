"""Bounded capture of complete native files into the existing Store.

These records establish byte custody only. The caller owns the original job,
manifest, access authority, writer closure, durable receipt and replay. This
module makes no scientific interpretation and grants no authority or credit.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
from typing import Literal, TypedDict
import unicodedata

from .domain import ContractError
from .materials import artifact_file, _verified_artifact_path


class NativeFileIdentity(TypedDict):
    artifact_ref: str
    sha256: str
    size_bytes: int
    format: str


class NativeFileDeclaration(TypedDict):
    relative_path: str
    format: str
    state: Literal["present", "absent"]
    sha256: str | None
    size_bytes: int | None


class NativeFileCapture(TypedDict):
    declared: NativeFileDeclaration
    observed: NativeFileIdentity | None
    outcome: Literal["verified", "declared_absent", "digest_mismatch", "unavailable"]
    failure: Literal["capture_file_unavailable", "capture_file_digest_mismatch"] | None


ErrorCode = Literal[
    "invalid_capture_path", "invalid_file_declaration", "invalid_file_identity",
    "capture_file_unavailable", "retained_artifact_unavailable", "retained_artifact_mismatch",
]


class NativeFileCaptureError(ValueError):
    code: ErrorCode

    def __init__(self, code: ErrorCode):
        self.code = code
        super().__init__(code)


_IDENTITY_FIELDS = frozenset(NativeFileIdentity.__annotations__)
_DECLARATION_FIELDS = frozenset(NativeFileDeclaration.__annotations__)
_METADATA_FIELDS = frozenset({"id", "record_type", "sha256", "size", "media_type"})
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _require(condition: bool, code: ErrorCode) -> None:
    if not condition:
        raise NativeFileCaptureError(code)


def _label(value) -> bool:
    return type(value) is str and bool(value) and not any(
        unicodedata.category(char) == "Cc" for char in value)


def _digest(value) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _size(value) -> bool:
    return type(value) is int and value >= 0


def _path(value, *, absolute: bool) -> PurePosixPath:
    _require(type(value) is str and bool(value) and
        not any(char in value for char in "\0\n\r\\"), "invalid_capture_path")
    path = PurePosixPath(value)
    _require(str(path) == value and ".." not in path.parts and value not in (".", "/")
        and (path.root == "/" if absolute else not path.is_absolute()), "invalid_capture_path")
    return path


def _identity(value) -> NativeFileIdentity:
    _require(type(value) is dict and set(value) == _IDENTITY_FIELDS, "invalid_file_identity")
    _require(_digest(value["sha256"]) and _size(value["size_bytes"])
        and _label(value["format"]) and type(value["artifact_ref"]) is str
        and value["artifact_ref"] == "artifact_" + value["sha256"], "invalid_file_identity")
    return dict(value)


def _declaration(value) -> NativeFileDeclaration:
    _require(type(value) is dict and set(value) == _DECLARATION_FIELDS, "invalid_file_declaration")
    _path(value["relative_path"], absolute=False)
    _require(_label(value["format"]) and type(value["state"]) is str
        and value["state"] in ("present", "absent"), "invalid_file_declaration")
    if value["state"] == "present":
        _require(_digest(value["sha256"]) and _size(value["size_bytes"]), "invalid_file_declaration")
    else:
        _require(value["sha256"] is None and value["size_bytes"] is None, "invalid_file_declaration")
    return dict(value)


@contextmanager
def _retention_errors():
    """Translate known storage failures without hiding programming errors."""
    try:
        yield
    except ContractError as error:
        if str(error) in ("unknown_reference", "unknown_artifact"):
            raise NativeFileCaptureError("retained_artifact_unavailable") from error
        if str(error) in ("artifact_digest_mismatch", "wrong_reference_type"):
            raise NativeFileCaptureError("retained_artifact_mismatch") from error
        raise
    except OSError as error:
        raise NativeFileCaptureError("retained_artifact_unavailable") from error
    except sqlite3.DatabaseError as error:
        if isinstance(error, sqlite3.ProgrammingError):
            raise
        raise NativeFileCaptureError("retained_artifact_unavailable") from error


def _metadata(store, reference: str) -> dict:
    _require(type(reference) is str and reference.startswith("artifact_")
        and _digest(reference.removeprefix("artifact_")), "invalid_file_identity")
    with _retention_errors():
        metadata = store._require(reference, {"artifact"})
    _require(type(metadata) is dict and set(metadata) == _METADATA_FIELDS,
        "retained_artifact_mismatch")
    _require(metadata["record_type"] == "artifact" and metadata["id"] == reference
        and _digest(metadata["sha256"]) and reference == "artifact_" + metadata["sha256"]
        and _size(metadata["size"]) and _label(metadata["media_type"]), "retained_artifact_mismatch")
    return dict(metadata)


@contextmanager
def _producer_file(directory: PurePosixPath, relative: PurePosixPath):
    with ExitStack() as stack:
        # Only path opening/fstat failures mean producer unavailability. The
        # copier and retained verification below have their own error boundary.
        try:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            fd = os.open("/", flags)
            stack.callback(os.close, fd)
            for part in (*directory.parts[1:], *relative.parts[:-1]):
                fd = os.open(part, flags, dir_fd=fd)
                stack.callback(os.close, fd)
            fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            stack.callback(os.close, fd)
            _require(stat.S_ISREG(os.fstat(fd).st_mode), "capture_file_unavailable")
        except OSError as error:
            raise NativeFileCaptureError("capture_file_unavailable") from error
        # The mutable producer directory entry is never looked up again.
        yield Path("/proc/self/fd") / str(fd)


def retained_native_file(store, identity: NativeFileIdentity) -> Path:
    """Verify only the retained identity, metadata, complete digest and size.

The returned Store path is a verified location, not a lock against subsequent
external mutation. The caller must keep its retained storage stable while read.
"""
    identity = _identity(identity)
    metadata = _metadata(store, identity["artifact_ref"])
    _require(metadata["sha256"] == identity["sha256"]
        and metadata["size"] == identity["size_bytes"], "retained_artifact_mismatch")
    expected = store.path / "artifacts" / identity["sha256"][:2] / identity["sha256"]
    with _retention_errors():
        # Avoid opening an already nonregular or symlinked retained node.
        initial = expected.lstat()
        _require(stat.S_ISREG(initial.st_mode), "retained_artifact_unavailable")
        _require(initial.st_size == identity["size_bytes"], "retained_artifact_mismatch")
        path = _verified_artifact_path(store, identity["artifact_ref"])
        _require(isinstance(path, Path) and path == expected, "retained_artifact_mismatch")
        current = path.lstat()
        _require(stat.S_ISREG(current.st_mode), "retained_artifact_unavailable")
        _require(current.st_size == identity["size_bytes"], "retained_artifact_mismatch")
    return path


def capture_native_file(
    store, *, directory: str, relative_path: str, format: str,
    media_type: str = "application/octet-stream",
) -> NativeFileIdentity:
    """Retain the complete bytes of one pinned regular producer file.

Producer-open failures are ``capture_file_unavailable``. Storage/copy failures
are retained-artifact failures; they must not be presented as producer absence.
The format and media type are supplied labels, never parser selection rules.
"""
    root = _path(directory, absolute=True)
    relative = _path(relative_path, absolute=False)
    _require(_label(format) and _label(media_type), "invalid_file_declaration")
    with _producer_file(root, relative) as pinned:
        with _retention_errors():
            reference = artifact_file(store, pinned, media_type)
    metadata = _metadata(store, reference)
    identity: NativeFileIdentity = {"artifact_ref": reference, "sha256": metadata["sha256"],
        "size_bytes": metadata["size"], "format": format}
    retained_native_file(store, identity)
    return identity


def capture_declared_native_files(
    store, *, directory: str, declarations: list[NativeFileDeclaration],
) -> list[NativeFileCapture]:
    """Validate the whole request, then capture each declared present file.

One detached row retains each declaration's original list position. An absent
declaration causes no producer access; a failed present file preserves other
successes. This function does not persist a receipt or implement replay.
"""
    _path(directory, absolute=True)
    _require(type(declarations) is list, "invalid_file_declaration")
    declared = [_declaration(value) for value in declarations]
    _require(len({row["relative_path"] for row in declared}) == len(declared),
        "invalid_file_declaration")
    result: list[NativeFileCapture] = []
    for declaration in declared:
        row: NativeFileCapture = {"declared": declaration, "observed": None,
            "outcome": "declared_absent", "failure": None}
        if declaration["state"] == "present":
            try:
                observed = capture_native_file(store, directory=directory,
                    relative_path=declaration["relative_path"], format=declaration["format"])
            except NativeFileCaptureError as error:
                if error.code != "capture_file_unavailable":
                    raise
                row.update(outcome="unavailable", failure="capture_file_unavailable")
            else:
                row["observed"] = observed
                equal = (observed["sha256"], observed["size_bytes"]) == (
                    declaration["sha256"], declaration["size_bytes"])
                row["outcome"] = "verified" if equal else "digest_mismatch"
                row["failure"] = None if equal else "capture_file_digest_mismatch"
        result.append(row)
    return result
