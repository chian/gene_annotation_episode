"""Retain one original protein attempt; replay uses only its captured artifacts.

Capture completeness describes byte custody. Native success, scientific parsing,
publication, received authority and episode credit belong to separate consumers.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
from typing import Literal, TypedDict, get_args

from .domain import ContractError
from .execution_contracts import canonical, digest, validate_target
from .materials import artifact_file, artifact_path
from .native_protein_structure_contracts import (
    ATTEMPT_DIRECTORY_NAME, BUNDLE_FILENAME, ManifestFile, NativeProteinBundle,
    NativeProteinRunPlan, validate_protein_structure_bundle,
    validate_protein_structure_requested_job, validate_protein_structure_run_plan,
)
from .protein_structure_contracts import (
    Count, FileIdentity, IssueCode, StructuredIssue, issue, same, validate_file_identity,
)


class CapturedManifestFile(TypedDict):
    manifest_index_0based: Count
    declared: ManifestFile
    observed: FileIdentity | None
    outcome: Literal["verified", "digest_mismatch", "unavailable", "declared_absent"]
    issue: StructuredIssue | None


class ProteinStructureCapture(TypedDict):
    version: Literal["native_protein_structure_capture_v1"]
    original_plan: NativeProteinRunPlan | None
    bundle_file: FileIdentity | None
    bundle_validated: bool
    files: list[CapturedManifestFile]
    failures: list[StructuredIssue]
    capture_complete: bool


VERSION = "native_protein_structure_capture_v1"
BUNDLE_FORMAT = "native_protein_structure_bundle_v1"
_CAPTURE_FIELDS = set(ProteinStructureCapture.__annotations__)
_ROW_FIELDS = set(CapturedManifestFile.__annotations__)
_ISSUE_CODES = frozenset(get_args(IssueCode))


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


def decode_protein_structure_json(data: bytes, *, canonical_bytes: bool = False):
    """Decode strict UTF-8 JSON; canonical control bytes have no trailing LF."""
    _require(type(data) is bytes and type(canonical_bytes) is bool)

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError("invalid_schema")

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        # Encoding also rejects overflowed JSON numbers and lone surrogates.
        encoded = canonical(value).encode("utf-8")
        _require(not canonical_bytes or data == encoded)
        return value
    except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error


def is_native_protein_structure_target(target: dict) -> bool:
    return (type(target) is dict and target.get("resource_kind") == "local"
        and type(target.get("assignment")) is dict
        and type(target["assignment"].get("requested_job")) is dict
        and "native_protein_structure" in target["assignment"]["requested_job"])


def _absolute(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"), "invalid_output_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts and value != "/", "invalid_output_path")
    return path


def _target(value):
    target = validate_target(value)
    _require(is_native_protein_structure_target(target), "original_commission_mismatch")
    assignment = target["assignment"]
    _require(assignment.get("resource_kind") == "local" and
        assignment.get("resource_id") == target["resource_id"], "original_commission_mismatch")
    _absolute(assignment.get("workspace"))
    _absolute(target["execution_id"])
    request = validate_protein_structure_requested_job(assignment["requested_job"])
    _require(target["request_sha256"] == digest(request), "original_commission_mismatch")
    return target


def qualify_protein_structure_target_plan(
    target: dict, plan: NativeProteinRunPlan
) -> NativeProteinRunPlan:
    """Qualify the original target/plan relationship without filesystem reads."""
    target = _target(target)
    plan = validate_protein_structure_run_plan(plan)
    owner = plan["identity"]
    _require(same(target["assignment"]["requested_job"], plan["requested_job"]), "original_commission_mismatch")
    _require(all(target[left] == owner[right] for left, right in (
        ("run_id", "run_id"), ("origin_episode_id", "episode_id"),
        ("resource_id", "resource_id"), ("execution_id", "execution_id"),
        ("request_sha256", "requested_job_sha256"))), "original_commission_mismatch")
    root = _absolute(target["assignment"]["workspace"]) / ".episode-operations" / digest({
        "run": owner["run_id"], "episode": owner["episode_id"]}) / digest(owner["operation_key"])
    _require(owner["execution_id"] == str(root / "native.json") and
        plan["attempt_directory"] == str(root / ATTEMPT_DIRECTORY_NAME), "original_commission_mismatch")
    return plan


@contextmanager
def _directory_fd(directory, *, create=False):
    """Pin every absolute directory component without resolving any symlink."""
    path = _absolute(str(directory))
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        yield fd


@contextmanager
def _regular_fd(directory_fd, relative):
    path = PurePosixPath(relative)
    _require(type(relative) is str and str(path) == relative and not path.is_absolute()
        and path.parts and ".." not in path.parts and relative != "."
        and not any(c in relative for c in "\0\n\r\\"), "invalid_output_path")
    with ExitStack() as stack:
        fd = directory_fd
        for part in path.parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=fd)
        stack.callback(os.close, fd)
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
        yield fd


@contextmanager
def _producer_file(directory, relative):
    with _directory_fd(directory) as root, _regular_fd(root, relative) as fd:
        # The shared streaming copier opens this pinned descriptor, never a
        # second lookup of the producer's mutable directory entry.
        yield Path("/proc/self/fd") / str(fd)


def _read_control(directory_fd, name):
    try:
        with _regular_fd(directory_fd, name) as fd, os.fdopen(os.dup(fd), "rb") as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def _immutable_control(directory_fd, name, value):
    data = canonical(value).encode("utf-8")
    previous = _read_control(directory_fd, name)
    if previous is not None:
        _require(previous == data, "original_commission_mismatch")
        return
    temporary = "." + name + "." + secrets.token_hex(16) + ".writing"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
        try:
            os.link(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
        except FileExistsError:
            _require(_read_control(directory_fd, name) == data, "original_commission_mismatch")
        os.fsync(directory_fd)
    finally:
        os.unlink(temporary, dir_fd=directory_fd)


def retained_protein_structure_file(store, identity: FileIdentity) -> Path:
    """Validate an exact Store artifact, never a path from the original plan."""
    identity = validate_file_identity(identity)
    try:
        metadata = store._require(identity["artifact_ref"], {"artifact"})
        _require(type(metadata) is dict and set(metadata) == {"id", "record_type", "sha256", "size", "media_type"})
        _require(metadata["record_type"] == "artifact" and type(metadata["media_type"]) is str
            and metadata["media_type"] and "\0" not in metadata["media_type"])
        _require(metadata["id"] == identity["artifact_ref"] and metadata["sha256"] == identity["sha256"]
            and type(metadata["size"]) is int and metadata["size"] == identity["byte_length"], "input_digest_mismatch")
        path = artifact_path(store, identity["artifact_ref"])
        _require(path.stat().st_size == identity["byte_length"], "input_digest_mismatch")
        return path
    except ContractError as error:
        code = "input_digest_mismatch" if str(error) == "artifact_digest_mismatch" else (
            "retained_artifact_missing" if str(error) in ("unknown_artifact", "unknown_reference") else "invalid_schema")
        raise ValueError(code) from error
    except OSError as error:
        raise ValueError("retained_artifact_missing") from error


def _capture_file(store, directory, relative, format):
    with _producer_file(directory, relative) as path:
        reference = artifact_file(store, path)
    metadata = store._require(reference, {"artifact"})
    identity = {"artifact_ref": reference, "sha256": metadata["sha256"],
        "byte_length": metadata["size"], "format": format}
    retained_protein_structure_file(store, identity)
    return identity


def _failure_code(error):
    return str(error) if str(error) in _ISSUE_CODES else (
        "capture_incomplete" if isinstance(error, OSError) else "invalid_schema")


def _bundle(store, identity, plan) -> NativeProteinBundle:
    _require(identity["format"] == BUNDLE_FORMAT)
    path = retained_protein_structure_file(store, identity)
    return validate_protein_structure_bundle(
        decode_protein_structure_json(path.read_bytes(), canonical_bytes=True), plan=plan)


def validate_protein_structure_capture(
    store, capture: ProteinStructureCapture, *, target: dict
) -> ProteinStructureCapture:
    """Revalidate detached capture facts using only retained bytes and pure ports."""
    target = _target(target)
    _require(type(capture) is dict and set(capture) == _CAPTURE_FIELDS and capture["version"] == VERSION)
    _require(type(capture["bundle_validated"]) is bool and type(capture["capture_complete"]) is bool)
    _require(type(capture["files"]) is list and type(capture["failures"]) is list)
    plan = capture["original_plan"]
    if plan is not None:
        plan = qualify_protein_structure_target_plan(target, plan)
    bundle_file = capture["bundle_file"]
    if bundle_file is not None:
        retained_protein_structure_file(store, bundle_file)
        _require(bundle_file["format"] == BUNDLE_FORMAT and plan is not None)
    if not capture["bundle_validated"]:
        _require(not capture["capture_complete"] and not capture["files"] and len(capture["failures"]) == 1)
        failure = capture["failures"][0]
        _require(type(failure) is dict and type(failure.get("code")) is str and failure["code"] in _ISSUE_CODES)
        _require(same(failure, issue(failure["code"], stage="capture", field="request" if plan is None else "manifest")))
        if bundle_file is not None:
            try:
                _bundle(store, bundle_file, plan)
            except ValueError as error:
                _require(failure["code"] == _failure_code(error))
            else:
                raise ValueError("invalid_schema")
        elif plan is not None:
            _require(failure["code"] in ("capture_incomplete", "invalid_output_path", "retained_artifact_missing", "input_digest_mismatch"))
        return deepcopy(capture)
    _require(plan is not None and bundle_file is not None)
    bundle = _bundle(store, bundle_file, plan)
    _require(len(capture["files"]) == len(bundle["files"]))
    failures = []
    for index, (row, declared) in enumerate(zip(capture["files"], bundle["files"])):
        _require(type(row) is dict and set(row) == _ROW_FIELDS)
        _require(type(row["manifest_index_0based"]) is int and row["manifest_index_0based"] == index)
        _require(same(row["declared"], declared))
        observed = row["observed"]
        if declared["state"] == "absent":
            outcome, expected_issue = "declared_absent", None
            _require(observed is None)
        elif observed is None:
            outcome = "unavailable"
            expected_issue = issue("capture_incomplete", stage="capture", field="manifest", artifact_role=declared["role"])
        else:
            retained_protein_structure_file(store, observed)
            _require(observed["format"] == declared["format"])
            equal = all(observed[k] == declared[k] for k in ("sha256", "byte_length"))
            outcome = "verified" if equal else "digest_mismatch"
            expected_issue = None if equal else issue("input_digest_mismatch", stage="capture", field="manifest", artifact_role=declared["role"])
        _require(row["outcome"] == outcome and same(row["issue"], expected_issue))
        if expected_issue is not None:
            failures.append(expected_issue)
    _require(same(capture["failures"], failures) and capture["capture_complete"] == (not failures))
    return deepcopy(capture)


def capture_local_protein_structure_bundle(
    store, *, target: dict, directory: Path
) -> ProteinStructureCapture:
    """Capture once for the selected action, or replay its exact saved intent."""
    target = _target(target)
    _absolute(str(directory))
    try:
        with _directory_fd(directory, create=True) as result_fd:
            _require(os.fstat(result_fd).st_uid == os.geteuid(), "invalid_output_path")
            intent = _read_control(result_fd, "capture-intent.json")
            if intent is None:
                _require(_read_control(result_fd, "capture.json") is None, "original_commission_mismatch")
            _immutable_control(result_fd, "capture-intent.json", {"target": target})
            saved = _read_control(result_fd, "capture.json")
            if saved is not None:
                return validate_protein_structure_capture(store,
                    decode_protein_structure_json(saved, canonical_bytes=True), target=target)
            capture = _capture_original(store, target)
            capture = validate_protein_structure_capture(store, capture, target=target)
            _immutable_control(result_fd, "capture.json", capture)
            return capture
    except OSError as error:
        raise ValueError("invalid_output_path") from error


def _capture_original(store, target):
    from .native_protein_structure_local import local_protein_structure_plan
    capture = {"version": VERSION, "original_plan": None, "bundle_file": None,
        "bundle_validated": False, "files": [], "failures": [], "capture_complete": False}
    try:
        plan = qualify_protein_structure_target_plan(target,
            local_protein_structure_plan(target["assignment"], target["execution_id"]))
        capture["original_plan"] = plan
        capture["bundle_file"] = _capture_file(store, plan["attempt_directory"], BUNDLE_FILENAME, BUNDLE_FORMAT)
        bundle = _bundle(store, capture["bundle_file"], plan)
        capture["bundle_validated"] = True
    except (ValueError, OSError, KeyError, TypeError) as error:
        capture["failures"] = [issue(_failure_code(error), stage="capture",
            field="request" if capture["original_plan"] is None else "manifest")]
        return capture
    for index, declared in enumerate(bundle["files"]):
        row = {"manifest_index_0based": index, "declared": deepcopy(declared),
            "observed": None, "outcome": "declared_absent", "issue": None}
        if declared["state"] == "present":
            try:
                row["observed"] = _capture_file(store, plan["attempt_directory"], declared["relative_path"], declared["format"])
            except (ValueError, OSError):
                row["outcome"] = "unavailable"
                row["issue"] = issue("capture_incomplete", stage="capture", field="manifest", artifact_role=declared["role"])
            else:
                equal = all(row["observed"][k] == declared[k] for k in ("sha256", "byte_length"))
                row["outcome"] = "verified" if equal else "digest_mismatch"
                if not equal:
                    row["issue"] = issue("input_digest_mismatch", stage="capture", field="manifest", artifact_role=declared["role"])
        capture["files"].append(row)
        if row["issue"] is not None:
            capture["failures"].append(deepcopy(row["issue"]))
    capture["capture_complete"] = not capture["failures"]
    return capture
