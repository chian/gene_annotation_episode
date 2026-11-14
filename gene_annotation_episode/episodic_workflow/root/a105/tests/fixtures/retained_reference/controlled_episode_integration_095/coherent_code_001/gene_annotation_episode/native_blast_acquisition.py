"""Complete custody of a selected original BLAST attempt, without execution.

Capture and replay retain files; neither parses scientific reports nor starts a
job. Failed commands may have complete captures of their genuine partial output.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re

from .domain import ContractError
from .execution_contracts import validate_target
from .local_jobs import LocalJobPolicy
from .materials import artifact_file, artifact_path
from .native_blast_contracts import (
    _absolute, compile_native_blast_job, finite_json_copy, native_blast_digest,
    validate_native_blast_requested_job,
)
from .native_blast_local import local_blast_plan, OWNER_NAME
from .practical_execution_state import _immutable, _read

VERSION = "native_blast_capture_v1"
PROVIDER = "episode.execution_result"
ORIGIN = {"content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt"}


def is_native_blast_target(target):
    return (type(target) is dict and target.get("resource_kind") == "local"
        and type(target.get("assignment")) is dict
        and type(target["assignment"].get("requested_job")) is dict and
        "native_blast" in target.get("assignment", {}).get("requested_job", {}))


def _sha(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ContractError("native_blast_bundle_digest_invalid")


def _size(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or value < 0:
        raise ContractError("native_blast_bundle_size_invalid")


def _plan(value):
    """Pure qualification; unlike the producer's preflight, performs no I/O."""
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job", "attempt_directory", "policy"}
            or plan["version"] != "native_blast_run_plan_v1"):
        raise ContractError("native_blast_run_plan_required")
    owner = plan["identity"]
    keys = {"run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key", "requested_job_sha256"}
    if (type(owner) is not dict or set(owner) != keys
            or any(type(v) is not str or not v or "\0" in v for v in owner.values())):
        raise ContractError("native_blast_complete_attempt_identity_required")
    request = validate_native_blast_requested_job(plan["requested_job"])
    if owner["requested_job_sha256"] != native_blast_digest(request):
        raise ContractError("native_blast_requested_job_digest_mismatch")
    _absolute(plan["attempt_directory"])
    if type(plan["policy"]) is not dict or set(plan["policy"]) != {"memory_bytes", "scratch_bytes", "wall_seconds"}:
        raise ContractError("native_blast_explicit_policy_required")
    LocalJobPolicy(**plan["policy"])
    return plan


