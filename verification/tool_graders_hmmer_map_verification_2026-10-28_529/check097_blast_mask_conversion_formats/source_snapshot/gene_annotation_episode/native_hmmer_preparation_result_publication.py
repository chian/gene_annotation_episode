"""Retain preparation numbers and publish exactly the requested saved facts.

Capture must already be sealed. Native files never reopen here, and the host
never hydrates a full numerical sheet. Separate bounded workers grade retained
bytes or select retained values. Neither path creates an observation or credit.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

from .acquisition import AcquisitionError
from .domain import ContractError, canonical, validate_schema
from .hmmer_preparation_result_views import (
    ARTIFACT_SCHEMA, POPULATION_SCHEMA, ROW_SCHEMA, validate_preparation_result_selector,
)
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .native_infernal_contracts import finite_json_copy, native_infernal_digest
from .native_hmmer_preparation_acquisition import (
    _capture_file, _decode, _directory, _read_record, _retained, _shape, _validate_rows,
    capture_local_bundle, original_source_payload, validate_original_bundle,
)
from .native_hmmer_preparation_result_worker import (
    MANIFEST_VERSION, NUMERICAL_FILES, PLAN_VERSION, PREFIX, effective_metadata,
    eligible_occurrences, grading_context, exception_code, exception_diagnostic, failure,
    qualified_occurrences, unique_failures, validate_failures,
)
from .practical_execution_state import _immutable
from .tool_grading_artifacts import retain_tool_grading


PREPARED_VERSION = PREFIX + "prepared_v1"
RETAINED_VERSION = PREFIX + "retained_grading_v1"
_NUMERICAL = ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")
_PREPARED_FIELDS = {"version", "bundle_artifact_ref", "source_grading_artifact_ref",
    *_NUMERICAL, "occurrences", "failures", "graded"}
_STABLE_FIELDS = {"schema", "original_plan", "capture", "bundle_sha256", "original_parameters",
    "effective_metadata", "grading_context", "occurrences", *_NUMERICAL, "numerical_artifacts", "failures", "graded"}
_PUBLICATION_FIELDS = {"record_refs", "rows", "artifacts", "population", "failures", "projection_artifact_ref"}


def _error(code):
    raise ContractError(PREFIX + code)


def _artifact_path(store, reference, *, verify=True):
    row = _retained(store, reference) if verify else store._require(reference, {"artifact"})
    if reference != "artifact_" + row["sha256"] or type(row["size"]) is not int or row["size"] < 0:
        _error("retained_artifact_identity_conflict")
    return store.path / "artifacts" / row["sha256"][:2] / row["sha256"]


def _descriptor(store, reference):
    row = store._require(reference, {"artifact"})
    return {"artifact_ref": reference, "sha256": row["sha256"], "size_bytes": row["size"]}


def _worker_file(store, reference):
    descriptor = _descriptor(store, reference)
    return {"path": str(_artifact_path(store, reference)),
            **{k: descriptor[k] for k in ("sha256", "size_bytes")}}


def _prepared(bundle_ref=None, *, failures=()):
    return {"version": PREPARED_VERSION, "bundle_artifact_ref": bundle_ref,
        "source_grading_artifact_ref": None, **{k: None for k in _NUMERICAL},
        "occurrences": [], "failures": list(failures), "graded": False}


def _prepared_shape(value):
    prepared = finite_json_copy(value)
    if (type(prepared) is not dict or set(prepared) != _PREPARED_FIELDS
            or prepared["version"] != PREPARED_VERSION or type(prepared["graded"]) is not bool
            or type(prepared["occurrences"]) is not list):
        _error("prepared_grading_invalid")
    validate_failures(prepared["failures"])
    for key in ("bundle_artifact_ref", "source_grading_artifact_ref", *_NUMERICAL):
        if prepared[key] is not None and (type(prepared[key]) is not str or not prepared[key]):
            _error("prepared_grading_reference_invalid")
    return prepared


def _stable(store, prepared):
    reference = prepared["source_grading_artifact_ref"]
    if reference is None:
        _error("source_grading_required")
    _artifact_path(store, reference)
    envelope = _decode(store.get_artifact(reference))
    if (type(envelope) is not dict or set(envelope) != {"schema", "provider", "native_artifact_ref", "grading"}
            or envelope["schema"] != "tool_grading_artifact_v1"
            or envelope["provider"] != "episode.execution_result"
            or envelope["native_artifact_ref"] != prepared["bundle_artifact_ref"]):
        _error("source_grading_custody_conflict")
    stable = envelope["grading"]
    if type(stable) is not dict or set(stable) != _STABLE_FIELDS or stable["schema"] != RETAINED_VERSION:
        _error("source_grading_envelope_invalid")
    return stable


def validate_prepared_grading(store, prepared, *, bundle, verify_files=True):
    """Validate small custody records and stream byte checks; never parse a sheet."""
    prepared = _prepared_shape(prepared)
    if type(verify_files) is not bool:
        _error("verify_files_boolean_required")
    stable = _stable(store, prepared)
    bundle = validate_original_bundle(bundle, stable["original_plan"])
    _artifact_path(store, prepared["bundle_artifact_ref"], verify=verify_files)
    retained_bundle = _decode(store.get_artifact(prepared["bundle_artifact_ref"]))
    if (retained_bundle != bundle or stable["bundle_sha256"] != native_infernal_digest(bundle)
            or any(native_infernal_digest(stable[k]) != native_infernal_digest(prepared[k])
                   for k in (*_NUMERICAL, "occurrences", "failures", "graded"))):
        _error("prepared_grading_identity_conflict")
    capture = _shape(stable["capture"])
    if verify_files:
        _validate_rows(store, capture, bundle)
    occurrences, custody_failures = qualified_occurrences(bundle, prepared["bundle_artifact_ref"], capture)
    # A saved publication keeps its original interpretation. Absence of this
    # optional field is historical absence, never permission to upgrade it.
    metadata, metadata_failures = effective_metadata(bundle, occurrences,
        include_map_context="map_reconstruction_context" in stable["effective_metadata"])
    if (native_infernal_digest(occurrences) != native_infernal_digest(prepared["occurrences"])
            or native_infernal_digest(stable["effective_metadata"]) != native_infernal_digest(metadata)
            or native_infernal_digest(stable["grading_context"]) != native_infernal_digest(grading_context(bundle, occurrences, metadata))
            or native_infernal_digest(stable["original_parameters"]) != native_infernal_digest(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"])
            or any(r not in prepared["failures"] for r in [*custody_failures, *metadata_failures])):
        _error("prepared_grading_custody_conflict")
    for occurrence in occurrences:
        _artifact_path(store, occurrence["artifact_ref"], verify=verify_files)
        if _descriptor(store, occurrence["artifact_ref"]) != {k: occurrence[k] for k in ("artifact_ref", "sha256", "size_bytes")}:
            _error("prepared_occurrence_bytes_conflict")
    numerical = stable["numerical_artifacts"]
    if type(numerical) is not dict or set(numerical) != {k.removesuffix("_artifact_ref") for k in _NUMERICAL if prepared[k] is not None}:
        _error("prepared_numerical_artifact_population_conflict")
    for role, descriptor in numerical.items():
        reference = prepared[role + "_artifact_ref"]
        if native_infernal_digest(descriptor) != native_infernal_digest(_descriptor(store, reference)):
            _error("prepared_numerical_artifact_identity_conflict")
        _artifact_path(store, reference, verify=verify_files)
    if prepared["graded"] and any(prepared[k] is None for k in _NUMERICAL):
        _error("prepared_graded_artifacts_missing")
    return prepared


def _begin(directory, name, intent, receipt, *, failure_receipt=None):
    directory = _directory(directory) / name
    if directory.exists():
        if _read_record(directory, "intent.json") != intent:
            _error(name.replace("-", "_") + "_directory_identity_conflict")
        if failure_receipt and (directory / failure_receipt).is_file():
            if (directory / receipt).exists():
                _error("projection_success_failure_conflict")
            return directory, {"_failure": _read_record(directory, failure_receipt)}
        if not (directory / receipt).is_file():
            _error(name.replace("-", "_") + "_original_work_incomplete")
        return directory, _read_record(directory, receipt)
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", intent)
    return directory, None


def _execute_worker(store, directory, plan, policy):
    """Retain execution diagnostics separately from stable numerical custody."""
    _immutable(directory / "plan.json", plan)
    failures, successful = [], False
    try:
        for name in ("tmp", "cache"):
            (directory / name).mkdir()
        check_scratch_budget(directory, policy)
        result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_hmmer_preparation_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1",
                **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
                "XDG_CACHE_HOME": str(directory / "cache")})
        receipt = {"returncode": result.returncode, "metadata": result.metadata}
        successful = result.returncode == 0
        if not successful:
            failures.append(failure("worker", PREFIX + "result_worker_nonzero"))
    except (AcquisitionError, OSError, ValueError) as error:
        failures.append(failure("worker", exception_code(error, PREFIX + "result_worker_failed")))
        receipt = {**exception_diagnostic(error),
                   "operational": getattr(error, "operational", None)}
    diagnostics = {"artifacts": []}
    manifest = None
    try:
        manifest = _read_record(directory, "worker-result.json")
        if (type(manifest) is not dict or set(manifest) != {"version", "task", "plan_sha256", "completed", "outputs", "failures"}
                or manifest["version"] != MANIFEST_VERSION or manifest["task"] != plan["task"]
                or manifest["plan_sha256"] != native_infernal_digest(plan) or type(manifest["completed"]) is not bool
                or type(manifest["outputs"]) is not dict):
            _error("result_worker_manifest_invalid")
        validate_failures(manifest["failures"])
    except (ValueError, OSError) as error:
        manifest = None
        receipt["manifest_error"] = exception_diagnostic(error)
        failures.append(failure("worker", PREFIX + "result_worker_manifest_invalid"))
    outputs = {}
    allowed = NUMERICAL_FILES if plan["task"] == "grade" else {"projection": "projection.json"}
    if manifest is not None:
        failures.extend(manifest["failures"])
        if set(manifest["outputs"]) - allowed.keys():
            _error("result_worker_output_role_invalid")
        for role, descriptor in manifest["outputs"].items():
            try:
                if (type(descriptor) is not dict or set(descriptor) != {"filename", "sha256", "size_bytes"}
                        or descriptor["filename"] != allowed[role] or type(descriptor["size_bytes"]) is not int):
                    _error("result_worker_output_descriptor_invalid")
                reference = _capture_file(store, directory, descriptor["filename"], "application/json")
                _artifact_path(store, reference)
                if _descriptor(store, reference) != {"artifact_ref": reference, **{k: descriptor[k] for k in ("sha256", "size_bytes")}}:
                    _error("result_worker_output_bytes_conflict")
                outputs[role] = reference
            except (ValueError, OSError) as error:
                receipt.setdefault("output_errors", []).append({"role": role, **exception_diagnostic(error)})
                failures.append(failure("worker", exception_code(error, PREFIX + "result_worker_output_invalid") if isinstance(error, ValueError)
                    else PREFIX + "result_worker_output_unavailable:" + role))
    diagnostics["worker_receipt_artifact_ref"] = store.artifact(canonical(receipt), "application/json")
    for name in ("worker.stdout", "worker.stderr", "worker-result.json"):
        if (directory / name).exists():
            reference = _capture_file(store, directory, name)
            diagnostics["artifacts"].append({"role": name, "artifact_ref": reference})
    completed = successful and manifest is not None and manifest["completed"] and set(outputs) == set(allowed)
    if manifest is not None and manifest["completed"] and set(outputs) != set(allowed):
        failures.append(failure("worker", PREFIX + "result_worker_outputs_incomplete"))
    return outputs, unique_failures([*plan["failures"], *failures]), bool(completed), diagnostics


def prepare_native_hmmer_preparation_grading(store, *, target, capture, capture_directory, directory, policy):
    """Grade one already captured attempt once, independent of parent selection."""
    if not isinstance(policy, LocalJobPolicy):
        _error("local_job_policy_required")
    target, capture = finite_json_copy(target), finite_json_copy(capture)
    capture_directory = _directory(capture_directory)
    intent = {"target": target, "capture": capture, "capture_directory": str(capture_directory), "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-hmmer-preparation-grading", intent, "prepared.json")
    if saved is not None and saved.get("source_grading_artifact_ref") is None:
        prepared = _prepared_shape(saved)
        if prepared["graded"] or prepared["occurrences"] or any(prepared[k] is not None for k in _NUMERICAL) or not prepared["failures"]:
            _error("ungraded_prerequisite_receipt_invalid")
        if prepared["bundle_artifact_ref"] is not None:
            _artifact_path(store, prepared["bundle_artifact_ref"])
        return prepared
    # This is deliberately checked BEFORE calling capture_local_bundle: a grade
    # selection never performs the first native acquisition.
    if not (capture_directory / "capture.json").is_file():
        if saved is not None:
            _error("grading_capture_receipt_unavailable")
        prepared = _prepared(failures=[failure("prerequisite", PREFIX + "completed_capture_required")])
        _immutable(directory / "prepared.json", prepared)
        return prepared
    authenticated = capture_local_bundle(store, target=target, directory=capture_directory)
    if native_infernal_digest(authenticated) != native_infernal_digest(capture):
        _error("supplied_capture_conflict")
    if not capture["bundle_validated"]:
        prepared = _prepared(capture["bundle_artifact_ref"], failures=capture["failures"])
        _immutable(directory / "prepared.json", prepared)
        return prepared
    bundle = _decode(store.get_artifact(capture["bundle_artifact_ref"]))
    if saved is not None:
        return validate_prepared_grading(store, saved, bundle=bundle)
    original_plan = _read_record(capture_directory, "capture-plan.json")
    bundle = validate_original_bundle(bundle, original_plan)
    occurrences, problems = qualified_occurrences(bundle, capture["bundle_artifact_ref"], capture)
    metadata, metadata_failures = effective_metadata(bundle, occurrences, include_map_context=True)
    failures = unique_failures([*problems, *metadata_failures])
    files = [{"occurrence_id": r["occurrence_id"], "path": str(_artifact_path(store, r["artifact_ref"]))}
             for r in eligible_occurrences(occurrences)]
    plan = {"version": PLAN_VERSION, "task": "grade", "directory": str(directory), "bundle": bundle,
        "original_plan": original_plan, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "capture": capture, "occurrences": occurrences, "effective_metadata": metadata,
        "files": files, "failures": failures}
    outputs, failures, completed, diagnostics = _execute_worker(store, directory, plan, policy)
    prepared = _prepared(capture["bundle_artifact_ref"], failures=failures)
    prepared.update({role + "_artifact_ref": ref for role, ref in outputs.items()})
    prepared.update(occurrences=occurrences, graded=completed)
    stable = {"schema": RETAINED_VERSION, "original_plan": original_plan, "capture": capture,
        "bundle_sha256": native_infernal_digest(bundle),
        "original_parameters": deepcopy(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"]),
        "effective_metadata": metadata, "grading_context": grading_context(bundle, occurrences, metadata), "numerical_artifacts": {role: _descriptor(store, ref) for role, ref in outputs.items()},
        **{k: prepared[k] for k in (*_NUMERICAL, "occurrences", "failures", "graded")}}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=prepared["bundle_artifact_ref"], grading=stable)
    _immutable(directory / "grading-receipt.json", {"prepared_sha256": native_infernal_digest(prepared), **diagnostics})
    _immutable(directory / "prepared.json", prepared)
    return validate_prepared_grading(store, prepared, bundle=bundle)


def _record_refs(source_ref, projection):
    refs = [source_ref]
    for row in projection["rows"]:
        if row["artifact_ref"] is not None:
            refs.append(row["artifact_ref"])
        for check in row["checks"]:
            refs.extend(r["artifact_ref"] for r in check["occurrences"])
    refs.extend(r["artifact_ref"] for r in projection["artifacts"])
    return list(dict.fromkeys(refs))


def _selected(store, reference, *, source_ref, selector, occurrences):
    """Validate the small selected return; no re-projection or recalculation."""
    _artifact_path(store, reference)
    selected = _decode(store.get_artifact(reference))
    if type(selected) is not dict or set(selected) != {"rows", "artifacts", "population"}:
        _error("selected_projection_invalid")
    validate_schema(selected["rows"], {"type": "array", "items": ROW_SCHEMA})
    validate_schema(selected["artifacts"], {"type": "array", "items": ARTIFACT_SCHEMA})
    validate_schema(selected["population"], POPULATION_SCHEMA)
    choice, population = selector["projection"], selected["population"]
    lookup = {(r["direction"], r["role"], r["ordinal"]): r for r in occurrences}
    if (population["source_ref"] != source_ref or population["collection"] != (choice["collection"] if choice else None)
            or population["returned_records"] != len(selected["rows"])
            or population["total_records"] != population["returned_records"] + population["omitted_records"]
            or population["requested_artifact_count"] != len(selector["artifacts"])
            or population["returned_artifact_count"] != len(selected["artifacts"])
            or choice is None and selected["rows"]):
        _error("selected_population_conflict")
    expected_artifacts, missing = [], []
    for request in selector["artifacts"]:
        row = lookup.get(tuple(request[k] for k in ("direction", "role", "ordinal")))
        if row is None:
            missing.append(request)
        else:
            expected_artifacts.append({k: source_ref if k == "source_ref" else row[k]
                                       for k in ARTIFACT_SCHEMA["properties"]})
    # V1 preserves explicitly selected files first, then the exact occurrence
    # dependencies of selected quantities/rows/checks. Those joins are validated
    # by the bounded selector against the saved sheet. The host authenticates
    # that worker output and its byte custody without hydrating the full sheet.
    artifacts = selected["artifacts"]
    if (artifacts[:len(expected_artifacts)] != expected_artifacts
            or population["missing_artifacts"] != missing
            or not selected["rows"] and artifacts != expected_artifacts):
        _error("selected_artifact_association_conflict")
    selected_slots, selected_refs = set(), set()
    for artifact in artifacts:
        slot = tuple(artifact[k] for k in ("direction", "role", "ordinal"))
        original = lookup.get(slot)
        if (slot in selected_slots or original is None or artifact["source_ref"] != source_ref
                or any(original[k] != v for k, v in artifact.items() if k != "source_ref")):
            _error("selected_artifact_custody_conflict")
        selected_slots.add(slot)
        selected_refs.add(artifact["artifact_ref"])
    seen = set()
    for row in selected["rows"]:
        if (row["source_ref"] != source_ref or row["record_key"] in seen or row["artifact_ref"] is not None
                and row["artifact_ref"] not in selected_refs or choice is None
                or [q["path"] for q in row["quantities"]] != choice["quantities"]
                or set(c["name"] for c in row["checks"]) != set(choice["checks"])):
            _error("selected_row_custody_conflict")
        seen.add(row["record_key"])
        for check in row["checks"]:
            for occurrence in check["occurrences"]:
                original = lookup.get(tuple(occurrence[k] for k in ("direction", "role", "ordinal")))
                if (original is None or any(original[k] != v for k, v in occurrence.items())
                        or tuple(occurrence[k] for k in ("direction", "role", "ordinal")) not in selected_slots):
                    _error("selected_check_occurrence_conflict")
    if choice is not None:
        wanted = choice["rows"]
        if "record_keys" in wanted:
            keys = [r["record_key"] for r in selected["rows"]]
            if (keys != [key for key in wanted["record_keys"] if key in seen]
                    or population["missing_record_keys"] != [key for key in wanted["record_keys"] if key not in seen]):
                _error("selected_record_keys_conflict")
        elif len(selected["rows"]) > wanted["limit"] or population["missing_record_keys"]:
            _error("selected_record_window_conflict")
    return selected


def publish_selected_preparation_result(store, *, source_ref, prepared, selector, directory, policy):
    """Return pure V1 selections, retaining a separate immutable projection."""
    if not isinstance(policy, LocalJobPolicy):
        _error("local_job_policy_required")
    prepared = _prepared_shape(prepared)
    bundle = _decode(store.get_artifact(prepared["bundle_artifact_ref"]))
    prepared = validate_prepared_grading(store, prepared, bundle=bundle)
    stable = _stable(store, prepared)
    source = store._require(source_ref, {"source"})
    expected = original_source_payload(bundle=bundle, capture=stable["capture"], prepared=prepared)
    if source.get("origin") != "tool" or any(source.get(k) != v for k, v in expected.items()):
        _error("publication_source_custody_conflict")
    selector = validate_preparation_result_selector(selector, program=bundle["program"], mode=bundle["mode"])
    intent = {"source_ref": source_ref, "prepared_sha256": native_infernal_digest(prepared),
        "selector": selector, "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-hmmer-preparation-projection", intent, "publication.json",
                             failure_receipt="projection-failure.json")
    if saved is not None:
        if set(saved) == {"_failure"}:
            record = saved["_failure"]
            if (type(record) is not dict or set(record) != {"version", "intent", "code", "failures",
                    "projection_artifact_ref", "worker_receipt_artifact_ref", "artifacts"}
                    or record["version"] != PREFIX + "projection_failure_v1" or record["intent"] != intent
                    or record["code"] not in {PREFIX + "projection_worker_failed", PREFIX + "saved_numerical_grading_unavailable"}):
                _error("projection_failure_receipt_invalid")
            validate_failures(record["failures"])
            for ref in [record["worker_receipt_artifact_ref"], *[r["artifact_ref"] for r in record["artifacts"]],
                        *([record["projection_artifact_ref"]] if record["projection_artifact_ref"] else [])]:
                _artifact_path(store, ref)
            raise ContractError(record["code"])
        if (type(saved) is not dict or set(saved) != _PUBLICATION_FIELDS
                or type(saved["projection_artifact_ref"]) is not str or not saved["projection_artifact_ref"]):
            _error("publication_receipt_invalid")
        receipt = _read_record(directory, "projection-receipt.json")
        if (receipt["publication_sha256"] != native_infernal_digest(saved) or receipt["intent"] != intent
                or receipt.get("completed") is not True or saved["failures"] != prepared["failures"]):
            _error("publication_receipt_identity_conflict")
        selected = _selected(store, saved["projection_artifact_ref"], source_ref=source_ref,
            selector=selector, occurrences=prepared["occurrences"])
        if any(saved[k] != selected[k] for k in selected) or saved["record_refs"] != _record_refs(source_ref, selected):
            _error("publication_selected_data_conflict")
        validate_failures(saved["failures"])
        for ref in [receipt["worker_receipt_artifact_ref"], *[r["artifact_ref"] for r in receipt["artifacts"]]]:
            _artifact_path(store, ref)
        return saved
    plan = {"version": PLAN_VERSION, "task": "project", "directory": str(directory),
        "grading": _worker_file(store, prepared["grading_artifact_ref"]) if prepared["grading_artifact_ref"] else None,
        "grading_context": stable["grading_context"], "occurrences": prepared["occurrences"], "source_ref": source_ref,
        "selector": selector, "failures": deepcopy(prepared["failures"])}
    outputs, failures, completed, diagnostics = _execute_worker(store, directory, plan, policy)
    reference = outputs.get("projection")
    if not completed or reference is None:
        code = PREFIX + ("saved_numerical_grading_unavailable" if any(
            row["code"] == PREFIX + "saved_numerical_grading_unavailable" for row in failures)
            else "projection_worker_failed")
        _immutable(directory / "projection-failure.json", {"version": PREFIX + "projection_failure_v1",
            "intent": intent, "code": code, "failures": failures,
            "projection_artifact_ref": reference, **diagnostics})
        raise ContractError(code)
    selected = _selected(store, reference, source_ref=source_ref, selector=selector, occurrences=prepared["occurrences"])
    result = {"record_refs": _record_refs(source_ref, selected), **selected,
        "failures": failures, "projection_artifact_ref": reference}
    _immutable(directory / "projection-receipt.json", {"intent": intent,
        "publication_sha256": native_infernal_digest(result), "completed": completed, **diagnostics})
    _immutable(directory / "publication.json", result)
    return result


def validate_publication(store, publication, *, source_ref, prepared, selector, directory, policy):
    """Authenticate an existing selection receipt with all worker work forbidden."""
    saved_directory = _directory(directory) / "native-hmmer-preparation-projection"
    if not (saved_directory / "publication.json").is_file():
        _error("saved_publication_required")
    saved = publish_selected_preparation_result(store, source_ref=source_ref, prepared=prepared,
        selector=selector, directory=directory, policy=policy)
    if saved != finite_json_copy(publication):
        _error("supplied_publication_conflict")
    return saved


__all__ = ["prepare_native_hmmer_preparation_grading", "publish_selected_preparation_result",
           "validate_prepared_grading", "validate_publication"]
