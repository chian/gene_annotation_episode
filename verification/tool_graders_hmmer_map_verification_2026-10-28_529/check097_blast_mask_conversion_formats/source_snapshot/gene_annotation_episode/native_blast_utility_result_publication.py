"""Retain original utility readings and authenticate frozen selected returns.

The original source record is never updated. Preparation and selection each have
one immutable worker receipt; an unfinished intent is not permission to rerun.
Saved validation authenticates hashes and those receipts without reopening native
paths, parsing native data, recalculating a payload, or starting a worker.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

from .acquisition import AcquisitionError
from .blast_utility_contracts import validate_blast_utility_record as core
from .blast_utility_result_views import (
    PROJECTION_FIELDS, validate_blast_utility_projection, validate_blast_utility_result_selector,
)
from .domain import ContractError, canonical
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .native_blast_utility_acquisition import _validate_saved
from .native_blast_utility_contracts import finite_json_copy, native_blast_digest
from .native_blast_utility_result_worker import (
    CONTEXT_FIELDS, OUTPUT_FILES, PLAN_VERSION, RESULT_SCHEMAS, diagnostic, failure,
    qualified_utility_context, unique_failures, validate_context, validate_worker_manifest, validate_worker_plan,
)
from .native_hmmer_preparation_acquisition import _capture_file, _decode, _directory, _read_record, _retained
from .practical_execution_state import _immutable
from .tool_grading_artifacts import retain_tool_grading


PREFIX = "native_blast_utility_"
PREPARED_VERSION = PREFIX + "prepared_v1"
PUBLICATION_VERSION = PREFIX + "publication_v1"
RETAINED_VERSION = PREFIX + "retained_v1"
PROJECTION_VERSION = PREFIX + "projection_artifact_v1"
RECEIPT_VERSION = PREFIX + "worker_receipt_v1"
PAYLOAD_REFS = {"result": "result_artifact_ref", "prepared_database": "prepared_database_projection_artifact_ref",
                "prepared_manifest": "prepared_database_manifest_artifact_ref"}
_PREPARED_FIELDS = {"version", "source_ref", "bundle_artifact_ref", "source_grading_artifact_ref",
    "operation", "native_outcome", "occurrences", "failures", "worker_completed", *PAYLOAD_REFS.values()}
_STABLE_FIELDS = {"version", "capture", "payload_artifacts", "worker_receipt_artifact_ref",
                  *(_PREPARED_FIELDS - {"version", "source_grading_artifact_ref"})}
_PUBLICATION_FIELDS = {"version", "source_ref", "prepared_sha256", "selector", "projection_artifact_ref", *PROJECTION_FIELDS}


def _error(code):
    raise ContractError(PREFIX + code)


def _shape(value, fields, code):
    if type(value) is not dict or set(value) != fields:
        _error(code)


def _artifact_ref(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or re.fullmatch(r"artifact_[0-9a-f]{64}", value) is None:
        _error("result_artifact_reference_invalid")


def _descriptor(store, reference):
    meta = _retained(store, reference)
    return {"artifact_ref": reference, "sha256": meta["sha256"], "size_bytes": meta["size"]}


def _json(store, reference):
    _descriptor(store, reference)
    return _decode(store.get_artifact(reference))


def _file(store, reference):
    row = _descriptor(store, reference)
    return {"path": str(store.path / "artifacts" / row["sha256"][:2] / row["sha256"]),
            **{k: row[k] for k in ("sha256", "size_bytes")}}


def validate_utility_prepared(prepared):
    """Closed structural validation; original custody uses the Store-aware port."""
    prepared = finite_json_copy(prepared)
    _shape(prepared, _PREPARED_FIELDS, "prepared_fields_invalid")
    if (prepared["version"] != PREPARED_VERSION or type(prepared["worker_completed"]) is not bool
            or type(prepared["source_ref"]) is not str or not prepared["source_ref"]):
        _error("prepared_version_or_source_invalid")
    _artifact_ref(prepared["bundle_artifact_ref"])
    _artifact_ref(prepared["source_grading_artifact_ref"])
    for key in PAYLOAD_REFS.values():
        _artifact_ref(prepared[key], nullable=True)
    core("Operation", prepared["operation"])
    core("NativeOutcome", prepared["native_outcome"])
    if type(prepared["occurrences"]) is not list:
        _error("prepared_occurrences_invalid")
    rows = [core("ArtifactOccurrence", row) for row in prepared["occurrences"]]
    ids = {r["occurrence_id"] for r in rows}
    if len(ids) != len(rows) or len({(r["direction"], r["role"], r["ordinal"]) for r in rows}) != len(rows):
        _error("prepared_occurrences_duplicate")
    if unique_failures(prepared["failures"]) != prepared["failures"]:
        _error("prepared_duplicate_failures")
    if any(row["occurrence_id"] is not None and row["occurrence_id"] not in ids or
           row["native_returncode"] is not None and row["native_returncode"] != prepared["native_outcome"]["returncode"]
           for row in prepared["failures"]):
        _error("prepared_failure_context_conflict")
    projection, manifest = prepared["prepared_database_projection_artifact_ref"], prepared["prepared_database_manifest_artifact_ref"]
    if (projection is not None and (prepared["result_artifact_ref"] is None or
            prepared["operation"]["mode"] != "create_sequence_database") or manifest is not None and projection is None):
        _error("prepared_database_payload_conflict")
    return prepared


def _stable(store, prepared):
    envelope = _json(store, prepared["source_grading_artifact_ref"])
    _shape(envelope, {"schema", "provider", "native_artifact_ref", "grading"}, "retained_envelope_invalid")
    if (envelope["schema"] != "tool_grading_artifact_v1" or envelope["provider"] != "episode.execution_result"
            or envelope["native_artifact_ref"] != prepared["bundle_artifact_ref"]):
        _error("retained_envelope_identity_conflict")
    stable = envelope["grading"]
    _shape(stable, _STABLE_FIELDS, "retained_grading_fields_invalid")
    if stable["version"] != RETAINED_VERSION or any(stable[key] != prepared[key]
            for key in _PREPARED_FIELDS - {"version", "source_grading_artifact_ref"}):
        _error("prepared_retained_identity_conflict")
    return stable


def _validate_receipt(store, reference, *, task):
    receipt = _json(store, reference)
    _shape(receipt, {"version", "plan", "returncode", "manifest", "outputs", "failures", "diagnostic_artifact_refs", "exception"},
           "worker_receipt_fields_invalid")
    plan = validate_worker_plan(receipt["plan"])
    if receipt["version"] != RECEIPT_VERSION or plan["task"] != task:
        _error("worker_receipt_identity_conflict")
    if receipt["returncode"] is not None and type(receipt["returncode"]) is not int:
        _error("worker_receipt_returncode_invalid")
    if unique_failures(receipt["failures"]) != receipt["failures"]:
        _error("worker_receipt_failures_invalid")
    if receipt["exception"] is not None and (type(receipt["exception"]) is not dict or
            set(receipt["exception"]) != {"exception_type", "detail"} or
            any(type(v) is not str for v in receipt["exception"].values())):
        _error("worker_receipt_exception_invalid")
    manifest = None if receipt["manifest"] is None else validate_worker_manifest(receipt["manifest"], plan)
    if type(receipt["outputs"]) is not dict or manifest is None and receipt["outputs"]:
        _error("worker_receipt_outputs_invalid")
    for role, descriptor in receipt["outputs"].items():
        if (manifest is None or role not in manifest["outputs"] or type(descriptor) is not dict
                or set(descriptor) != {"artifact_ref", "sha256", "size_bytes"}
                or descriptor != _descriptor(store, descriptor["artifact_ref"])):
            _error("worker_receipt_output_identity_conflict")
        if any(descriptor[k] != manifest["outputs"][role][k] for k in ("sha256", "size_bytes")):
            _error("worker_receipt_output_bytes_conflict")
    if type(receipt["diagnostic_artifact_refs"]) is not list or any(type(v) is not str for v in receipt["diagnostic_artifact_refs"]):
        _error("worker_receipt_diagnostics_invalid")
    for ref in receipt["diagnostic_artifact_refs"]:
        _descriptor(store, ref)
    original = plan["context"]["failures"] + ([] if manifest is None else manifest["failures"])
    if any(row not in receipt["failures"] for row in original):
        _error("worker_receipt_original_failures_missing")
    return receipt


def _completed(receipt):
    return bool(receipt["returncode"] == 0 and receipt["manifest"] is not None and receipt["manifest"]["completed"]
        and set(receipt["outputs"]) == set(receipt["manifest"]["outputs"]) and receipt["exception"] is None)


def _same_file_identity(left, right):
    return (left is None and right is None or left is not None and right is not None
            and all(left[k] == right[k] for k in ("sha256", "size_bytes")))


def validate_prepared_utility_result(store, prepared):
    """Validate retained custody and original receipts, never native data readers."""
    prepared = validate_utility_prepared(prepared)
    stable = _stable(store, prepared)
    capture = _validate_saved(store, stable["capture"])
    if capture["source_ref"] != prepared["source_ref"] or capture["bundle_artifact_ref"] != prepared["bundle_artifact_ref"]:
        _error("prepared_original_capture_conflict")
    original = qualified_utility_context(capture)
    if any(prepared[k] != original[k] for k in ("operation", "native_outcome", "occurrences")):
        _error("prepared_original_context_conflict")
    receipt = _validate_receipt(store, stable["worker_receipt_artifact_ref"], task="parse_original")
    plan = receipt["plan"]
    if plan["capture"] != capture or plan["context"] != original:
        _error("prepared_worker_context_conflict")
    if not _same_file_identity(plan["bundle_file"], _file(store, prepared["bundle_artifact_ref"])):
        _error("prepared_worker_bundle_identity_conflict")
    expected = [{"occurrence_id": row["occurrence_id"], **_file(store, row["artifact_ref"])} for row in original["occurrences"]]
    if [{k: v for k, v in row.items() if k != "path"} for row in plan["files"]] != [
            {k: v for k, v in row.items() if k != "path"} for row in expected]:
        _error("prepared_worker_file_identity_conflict")
    if stable["payload_artifacts"] != receipt["outputs"] or prepared["failures"] != receipt["failures"]:
        _error("prepared_worker_result_conflict")
    for role, key in PAYLOAD_REFS.items():
        if prepared[key] != receipt["outputs"].get(role, {}).get("artifact_ref"):
            _error("prepared_payload_artifact_conflict")
    if prepared["worker_completed"] != _completed(receipt):
        _error("prepared_worker_completion_conflict")
    return prepared


def _begin(directory, name, intent, result_file):
    directory = _directory(directory) / name
    if directory.exists():
        if _read_record(directory, "intent.json") != intent:
            _error("result_directory_identity_conflict")
        if (directory / "failure.json").is_file():
            failed = _read_record(directory, "failure.json")
            if failed.get("intent") != intent:
                _error("result_failure_identity_conflict")
            _error("selected_projection_worker_failed")
        if not (directory / result_file).is_file():
            _error("original_result_work_incomplete")
        return directory, _read_record(directory, result_file)
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", intent)
    return directory, None


def _policy(policy, capture):
    if not isinstance(policy, LocalJobPolicy):
        _error("local_job_policy_required")
    if policy.to_dict() != capture["plan"]["policy"]:
        _error("result_allocation_conflict")


def _execute_worker(store, directory, plan, policy):
    plan = validate_worker_plan(plan)
    _immutable(directory / "plan.json", plan)
    failures, rc, exception = deepcopy(plan["context"]["failures"]), None, None
    stage = "parse" if plan["task"] == "parse_original" else "projection"
    try:
        for name in ("tmp", "cache"):
            (directory / name).mkdir()
        check_scratch_budget(directory, policy)
        result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_blast_utility_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1",
                **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")}, "XDG_CACHE_HOME": str(directory / "cache")})
        rc = result.returncode
        _immutable(directory / "execution-metadata.json", result.metadata)
        if rc != 0:
            failures.append(failure(stage, "semantic_validation_unavailable"))
    except (AcquisitionError, OSError, ValueError) as error:
        exception = diagnostic(error)
        failures.append(failure(stage, "semantic_validation_unavailable"))
    manifest, outputs = None, {}
    try:
        manifest = validate_worker_manifest(_read_record(directory, "worker-result.json"), plan)
        failures.extend(manifest["failures"])
        for role, descriptor in manifest["outputs"].items():
            reference = _capture_file(store, directory, descriptor["filename"], "application/json")
            actual = _descriptor(store, reference)
            if any(actual[k] != descriptor[k] for k in ("sha256", "size_bytes")):
                _error("worker_output_bytes_conflict")
            outputs[role] = actual
    except (OSError, ValueError) as error:
        exception = diagnostic(error)
        failures.append(failure(stage, "semantic_validation_unavailable"))
    diagnostics = [_capture_file(store, directory, name) for name in
        ("worker.stdout", "worker.stderr", "worker-result.json", "execution-metadata.json") if (directory / name).is_file()]
    receipt = {"version": RECEIPT_VERSION, "plan": plan, "returncode": rc, "manifest": manifest,
        "outputs": outputs, "failures": unique_failures(failures), "diagnostic_artifact_refs": diagnostics, "exception": exception}
    reference = store.artifact(canonical(receipt), "application/json")
    _immutable(directory / "worker-receipt.json", {"artifact_ref": reference})
    return receipt, reference


def prepare_native_blast_utility_result(store, *, capture, directory, policy):
    capture = _validate_saved(store, capture)
    context = qualified_utility_context(capture)
    _policy(policy, capture)
    intent = {"capture": capture, "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-blast-utility-preparation", intent, "prepared.json")
    if saved is not None:
        return validate_prepared_utility_result(store, saved)
    plan = {"version": PLAN_VERSION, "task": "parse_original", "directory": str(directory), "capture": capture,
        "context": context, "bundle_file": _file(store, capture["bundle_artifact_ref"]),
        "files": [{"occurrence_id": row["occurrence_id"], **_file(store, row["artifact_ref"])} for row in context["occurrences"]]}
    receipt, reference = _execute_worker(store, directory, plan, policy)
    prepared = {"version": PREPARED_VERSION, "source_ref": capture["source_ref"], "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "source_grading_artifact_ref": None, **{k: context[k] for k in ("operation", "native_outcome", "occurrences")},
        "failures": receipt["failures"], "worker_completed": _completed(receipt),
        **{key: receipt["outputs"].get(role, {}).get("artifact_ref") for role, key in PAYLOAD_REFS.items()}}
    stable = {"version": RETAINED_VERSION, "capture": capture, "payload_artifacts": receipt["outputs"],
        "worker_receipt_artifact_ref": reference,
        **{k: prepared[k] for k in _PREPARED_FIELDS - {"version", "source_grading_artifact_ref"}}}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=capture["bundle_artifact_ref"], grading=stable)
    prepared = validate_prepared_utility_result(store, prepared)
    _immutable(directory / "prepared.json", prepared)
    return prepared


def _projection_context(prepared, stable):
    original = qualified_utility_context(stable["capture"])
    return validate_context({**original, "failures": prepared["failures"]})


def _saved_descriptors(store, prepared):
    result = []
    for kind, key, schema in (("result", "result_artifact_ref", RESULT_SCHEMAS[prepared["operation"]["mode"]]),
            ("prepared_database", "prepared_database_manifest_artifact_ref", "native_blast_standard_prepared_database_manifest_v1")):
        if prepared[key] is not None:
            result.append({"source_ref": prepared["source_ref"], "kind": kind, **_descriptor(store, prepared[key]), "schema": schema})
    return result


def _source(source_ref, prepared):
    if source_ref != prepared["source_ref"]:
        _error("publication_original_source_conflict")


def publish_selected_utility_result(store, *, source_ref, prepared, selector, directory, policy):
    prepared = validate_prepared_utility_result(store, prepared)
    _source(source_ref, prepared)
    stable = _stable(store, prepared)
    _policy(policy, stable["capture"])
    selector = validate_blast_utility_result_selector(selector, operation=prepared["operation"])
    intent = {"source_ref": source_ref, "prepared_sha256": native_blast_digest(prepared), "selector": selector, "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-blast-utility-projection", intent, "publication.json")
    if saved is not None:
        return validate_utility_publication(store, source_ref=source_ref, prepared=prepared, selector=selector, publication=saved)
    plan = {"version": PLAN_VERSION, "task": "project_saved", "directory": str(directory), "source_ref": source_ref,
        "context": _projection_context(prepared, stable), "selector": selector, "saved_data": _saved_descriptors(store, prepared),
        "files": {role: _file(store, prepared[key]) if prepared[key] is not None else None for role, key in PAYLOAD_REFS.items()}}
    receipt, reference = _execute_worker(store, directory, plan, policy)
    if not _completed(receipt) or "projection" not in receipt["outputs"]:
        _immutable(directory / "failure.json", {"intent": intent, "code": "selected_projection_worker_failed", "worker_receipt_artifact_ref": reference})
        _error("selected_projection_worker_failed")
    selected_ref = receipt["outputs"]["projection"]["artifact_ref"]
    selected = validate_blast_utility_projection(_json(store, selected_ref), source_ref=source_ref,
        operation=prepared["operation"], native_outcome=prepared["native_outcome"], selector=selector, occurrences=prepared["occurrences"])
    envelope = {"version": PROJECTION_VERSION, "source_ref": source_ref, "prepared_sha256": native_blast_digest(prepared),
        "selector": selector, "projection": selected, "worker_receipt_artifact_ref": reference, "selected_projection_artifact_ref": selected_ref}
    projection_ref = store.artifact(canonical(envelope), "application/json")
    publication = {"version": PUBLICATION_VERSION, "source_ref": source_ref, "prepared_sha256": native_blast_digest(prepared),
        "selector": selector, "projection_artifact_ref": projection_ref, **selected}
    publication = validate_utility_publication(store, source_ref=source_ref, prepared=prepared, selector=selector, publication=publication)
    _immutable(directory / "publication.json", publication)
    return publication


def validate_utility_publication(store, *, source_ref, prepared, selector, publication):
    """Validate frozen values and grants; do not invoke a worker or result reader."""
    prepared = validate_prepared_utility_result(store, prepared)
    _source(source_ref, prepared)
    stable = _stable(store, prepared)
    selector = validate_blast_utility_result_selector(selector, operation=prepared["operation"])
    publication = finite_json_copy(publication)
    _shape(publication, _PUBLICATION_FIELDS, "publication_fields_invalid")
    if (publication["version"] != PUBLICATION_VERSION or publication["source_ref"] != source_ref
            or publication["selector"] != selector or publication["prepared_sha256"] != native_blast_digest(prepared)):
        _error("publication_original_selection_conflict")
    envelope = _json(store, publication["projection_artifact_ref"])
    _shape(envelope, {"version", "source_ref", "prepared_sha256", "selector", "projection", "worker_receipt_artifact_ref",
                     "selected_projection_artifact_ref"}, "projection_envelope_invalid")
    if envelope["version"] != PROJECTION_VERSION or any(envelope[k] != publication[k] for k in ("source_ref", "prepared_sha256", "selector")):
        _error("projection_envelope_identity_conflict")
    selected = validate_blast_utility_projection(envelope["projection"], source_ref=source_ref,
        operation=prepared["operation"], native_outcome=prepared["native_outcome"], selector=selector, occurrences=prepared["occurrences"])
    if any(publication[k] != selected[k] for k in PROJECTION_FIELDS) or _json(store, envelope["selected_projection_artifact_ref"]) != selected:
        _error("publication_frozen_values_conflict")
    available = _saved_descriptors(store, prepared)
    by_kind = {row["kind"]: row for row in available}
    if selected["saved_data"] != [by_kind[k] for k in selector["saved_data"] if k in by_kind]:
        _error("publication_saved_data_grant_conflict")
    receipt = _validate_receipt(store, envelope["worker_receipt_artifact_ref"], task="project_saved")
    plan = receipt["plan"]
    if (plan["source_ref"] != source_ref or plan["selector"] != selector or plan["saved_data"] != available
            or plan["context"] != _projection_context(prepared, stable)):
        _error("publication_worker_context_conflict")
    for role, key in PAYLOAD_REFS.items():
        expected = None if prepared[key] is None else _file(store, prepared[key])
        if not _same_file_identity(plan["files"][role], expected):
            _error("publication_saved_input_conflict")
    if not _completed(receipt) or receipt["outputs"]["projection"]["artifact_ref"] != envelope["selected_projection_artifact_ref"]:
        _error("publication_worker_result_conflict")
    return publication


__all__ = ["prepare_native_blast_utility_result", "validate_utility_prepared", "validate_prepared_utility_result",
           "publish_selected_utility_result", "validate_utility_publication"]