def validate_original_bundle(bundle, plan):
    """Validate the exact sealed manifest against its original plan, without I/O."""
    plan, bundle = _plan(plan), finite_json_copy(bundle)
    fields = {"version", "identity", "requested_job", "program", "mode", "software",
        "realized_argv", "environment", "inputs", "operand_bindings", "returncode",
        "artifacts", "failures", "started_at", "finished_at"}
    if (type(bundle) is not dict or set(bundle) != fields
            or bundle["version"] != "native_blast_bundle_v1" or bundle["identity"] != plan["identity"]
            or bundle["requested_job"] != plan["requested_job"]):
        raise ContractError("native_blast_original_bundle_identity_conflict")
    job, root = plan["requested_job"]["native_blast"], Path(plan["attempt_directory"])
    software = bundle["software"]
    if (bundle["program"] != job["program"] or bundle["mode"] != job["mode"]
            or bundle["operand_bindings"] != job["operand_bindings"]
            or type(software) is not dict or set(software) != {
                "executable", "expected_sha256", "actual_sha256", "declared_engine_version"}
            or software["executable"] != job["software"]["executable"]
            or software["expected_sha256"] != job["software"]["sha256"]
            or software["declared_engine_version"] != job["software"]["engine_version"]):
        raise ContractError("native_blast_original_bundle_request_conflict")
    _sha(software["actual_sha256"], nullable=True)
    if bundle["returncode"] is not None and type(bundle["returncode"]) is not int:
        raise ContractError("native_blast_bundle_returncode_invalid")
    if (type(bundle["failures"]) is not list or any(type(row) is not dict
            or set(row) != {"stage", "code", "role", "detail"} or type(row["detail"]) is not dict
            or any(type(row[key]) is not str or not row[key] for key in ("stage", "code"))
            or row["role"] is not None and type(row["role"]) is not str for row in bundle["failures"])):
        raise ContractError("native_blast_bundle_failures_invalid")
    try:
        dates = [datetime.fromisoformat(bundle[key]) for key in ("started_at", "finished_at")]
        if any(value.utcoffset() is None for value in dates) or dates[1] < dates[0]:
            raise ValueError
    except (TypeError, ValueError):
        raise ContractError("native_blast_bundle_sealed_timestamp_invalid") from None
    operands = {row["role"]: row for row in job["operands"]}
    if type(bundle["inputs"]) is not list or len(bundle["inputs"]) != len(operands):
        raise ContractError("native_blast_original_bundle_inputs_conflict")
    seen, staged = set(), {}
    for row in bundle["inputs"]:
        if (type(row) is not dict or set(row) != {"role", "format", "original_path", "relative_path",
                "artifact_ref", "expected_sha256", "actual_sha256", "expected_size_bytes", "size_bytes"}
                or type(row["role"]) is not str or row["role"] not in operands or row["role"] in seen):
            raise ContractError("native_blast_original_bundle_input_conflict")
        original = operands[row["role"]]
        if (row["relative_path"] != "inputs/" + row["role"] + ".fa"
                or any(row[a] != original[b] for a, b in (("format", "format"), ("original_path", "path"),
                    ("artifact_ref", "artifact_ref"), ("expected_sha256", "sha256"), ("expected_size_bytes", "size_bytes")))):
            raise ContractError("native_blast_original_bundle_input_conflict")
        _sha(row["actual_sha256"], nullable=True)
        _size(row["size_bytes"], nullable=row["actual_sha256"] is None)
        seen.add(row["role"])
        staged[row["role"]] = str(root / row["relative_path"])
    compiled = compile_native_blast_job(job, input_paths=staged, output_directory=str(root))
    environment = {**compiled["environment"],
        **{key: str(root / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
        "XDG_CACHE_HOME": str(root / "cache")}
    if bundle["realized_argv"] != compiled["argv"] or bundle["environment"] != environment:
        raise ContractError("native_blast_original_realized_command_conflict")
    outputs, seen = {row["role"]: row for row in job["outputs"]}, set()
    if type(bundle["artifacts"]) is not list:
        raise ContractError("native_blast_bundle_artifacts_invalid")
    for row in bundle["artifacts"]:
        if (type(row) is not dict or set(row) != {"role", "format", "relative_path", "size_bytes", "sha256"}
                or type(row["role"]) is not str or row["role"] not in outputs or row["role"] in seen
                or any(row[key] != outputs[row["role"]][key] for key in ("format", "relative_path"))):
            raise ContractError("native_blast_original_bundle_output_conflict")
        seen.add(row["role"])
        _sha(row["sha256"])
        _size(row["size_bytes"])
    if not bundle["failures"]:
        if (bundle["returncode"] != 0 or software["actual_sha256"] is None
                or software["actual_sha256"].lower() != software["expected_sha256"].lower()
                or any(row["actual_sha256"] is None or row["actual_sha256"].lower() != row["expected_sha256"].lower()
                    or row["size_bytes"] != row["expected_size_bytes"] for row in bundle["inputs"])):
            raise ContractError("native_blast_successful_bundle_measurement_conflict")
        if seen != outputs.keys():
            raise ContractError("native_blast_successful_bundle_missing_outputs")
    failures, rc = bundle["failures"], bundle["returncode"]
    for failure in failures:
        if failure["role"] is not None and failure["role"] not in operands.keys() | outputs.keys():
            raise ContractError("native_blast_bundle_failure_role_conflict")
        if failure["stage"] == "outputs" and (failure["role"] not in outputs
                or failure["detail"].get("relative_path") != outputs[failure["role"]]["relative_path"]):
            raise ContractError("native_blast_bundle_failure_output_conflict")
        if failure["code"] == "native_blast_nonzero_returncode" and (rc in (None, 0)
                or failure["detail"].get("returncode") != rc):
            raise ContractError("native_blast_bundle_failure_returncode_conflict")
    if rc is not None:
        if (any(row["stage"] in {"software", "inputs", "staging"} for row in failures)
                or software["actual_sha256"] is None
                or software["actual_sha256"].lower() != software["expected_sha256"].lower()
                or any(row["actual_sha256"] is None or row["actual_sha256"].lower() != row["expected_sha256"].lower()
                    or row["size_bytes"] != row["expected_size_bytes"] for row in bundle["inputs"])):
            raise ContractError("native_blast_executed_input_or_software_conflict")
        if rc != 0 and not any(row["code"] == "native_blast_nonzero_returncode" for row in failures):
            raise ContractError("native_blast_bundle_execution_failure_missing")
    elif not any(row["stage"] in {"software", "inputs", "staging", "execution"} for row in failures):
        raise ContractError("native_blast_bundle_execution_failure_missing")
    if any(not any(f["stage"] == "outputs" and f["role"] == role for f in failures)
            for role in outputs.keys() - seen):
        raise ContractError("native_blast_bundle_missing_output_failure_required")
    return bundle


def _target_plan(target, plan=None):
    plan = (local_blast_plan(target["assignment"], target["execution_id"])
        if plan is None else _plan(plan))
    expected = {"run_id": target.get("run_id"), "episode_id": target.get("origin_episode_id"),
        "resource_id": target.get("resource_id"), "execution_id": target.get("execution_id"),
        "requested_job_sha256": target.get("request_sha256")}
    if any(value is None or plan["identity"][key] != value for key, value in expected.items()):
        raise ContractError("native_blast_original_target_owner_conflict")
    owner, assignment = plan["identity"], target["assignment"]
    expected_root = (Path(assignment["workspace"]) / ".episode-operations" /
        native_blast_digest({"run": owner["run_id"], "episode": owner["episode_id"]}) /
        native_blast_digest(owner["operation_key"]))
    if (assignment.get("resource_kind") != "local" or assignment.get("resource_id") != owner["resource_id"]
            or assignment.get("requested_job") != plan["requested_job"]
            or target["execution_id"] != str(expected_root / "native.json")
            or plan["attempt_directory"] != str(expected_root / "blast-attempt")
            or owner["attempt_id"] != native_blast_digest(owner["operation_key"])):
        raise ContractError("native_blast_original_target_owner_conflict")
    for field, key in (("original_operation_key", "operation_key"), ("attempt_id", "attempt_id")):
        if target.get(field) is not None and target[field] != plan["identity"][key]:
            raise ContractError("native_blast_original_target_owner_conflict")
    return plan


def _capture_shape(value):
    capture = finite_json_copy(value)
    fields = {"version", "bundle_artifact_ref", "bundle_validated", "artifacts", "invalid_artifacts", "failures", "complete"}
    if (type(capture) is not dict or set(capture) != fields or capture["version"] != VERSION
            or type(capture["bundle_validated"]) is not bool or type(capture["complete"]) is not bool
            or capture["bundle_artifact_ref"] is not None and (type(capture["bundle_artifact_ref"]) is not str
                or not capture["bundle_artifact_ref"])):
        raise ContractError("native_blast_capture_record_invalid")
    seen = set()
    for category in ("artifacts", "invalid_artifacts"):
        if type(capture[category]) is not list:
            raise ContractError("native_blast_capture_record_invalid")
        for row in capture[category]:
            if (type(row) is not dict or set(row) != {"role", "format", "relative_path", "artifact_ref"}
                    or any(type(v) is not str or not v for v in row.values())
                    or (row["role"], row["relative_path"]) in seen):
                raise ContractError("native_blast_capture_record_invalid")
            seen.add((row["role"], row["relative_path"]))
    if (type(capture["failures"]) is not list or any(type(row) is not dict
            or set(row) != {"stage", "code", "record_key"} or row["record_key"] is not None
            or any(type(row[k]) is not str or not row[k] for k in ("stage", "code"))
            for row in capture["failures"]) or capture["complete"] != (capture["bundle_validated"] and not capture["failures"])
            or capture["bundle_validated"] and capture["bundle_artifact_ref"] is None
            or capture["invalid_artifacts"] and not capture["failures"]):
        raise ContractError("native_blast_capture_record_invalid")
    return capture


def _retained(store, reference):
    path = artifact_path(store, reference)
    if path.stat().st_size != store.get(reference)["size"]:
        raise ContractError("native_blast_retained_artifact_size_mismatch")
    return path


def _retained_rows(store, capture, bundle):
    selected, mandatory = {}, set()
    for row in bundle["inputs"]:
        key = row["role"], row["relative_path"]
        selected[key] = (row["format"], row["actual_sha256"], row["size_bytes"],
            row["expected_sha256"], row["expected_size_bytes"])
        if row["actual_sha256"] is not None:
            mandatory.add(key)
    for row in bundle["artifacts"]:
        key = row["role"], row["relative_path"]
        selected[key] = (row["format"], row["sha256"], row["size_bytes"], row["sha256"], row["size_bytes"])
        mandatory.add(key)
    seen = set()
    for category in ("artifacts", "invalid_artifacts"):
        for row in capture[category]:
            key = row["role"], row["relative_path"]
            if key not in selected or row["format"] != selected[key][0]:
                raise ContractError("native_blast_capture_artifact_association_conflict")
            seen.add(key)
            _retained(store, row["artifact_ref"])
            if category == "artifacts":
                actual = store.get(row["artifact_ref"])
                _, sha, size, expected_sha, expected_size = selected[key]
                if (sha is None or sha.lower() != actual["sha256"].lower() or size != actual["size"]
                        or expected_sha.lower() != actual["sha256"].lower() or expected_size != actual["size"]):
                    raise ContractError("native_blast_capture_artifact_association_conflict")
    if capture["complete"] and seen != mandatory:
        raise ContractError("native_blast_capture_artifact_association_conflict")


def _file(root, relative):
    path = root / relative
    if root.resolve() != root or path.resolve() != path or not path.is_relative_to(root) or not path.is_file():
        raise ContractError("native_blast_bundle_file_unavailable_or_escaped:" + relative)
    return path


def _capture_file(store, result, root, row, *, sha, size, invalid=False):
    item = {key: row[key] for key in ("role", "format", "relative_path")}
    reference = None
    try:
        path = _file(root, row["relative_path"])
        reference = artifact_file(store, path)
        retained = artifact_path(store, reference)
        captured = store.get(reference)
        if (invalid or captured["sha256"].lower() != (sha or "").lower()
                or captured["size"] != size or retained.stat().st_size != size):
            raise ContractError("native_blast_sealed_artifact_digest_mismatch:" + row["relative_path"])
        result["artifacts"].append({**item, "artifact_ref": reference})
    except (ValueError, OSError) as error:
        if reference is not None:
            result["invalid_artifacts"].append({**item, "artifact_ref": reference})
        result["failures"].append({"stage": "capture", "code": str(error) if isinstance(error, ValueError)
            else "native_blast_bundle_file_unavailable:" + row["relative_path"], "record_key": None})


def capture_local_bundle(store, *, target, directory):
    """Acquire original complete files once; replay only checks retained custody."""
    if not is_native_blast_target(target):
        raise ContractError("native_blast_local_capture_binding_required")
    target = finite_json_copy(target)
    base = {k: v for k, v in target.items() if k not in {"original_operation_key", "attempt_id"}}
    validate_target(base)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "capture.json"
    _immutable(directory / "capture-intent.json", {"target": target})
    if receipt.exists():
        saved = _capture_shape(_read(receipt))
        plan = _target_plan(target, _read(directory / "capture-plan.json"))
        for reference in [saved["bundle_artifact_ref"], *[row["artifact_ref"]
                for row in saved["artifacts"] + saved["invalid_artifacts"]]]:
            if reference is not None:
                _retained(store, reference)
        if saved["bundle_validated"]:
            bundle = validate_original_bundle(json.loads(_retained(store, saved["bundle_artifact_ref"]).read_bytes()), plan)
            _retained_rows(store, saved, bundle)
        return saved
    plan = _target_plan(target)
    _immutable(directory / "capture-plan.json", plan)
    root = Path(plan["attempt_directory"])
    result = {"version": VERSION, "bundle_artifact_ref": None, "bundle_validated": False,
        "artifacts": [], "invalid_artifacts": [], "failures": [], "complete": False}
    bundle = None
    try:
        if json.loads(_file(root, OWNER_NAME).read_bytes()) != plan:
            raise ContractError("native_blast_original_attempt_owner_conflict")
        reference = artifact_file(store, _file(root, "bundle.json"), "application/json")
        result["bundle_artifact_ref"] = reference
        bundle = validate_original_bundle(json.loads(artifact_path(store, reference).read_bytes()), plan)
        result["bundle_validated"] = True
    except (ValueError, OSError) as error:
        result["failures"].append({"stage": "capture", "code": str(error) if isinstance(error, ValueError)
            else "native_blast_sealed_bundle_unavailable", "record_key": None})
    if bundle is None:
        # Preserve supplied input bytes and unsealed partial outputs without
        # presenting an unqualified manifest or report as original sealed data.
        job = plan["requested_job"]["native_blast"]
        for row in job["operands"]:
            staged = {**row, "relative_path": "inputs/" + row["role"] + ".fa"}
            if (root / staged["relative_path"]).exists():
                _capture_file(store, result, root, staged, sha=row["sha256"], size=row["size_bytes"])
        for row in job["outputs"]:
            if (root / row["relative_path"]).exists():
                _capture_file(store, result, root, row, sha=None, size=None, invalid=True)
    else:
        for row in bundle["inputs"]:
            if row["actual_sha256"] is None and not (root / row["relative_path"]).exists():
                continue  # The producer recorded no staged file, not an empty file.
            invalid = (row["actual_sha256"] is None
                or row["actual_sha256"].lower() != row["expected_sha256"].lower()
                or row["size_bytes"] != row["expected_size_bytes"])
            _capture_file(store, result, root, row, sha=row["actual_sha256"], size=row["size_bytes"], invalid=invalid)
        for row in bundle["artifacts"]:
            _capture_file(store, result, root, row, sha=row["sha256"], size=row["size_bytes"])
    result["complete"] = result["bundle_validated"] and not result["failures"]
    _immutable(receipt, result)
    return result


def original_source_payload(*, bundle, capture, prepared):
    capture = _capture_shape(capture)
    if (not capture["bundle_validated"] or type(bundle) is not dict
            or bundle.get("version") != "native_blast_bundle_v1"):
        raise ContractError("native_blast_source_validated_manifest_required")
    auxiliary = [row["artifact_ref"] for row in capture["artifacts"] + capture["invalid_artifacts"]]
    if prepared is not None and prepared.get("source_grading_artifact_ref") is not None:
        auxiliary.append(prepared["source_grading_artifact_ref"])
    return {"provider": PROVIDER, "accession": "native_blast_" + native_blast_digest(bundle["identity"]),
        "uri": None, "artifact_ref": capture["bundle_artifact_ref"], "text_ref": None,
        "request_ref": None, "version": "native_blast_bundle_v1", "retrieved_at": bundle["finished_at"],
        "auxiliary_artifact_refs": sorted(set(auxiliary))}


def publish_original_source(store, *, bundle, capture, prepared):
    payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    retained = json.loads(_retained(store, payload["artifact_ref"]).read_bytes())
    if native_blast_digest(retained) != native_blast_digest(bundle):
        raise ContractError("native_blast_source_bundle_association_conflict")
    _retained_rows(store, capture, bundle)
    for reference in payload["auxiliary_artifact_refs"]:
        _retained(store, reference)
    return store.put("source", payload, origin="tool")["id"]


__all__ = ["is_native_blast_target", "validate_original_bundle", "capture_local_bundle",
    "original_source_payload", "publish_original_source", "VERSION", "ORIGIN"]
