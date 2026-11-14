"""Retain qualified original utility files; replay uses only saved custody."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .execution_contracts import validate_target
from .native_hmmer_preparation_acquisition import (
    _capture_file, _decode, _directory, _read_record, _retained,
)
from .library.native_worker_files import _encoded
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import ATTEMPT_NAME, BUNDLE_NAME, BUNDLE_VERSION, DATABASE_ROLES, OUTPUT_ROLES, OWNER_NAME, PLAN_NAME, JOB_VERSION_V2, JOB_VERSION_V3, _error, _producer_path, database_file_selections, finite_json_copy, measurement_pair, native_blast_digest, staged_relative, validate_native_blast_utility_bundle, validate_native_blast_utility_plan
from .native_blast_utility_local import local_blast_utility_plan, _policy
from .practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_capture_contracts import VERSION, _ASSOCIATION_FIELDS, _ROW_FIELDS, _key, _selected_files, validate_native_blast_utility_capture

PROVIDER = "episode.execution_result"


def is_native_blast_utility_target(target):
    return (type(target) is dict and target.get("resource_kind") == "local"
        and type(target.get("assignment")) is dict and type(target["assignment"].get("requested_job")) is dict
        and "native_blast_utility" in target["assignment"]["requested_job"])


def _target_plan(target, plan):
    plan = validate_native_blast_utility_plan(plan)
    identity, assignment = plan["identity"], target["assignment"]
    if (target["resource_kind"] != "local" or assignment.get("resource_kind") != "local"
            or assignment.get("resource_id") != target["resource_id"]
            or native_blast_digest(assignment.get("requested_job")) != native_blast_digest(plan["requested_job"])
            or target["request_sha256"] != identity["requested_job_sha256"]
            or any(target[k] != identity[v] for k, v in (("run_id", "run_id"), ("origin_episode_id", "episode_id"),
                ("resource_id", "resource_id"), ("execution_id", "execution_id")))):
        _error("original_target_conflict")
    root = _producer_path(assignment.get("workspace"), absolute=True) / ".episode-operations" / native_blast_digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / identity["attempt_id"]
    if PurePosixPath(plan["attempt_directory"]) != root / ATTEMPT_NAME:
        _error("original_target_directory_conflict")
    for key, field in (("attempt_id", "attempt_id"), ("original_operation_key", "operation_key")):
        if key in target and target[key] != identity[field]:
            _error("original_target_conflict")
    _policy(assignment, plan["policy"])
    return plan







def _validate_saved_realizations(store, capture):
    from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_materializations import preparation_path_maps, realize_selected_list
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    paths = preparation_path_maps(job, capture["plan"]["attempt_directory"])
    selected = {r["input_key"]: r for r in job["materializations"]["list_files"]}
    originals = {r["input_key"]: r for r in capture["artifacts"] if r["direction"] == "input"}
    for receipt in capture["original_bundle"]["materializations"]:
        if receipt["kind"] != "list_rewrite" or receipt["input_key"] not in originals:
            continue
        original = originals[receipt["input_key"]]
        _, expected = realize_selected_list(job, selected[receipt["input_key"]],
            store.get_artifact(original["artifact_ref"]), paths)
        if expected != receipt:
            _error("capture_list_realization_conflict")



def _failure(code, row=None, reference=None):
    return {"stage": "custody", "code": code, **{k: row[k] if row else None for k in _ASSOCIATION_FIELDS},
            "diagnostic_artifact_ref": reference}






def _source_payload(capture):
    bundle = capture["original_bundle"]
    return {"provider": PROVIDER, "accession": "native_blast_utility_" + native_blast_digest(bundle["identity"]),
        "uri": None, "artifact_ref": capture["bundle_artifact_ref"], "text_ref": None, "request_ref": None,
        "version": BUNDLE_VERSION, "retrieved_at": bundle["finished_at"],
        "auxiliary_artifact_refs": sorted({row["artifact_ref"] for row in capture["artifacts"]})}


def _validate_saved(store, capture):
    capture = validate_native_blast_utility_capture(capture)
    bundle, reference = capture["original_bundle"], capture["bundle_artifact_ref"]
    if reference is not None:
        _retained(store, reference)
        if bundle is not None and _decode(store.get_artifact(reference)) != bundle:
            _error("capture_bundle_association_conflict")
    selected = {_key(row): row for row in _selected_files(capture["plan"], bundle)}
    seen = set()
    for row in capture["artifacts"]:
        key, meta = _key(row), _retained(store, row["artifact_ref"])
        expected = selected.get(key)
        if (expected is None or not expected["original"]
                or any(row[k] != expected[k] for k in _ROW_FIELDS - {"artifact_ref"})
                or (meta["size"], meta["sha256"]) != measurement_pair(row)):
            _error("capture_artifact_association_conflict")
        seen.add(key)
    global_failures = []
    for row in capture["failures"]:
        meta = _retained(store, row["diagnostic_artifact_ref"]) if row["diagnostic_artifact_ref"] is not None else None
        if row["direction"] is None:
            if row["code"] not in {"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid"}:
                _error("capture_failure_association_conflict")
            global_failures.append(row)
            continue
        key = _key(row)
        expected = selected.get(key)
        if expected is None or key in seen:
            _error("capture_failure_association_conflict")
        seen.add(key)
        if row["code"] == "unsealed_file" and bundle is not None:
            _error("capture_failure_association_conflict")
        if row["code"] == "input_not_original" and (expected["original"] or row["direction"] not in {"input", "database", "materialization"} or bundle is None):
            _error("capture_failure_association_conflict")
        if row["code"] in {"unsealed_file", "input_not_original", "original_file_identity_mismatch"} and meta is None:
            _error("capture_failure_diagnostic_required")
        if row["code"] == "original_file_identity_mismatch" and (meta["size"], meta["sha256"]) == measurement_pair(expected):
            _error("capture_failure_measurement_conflict")
    if (capture["bundle_validated"] and global_failures or not capture["bundle_validated"] and not global_failures
            or any(row["sha256"] is not None and key not in seen for key, row in selected.items())):
        _error("capture_missing_original_association")
    if capture["source_ref"] is not None:
        source = store._require(capture["source_ref"], {"source"})
        if {k: v for k, v in source.items() if k not in {"id", "origin", "record_type"}} != _source_payload(capture):
            _error("capture_source_association_conflict")
    if bundle is not None and capture["plan"]["requested_job"]["native_blast_utility"]["version"] == JOB_VERSION_V2:
        _validate_saved_realizations(store, capture)
    return capture


def capture_local_utility_bundle(store, *, target: dict, directory) -> dict:
    if not is_native_blast_utility_target(target):
        _error("local_capture_binding_required")
    target = finite_json_copy(target)
    validate_target({k: v for k, v in target.items() if k not in {"attempt_id", "original_operation_key"}})
    directory = _directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("capture-intent.json", "capture-plan.json", "capture.json"):
        path = directory / name
        if path.is_symlink() or path.exists() and not path.is_file():
            _error("capture_record_path_invalid")
    _immutable(directory / "capture-intent.json", {"target": target})
    if (directory / "capture.json").exists():
        plan = _target_plan(target, _read_record(directory, "capture-plan.json"))
        capture = _validate_saved(store, _read_record(directory, "capture.json"))
        if capture["plan"] != plan:
            _error("capture_plan_association_conflict")
        return capture
    try:
        original_plan = local_blast_utility_plan(target["assignment"], target["execution_id"])
    except ValueError as error:
        if str(error) != "native_blast_utility_original_attempt_owner_conflict":
            raise
        # The local port verifies every reservation field before its final
        # native-owner check. Keep that specific failure representable; never
        # bypass a failed command, allocation, path or request qualification.
        original_plan = _read(Path(target["execution_id"]).parent / PLAN_NAME)
    plan = _target_plan(target, original_plan)
    _immutable(directory / "capture-plan.json", plan)
    root = Path(plan["attempt_directory"])
    capture = {"version": VERSION, "source_ref": None, "plan": plan, "original_bundle": None,
        "bundle_artifact_ref": None, "bundle_validated": False, "artifacts": [], "failures": []}
    try:
        owner_ref = _capture_file(store, root, OWNER_NAME, "application/json")
        if store.get_artifact(owner_ref) != _encoded(plan):
            capture["failures"].append(_failure("original_owner_invalid", reference=owner_ref))
        else:
            reference = _capture_file(store, root, BUNDLE_NAME, "application/json")
            capture["bundle_artifact_ref"] = reference
            try:
                raw = store.get_artifact(reference)
                bundle = validate_native_blast_utility_bundle(_decode(raw), plan)
                if raw != _encoded(bundle) or not bundle["writer_closed"]:
                    _error("original_bundle_unsealed")
                capture["original_bundle"], capture["bundle_validated"] = bundle, True
            except ValueError:
                capture["failures"].append(_failure("original_bundle_invalid", reference=reference))
    except (OSError, ValueError):
        capture["failures"].append(_failure("sealed_bundle_unavailable"))
    for row in _selected_files(plan, capture["original_bundle"]):
        try:
            reference = _capture_file(store, Path(row["read_root"]), row["read_relative"])
        except FileNotFoundError:
            if row["sha256"] is not None:
                capture["failures"].append(_failure("original_file_unavailable", row))
            continue
        except (OSError, ValueError):
            capture["failures"].append(_failure("original_file_unavailable", row))
            continue
        meta = _retained(store, reference)
        code = ("unsealed_file" if not capture["bundle_validated"] else
                "input_not_original" if not row["original"] else
                "original_file_identity_mismatch" if (meta["size"], meta["sha256"]) != measurement_pair(row) else None)
        if code:
            capture["failures"].append(_failure(code, row, reference))
        else:
            capture["artifacts"].append({k: row[k] for k in _ROW_FIELDS - {"artifact_ref"}} | {"artifact_ref": reference})
    _validate_saved(store, capture)
    if capture["bundle_validated"]:
        capture["source_ref"] = store.put("source", _source_payload(capture), origin="tool")["id"]
    _validate_saved(store, capture)
    _immutable(directory / "capture.json", capture)
    return capture


__all__ = ["capture_local_utility_bundle", "is_native_blast_utility_target", "validate_native_blast_utility_capture"]
