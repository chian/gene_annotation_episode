"""Finite restriction capture/read worker; callers own authority and resources.

Native and saved modes retain complete independent files before reading. Saved
mode imports no native producer and makes no catalog refresh or search. Counts
and coordinates belong exclusively to restriction_mapping_readers.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from .restriction_mapping_contracts import (
    restriction_canonical, restriction_digest, validate_restriction_record,
)
from .restriction_mapping_readers import read_restriction_mapping


_NATIVE_FIELDS = frozenset(("version", "mode", "sequence", "selected_sequence",
                           "enzyme_selection", "topology"))
_SAVED_FIELDS = frozenset(("version", "mode", "native_file", "catalog_file", "selected_sequence"))
_MANIFEST_FIELDS = frozenset(("version", "mode", "request_sha256", "status", "native_file",
    "catalog_file", "mapping_file", "native_state", "reader_state", "failure"))
_PHASE_CODES = {
    "request": frozenset(("request_invalid",)),
    "native": frozenset(("native_exception", "native_record_invalid")),
    "capture": frozenset(("saved_native_unavailable", "saved_catalog_unavailable", "saved_file_conflict",
                           "saved_json_invalid", "native_record_invalid", "output_capture_failed")),
    "read": frozenset(("reader_exception", "mapping_record_invalid")),
}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def validate_restriction_worker_request(value):
    """Closed, detached, finite validation; no paths are read here."""
    try:
        restriction_canonical(value)
        _require(type(value) is dict and value.get("version") == "restriction_worker_request_v1",
                 "request_invalid")
        mode = value.get("mode")
        _require(mode in ("native", "saved") and set(value) ==
                 (_NATIVE_FIELDS if mode == "native" else _SAVED_FIELDS), "request_invalid")
        validate_restriction_record("SequenceBinding", value["selected_sequence"])
        if mode == "native":
            _require(type(value["sequence"]) is str and value["topology"] in ("linear", "circular"),
                     "request_invalid")
            validate_restriction_record("EnzymeSelection", value["enzyme_selection"])
        else:
            validate_restriction_record("FilePin", value["native_file"])
            if value["catalog_file"] is not None:
                validate_restriction_record("FilePin", value["catalog_file"])
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise ValueError("request_invalid") from error
    return deepcopy(value)


def validate_restriction_worker_manifest(value):
    """Validate retained-file/state relationships without doing file I/O."""
    try:
        restriction_canonical(value)
        _require(type(value) is dict and set(value) == _MANIFEST_FIELDS
            and value["version"] == "restriction_worker_manifest_v1"
            and value["mode"] in ("native", "saved")
            and type(value["request_sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["request_sha256"]) is not None
            and value["status"] in ("complete", "partial", "failed", "invalid")
            and value["native_state"] in ("not_started", "returned", "failed", "unavailable")
            and value["reader_state"] in ("not_started", "returned", "failed"), "manifest_invalid")
        paths = []
        for field in ("native_file", "catalog_file", "mapping_file"):
            if value[field] is not None:
                paths.append(validate_restriction_record("FilePin", value[field])["path"])
        _require(len(paths) == len(set(paths)), "manifest_invalid")
        failure = value["failure"]
        if failure is not None:
            _require(type(failure) is dict and set(failure) == {"phase", "code", "exception"}
                and failure["phase"] in _PHASE_CODES
                and failure["code"] in _PHASE_CODES[failure["phase"]], "manifest_invalid")
            if failure["exception"] is not None:
                validate_restriction_record("NativeException", failure["exception"])
        _require(value["catalog_file"] is None or value["native_file"] is not None, "manifest_invalid")
        if value["mapping_file"] is not None:
            _require(value["native_file"] is not None and value["reader_state"] == "returned", "manifest_invalid")
        if value["reader_state"] == "returned" and value["mapping_file"] is None:
            _require(failure is not None and failure["code"] == "output_capture_failed", "manifest_invalid")
        if value["reader_state"] == "failed":
            _require(value["mapping_file"] is None and failure is not None
                and failure["phase"] == "read", "manifest_invalid")
        if value["status"] == "complete":
            _require(len(paths) == 3 and value["native_state"] == "returned"
                and value["reader_state"] == "returned" and failure is None, "manifest_invalid")
        if value["status"] == "partial":
            _require(value["native_file"] is not None, "manifest_invalid")
        if value["status"] == "invalid":
            _require(value["mapping_file"] is not None and failure is None, "manifest_invalid")
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise ValueError("manifest_invalid") from error
    return deepcopy(value)


def _exception(error):
    return {"module": type(error).__module__, "class": type(error).__name__, "message": str(error)}


def _strict_json(raw):
    def pairs(rows):
        value = {}
        for key, child in rows:
            _require(key not in value, "saved_json_invalid")
            value[key] = child
        return value

    def invalid(_):
        raise ValueError("saved_json_invalid")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
        restriction_canonical(value)
    except (UnicodeError, ValueError, TypeError, RecursionError) as error:
        raise ValueError("saved_json_invalid") from error
    return value


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_regular(path, expected=None):
    """Read one pinned descriptor, detecting replacement or writes during capture."""
    before_path = os.stat(path, follow_symlinks=False)
    _require(stat.S_ISREG(before_path.st_mode), "saved_file_conflict")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _require(stat.S_ISREG(before.st_mode) and _stamp(before) == _stamp(before_path), "saved_file_conflict")
        raw = stream.read()
        after = os.fstat(stream.fileno())
        after_path = os.stat(path, follow_symlinks=False)
    _require(_stamp(before) == _stamp(after) == _stamp(after_path), "saved_file_conflict")
    if expected is not None:
        _require(len(raw) == expected["size_bytes"]
            and hashlib.sha256(raw).hexdigest() == expected["sha256"], "saved_file_conflict")
    return raw


class _Output:
    """Fresh directory plus exclusive complete-file publication, without cleanup."""
    def __init__(self, directory):
        supplied = Path(directory).absolute()
        # Resolve the existing parent, never a pre-existing or dangling output alias.
        self.path = supplied.parent.resolve(strict=True) / supplied.name
        self.path.mkdir(mode=0o700, exist_ok=False)
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.identity = (os.fstat(self.fd).st_dev, os.fstat(self.fd).st_ino)

    def close(self):
        os.close(self.fd)

    def _check(self):
        info = os.stat(self.path, follow_symlinks=False)
        _require(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == self.identity,
                 "output_capture_failed")

    def write(self, name, raw):
        self._check()
        temporary = "." + name + "." + uuid.uuid4().hex + ".partial"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=self.fd)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # link is exclusive, unlike replace: a retained destination is never overwritten.
        os.link(temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False)
        os.unlink(temporary, dir_fd=self.fd)
        os.fsync(self.fd)
        self._check()
        return validate_restriction_record("FilePin", {"path": str(self.path / name),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})


def _json_bytes(value):
    return (restriction_canonical(value) + "\n").encode("utf-8")


def _failed(manifest, phase, code, error):
    manifest["failure"] = {"phase": phase, "code": code, "exception": _exception(error)}
    manifest["status"] = "partial" if manifest["native_file"] is not None else "failed"


def _saved_file(pin, *, missing_code):
    try:
        raw = _read_regular(pin["path"], pin)
    except FileNotFoundError as error:
        raise _SavedError(missing_code, error) from error
    except (OSError, ValueError) as error:
        raise _SavedError("saved_file_conflict", error) from error
    try:
        return raw, _strict_json(raw)
    except ValueError as error:
        raise _SavedError("saved_json_invalid", error) from error


class _SavedError(Exception):
    def __init__(self, code, original):
        self.code, self.original = code, original
        super().__init__(code)


def run_restriction_worker(request, *, output_directory):
    """Execute the selected finite mode once and retain independent complete outputs."""
    request = validate_restriction_worker_request(request)
    output = _Output(output_directory)
    manifest = {"version": "restriction_worker_manifest_v1", "mode": request["mode"],
        "request_sha256": restriction_digest(request), "status": "failed",
        "native_file": None, "catalog_file": None, "mapping_file": None,
        "native_state": "not_started", "reader_state": "not_started", "failure": None}
    try:
        native, catalog = None, None
        if request["mode"] == "native":
            try:
                from .restriction_mapping_native import run_restriction_mapping
                native = run_restriction_mapping(request["sequence"],
                    sequence_binding=request["selected_sequence"],
                    enzyme_selection=request["enzyme_selection"], topology=request["topology"])
            except Exception as error:
                manifest["native_state"] = "failed"
                _failed(manifest, "native", "native_exception", error)
            else:
                try:
                    native = validate_restriction_record("NativeResult", native)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    manifest["native_state"] = "failed"
                    _failed(manifest, "native", "native_record_invalid", error)
                else:
                    manifest["native_state"] = native["batch_state"]
                    catalog = native["catalog"]
                    try:
                        manifest["native_file"] = output.write("native.json", _json_bytes(native))
                        if catalog is not None:
                            manifest["catalog_file"] = output.write("catalog.json", _json_bytes(catalog))
                    except Exception as error:
                        _failed(manifest, "capture", "output_capture_failed", error)
        else:
            try:
                raw, native = _saved_file(request["native_file"], missing_code="saved_native_unavailable")
                if type(native) is not dict or native.get("version") != "restriction_mapping_native_v1":
                    raise _SavedError("native_record_invalid", ValueError("native_record_invalid"))
                manifest["native_state"] = (native.get("batch_state") if native.get("batch_state")
                    in ("not_started", "returned", "failed") else "unavailable")
                manifest["native_file"] = output.write("native.json", raw)
                if request["catalog_file"] is not None:
                    raw, catalog = _saved_file(request["catalog_file"], missing_code="saved_catalog_unavailable")
                    manifest["catalog_file"] = output.write("catalog.json", raw)
            except _SavedError as error:
                if manifest["native_file"] is None:
                    manifest["native_state"] = "unavailable"
                _failed(manifest, "capture", error.code, error.original)
            except Exception as error:
                _failed(manifest, "capture", "output_capture_failed", error)
        if manifest["failure"] is None:
            try:
                mapping = read_restriction_mapping(native,
                    selected_sequence=request["selected_sequence"], enzyme_catalog=catalog)
            except Exception as error:
                manifest["reader_state"] = "failed"
                _failed(manifest, "read", "reader_exception", error)
            else:
                try:
                    mapping = validate_restriction_record("MappingResult", mapping)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    manifest["reader_state"] = "failed"
                    _failed(manifest, "read", "mapping_record_invalid", error)
                else:
                    manifest["reader_state"] = "returned"
                    try:
                        manifest["mapping_file"] = output.write("mapping.json", _json_bytes(mapping))
                        manifest["status"] = {"complete": "complete", "partial": "partial",
                            "invalid": "invalid", "unavailable": "failed"}[mapping["status"]]
                    except Exception as error:
                        _failed(manifest, "capture", "output_capture_failed", error)
        manifest = validate_restriction_worker_manifest(manifest)
        output.write("manifest.json", _json_bytes(manifest))
        return manifest
    finally:
        output.close()


def main():
    try:
        if len(sys.argv) != 3:
            raise ValueError("request_invalid")
        request = _strict_json(_read_regular(sys.argv[1]))
        request = validate_restriction_worker_request(request)
    except (OSError, ValueError, TypeError, RecursionError):
        sys.stderr.write('{"phase":"request","code":"request_invalid"}\n')
        return 2
    try:
        result = run_restriction_worker(request, output_directory=sys.argv[2])
    except Exception:
        # Complete prior output files remain available even if final publication fails.
        sys.stderr.write('{"phase":"capture","code":"output_capture_failed"}\n')
        return 3
    return 0 if result["status"] in ("complete", "partial") else 2 if result["status"] == "invalid" else 3


__all__ = ["run_restriction_worker", "validate_restriction_worker_request",
           "validate_restriction_worker_manifest"]


if __name__ == "__main__":
    raise SystemExit(main())
