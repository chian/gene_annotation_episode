"""Retain authenticated masking originals; replay reads only saved custody."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .execution_contracts import validate_target
from .native_hmmer_preparation_acquisition import (
    _capture_file, _decode, _directory, _read_record, _retained,
)
from .native_blast_masking_contracts import (
    ATTEMPT_NAME, BUNDLE_VERSION, OWNER_NAME, _error, _pair, _path, _sha,
    finite_json_copy, native_blast_digest, staged_relative,
    validate_native_blast_masking_plan, validate_original_bundle, validate_preflight_failures,
)
from .native_blast_masking_local import local_blast_masking_plan
from .practical_execution_state import _immutable

VERSION = "native_blast_masking_capture_v1"
PROVIDER = "episode.execution_result"
CAPTURE_FAILURE_CODES = frozenset({"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid",
    "original_file_unavailable", "original_file_identity_mismatch", "input_not_original", "unsealed_file"})
_ROW_KEYS = {"direction", "role", "ordinal", "format", "relative_path", "artifact_ref", "sha256", "size_bytes"}


def is_native_blast_masking_target(target):
    return (type(target) is dict and target.get("resource_kind") == "local"
        and type(target.get("assignment")) is dict and type(target["assignment"].get("requested_job")) is dict
        and "native_blast_masking" in target["assignment"]["requested_job"])


def _target_plan(target, plan):
    plan = validate_native_blast_masking_plan(plan)
    identity, assignment = plan["identity"], target["assignment"]
    if (target["resource_kind"] != "local" or assignment.get("resource_kind") != "local"
            or assignment.get("resource_id") != target["resource_id"]
            or assignment.get("requested_job") != plan["requested_job"]
            or target["request_sha256"] != identity["requested_job_sha256"]
            or any(target[k] != identity[v] for k, v in (("run_id", "run_id"), ("origin_episode_id", "episode_id"),
                ("resource_id", "resource_id"), ("execution_id", "execution_id")))):
        _error("original_target_conflict")
    expected = _path(assignment.get("workspace"), absolute=True) / ".episode-operations" / native_blast_digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / identity["attempt_id"]
    if PurePosixPath(plan["attempt_directory"]) != expected / ATTEMPT_NAME:
        _error("original_target_directory_conflict")
    for key in ("attempt_id", "original_operation_key"):
        if target.get(key) is not None and target[key] != identity["operation_key" if key == "original_operation_key" else key]:
            _error("original_target_conflict")
    return plan


def _selected_files(plan, bundle):
    job = (plan if bundle is None else bundle)["requested_job"]["native_blast_masking"]
    result = []
    if bundle is None:
        for operand in job["operands"]:
            result.append({"direction": "input", "role": operand["role"], "ordinal": 0, "format": operand["format"],
                "relative_path": staged_relative(operand), "sha256": None, "size_bytes": None, "original": False})
        for output in job["outputs"]:
            result.append({"direction": "output", **output, "ordinal": 0,
                "sha256": None, "size_bytes": None, "original": False})
        return result
    for row in bundle["inputs"]:
        result.append({"direction": "input", **{k: row[k] for k in ("role", "ordinal", "format", "relative_path")},
            "sha256": row["final_sha256"], "size_bytes": row["final_size_bytes"],
            "original": _pair(row, "final_") == _pair(row, "staged_") == (row["expected_size_bytes"], row["expected_sha256"])})
    for row in bundle["artifacts"]:
        result.append({"direction": "output", **row, "original": True})
    return result


def _key(row):
    return row["direction"], row["role"], row["ordinal"], row["relative_path"]


def _failure(code, row=None, reference=None):
    return {"stage": "custody", "code": code, "direction": row["direction"] if row else None,
        "role": row["role"] if row else None, "ordinal": row["ordinal"] if row else None,
        "relative_path": row["relative_path"] if row else None, "diagnostic_artifact_ref": reference,
        "input_failures": []}


def validate_native_blast_masking_capture(value):
    capture = finite_json_copy(value)
    if (type(capture) is not dict or set(capture) != {"version", "bundle_artifact_ref", "bundle_validated", "artifacts", "failures"}
            or capture["version"] != VERSION or type(capture["bundle_validated"]) is not bool
            or type(capture["artifacts"]) is not list or type(capture["failures"]) is not list
            or capture["bundle_artifact_ref"] is not None and type(capture["bundle_artifact_ref"]) is not str
            or capture["bundle_validated"] and capture["bundle_artifact_ref"] is None):
        _error("capture_shape_invalid")
    seen = set()
    for row in capture["artifacts"]:
        if (type(row) is not dict or set(row) != _ROW_KEYS or type(row["direction"]) is not str or row["direction"] not in {"input", "output"}
                or type(row["ordinal"]) is not int or row["ordinal"] != 0
                or any(type(row[k]) is not str or not row[k] for k in ("role", "format", "relative_path", "artifact_ref"))):
            _error("capture_artifact_invalid")
        _path(row["relative_path"])
        if _pair(row)[0] is None or row["artifact_ref"] != "artifact_" + row["sha256"] or _key(row) in seen:
            _error("capture_artifact_identity_invalid")
        seen.add(_key(row))
    for f in capture["failures"]:
        if (type(f) is not dict or set(f) != {"stage", "code", "direction", "role", "ordinal", "relative_path", "diagnostic_artifact_ref", "input_failures"}
                or f["stage"] != "custody" or type(f["code"]) is not str or f["code"] not in CAPTURE_FAILURE_CODES
                or f["diagnostic_artifact_ref"] is not None and (type(f["diagnostic_artifact_ref"]) is not str
                    or not f["diagnostic_artifact_ref"].startswith("artifact_"))):
            _error("capture_failure_invalid")
        validate_preflight_failures(f["input_failures"])
        if f["input_failures"]:
            _error("capture_custody_input_failure_context")
        if f["direction"] is None:
            if any(f[k] is not None for k in ("role", "ordinal", "relative_path")):
                _error("capture_failure_association_invalid")
        else:
            if type(f["direction"]) is not str or f["direction"] not in {"input", "output"} or type(f["ordinal"]) is not int or f["ordinal"] != 0 or type(f["role"]) is not str:
                _error("capture_failure_association_invalid")
            _path(f["relative_path"])
    if not capture["bundle_validated"] and capture["artifacts"]:
        _error("capture_unsealed_artifacts_forbidden")
    return capture


def _validate_retained_rows(store, capture, plan, bundle):
    selected = {_key(row): row for row in _selected_files(plan, bundle)}
    seen = set()
    for row in capture["artifacts"]:
        key = _key(row)
        original = selected.get(key)
        meta = _retained(store, row["artifact_ref"])
        if (original is None or not original["original"] or original["format"] != row["format"]
                or (row["size_bytes"], row["sha256"]) != (original["size_bytes"], original["sha256"])
                or (meta["size"], meta["sha256"]) != (row["size_bytes"], row["sha256"])):
            _error("capture_artifact_association_conflict")
        seen.add(key)
    for f in capture["failures"]:
        if f["diagnostic_artifact_ref"] is not None:
            _retained(store, f["diagnostic_artifact_ref"])
        if f["direction"] is None:
            if f["code"] not in {"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid"}:
                _error("capture_failure_association_conflict")
            continue
        key = _key(f)
        if key not in selected or key in seen:
            _error("capture_failure_association_conflict")
        seen.add(key)
        expected = selected[key]
        if f["code"] == "input_not_original" and (f["direction"] != "input" or expected["original"]):
            _error("capture_failure_association_conflict")
        if f["code"] == "unsealed_file" and bundle is not None:
            _error("capture_failure_association_conflict")
        if f["code"] in {"unsealed_file", "input_not_original", "original_file_identity_mismatch"} and f["diagnostic_artifact_ref"] is None:
            _error("capture_failure_diagnostic_required")
        if f["code"] == "original_file_identity_mismatch":
            meta = _retained(store, f["diagnostic_artifact_ref"])
            if (meta["size"], meta["sha256"]) == (expected["size_bytes"], expected["sha256"]):
                _error("capture_failure_measurement_conflict")
    if any(row["sha256"] is not None and key not in seen for key, row in selected.items()):
        _error("capture_missing_original_association")


def _saved(store, target, directory):
    plan = _target_plan(target, _read_record(directory, "capture-plan.json"))
    capture = validate_native_blast_masking_capture(_read_record(directory, "capture.json"))
    bundle = None
    reference = capture["bundle_artifact_ref"]
    if reference is not None:
        _retained(store, reference)
        if capture["bundle_validated"]:
            bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
    if not capture["bundle_validated"] and not any(f["direction"] is None for f in capture["failures"]):
        _error("capture_bundle_failure_required")
    _validate_retained_rows(store, capture, plan, bundle)
    return capture


def capture_local_bundle(store, *, target, directory):
    if not is_native_blast_masking_target(target):
        _error("local_capture_binding_required")
    target = finite_json_copy(target)
    validate_target({k: v for k, v in target.items() if k not in {"original_operation_key", "attempt_id"}})
    directory = _directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("capture-intent.json", "capture-plan.json", "capture.json"):
        path = directory / name
        if path.is_symlink() or path.exists() and not path.is_file():
            _error("capture_record_path_invalid")
    _immutable(directory / "capture-intent.json", {"target": target})
    if (directory / "capture.json").exists():
        return _saved(store, target, directory)
    plan = _target_plan(target, local_blast_masking_plan(target["assignment"], target["execution_id"]))
    _immutable(directory / "capture-plan.json", plan)
    root, bundle = Path(plan["attempt_directory"]), None
    capture = {"version": VERSION, "bundle_artifact_ref": None, "bundle_validated": False, "artifacts": [], "failures": []}
    try:
        owner_ref = _capture_file(store, root, OWNER_NAME, "application/json")
        if _decode(store.get_artifact(owner_ref)) != plan:
            capture["failures"].append(_failure("original_owner_invalid", reference=owner_ref))
        else:
            reference = _capture_file(store, root, "bundle.json", "application/json")
            capture["bundle_artifact_ref"] = reference
            _retained(store, reference)
            try:
                bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
                capture["bundle_validated"] = True
            except ValueError:
                capture["failures"].append(_failure("original_bundle_invalid", reference=reference))
    except (OSError, ValueError):
        capture["failures"].append(_failure("sealed_bundle_unavailable"))
    for row in _selected_files(plan, bundle):
        try:
            reference = _capture_file(store, root, row["relative_path"])
        except FileNotFoundError:
            if row["sha256"] is not None:
                capture["failures"].append(_failure("original_file_unavailable", row))
            continue
        except (OSError, ValueError):
            capture["failures"].append(_failure("original_file_unavailable", row))
            continue
        meta = _retained(store, reference)
        code = ("unsealed_file" if bundle is None else "input_not_original" if not row["original"] else
            "original_file_identity_mismatch" if (meta["sha256"], meta["size"]) != (row["sha256"], row["size_bytes"]) else None)
        if code:
            capture["failures"].append(_failure(code, row, reference))
        else:
            capture["artifacts"].append({k: row[k] for k in _ROW_KEYS - {"artifact_ref"}} | {"artifact_ref": reference})
    validate_native_blast_masking_capture(capture)
    _validate_retained_rows(store, capture, plan, bundle)
    _immutable(directory / "capture.json", capture)
    return capture


def original_source_payload(*, bundle, capture, prepared=None):
    capture = validate_native_blast_masking_capture(capture)
    if not capture["bundle_validated"] or type(bundle) is not dict or bundle.get("version") != BUNDLE_VERSION:
        _error("source_validated_bundle_required")
    refs = [r["artifact_ref"] for r in capture["artifacts"]]
    refs.extend(f["diagnostic_artifact_ref"] for f in capture["failures"] if f["diagnostic_artifact_ref"] is not None)
    if prepared is not None:
        if type(prepared) is not dict or "source_grading_artifact_ref" not in prepared:
            _error("prepared_artifact_port_required")
        if prepared["source_grading_artifact_ref"] is not None:
            refs.append(prepared["source_grading_artifact_ref"])
    if any(type(ref) is not str or not ref.startswith("artifact_") for ref in refs):
        _error("source_artifact_reference_invalid")
    return {"provider": PROVIDER, "accession": "native_blast_masking_" + native_blast_digest(bundle["identity"]),
        "uri": None, "artifact_ref": capture["bundle_artifact_ref"], "text_ref": None, "request_ref": None,
        "version": BUNDLE_VERSION, "retrieved_at": bundle["finished_at"], "auxiliary_artifact_refs": sorted(set(refs))}


def publish_original_source(store, *, bundle, capture, prepared=None):
    payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    _retained(store, payload["artifact_ref"])
    if native_blast_digest(_decode(store.get_artifact(payload["artifact_ref"]))) != native_blast_digest(bundle):
        _error("source_bundle_association_conflict")
    _validate_retained_rows(store, capture, None, bundle)
    # This port has no current native path dependency. Reconstruct the pure plan
    # from original records only; capture itself was bound to the frozen plan.
    for row in capture["artifacts"]:
        meta = _retained(store, row["artifact_ref"])
        if (meta["size"], meta["sha256"]) != (row["size_bytes"], row["sha256"]):
            _error("source_artifact_identity_conflict")
        collection = bundle["inputs"] if row["direction"] == "input" else bundle["artifacts"]
        matches = [r for r in collection if (r["role"], r["ordinal"], r["relative_path"], r["format"]) ==
            (row["role"], row["ordinal"], row["relative_path"], row["format"])]
        if len(matches) != 1:
            _error("source_artifact_association_conflict")
        item = matches[0]
        if row["direction"] == "input":
            valid = _pair(item, "staged_") == _pair(item, "final_") == (item["expected_size_bytes"], item["expected_sha256"])
            expected = _pair(item, "final_")
        else:
            valid, expected = True, _pair(item)
        if not valid or expected != (row["size_bytes"], row["sha256"]):
            _error("source_artifact_association_conflict")
    for reference in payload["auxiliary_artifact_refs"]:
        _retained(store, reference)
    return store.put("source", payload, origin="tool")["id"]


__all__ = ["is_native_blast_masking_target", "validate_original_bundle", "capture_local_bundle",
    "validate_native_blast_masking_capture", "original_source_payload", "publish_original_source"]
