"""Retain qualified original utility files; replay uses only saved custody."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .execution_contracts import validate_target
from .native_hmmer_preparation_acquisition import (
    _capture_file, _decode, _directory, _read_record, _retained,
)
from .native_infernal_driver import _encoded
from .native_blast_utility_contracts import (
    ATTEMPT_NAME, BUNDLE_NAME, BUNDLE_VERSION, DATABASE_ROLES, OUTPUT_ROLES, OWNER_NAME, PLAN_NAME, JOB_VERSION_V2, JOB_VERSION_V3,
    _error, _producer_path, database_file_selections, finite_json_copy, measurement_pair,
    native_blast_digest, staged_relative, validate_native_blast_utility_bundle,
    validate_native_blast_utility_plan,
)
from .native_blast_utility_local import local_blast_utility_plan, _policy
from .practical_execution_state import _immutable, _read

VERSION = "native_blast_utility_captured_bundle_v1"
PROVIDER = "episode.execution_result"
CAPTURE_FAILURE_CODES = frozenset({"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid",
    "original_file_unavailable", "original_file_identity_mismatch", "input_not_original", "unsealed_file"})
_CAPTURE_FIELDS = {"version", "source_ref", "plan", "original_bundle", "bundle_artifact_ref", "bundle_validated", "artifacts", "failures"}
_ROW_FIELDS = {"direction", "input_key", "database_key", "role", "ordinal", "original_path", "artifact_ref", "sha256", "size_bytes", "format", "completeness"}
_ASSOCIATION_FIELDS = {"direction", "input_key", "database_key", "role", "ordinal", "original_path"}
_FORMATS = {"fasta", "text", "maskinfo_xml", "maskinfo_asn1_text", "blastdbcmd_tabular_v1", "blastdb_info_text",
            "blastdb_metadata_json", "blastdbcheck_text", "blastdb_binary", "json", "unknown",
            "gi_list_binary", "seqid_list_binary", "blast_alias_text", "blast_seqid_list_info_text",
            "blast_index_binary", "blast_index_map_text", "blast_profile_aux_text", "pssm_asn1_text", "pssm_asn1_binary"}
_VDB_FORMATS = {"blast_vdb_cmd_table_v1", "blast_vdb_info_text_v1", "blast_vdb_paths_text_v1"}


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


def _selected_files(plan, bundle):
    """Keep original-path identity distinct from the actual staged-read location."""
    job, root = plan["requested_job"]["native_blast_utility"], Path(plan["attempt_directory"])
    result = []
    inputs = job["inputs"] if bundle is None else bundle["inputs"]
    for ordinal, row in enumerate(inputs):
        relative = staged_relative(row) if bundle is None else row["relative_path"]
        pair = (None, None) if bundle is None else measurement_pair(row, "final_")
        original = bundle is not None and pair == measurement_pair(row, "staged_") == measurement_pair(row, "expected_")
        result.append({"direction": "input", "input_key": row["input_key"], "database_key": None,
            "role": row["role"], "ordinal": ordinal, "original_path": row["path"] if bundle is None else row["original_path"],
            "format": row["format"], "completeness": "complete" if original else "unknown",
            "size_bytes": pair[0], "sha256": pair[1], "original": original,
            "read_root": str(root), "read_relative": relative})
    outputs = [r for r in job["outputs"] if r["path_kind"] == "file"] if bundle is None else bundle["artifacts"]
    for row in outputs:
        result.append({"direction": "output", "input_key": None, "database_key": None,
            "role": row["role"], "ordinal": row.get("ordinal", 0), "original_path": str(root / row["relative_path"]),
            "format": row["format"], "completeness": row.get("completeness", "unknown"),
            "size_bytes": row.get("size_bytes"), "sha256": row.get("sha256"), "original": bundle is not None,
            "read_root": str(root), "read_relative": row["relative_path"]})
    databases = database_file_selections(job) if bundle is None else bundle["database_files"]
    for ordinal, row in enumerate(databases):
        path = Path(row["original_path"])
        pair = (None, None) if bundle is None else measurement_pair(row, "final_")
        original = bundle is not None and pair == measurement_pair(row, "before_") == measurement_pair(row, "expected_")
        fmt = ("blastdb_metadata_json" if path.suffix in {".njs", ".pjs"} else "blastdb_binary") if row["role"] == "database_file" else (
            "json" if row["role"] in {"manifest", "metadata_manifest", "input_manifest"} else "unknown")
        if job["version"] == JOB_VERSION_V3:
            from .native_blast_vdb_utility_context import vdb_utility_database_operands
            db = next(d for d in vdb_utility_database_operands(job) if d["database_key"] == row["database_key"])
            if db["kind"] == "vdb" and row["role"] == "database_file":
                fmt = "unknown"
            elif row["role"] == "preparation_receipt":
                fmt = "json"
        result.append({"direction": "database", "input_key": None, "database_key": row["database_key"],
            "role": row["role"], "ordinal": ordinal, "original_path": str(path), "format": fmt,
            "completeness": "complete" if original else "unknown", "size_bytes": pair[0], "sha256": pair[1],
            "original": original, "read_root": str(path.parent), "read_relative": path.name})
    if job["version"] == JOB_VERSION_V2:
        result.extend(_materialized_files(plan, bundle, result))
    return result



def _materialized_files(plan, bundle, selected):
    """646/002+003: immutable originals and realized occurrences stay separate."""
    job, root = plan["requested_job"]["native_blast_utility"], Path(plan["attempt_directory"])
    receipts = [] if bundle is None else bundle["materializations"]
    by_relative = {r["relative_path"]: r for r in receipts}
    result = []
    originals = {r["input_key"]: r for r in job["inputs"]}
    db_files = {(r["database_key"], r["original_path"]): r for r in selected if r["direction"] == "database" and r["role"] == "database_file"}
    requests = [(r["input_key"], None, r["role"], i, staged_relative(r), r["format"])
                for i, r in enumerate(job["inputs"])]
    ordinal = 0
    for copy in job["materializations"]["database_copies"]:
        for row in copy["files"]:
            requests.append((None, copy["database_key"], "database_file", ordinal, row["relative_path"],
                             db_files[copy["database_key"], row["source_path"]]["format"]))
            ordinal += 1
    requests += [(r["input_key"], None, "materialized_list", i, r["relative_path"], "text")
                 for i, r in enumerate(job["materializations"]["list_files"])]
    for key, db, role, ordinal, relative, fmt in requests:
        receipt = by_relative.get(relative)
        pair, original = (None, None), False
        if receipt is not None:
            if receipt["kind"] == "list_rewrite":
                pair = receipt["size_bytes"], receipt["sha256"]
                original = not any(f["stage"] == "materializations" and f["relative_path"] == relative for f in bundle["failures"])
            else:
                final = receipt["final"]
                pair = (None, None) if final is None else (final["size_bytes"], final["sha256"])
                original = receipt["expected"] == receipt["staged"] == final
        result.append({"direction": "materialization", "input_key": key, "database_key": db,
            "role": role, "ordinal": ordinal, "original_path": str(root / relative), "format": fmt,
            "completeness": "complete" if original else "unknown", "size_bytes": pair[0], "sha256": pair[1],
            "original": original, "read_root": str(root), "read_relative": relative})
    return result


def _validate_saved_realizations(store, capture):
    from .native_blast_utility_materializations import preparation_path_maps, realize_selected_list
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

def _key(row):
    return tuple(row[k] for k in ("direction", "input_key", "database_key", "role", "ordinal", "original_path"))


def _failure(code, row=None, reference=None):
    return {"stage": "custody", "code": code, **{k: row[k] if row else None for k in _ASSOCIATION_FIELDS},
            "diagnostic_artifact_ref": reference}


def _association(row, *, nullable=False, preparation=False, vdb=False):
    if nullable and row["direction"] is None:
        if any(row[k] is not None for k in _ASSOCIATION_FIELDS):
            _error("capture_global_failure_association")
        return
    direction = row["direction"]
    if type(direction) is not str or direction not in ({"input", "output", "database", "materialization"} if preparation else {"input", "output", "database"}):
        _error("capture_direction_invalid")
    if type(row["ordinal"]) is not int or row["ordinal"] < 0:
        _error("capture_ordinal_invalid")
    _producer_path(row["original_path"], absolute=True)
    roles = {"input": {"sequence_input", "taxid_map", "mask_input"}, "output": OUTPUT_ROLES, "database": DATABASE_ROLES}
    if vdb:
        roles["input"] = {"entry_batch", "database_list"}
    if preparation:
        roles["input"] |= {"identifier_list", "database_list", "profile_list", "profile_input"}
        roles["output"] = set(roles["output"]) | {"identifier_list", "alias_file", "index_file", "profile_file", "statistics"}
        roles["materialization"] = roles["input"] | {"materialized_list", "database_file"}
    if type(row["role"]) is not str or row["role"] not in roles[direction]:
        _error("capture_role_invalid")
    for key, expected in (("input_key", direction == "input" or direction == "materialization" and row["role"] != "database_file"),
                          ("database_key", direction == "database" or direction == "materialization" and row["role"] == "database_file")):
        if expected and (type(row[key]) is not str or not row[key]) or not expected and row[key] is not None:
            _error("capture_key_invalid")


def validate_native_blast_utility_capture(value):
    capture = finite_json_copy(value)
    if (type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture["version"] != VERSION
            or type(capture["bundle_validated"]) is not bool or type(capture["artifacts"]) is not list
            or type(capture["failures"]) is not list):
        _error("capture_shape_invalid")
    validate_native_blast_utility_plan(capture["plan"])
    preparation = capture["plan"]["requested_job"]["native_blast_utility"]["version"] == JOB_VERSION_V2
    vdb = capture["plan"]["requested_job"]["native_blast_utility"]["version"] == JOB_VERSION_V3
    for key in ("source_ref", "bundle_artifact_ref"):
        if capture[key] is not None and (type(capture[key]) is not str or not capture[key]):
            _error("capture_reference_invalid")
    if capture["bundle_validated"]:
        if capture["bundle_artifact_ref"] is None:
            _error("capture_bundle_reference_required")
        validate_native_blast_utility_bundle(capture["original_bundle"], capture["plan"])
        if not capture["original_bundle"]["writer_closed"]:
            _error("capture_writer_not_closed")
    elif capture["original_bundle"] is not None or capture["source_ref"] is not None or capture["artifacts"]:
        _error("capture_unvalidated_measurements_forbidden")
    seen = set()
    for row in capture["artifacts"]:
        if type(row) is not dict or set(row) != _ROW_FIELDS:
            _error("capture_artifact_shape")
        _association(row, preparation=preparation, vdb=vdb)
        pair = measurement_pair(row)
        if (pair[0] is None or row["artifact_ref"] != "artifact_" + row["sha256"]
                or type(row["format"]) is not str or row["format"] not in (_FORMATS | _VDB_FORMATS if vdb else _FORMATS)
                or type(row["completeness"]) is not str or row["completeness"] not in {"complete", "partial", "unknown"}
                or _key(row) in seen):
            _error("capture_artifact_identity_invalid")
        seen.add(_key(row))
    seen_failures = set()
    for row in capture["failures"]:
        if (type(row) is not dict or set(row) != {"stage", "code", "diagnostic_artifact_ref"} | _ASSOCIATION_FIELDS
                or row["stage"] != "custody" or type(row["code"]) is not str or row["code"] not in CAPTURE_FAILURE_CODES
                or row["diagnostic_artifact_ref"] is not None and (type(row["diagnostic_artifact_ref"]) is not str
                    or not row["diagnostic_artifact_ref"].startswith("artifact_"))):
            _error("capture_failure_shape")
        _association(row, nullable=True, preparation=preparation, vdb=vdb)
        digest = native_blast_digest(row)
        if digest in seen_failures:
            _error("capture_duplicate_failure")
        seen_failures.add(digest)
    return capture


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
