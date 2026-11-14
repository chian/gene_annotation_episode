"""Custody of an original sealed RNA attempt, independent of native success.

Only the first selected capture reads producer files. Replay validates the saved
plan, immutable receipt and retained bytes without returning to that filesystem.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path, PurePosixPath
import stat

from .execution_contracts import canonical, digest, validate_target
from .materials import artifact_file, artifact_path
from .practical_execution_state import _immutable, _read
from .rna_structure_contracts import RNA_ISSUE_CODES, issue, validate_rna_issue

VERSION = "native_rna_structure_capture_v1"
PROVIDER = "episode.execution_result"
ORIGIN = {"content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt"}
CAPTURE_FIELDS = {"version", "bundle_artifact_ref", "bundle_validated", "artifacts",
    "invalid_artifacts", "absent_artifacts", "failures", "capture_complete"}
FILE_FIELDS = {"kind", "role", "format", "relative_path", "artifact_ref", "sha256", "size_bytes"}


def require(condition, code="rna_original_attempt_mismatch"):
    if not condition:
        raise ValueError(code)


def decode_json(raw, *, canonical_bytes=False):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "rna_invalid_native_schema")
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError("rna_invalid_native_schema")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
        encoded = (canonical(result) + "\n").encode()
        require(not canonical_bytes or raw == encoded, "rna_invalid_native_schema")
        return result
    except (UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError("rna_invalid_native_schema") from error


def retained(store, reference):
    """Use the shared artifact verifier and check its complete metadata."""
    metadata = store._require(reference, {"artifact"})
    path = artifact_path(store, reference)
    require(reference == "artifact_" + metadata["sha256"] and path.stat().st_size == metadata["size"],
        "rna_capture_digest_mismatch")
    return metadata, path


def is_native_rna_structure_target(target):
    return (isinstance(target, dict) and target.get("resource_kind") == "local" and
        isinstance(target.get("assignment"), dict) and
        isinstance(target["assignment"].get("requested_job"), dict) and
        "native_rna_structure" in target["assignment"]["requested_job"])


def qualify_target_plan(target, plan):
    from .native_rna_structure_contracts import validate_rna_structure_run_plan
    plan = validate_rna_structure_run_plan(plan)
    ident = plan["identity"]
    require(is_native_rna_structure_target(target) and target["assignment"]["requested_job"] == plan["requested_job"])
    require(all(target[left] == ident[right] for left, right in (
        ("run_id", "run_id"), ("origin_episode_id", "episode_id"), ("resource_id", "resource_id"),
        ("execution_id", "execution_id"), ("request_sha256", "requested_job_sha256"))))
    require(target["assignment"].get("resource_kind") == "local" and target["assignment"].get("resource_id") == target["resource_id"])
    root = Path(target["assignment"]["workspace"]) / ".episode-operations" / digest({
        "run": ident["run_id"], "episode": ident["episode_id"]}) / digest(ident["operation_key"])
    require(Path(ident["execution_id"]) == root / "native.json")
    return plan


@contextmanager
def confined_regular_file(root, relative):
    """Pin every path component with O_NOFOLLOW before the shared byte capture."""
    root, relative = Path(root), PurePosixPath(relative)
    require(root.is_absolute() and str(root) == str(root.absolute()) and ".." not in root.parts,
        "rna_output_path_conflict")
    require(not relative.is_absolute() and relative.parts and ".." not in relative.parts and
        str(relative) not in (".", ""), "rna_output_path_conflict")
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for component in (*root.parts[1:], *relative.parts[:-1]):
            fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        fd = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=fd)
        stack.callback(os.close, fd)
        require(stat.S_ISREG(os.fstat(fd).st_mode), "rna_capture_unavailable")
        yield Path("/proc/self/fd") / str(fd)


def validate_capture(store, capture, *, bundle=None):
    require(type(capture) is dict and set(capture) == CAPTURE_FIELDS and capture["version"] == VERSION,
        "rna_invalid_native_schema")
    require(type(capture["bundle_validated"]) is bool and type(capture["capture_complete"]) is bool,
        "rna_invalid_native_schema")
    for key in ("artifacts", "invalid_artifacts", "absent_artifacts", "failures"):
        require(type(capture[key]) is list, "rna_invalid_native_schema")
    for failure in capture["failures"]:
        validate_rna_issue(failure)
        require(failure["stage"] == "capture", "rna_invalid_native_schema")
    if capture["bundle_artifact_ref"] is not None:
        retained(store, capture["bundle_artifact_ref"])
    if not capture["bundle_validated"]:
        require(not capture["capture_complete"] and not capture["artifacts"] and not capture["invalid_artifacts"]
            and not capture["absent_artifacts"] and len(capture["failures"]) == 1, "rna_invalid_native_schema")
        return deepcopy(capture)
    require(bundle is not None and capture["bundle_artifact_ref"] is not None)
    require(decode_json(store.get_artifact(capture["bundle_artifact_ref"]), canonical_bytes=True) == bundle)
    expected, seen, failures = bundle["files"], set(), []
    for category in ("artifacts", "invalid_artifacts"):
        previous = -1
        for row in capture[category]:
            require(type(row) is dict and set(row) == FILE_FIELDS, "rna_invalid_native_schema")
            matches = [i for i, item in enumerate(expected) if all(item[key] == row[key]
                for key in ("kind", "role", "format", "relative_path"))]
            require(len(matches) == 1 and matches[0] not in seen and matches[0] > previous)
            index = previous = matches[0]
            seen.add(index)
            declared = expected[index]
            require(declared["state"] == "present")
            metadata, _ = retained(store, row["artifact_ref"])
            require((metadata["sha256"], metadata["size"]) == (row["sha256"], row["size_bytes"]), "rna_capture_digest_mismatch")
            equal = (row["sha256"], row["size_bytes"]) == (declared["sha256"], declared["size_bytes"])
            require(equal == (category == "artifacts"), "rna_capture_digest_mismatch")
    require(capture["absent_artifacts"] == [row for row in expected if row["state"] == "absent"])
    invalid = {row["relative_path"] for row in capture["invalid_artifacts"]}
    for i, row in enumerate(expected):
        if row["state"] == "present" and (i not in seen or row["relative_path"] in invalid):
            failures.append(issue("rna_capture_unavailable" if i not in seen else "rna_capture_digest_mismatch",
                stage="capture", record_key=bundle["record_key"], field=f"/files/{i}", artifact_role=row["role"]))
    require(capture["failures"] == failures and capture["capture_complete"] == (not failures), "rna_capture_digest_mismatch")
    return deepcopy(capture)


def capture_local_rna_structure_bundle(store, *, target, directory):
    from .native_rna_structure_contracts import BUNDLE_FILENAME, validate_rna_structure_bundle
    from .native_rna_structure_local import local_rna_structure_plan
    target = validate_target(target)
    require(is_native_rna_structure_target(target))
    job = target["assignment"]["requested_job"]["native_rna_structure"]
    directory = Path(directory).absolute()
    require(directory.resolve() == directory, "rna_output_path_conflict")
    directory.mkdir(parents=True, exist_ok=True)
    _immutable(directory / "capture-intent.json", {"target": target})
    saved_path = directory / "capture.json"
    if saved_path.exists():
        plan = _read(directory / "capture-plan.json")
        capture = _read(saved_path)
        if plan is not None:
            qualify_target_plan(target, plan)
        bundle = None
        if capture["bundle_validated"]:
            require(plan is not None)
            bundle = validate_rna_structure_bundle(decode_json(store.get_artifact(capture["bundle_artifact_ref"]), canonical_bytes=True), plan=plan)
        return validate_capture(store, capture, bundle=bundle)
    result = {"version": VERSION, "bundle_artifact_ref": None, "bundle_validated": False,
        "artifacts": [], "invalid_artifacts": [], "absent_artifacts": [], "failures": [], "capture_complete": False}
    plan = None
    try:
        plan = qualify_target_plan(target, local_rna_structure_plan(target["assignment"], target["execution_id"]))
        _immutable(directory / "capture-plan.json", plan)
        with confined_regular_file(plan["attempt_directory"], BUNDLE_FILENAME) as path:
            result["bundle_artifact_ref"] = artifact_file(store, path, "application/json")
        raw = store.get_artifact(result["bundle_artifact_ref"])
        candidate = decode_json(raw, canonical_bytes=True)
        require(type(candidate) is dict, "rna_invalid_native_schema")
        require(candidate.get("sealed") is True, "rna_unsealed_native_attempt")
        bundle = validate_rna_structure_bundle(candidate, plan=plan)
        result["bundle_validated"] = True
    except (ValueError, OSError, KeyError, TypeError) as error:
        _immutable(directory / "capture-plan.json", plan)
        code = str(error) if str(error) in RNA_ISSUE_CODES else "rna_capture_unavailable" if isinstance(error, OSError) else "rna_original_attempt_mismatch"
        result["failures"] = [issue(code, stage="capture", record_key=job["record_key"])]
        _immutable(saved_path, result)
        return result
    for i, row in enumerate(bundle["files"]):
        if row["state"] == "absent":
            result["absent_artifacts"].append(deepcopy(row))
            continue
        try:
            with confined_regular_file(plan["attempt_directory"], row["relative_path"]) as path:
                ref = artifact_file(store, path)
            metadata, _ = retained(store, ref)
            captured = {key: row[key] for key in ("kind", "role", "format", "relative_path")}
            captured.update(artifact_ref=ref, sha256=metadata["sha256"], size_bytes=metadata["size"])
            equal = (metadata["sha256"], metadata["size"]) == (row["sha256"], row["size_bytes"])
            result["artifacts" if equal else "invalid_artifacts"].append(captured)
            if equal:
                continue
            code = "rna_capture_digest_mismatch"
        except (ValueError, OSError):
            code = "rna_capture_unavailable"
        result["failures"].append(issue(code, stage="capture", record_key=job["record_key"],
            field=f"/files/{i}", artifact_role=row["role"]))
    result["capture_complete"] = not result["failures"]
    validate_capture(store, result, bundle=bundle)
    _immutable(saved_path, result)
    return result


def rna_structure_source_payload(*, bundle, capture, prepared):
    require(capture["bundle_validated"] and capture["bundle_artifact_ref"] is not None)
    auxiliary = [row["artifact_ref"] for row in capture["artifacts"] + capture["invalid_artifacts"]]
    if prepared is not None and prepared["source_grading_artifact_ref"] is not None:
        auxiliary.append(prepared["source_grading_artifact_ref"])
    return {"provider": PROVIDER, "accession": "native_rna_structure_" + digest(bundle["identity"]),
        "uri": None, "artifact_ref": capture["bundle_artifact_ref"], "text_ref": None, "request_ref": None,
        "version": "native_rna_structure_bundle_v1", "retrieved_at": bundle["finished_at"],
        "auxiliary_artifact_refs": list(dict.fromkeys(auxiliary))}


def publish_rna_structure_source(store, *, bundle, capture, prepared):
    validate_capture(store, capture, bundle=bundle)
    payload = rna_structure_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    for ref in payload["auxiliary_artifact_refs"]:
        retained(store, ref)
    return store.put("source", payload, origin="tool")["id"]
