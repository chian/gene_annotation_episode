"""Bounded original utility reading and separate saved-result selection.

Internal ports were frozen with the host before implementation (631/010).
``parse_original`` plans contain capture, exact qualified context, bundle_file
and occurrence-associated files. ``project_saved`` plans contain source_ref,
context, selector, saved_data and nullable result/prepared_database/
prepared_manifest files. Both also contain version, task and directory.
Manifests contain version, task, plan_sha256, completed, outputs and failures;
output descriptors contain filename, sha256 and size_bytes. Completion describes
technical processing, including a qualified unavailable result, not native success.

The sealed original bundle is also an output preparation_receipt occurrence
(root's additive reuse correction to 010). Its FileIdentity uses original
attempt/bundle.json; bundle_file.path is only its retained read location. Thus a
later reuse can explicitly request these actual bytes without a source granting
auxiliary files. This receipt is outside the native output-family enumeration.
Binary family members are streamed for custody only. This module has no Store,
native invocation, model, retry, acquisition or episode loop.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys

from .blast_utility_contracts import (
    blast_utility_result_version_for_operation,
    validate_blast_utility_record as core,
)
from .domain import ContractError, canonical
from .native_blast_utility_acquisition import (
    _key, _selected_files, validate_native_blast_utility_capture,
)
from .native_blast_utility_contracts import finite_json_copy, native_blast_digest
from .native_hmmer_preparation_acquisition import (
    _confined_reader, _decode, _directory, _read_record,
)
from .native_hmmer_preparation_result_worker import _read_bytes, _write
from .native_infernal_driver import _encoded
from .practical_execution_state import _immutable


PREFIX = "native_blast_utility_"
PLAN_VERSION = PREFIX + "result_worker_plan_v1"
MANIFEST_VERSION = PREFIX + "result_worker_manifest_v1"
PLAN_VERSION_V2 = PREFIX + "result_worker_plan_v2"
MANIFEST_VERSION_V2 = PREFIX + "result_worker_manifest_v2"
OUTPUT_FILES = {"result": "result.json", "prepared_database": "prepared-projection.json",
                "prepared_manifest": "prepared-manifest.json", "projection": "projection.json"}
CONTEXT_FIELDS = {"operation", "native_outcome", "occurrences", "database_binding", "failures"}
VDB_CONTEXT_FIELDS = CONTEXT_FIELDS | {"operation_input_occurrences", "vdb_context"}
PREPARATION_CONTEXT_FIELDS = {"operation", "native_outcome", "occurrences", "database_bindings",
                              "materializations", "failures"}


def _error(code):
    raise ContractError(PREFIX + code)


def failure(stage, code, occurrence_id=None, *, native_returncode=None):
    return core("UtilityFailure", {"stage": stage, "code": code, "occurrence_id": occurrence_id,
        "record_key": None, "line_number": None, "native_returncode": native_returncode})


def unique_failures(rows):
    if type(rows) is not list:
        _error("result_failures_invalid")
    result = []
    for row in rows:
        row = core("UtilityFailure", row)
        if row not in result:
            result.append(row)
    return result


def diagnostic(error):
    return {"exception_type": type(error).__name__, "detail": str(error)}


def _occurrence_id(capture, row):
    if row["direction"] == "input":
        return row["input_key"]
    if capture["original_bundle"]["operation"]["version"] == "blast_utility_operation_v3":
        from .native_blast_vdb_utility_context import vdb_utility_occurrence_id
        return vdb_utility_occurrence_id(capture, row)
    if capture["original_bundle"]["operation"]["version"] == "blast_utility_operation_v2":
        return PREFIX + "occurrence_" + native_blast_digest({
            "identity": capture["original_bundle"]["identity"],
            **{key: row.get(key) for key in
               ("direction", "input_key", "database_key", "role", "ordinal", "original_path")}})
    return PREFIX + "occurrence_" + native_blast_digest({
        "identity": capture["original_bundle"]["identity"],
        **{key: row[key] for key in ("direction", "role", "ordinal", "original_path")}})


def qualified_utility_context(capture: dict) -> dict:
    """Reconstruct C facts from exact original rows, without reading any paths."""
    return _qualified_utility_context(capture, observations_only=False)


def captured_utility_observations(capture: dict) -> dict:
    """Original captured facts, without claiming qualified database metadata."""
    return _qualified_utility_context(capture, observations_only=True)


def _qualified_utility_context(capture: dict, *, observations_only: bool) -> dict:
    capture = validate_native_blast_utility_capture(capture)
    if not capture["bundle_validated"] or capture["source_ref"] is None:
        _error("validated_capture_source_required")
    bundle, plan = capture["original_bundle"], capture["plan"]
    new_preparation = bundle["operation"]["version"] == "blast_utility_operation_v2"
    vdb = bundle["operation"]["version"] == "blast_utility_operation_v3"
    job = plan["requested_job"]["native_blast_utility"]
    def qualified_role(row):
        if vdb:
            from .native_blast_vdb_utility_context import vdb_utility_occurrence_role
            return vdb_utility_occurrence_role(job, row)
        return {"manifest": "database_manifest", "metadata_manifest": "database_metadata"}.get(row["role"], row["role"])
    if capture["bundle_artifact_ref"] != "artifact_" + hashlib.sha256(_encoded(bundle)).hexdigest():
        _error("captured_bundle_identity_conflict")
    selected = {_key(row): row for row in _selected_files(plan, bundle)}
    seen, ids, slots, occurrences, by_key = set(), set(), set(), [], {}
    selected_slots, next_ordinals = {}, {}
    if new_preparation or vdb:
        # Slots belong to the selected population, including missing members.
        # Otherwise a missing original would give its staged copy ordinal zero.
        for key, item in selected.items():
            role = qualified_role(item)
            direction = "input" if item["direction"] in {"database", "materialization"} else item["direction"]
            ordinal = next_ordinals.get((direction, role), 0)
            next_ordinals[direction, role] = ordinal + 1
            selected_slots[key] = direction, role, ordinal
    for item in capture["artifacts"]:
        key, expected = _key(item), selected.get(_key(item))
        if (expected is None or not expected["original"] or any(item[k] != expected[k]
                for k in item if k != "artifact_ref")):
            _error("captured_occurrence_association_conflict")
        oid = _occurrence_id(capture, item)
        role = qualified_role(item)
        direction = "input" if item["direction"] in {"database", "materialization"} else item["direction"]
        ordinal = selected_slots[key][2] if new_preparation or vdb else item["ordinal"]
        slot = direction, role, ordinal
        if key in seen or oid in ids or slot in slots:
            _error("captured_occurrence_duplicate")
        seen.add(key); ids.add(oid); slots.add(slot); by_key[key] = oid
        occurrences.append(core("ArtifactOccurrence", {"occurrence_id": oid,
            "direction": direction, "role": role, "ordinal": ordinal,
            **{k: item[k] for k in ("artifact_ref", "sha256", "size_bytes", "completeness")},
            "native_format": "text" if vdb and role == "database_list" else item["format"], "native_path": item["original_path"]}))
    for row in capture["failures"]:
        key, expected = _key(row), selected.get(_key(row))
        if expected is None or key in seen or row["code"] in {"unsealed_file", "sealed_bundle_unavailable",
                "original_bundle_invalid", "original_owner_invalid"}:
            _error("captured_failure_association_conflict")
        if row["code"] == "input_not_original" and (expected["original"] or row["direction"] not in {"input", "database", "materialization"}):
            _error("captured_failure_association_conflict")
        if row["code"] in {"input_not_original", "original_file_identity_mismatch"} and row["diagnostic_artifact_ref"] is None:
            _error("captured_failure_diagnostic_required")
        seen.add(key)
    if any(row["sha256"] is not None and key not in seen for key, row in selected.items()):
        _error("captured_original_association_missing")
    captured_keys = set(by_key)
    capture_complete = not capture["failures"] and captured_keys == set(selected)
    rc = bundle["returncode"]
    state = ("succeeded" if bundle["started"] and rc == 0 and bundle["writer_closed"] else
             "failed" if rc not in (None, 0) or not bundle["started"] and bundle["failures"] else "unknown")
    if vdb and not bundle["started"] and any(r["code"] == "offline_status_unavailable" for r in bundle["failures"]) and not any(
            r["code"] in {"offline_setup_failed", "offline_child_exec_failed", "offline_launcher_unavailable"} for r in bundle["failures"]):
        state = "unknown"
    outcome = core("NativeOutcome", {"started": bundle["started"], "returncode": rc,
        "state": state, "writer_closed": bundle["writer_closed"],
        "inventory_complete": bundle["inventory_complete"] and capture_complete})
    failures = []
    mapping = {
        "software_unavailable": ("native", "dependency_unavailable"),
        "software_digest_mismatch": ("input", "input_identity_mismatch"),
        "software_not_executable": ("native", "native_start_failed"),
        "input_unavailable": ("input", "input_population_unavailable"),
        "input_identity_mismatch": ("input", "input_identity_mismatch"),
        "staging_scratch_limit": ("input", "semantic_validation_unavailable"),
        "database_unavailable": ("input", "dependency_unavailable"),
        "database_identity_mismatch": ("input", "input_identity_mismatch"),
        "database_changed": ("input", "input_identity_mismatch"),
        "command_unavailable": ("native", "native_start_failed"),
        "nonzero_returncode": ("native", "native_nonzero_exit"),
        "execution_scratch_limit": ("native", "semantic_validation_unavailable"),
        "immutable_input_changed": ("input", "input_identity_mismatch"),
        "input_final_unavailable": ("input", "input_population_unavailable"),
        "missing_output": ("capture", "output_missing"),
        "invalid_output": ("capture", "native_document_invalid"),
        "output_inventory_incomplete": ("capture", "output_inventory_incomplete"),
        "materialization_unavailable": ("input", "dependency_unavailable"),
        "materialization_identity_mismatch": ("input", "input_identity_mismatch"),
        "materialization_changed": ("input", "input_identity_mismatch"),
        "materialization_scratch_limit": ("input", "semantic_validation_unavailable"),
        "materialization_binding_invalid": ("input", "supplied_binding_conflict"),
        "original_input_changed": ("input", "input_identity_mismatch"),
        "offline_launcher_unavailable": ("native", "dependency_unavailable"),
        "offline_runtime_identity_mismatch": ("input", "input_identity_mismatch"),
        "offline_setup_failed": ("native", "native_start_failed"),
        "offline_status_unavailable": ("native", "semantic_validation_unavailable"),
        "offline_configuration_conflict": ("input", "supplied_binding_conflict"),
        "offline_child_exec_failed": ("native", "native_start_failed"),
    }
    for row in bundle["failures"]:
        matches = [by_key[key] for key, original in selected.items() if key in by_key and (
            row["input_key"] is not None and original["input_key"] == row["input_key"] or
            row["database_key"] is not None and original["database_key"] == row["database_key"] or
            row["relative_path"] is not None and original["direction"] == "output" and
                original["original_path"] == str(PurePosixPath(plan["attempt_directory"]) / row["relative_path"]))]
        stage, code = mapping[row["code"]]
        failures.append(failure(stage, code, matches[0] if len(matches) == 1 else None,
            native_returncode=rc if code == "native_nonzero_exit" else None))
    for row in capture["failures"]:
        code = ("input_identity_mismatch" if row["code"] in {"input_not_original", "original_file_identity_mismatch"} else
                "dependency_unavailable" if row["direction"] == "database" else
                "input_population_unavailable" if row["direction"] in {"input", "materialization"} else "output_missing")
        failures.append(failure("capture", code))
    if not outcome["inventory_complete"]:
        failures.append(failure("capture", "output_inventory_incomplete"))
    if state == "failed" and not any(row["code"] in {"native_nonzero_exit", "native_start_failed"} for row in failures):
        failures.append(failure("native", "native_nonzero_exit" if bundle["started"] else "native_start_failed",
            native_returncode=rc if bundle["started"] else None))
    receipt_row = {"direction": "output", "role": "preparation_receipt", "ordinal": 0,
        "original_path": str(PurePosixPath(plan["attempt_directory"]) / "bundle.json")}
    encoded_bundle = _encoded(bundle)
    occurrences.append(core("ArtifactOccurrence", {"occurrence_id": _occurrence_id(capture, receipt_row),
        "direction": "output", "role": "preparation_receipt", "ordinal": 0,
        "artifact_ref": capture["bundle_artifact_ref"], "sha256": hashlib.sha256(encoded_bundle).hexdigest(),
        "size_bytes": len(encoded_bundle), "completeness": "complete", "native_format": "json",
        "native_path": receipt_row["original_path"]}))
    if observations_only:
        return {"operation": bundle["operation"], "native_outcome": outcome,
            "occurrences": occurrences, "failures": unique_failures(failures)}
    databases = plan["requested_job"]["native_blast_utility"]["databases"]
    if vdb:
        from .native_blast_vdb_utility_context import qualify_vdb_utility_context
        return validate_context(qualify_vdb_utility_context(capture, base_context={
            "operation": bundle["operation"], "native_outcome": outcome, "occurrences": occurrences,
            "database_binding": None, "failures": unique_failures(failures)}))
    if new_preparation:
        bindings = []
        for database in databases:
            key = database["database_key"]
            db_keys = {k for k, row in selected.items()
                       if row["direction"] == "database" and row["database_key"] == key}
            bindings.append(core("DatabaseBinding", {
                "database_key": key, "kind": database["kind"],
                "molecule": {"blast_nucleotide_sequence": "dna", "blast_protein_sequence": "protein"}.get(
                    database["kind"], bundle["operation"]["molecule"]),
                "identity": {k: database["identity"][k] for k in ("namespace", "value", "version", "release")},
                "source_ref": database["identity"]["source"]["source_ref"], "native_paths": database["native_paths"],
                "occurrence_ids": [by_key[k] for k in selected if k in by_key and k in db_keys],
                "inventory_complete": database["manifest"]["inventory_complete"] and db_keys <= captured_keys}))
        return validate_context({"operation": bundle["operation"], "native_outcome": outcome,
            "occurrences": occurrences, "database_bindings": bindings,
            "materializations": bundle["materializations"], "failures": unique_failures(failures)})
    binding = None
    if databases:
        database = databases[0]
        db_keys = {key for key, row in selected.items() if row["direction"] == "database"}
        binding = core("DatabaseBinding", {"database_key": database["database_key"], "kind": database["kind"],
            "molecule": bundle["operation"]["molecule"],
            "identity": {k: database["identity"][k] for k in ("namespace", "value", "version", "release")},
            "source_ref": database["identity"]["source"]["source_ref"], "native_paths": database["native_paths"],
            "occurrence_ids": [by_key[key] for key in selected if key in by_key and key in db_keys],
            "inventory_complete": database["manifest"]["inventory_complete"] and db_keys <= captured_keys})
    return validate_context({"operation": bundle["operation"], "native_outcome": outcome,
        "occurrences": occurrences, "database_binding": binding, "failures": unique_failures(failures)})


def validate_context(value):
    context = finite_json_copy(value)
    new_preparation = (type(context) is dict and type(context.get("operation")) is dict
                       and context["operation"].get("version") == "blast_utility_operation_v2")
    vdb = (type(context) is dict and type(context.get("operation")) is dict
           and context["operation"].get("version") == "blast_utility_operation_v3")
    fields = VDB_CONTEXT_FIELDS if vdb else PREPARATION_CONTEXT_FIELDS if new_preparation else CONTEXT_FIELDS
    if type(context) is not dict or set(context) != fields or type(context["occurrences"]) is not list:
        _error("worker_context_invalid")
    operation = core("Operation", context["operation"])
    outcome = core("NativeOutcome", context["native_outcome"])
    rows = [core("ArtifactOccurrence", row) for row in context["occurrences"]]
    ids = {row["occurrence_id"] for row in rows}
    if len(ids) != len(rows) or len({(r["direction"], r["role"], r["ordinal"]) for r in rows}) != len(rows):
        _error("worker_occurrences_duplicate")
    if new_preparation:
        if type(context["database_bindings"]) is not list or type(context["materializations"]) is not list:
            _error("worker_preparation_context_invalid")
        bindings = [core("DatabaseBinding", b) for b in context["database_bindings"]]
        if len({b["database_key"] for b in bindings}) != len(bindings) or any(
                not set(b["occurrence_ids"]) <= ids for b in bindings):
            _error("worker_database_binding_conflict")
        for receipt in context["materializations"]:
            core("MaterializationReceipt", receipt)
    elif operation["mode"] == "create_sequence_database":
        if context["database_binding"] is not None:
            _error("worker_builder_database_conflict")
    else:
        binding = core("DatabaseBinding", context["database_binding"])
        if (binding["database_key"] != operation["database_key"] or binding["molecule"] != operation["molecule"]
                or not set(binding["occurrence_ids"]) <= ids):
            _error("worker_database_binding_conflict")
    if vdb:
        from .blast_vdb_utility_contracts import validate_vdb_utility_context
        validate_vdb_utility_context(context["vdb_context"], operation=operation,
            database_binding=context["database_binding"], operation_input_occurrences=context["operation_input_occurrences"])
        by_id = {row["occurrence_id"]: row for row in rows}
        if any(by_id.get(row["occurrence_id"]) != row for row in context["operation_input_occurrences"]) or any(
                not set(db["occurrence_ids"]) <= ids for db in context["vdb_context"]["dependency_database_bindings"]):
            _error("worker_database_binding_conflict")
        for dependency in context["vdb_context"]["declared_dependencies"]:
            oid = dependency["list_occurrence_id"]
            if oid is not None and (oid not in by_id or by_id[oid]["role"] != "database_list" or by_id[oid]["native_format"] != "text"):
                _error("worker_database_list_conflict")
    failures = unique_failures(context["failures"])
    if failures != context["failures"] or any(row["occurrence_id"] is not None and row["occurrence_id"] not in ids
            or row["native_returncode"] is not None and row["native_returncode"] != outcome["returncode"] for row in failures):
        _error("worker_failure_context_conflict")
    return context


def _file_descriptor(value):
    if (type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}
            or type(value["path"]) is not str or not PurePosixPath(value["path"]).is_absolute()
            or type(value["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
            or type(value["size_bytes"]) is not int or value["size_bytes"] < 0):
        _error("worker_file_descriptor_invalid")
    return value


def _verify_file(value):
    """Authenticate a binary occurrence in bounded blocks, without parsing it."""
    value = _file_descriptor(value)
    path, digest, size = Path(value["path"]), hashlib.sha256(), 0
    with _confined_reader(path.parent, path.name) as retained:
        with retained.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(block); digest.update(block)
    if size != value["size_bytes"] or digest.hexdigest() != value["sha256"]:
        _error("worker_retained_bytes_mismatch")


def validate_worker_plan(value):
    plan = finite_json_copy(value)
    common = {"version", "task", "directory", "context", "files"}
    variants = {"parse_original": {"capture", "bundle_file"},
        "project_saved": {"source_ref", "selector", "saved_data"}}
    vdb = type(plan) is dict and plan.get("version") == PLAN_VERSION_V2
    if vdb:
        variants["project_saved"] |= {"context_authentication"}
    if (type(plan) is not dict or plan.get("version") not in {PLAN_VERSION, PLAN_VERSION_V2} or plan.get("task") not in variants
            or set(plan) != common | variants[plan["task"]] or type(plan["directory"]) is not str
            or not PurePosixPath(plan["directory"]).is_absolute()):
        _error("worker_plan_invalid")
    context = validate_context(plan["context"])
    if vdb != (context["operation"]["version"] == "blast_utility_operation_v3"):
        _error("worker_plan_version_conflict")
    if plan["task"] == "parse_original":
        if context != qualified_utility_context(plan["capture"]):
            _error("worker_original_context_conflict")
        bundle_file = _file_descriptor(plan["bundle_file"])
        encoded = _encoded(plan["capture"]["original_bundle"])
        if (bundle_file["sha256"] != hashlib.sha256(encoded).hexdigest() or bundle_file["size_bytes"] != len(encoded)
                or plan["capture"]["bundle_artifact_ref"] != "artifact_" + bundle_file["sha256"]):
            _error("worker_bundle_file_conflict")
        if type(plan["files"]) is not list or len(plan["files"]) != len(context["occurrences"]):
            _error("worker_file_population_conflict")
        for row, occurrence in zip(plan["files"], context["occurrences"]):
            if type(row) is not dict or set(row) != {"occurrence_id", "path", "sha256", "size_bytes"}:
                _error("worker_file_association_conflict")
            _file_descriptor({k: row[k] for k in ("path", "sha256", "size_bytes")})
            if any(row[k] != occurrence[k] for k in ("occurrence_id", "sha256", "size_bytes")):
                _error("worker_file_association_conflict")
    else:
        from .blast_utility_result_views import validate_blast_utility_result_selector
        validate_blast_utility_result_selector(plan["selector"], operation=context["operation"])
        if type(plan["source_ref"]) is not str or not plan["source_ref"] or type(plan["saved_data"]) is not list:
            _error("worker_projection_context_invalid")
        if type(plan["files"]) is not dict or set(plan["files"]) != {"result", "prepared_database", "prepared_manifest"}:
            _error("worker_saved_files_invalid")
        for descriptor in plan["files"].values():
            if descriptor is not None:
                _file_descriptor(descriptor)
        if plan["files"]["prepared_manifest"] is not None and plan["files"]["prepared_database"] is None:
            _error("worker_prepared_manifest_unbound")
        if vdb:
            from .native_blast_vdb_utility_context import validate_vdb_context_authentication_shape
            if plan["files"]["prepared_database"] is not None or plan["files"]["prepared_manifest"] is not None:
                _error("worker_vdb_prepared_payload_forbidden")
            if (plan["context_authentication"] is None) != (plan["files"]["result"] is None):
                _error("worker_vdb_context_authentication_required")
            if plan["context_authentication"] is not None:
                validate_vdb_context_authentication_shape(plan["context_authentication"], context=context)
    return plan


def _can_read_result(context):
    op, rows = context["operation"], context["occurrences"]
    if op["version"] == "blast_utility_operation_v3":
        return {"stdout", "stderr"} <= {r["role"] for r in rows if r["direction"] == "output"}
    if op["version"] == "blast_utility_operation_v2":
        return (blast_utility_result_version_for_operation(op) == "blast_database_artifact_set_v2"
                or any(r["direction"] == "output" and r["role"] == "stdout" for r in rows))
    if op["mode"] == "create_sequence_database":
        return set(op["input_occurrence_ids"]) <= {r["occurrence_id"] for r in rows if r["direction"] == "input"}
    streams = {r["role"] for r in rows if r["direction"] == "output"}
    return {"stdout", "stderr"} <= streams if op["mode"] == "integrity" else "stdout" in streams


def _parse_original(plan, directory, manifest):
    from .blast_database_extraction import _check, _check_bytes, parse_blastdbcmd_sequences
    from .blast_database_inspection import _metadata_fields, parse_blast_database_inspection, parse_blastdbcheck_diagnostics
    from .blast_database_preparation import populate_database_artifact_set, project_prepared_blast_database
    context = plan["context"]
    bundle = plan["capture"]["original_bundle"]
    if _decode(_read_bytes(plan["bundle_file"])) != bundle:
        _error("worker_original_bundle_bytes_conflict")
    content = {}
    vdb = context["operation"]["version"] == "blast_utility_operation_v3"
    authentication_ids = set()
    if vdb:
        from .native_blast_vdb_utility_context import vdb_utility_authentication_occurrence_ids
        authentication_ids = vdb_utility_authentication_occurrence_ids(plan["capture"])
    for row, occurrence in zip(plan["files"], context["occurrences"]):
        descriptor = {k: row[k] for k in ("path", "sha256", "size_bytes")}
        if (occurrence["occurrence_id"] in authentication_ids or
                (occurrence["direction"] == "output" and occurrence["role"] in {"stdout", "stderr", "database_metadata"})
                or context["operation"]["version"] == "blast_utility_operation_v2" and (
                    occurrence["role"] in {"database_list", "profile_list", "materialized_list", "alias_file"}
                    or occurrence["native_format"] == "blast_profile_aux_text")):
            content[occurrence["occurrence_id"]] = _read_bytes(descriptor)
        else:
            _verify_file(descriptor)
    operation, outcome, rows = context["operation"], context["native_outcome"], context["occurrences"]
    if not _can_read_result(context):
        manifest["failures"].append(failure("input" if operation["mode"] == "create_sequence_database" else "capture",
            "input_population_unavailable" if operation["mode"] == "create_sequence_database" else "output_missing"))
        return
    streams = {row["role"]: row for row in rows if row["direction"] == "output" and row["role"] in {"stdout", "stderr"}}
    if vdb:
        from .native_blast_vdb_utility_context import authenticate_vdb_utility_context
        from .blast_vdb_utility_inputs import parse_blast_vdb_extraction, parse_blast_vdb_inspection
        manifest["context_authentication"] = authenticate_vdb_utility_context(
            plan["capture"], context=context, contents_by_occurrence=content)
        parser = parse_blast_vdb_extraction if operation["mode"] == "extract_sequences" else parse_blast_vdb_inspection
        result = parser(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"],
            operation=operation, database_binding=context["database_binding"], outcome=outcome,
            operation_input_occurrences=context["operation_input_occurrences"], vdb_context=context["vdb_context"],
            stderr_contents=content[streams["stderr"]["occurrence_id"]], stderr_occurrence=streams["stderr"])
        manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
        manifest["failures"].extend(result["failures"])
        return
    if operation["version"] == "blast_utility_operation_v2":
        from .blast_preparation_result_assembly import assemble_blast_preparation_result
        result, prepared = assemble_blast_preparation_result(
            context=context, capture=plan["capture"], contents=content)
        manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
        manifest["failures"].extend(result["failures"])
        if prepared is not None:
            manifest["outputs"]["prepared_database"] = _write(directory, OUTPUT_FILES["prepared_database"], prepared)
            if prepared["status"] == "available":
                manifest["outputs"]["prepared_manifest"] = _write(directory, OUTPUT_FILES["prepared_manifest"], prepared["manifest"])
        return
    common = {"operation": operation, "database_binding": context["database_binding"], "outcome": outcome}
    mode = operation["mode"]
    if mode == "extract_sequences":
        result = parse_blastdbcmd_sequences(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"], **common)
    elif mode in {"info", "metadata"}:
        result = parse_blast_database_inspection(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"], **common)
    elif mode == "integrity":
        result = parse_blastdbcheck_diagnostics(content[streams["stdout"]["occurrence_id"]],
            content[streams["stderr"]["occurrence_id"]], stdout_occurrence=streams["stdout"], stderr_occurrence=streams["stderr"], **common)
    else:
        metadata, checks, problems = [], [], []
        database_key = PREFIX + native_blast_digest(bundle["identity"])
        for row in rows:
            if row["direction"] != "output" or row["role"] != "database_metadata":
                continue
            raw, oid = content[row["occurrence_id"]], row["occurrence_id"]
            checks.append(_check_bytes(raw, row))
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            fields, parsing, units = _metadata_fields(text, oid)
            metadata.extend(fields); problems.extend(parsing)
            if units and units != {"nt" if operation["molecule"] == "dna" else "aa"}:
                problems.append(failure("validation", "database_kind_conflict", oid))
            if not raw:
                problems.append(failure("capture", "output_missing", oid))
            checks.append(_check("syntax", "fail" if parsing else "pass", [oid], "native_format_parser", [oid],
                "native_document_invalid" if parsing else None))
        identity = {"namespace": "episode_native_execution", "value": bundle["identity"]["execution_id"],
            "version": None, "release": None, "scope": None, "preparation_type": "sequence_database",
            "source": {"source_ref": plan["capture"]["source_ref"], "pointer": ""}}
        result = populate_database_artifact_set(operation=operation,
            inputs=[r for r in rows if r["direction"] == "input"], outputs=[r for r in rows if r["direction"] == "output"],
            database_key=database_key, identity=identity,
            software={"name": operation["program"], "version": bundle["software"]["declared_engine_version"],
                "executable_sha256": bundle["software"]["actual_sha256"]}, argv=bundle["realized_argv"],
            native_paths=[str(PurePosixPath(plan["capture"]["plan"]["attempt_directory"]) / operation["parameters"]["output_prefix"])],
            dependency_bindings=[{"role": r["role"], "occurrence_id": r["occurrence_id"]} for r in rows
                                 if r["direction"] == "input" and r["role"] in {"taxid_map", "mask_input"}],
            native_metadata=metadata, outcome=outcome)
        result["checks"].extend(check for check in checks if check not in result["checks"])
        result["failures"] = unique_failures([*result["failures"], *problems, *context["failures"]])
        result = core("DatabaseArtifactSet", result)
        receipt_occurrence = next(r for r in rows if r["direction"] == "output" and r["role"] == "preparation_receipt")
        receipt = {"path": receipt_occurrence["native_path"],
            **{k: receipt_occurrence[k] for k in ("artifact_ref", "sha256", "size_bytes")}}
        metadata_files = [{"path": r["native_path"], **{k: r[k] for k in ("sha256", "size_bytes", "artifact_ref")}}
                          for r in rows if r["direction"] == "output" and r["role"] == "database_metadata"]
        prepared = project_prepared_blast_database(result, contract="standard", preparation_receipt=receipt,
            input_manifest=None, metadata_manifests=metadata_files)
        manifest["outputs"]["prepared_database"] = _write(directory, OUTPUT_FILES["prepared_database"], prepared)
        manifest["failures"].extend(prepared["failures"])
        if prepared["status"] == "available":
            manifest["outputs"]["prepared_manifest"] = _write(directory, OUTPUT_FILES["prepared_manifest"], prepared["manifest"])
    manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
    manifest["failures"].extend(result["failures"])


def _project_saved(plan, directory, manifest):
    from .blast_utility_result_views import project_blast_utility_result
    saved = {role: _decode(_read_bytes(row)) if row is not None else None for role, row in plan["files"].items()}
    prepared = saved["prepared_database"]
    if ((prepared is not None and prepared.get("status") == "available") != (saved["prepared_manifest"] is not None)
            or saved["prepared_manifest"] is not None and prepared["manifest"] != saved["prepared_manifest"]):
        _error("worker_saved_manifest_conflict")
    context = plan["context"]
    selected = project_blast_utility_result(source_ref=plan["source_ref"], operation=context["operation"],
        native_outcome=context["native_outcome"], result=saved["result"], prepared_database=prepared,
        occurrences=context["occurrences"], selector=plan["selector"], failures=context["failures"], saved_data=plan["saved_data"],
        **({"context": context} if plan["version"] == PLAN_VERSION_V2 else {}))
    manifest["outputs"]["projection"] = _write(directory, OUTPUT_FILES["projection"], selected)
    if plan["version"] == PLAN_VERSION_V2:
        manifest["context_authentication"] = deepcopy(plan["context_authentication"])


def validate_worker_manifest(manifest: dict, plan: dict) -> dict:
    plan, manifest = validate_worker_plan(plan), finite_json_copy(manifest)
    vdb = plan["version"] == PLAN_VERSION_V2
    fields = {"version", "task", "plan_sha256", "completed", "outputs", "failures"} | ({"context_authentication"} if vdb else set())
    if (type(manifest) is not dict or set(manifest) != fields
            or manifest["version"] != (MANIFEST_VERSION_V2 if vdb else MANIFEST_VERSION) or manifest["task"] != plan["task"]
            or manifest["plan_sha256"] != native_blast_digest(plan) or type(manifest["completed"]) is not bool
            or type(manifest["outputs"]) is not dict or unique_failures(manifest["failures"]) != manifest["failures"]):
        _error("worker_manifest_invalid")
    outputs = set(manifest["outputs"])
    builder = blast_utility_result_version_for_operation(plan["context"]["operation"]) in {
        "blast_database_artifact_set_v1", "blast_database_artifact_set_v2"}
    allowed = {"projection"} if plan["task"] == "project_saved" else {"result", "prepared_database", "prepared_manifest"} if builder else {"result"}
    required = ({"projection"} if plan["task"] == "project_saved" else
                {"result", "prepared_database"} if builder else {"result"}) if plan["task"] == "project_saved" or _can_read_result(plan["context"]) else set()
    if not outputs <= allowed or manifest["completed"] and not required <= outputs:
        _error("worker_manifest_output_population_conflict")
    if plan["task"] == "parse_original" and not _can_read_result(plan["context"]) and outputs:
        _error("worker_unavailable_result_conflict")
    if "prepared_manifest" in outputs and not {"result", "prepared_database"} <= outputs:
        _error("worker_manifest_preparation_conflict")
    for role, row in manifest["outputs"].items():
        if (type(row) is not dict or set(row) != {"filename", "sha256", "size_bytes"} or row["filename"] != OUTPUT_FILES[role]
                or type(row["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0):
            _error("worker_manifest_descriptor_invalid")
    if any(row not in manifest["failures"] for row in plan["context"]["failures"]):
        _error("worker_manifest_original_failure_missing")
    if vdb:
        proof = manifest["context_authentication"]
        if proof is not None:
            from .native_blast_vdb_utility_context import validate_vdb_context_authentication, validate_vdb_context_authentication_shape
            if plan["task"] == "parse_original":
                validate_vdb_context_authentication(proof, capture=plan["capture"], context=plan["context"])
            else:
                validate_vdb_context_authentication_shape(proof, context=plan["context"])
        if plan["task"] == "parse_original":
            if "result" in outputs and proof is None or manifest["completed"] and "result" not in outputs:
                _error("worker_vdb_context_authentication_required")
        elif manifest["completed"] and proof != plan["context_authentication"]:
            _error("worker_vdb_context_authentication_conflict")
    return manifest


def run(plan: dict) -> dict:
    plan = validate_worker_plan(plan)
    directory = _directory(plan["directory"])
    if not directory.is_dir():
        _error("worker_directory_required")
    intent = {"plan_sha256": native_blast_digest(plan)}
    if (directory / "worker-intent.json").exists():
        if _read_record(directory, "worker-intent.json") != intent:
            _error("worker_identity_conflict")
        if not (directory / "worker-result.json").is_file():
            _error("worker_original_work_incomplete")
        saved = validate_worker_manifest(_read_record(directory, "worker-result.json"), plan)
        for row in saved["outputs"].values():
            _verify_file({"path": str(directory / row["filename"]), **{k: row[k] for k in ("sha256", "size_bytes")}})
        return saved
    _immutable(directory / "worker-intent.json", intent)
    vdb = plan["version"] == PLAN_VERSION_V2
    manifest = {"version": MANIFEST_VERSION_V2 if vdb else MANIFEST_VERSION, "task": plan["task"], "plan_sha256": native_blast_digest(plan),
        "completed": False, "outputs": {}, "failures": deepcopy(plan["context"]["failures"])}
    if vdb:
        manifest["context_authentication"] = None
    try:
        (_parse_original if plan["task"] == "parse_original" else _project_saved)(plan, directory, manifest)
        manifest["completed"] = not (vdb and plan["task"] == "parse_original" and "result" not in manifest["outputs"])
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(canonical(diagnostic(error)), file=sys.stderr)
        code = str(error).removeprefix(PREFIX)
        if vdb and str(error).endswith("_worker_retained_bytes_mismatch"):
            code = "input_identity_mismatch"
        code = code if vdb and code in {"supplied_binding_conflict", "input_identity_mismatch", "input_population_unavailable"} else "semantic_validation_unavailable"
        manifest["failures"].append(failure("parse" if plan["task"] == "parse_original" else "projection", code))
    manifest["failures"] = unique_failures(manifest["failures"])
    manifest = validate_worker_manifest(manifest, plan)
    _immutable(directory / "worker-result.json", manifest)
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        _error("one_worker_plan_required")
    result = run(_decode(Path(args[0]).read_bytes()))
    print(canonical(result))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
