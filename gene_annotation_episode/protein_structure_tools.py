"""Ordinary selected protein operations over the existing native primitives.

Configuration and argument schemas are declarations. Preparation authenticates
one actual selected action, runs or recovers its original native unit, and
qualifies retained inputs for the shared projection reader. It publishes no
Source, report, observation or scientific interpretation.
"""
from __future__ import annotations

from copy import deepcopy
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
from typing import TypedDict

from .acquisition import AcquisitionError
from .communication import plain
from .domain import ContractError, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy, run_cancellable_native
from .molecular_measurement_tools import MolecularOperationUnpublished, authenticate_molecular_invocation
from .native_protein_structure_acquisition import (
    capture_protein_structure_plan_bundle, decode_protein_structure_json,
    retained_protein_structure_file, validate_protein_structure_plan_capture,
)
from .native_protein_structure_contracts import (
    ATTEMPT_DIRECTORY_NAME, POLICY, RUN_PLAN_FILENAME, _environment, _path, driver_argv, output_files,
    protein_structure_execution_schema, requested_job_from_protein_structure,
    required_input_files,
    validate_native_protein_structure_result, validate_protein_structure_bindings,
    validate_protein_structure_bundle, validate_protein_structure_request,
    validate_protein_structure_run_plan,
)
from .native_protein_structure_driver import _directory, _immutable, _regular
from .native_protein_structure_local import (
    _environment as _native_environment, _invoke, _root,
    local_protein_structure_plan, prepare_selected_local_protein_structure,
)
from .native_protein_structure_preparation import (
    _check_handle as _check_worker_handle, _execution_issue, _intent as _worker_intent,
    _retained as _retained_control, _stored_json as _stored_control_json,
    prepare_protein_structure_worker, validate_prepared_protein_structure_worker,
)
from .native_protein_structure_tool_info import _DESCRIPTIONS, _INSTRUCTIONS, _NAMES
from .protein_structure_contracts import issue, same
from .protein_structure_operands import _sequence_refs, _transform_refs, resolve_protein_structure_operands
from .protein_structure_result_views import protein_structure_projection_schema
from .protein_structure_selection import (
    validate_protein_structure_result_selector,
)


PROTEIN_STRUCTURE_OPERATIONS = {name: operation for operation, name in _NAMES.items()}
PROTEIN_STRUCTURE_TOOLS = tuple(PROTEIN_STRUCTURE_OPERATIONS)
ProteinOperationUnpublished = MolecularOperationUnpublished
SAVED_MODES = ("read_stored", "recalculate", "select_projection")
SAVED_WORK_VERSION = "ordinary_protein_structure_saved_work_v1"


class PreparedSavedProteinWork(TypedDict):
    version: str
    mode: str
    tool_name: str
    arguments: dict
    scope: dict
    invocation: dict
    admission: dict
    binding: dict | None
    worker: dict | None
    qualified_files: dict
    scientific: dict | None
    issues: list[dict]
    redisplay: dict | None


class PreparedProteinWork(TypedDict):
    version: str
    tool_name: str
    arguments: dict
    scope: dict
    invocation: dict
    binding: dict
    requested_job: dict
    selector: dict
    selected_references: list[str]
    plan: dict | None
    execution: dict
    capture: dict | None
    bundle: dict | None
    worker: dict | None
    scientific: dict | None
    qualified_files: dict
    selected_projections: list[dict]
    issues: list[dict]


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _copy(value):
    return json.loads(canonical(plain(value)))


def normalize_protein_structure_configuration(resources, environments, policy):
    """Select only explicitly configured software/environment pairs; perform no I/O."""
    _require(environments is None or isinstance(environments, (list, tuple)),
        "protein_structure_environments_list_required")
    if not environments:
        return None
    resources, environments = _copy(resources), _copy(environments)
    _require(type(resources) is dict, "protein_structure_resources_required")
    selected_policy = policy if type(policy) is LocalJobPolicy else LocalJobPolicy(**_copy(policy))
    _require(same(selected_policy.to_dict(), POLICY), "protein_structure_policy_conflict")
    bindings, seen = [], set()
    for entry in environments:
        _require(type(entry) is dict and set(entry) == {
            "resource_id", "binding_ordinal_0based", "environment"},
            "protein_structure_environment_record_invalid")
        resource_id, ordinal = entry["resource_id"], entry["binding_ordinal_0based"]
        _require(type(resource_id) is str and resource_id and type(ordinal) is int and ordinal >= 0,
            "protein_structure_binding_selection_invalid")
        _require((resource_id, ordinal) not in seen, "protein_structure_binding_selection_duplicate")
        seen.add((resource_id, ordinal))
        resource = resources.get(resource_id)
        _require(type(resource) is dict and resource.get("kind") == "local",
            "protein_structure_local_resource_required")
        declared = validate_protein_structure_bindings(resource.get("native_protein_structure"))
        _require(ordinal < len(declared), "protein_structure_binding_selection_invalid")
        _require(same(resource.get("policy"), selected_policy.to_dict()), "protein_structure_policy_conflict")
        _path(resource.get("workspace"), absolute=True)
        _environment(entry["environment"])
        selected = declared[ordinal]
        bindings.append({"resource_id": resource_id, "binding_ordinal_0based": ordinal,
            **selected, "environment": entry["environment"], "workspace": resource["workspace"]})
    return _copy({"version": "ordinary_protein_structure_configuration_v1",
        "policy": selected_policy.to_dict(),
        "bindings": sorted(bindings, key=lambda row: (row["resource_id"], row["binding_ordinal_0based"]))})


def _definitions_for(roots):
    definitions = protein_structure_execution_schema("ScientificRequest", action_custody=True)["$defs"]
    for name, value in protein_structure_projection_schema("ProjectionSelection", action_custody=True)["$defs"].items():
        _require(name not in definitions or same(definitions[name], value),
            "protein_structure_schema_definition_conflict")
        definitions[name] = value
    selected = {}

    def visit(value):
        if isinstance(value, dict):
            reference = value.get("$ref")
            if reference is not None:
                _require(type(reference) is str and reference.startswith("#/$defs/"),
                    "protein_structure_schema_reference_invalid")
                name = reference[len("#/$defs/"):]
                _require(name in definitions, "protein_structure_schema_reference_invalid")
                if name not in selected:
                    selected[name] = deepcopy(definitions[name])
                    visit(selected[name])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for root in roots:
        visit({"$ref": "#/$defs/" + root})
    return selected


def _binding_choices_table(choices):
    headers = ("Resource", "Binding ordinal (zero-based)", "Operation", "Mode",
        "Python version", "NumPy version", "Biopython version")

    def cell(value):
        return ("null" if value is None else str(value)).replace("|", "\\|").replace("\n", "<br>")

    rows = [(row["resource_id"], row["binding_ordinal_0based"], row["operation"], row["scientific_mode"],
        row["software"]["python_version"], row["software"]["numpy_version"], row["software"]["biopython_version"])
        for row in choices]
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def _saved_argument_schemas(choices=None):
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source",
        "pattern": "^source_[a-f0-9]{24,64}$"}
    projections = {"type": "array", "items": {"allOf": [{"$ref": "#/$defs/ProjectionSelection"},
        {"properties": {"delivery_kind": {"const": "values"}, "family": {"enum": [
            "comparison_summary", "transform", "site_measurements", "correspondence",
            "structure_coordinates", "native_uncertainty"]}}}]}}
    common = dict(saved_sheet={"$ref": "#/$defs/SavedSheetDescriptorV2"}, projections=projections)
    shapes = {
        "read_stored": dict(result_ref=reference),
        "recalculate": dict(resource_id={"type": "string"}, binding_ordinal_0based={"type": "integer", "minimum": 0},
            parameters={"$ref": "#/$defs/CalculationParameters"}, **common),
        "select_projection": dict(result_ref=reference, **common),
    }
    result = {}
    for mode, properties in shapes.items():
        properties = dict(mode={"const": mode}, **deepcopy(properties))
        schema = {"type": "object", "additionalProperties": False, "required": list(properties),
            "properties": properties, "$defs": _definitions_for(("SavedSheetDescriptorV2", "CalculationParameters", "ProjectionSelection"))}
        if mode == "recalculate" and choices is not None:
            alternatives = []
            for row in choices:
                selection = dict(resource_id={"const": row["resource_id"]},
                    binding_ordinal_0based={"const": row["binding_ordinal_0based"]})
                if row["scientific_mode"] is not None:
                    selection["parameters"] = {"properties": {"mode": {"const": row["scientific_mode"]}}}
                alternatives.append({"properties": selection})
            schema["allOf"] = [{"anyOf": alternatives}]
        schema["$id"] = "urn:gene-annotation:ordinary-protein-saved-tool:" + digest(schema)
        result[mode] = schema
    return result


def protein_structure_tool_catalog(configuration):
    """Declare scientific arguments without exporting compiled native job machinery."""
    if configuration is None:
        return {}
    configuration = _copy(configuration)
    _require(configuration.get("version") == "ordinary_protein_structure_configuration_v1",
        "protein_structure_configuration_invalid")
    result = {}
    request_types = {"inspect": "InspectRequest", "extract_sequence": "ExtractRequest", "compare": "CompareRequest"}
    families = {"inspect": ["structure_inventory"], "extract_sequence": ["extracted_sequence", "native_uncertainty"],
        "compare": ["comparison_summary", "transform", "site_measurements", "correspondence",
            "structure_coordinates", "native_uncertainty"]}
    for name, operation in PROTEIN_STRUCTURE_OPERATIONS.items():
        choices = [row for row in configuration["bindings"] if row["operation"] == operation]
        if not choices:
            continue
        alternatives = []
        for row in choices:
            request = {"properties": {"operation": {"const": operation}}}
            if row["scientific_mode"] is not None:
                request["properties"]["parameters"] = {"properties": {"mode": {"const": row["scientific_mode"]}}}
            alternatives.append({"properties": {"resource_id": {"const": row["resource_id"]},
                "binding_ordinal_0based": {"const": row["binding_ordinal_0based"]}, "request": request}})
        selection = {"type": "object", "additionalProperties": False,
            "required": ["projections", "return_saved_sheet", "sequence_allowed_uses"], "properties": {
                "projections": {"type": "array", "items": {"allOf": [
                    {"$ref": "#/$defs/ProjectionSelection"}, {"properties": {"family": {"enum": families[operation]}}}]}},
                "return_saved_sheet": {"type": "boolean"} if operation == "compare" else {"const": False},
                "sequence_allowed_uses": {"type": "array", "uniqueItems": True,
                    "items": {"enum": ["sequence_align", "structure_correspondence"]},
                    **({} if operation == "extract_sequence" else {"maxItems": 0})}}}
        schema = {"type": "object", "additionalProperties": False,
            "required": ["resource_id", "binding_ordinal_0based", "request", "selection"],
            "properties": {"resource_id": {"type": "string",
                    "description": "Resource identity in the Configured software choices table."},
                "binding_ordinal_0based": {"type": "integer", "minimum": 0,
                    "description": "Zero-based binding ordinal for that resource in the Configured software choices table."},
                "request": {"$ref": "#/$defs/" + request_types[operation]}, "selection": selection},
            "allOf": [{"anyOf": alternatives}],
            "$defs": _definitions_for((request_types[operation], "ProjectionSelection"))}
        # Enter an owned schema resource when this contract is embedded inside
        # a decision envelope, preserving each local #/$defs reference.
        schema["$id"] = "urn:gene-annotation:ordinary-protein-tool:" + digest(schema)
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": deepcopy(schema["$defs"]), "allOf": [schema]}
        schema["$id"] = "urn:gene-annotation:ordinary-protein-tool:" + digest(schema)
        if operation == "compare":
            saved_schemas = _saved_argument_schemas(choices)
            definitions = deepcopy(schema["$defs"])
            for document in saved_schemas.values():
                for key, value in document["$defs"].items():
                    _require(key not in definitions or same(definitions[key], value),
                        "protein_structure_schema_definition_conflict")
                    definitions[key] = deepcopy(value)
            schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": definitions,
                "oneOf": [schema, *saved_schemas.values()]}
            schema["$id"] = "urn:gene-annotation:ordinary-protein-tool:" + digest(schema)
        result[name] = {"description": _DESCRIPTIONS[operation],
            "instructions": _INSTRUCTIONS[operation] + "\n\nConfigured software choices\n\n" + _binding_choices_table(choices),
            "resources": "local", "invocation_route": {"kind": "direct"}, "input_schema": schema,
            "configuration": {"job_limits": configuration["policy"], "bindings": [{
                "resource_id": row["resource_id"], "binding_ordinal_0based": row["binding_ordinal_0based"],
                "operation": operation, "scientific_mode": row["scientific_mode"],
                **{field: row["software"][field] for field in
                    ("python_version", "numpy_version", "biopython_version", "implementation", "algorithm")}}
                for row in choices]}}
        if operation == "compare":
            result[name]["instructions"] += ("\n\nSaved-data modes: read_stored returns the selected values and descriptors already published by the explicitly supplied, received result Source. "
                "recalculate uses an actually owned or received saved-sheet descriptor, the explicit new parameters and the selected configured software. "
                "select_projection selects value fields from the explicitly supplied authenticated saved result. "
                "These modes use retained data without rerunning the original structure comparison. "
                "Returned Source custody does not grant saved-data or control Files.")
    return result


def _authenticate(registry, name, arguments, scope, operation_key, authority):
    _require(isinstance(authority, tuple) and len(authority) == 2 and callable(authority[1]),
        "protein_structure_current_invocation_required")
    context, _ = authority
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protein_structure_tool_").authenticate(context)
    prefix = context.run_id + ":" + context.episode_id + ":"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(suffix.isdecimal() and str(int(suffix)) == suffix
        and canonical(plain(context.scope)) == canonical(scope), "protein_structure_selected_action_conflict")
    row = registry.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
    _require(row is not None and canonical(json.loads(row["action"])) == canonical(
        {"kind": "tool", "tool": name, "arguments": arguments}), "protein_structure_selected_action_conflict")
    return context


def _run_selected(assignment, operation_key, *, run_id, episode_id, root, policy, binding_control, cancel_event):
    lock = os.open(root / ".ordinary-native.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _immutable(root / "ordinary-tool-binding.json", binding_control)
        return _run_reserved(assignment, operation_key, run_id=run_id, episode_id=episode_id,
            root=root, policy=policy, cancel_event=cancel_event)
    finally:
        os.close(lock)


def _run_reserved(assignment, operation_key, *, run_id, episode_id, root, policy, cancel_event):
    from . import native_lifecycle as native
    record_path = root / "ordinary-execution.json"
    if record_path.exists():
        saved = decode_protein_structure_json(record_path.read_bytes(), canonical_bytes=True)
        _validate_execution(saved, assignment=assignment, root=root, policy=policy)
        return saved
    handle = native.NativeJobHandle(root / "native.json")
    execution = {"version": "ordinary_protein_structure_execution_v1", "outcome": "failed",
        "returncode": None, "metadata": None, "failure": None, "terminal": True, "quiescent": True}
    try:
        handle = prepare_selected_local_protein_structure(assignment, operation_key,
            run_id=run_id, episode_id=episode_id, root=root, policy=policy)
        view = native.status(handle)
        if view["terminal"] and view["quiescent"]:
            result = native.collect(handle)
        else:
            native.resume_start(handle, cancel_event=cancel_event)
            result = native.wait_job(handle, cancel_event=cancel_event)
        execution.update(outcome="returned", returncode=result.returncode, metadata=deepcopy(result.metadata))
    except Exception as error:
        if not isinstance(error, AcquisitionError):
            raise
        if handle.path.exists():
            view = native.status(handle)
            if not (view["terminal"] and view["quiescent"]):
                raise ProteinOperationUnpublished("protein_structure_original_attempt_unconfirmed") from error
        execution["failure"] = {"code": error.code, "phase": error.phase,
            "diagnostic": deepcopy(error.diagnostic), "operational": deepcopy(error.operational)}
    _validate_execution(execution, assignment=assignment, root=root, policy=policy)
    _immutable(record_path, execution)
    return execution


def _validate_execution(value, *, assignment, root, policy):
    from .native_lifecycle import NativeJobHandle
    _require(type(value) is dict and set(value) == {"version", "outcome", "returncode", "metadata", "failure",
        "terminal", "quiescent"} and value["version"] == "ordinary_protein_structure_execution_v1"
        and value["terminal"] is True and value["quiescent"] is True, "protein_structure_execution_record_invalid")
    returned = value["outcome"] == "returned"
    _require(value["outcome"] in ("returned", "failed"), "protein_structure_execution_record_invalid")
    if returned:
        _require(type(value["returncode"]) is int and type(value["metadata"]) is dict and value["failure"] is None,
            "protein_structure_execution_record_invalid")
        metadata = value["metadata"]
    else:
        failure = value["failure"]
        _require(value["returncode"] is None and value["metadata"] is None and type(failure) is dict
            and set(failure) == {"code", "phase", "diagnostic", "operational"} and type(failure["code"]) is str,
            "protein_structure_execution_record_invalid")
        metadata = failure["operational"]
    handle_path = root / "native.json"
    if not handle_path.exists():
        _require(not returned, "protein_structure_execution_record_invalid")
        return
    local_protein_structure_plan(assignment, str(handle_path))
    body = NativeJobHandle(handle_path).read()
    _require(same(body["metadata"]["policy"], policy.to_dict()) and type(metadata) is dict
        and all(same(metadata.get(key), item) for key, item in body["metadata"].items()),
        "protein_structure_execution_record_invalid")
    if returned:
        _require(body["stage"] == "released" and type(metadata.get("native_returncode")) is int
            and metadata["native_returncode"] == value["returncode"], "protein_structure_execution_record_invalid")
        with _regular(body["paths"]["status"]) as stream:
            status = decode_protein_structure_json(stream.read())
        with _regular(body["paths"]["result"]) as stream:
            receipt = decode_protein_structure_json(stream.read())
        _require(same(metadata.get("service_exit"), status)
            and receipt.get("native_returncode") == value["returncode"]
            and receipt.get("resource_failure") is None and receipt.get("execution_failure") is None,
            "protein_structure_execution_record_invalid")


def _retain_execution_controls(store, root, execution):
    from .materials import artifact_file
    from .native_lifecycle import NativeJobHandle
    paths = [root / name for name in ("ordinary-tool-binding.json", "ordinary-execution.json", RUN_PLAN_FILENAME,
        "invoke.json", "native.json", "stdout.log", "stderr.log")]
    if (root / "native.json").exists():
        paths.extend(Path(path) for path in NativeJobHandle(root / "native.json").read()["paths"].values())
    artifacts = {}
    for path in paths:
        _require(path.is_relative_to(root), "invalid_output_path")
        if path.exists():
            with _regular(path) as stream:
                artifacts[path.name] = artifact_file(store, Path("/proc/self/fd") / str(stream.fileno()))
    return {**deepcopy(execution), "artifacts": artifacts}


def _retained_bytes(store, identity):
    path = retained_protein_structure_file(store, identity)
    raw = path.read_bytes()
    _require(len(raw) == identity["byte_length"] and hashlib.sha256(raw).hexdigest() == identity["sha256"],
        "input_digest_mismatch")
    return raw


def _retained_json(store, identity):
    return decode_protein_structure_json(_retained_bytes(store, identity), canonical_bytes=True)


def _captured(capture, role):
    rows = [row["observed"] for row in capture["files"]
        if row["declared"]["role"] == role and row["outcome"] == "verified"]
    _require(len(rows) <= 1, "conflicting_identity")
    return deepcopy(rows[0]) if rows else None


def _problem(error, *, stage="capture", field="manifest", artifact_role=None):
    from .protein_structure_contracts import IssueCode
    from typing import get_args
    code = str(error) if str(error) in get_args(IssueCode) else "invalid_schema"
    return issue(code, stage=stage, field=field, artifact_role=artifact_role)


def _qualify_science(store, work):
    result = None if work["worker"] is None else work["worker"]["result"]
    if result is None:
        return
    operation = work["binding"]["operation"]
    required = ("native_result_file", "sheet_file", "components_file") if operation == "compare" else ("native_result_file",)
    if any(result[name] is None for name in required):
        return
    files = work["qualified_files"]
    native_file = result["native_result_file"]["file_identity"]
    native = validate_native_protein_structure_result(_retained_json(store, native_file))
    job = work["requested_job"]["native_protein_structure"]
    _require(same(native["request"], job["request"]) and same(native["producer"], job["software"]),
        "original_commission_mismatch")
    files["native_file"] = native_file
    if operation == "inspect":
        work["scientific"] = {"kind": "inspection", "inventory": native["inventory"]}
    elif operation == "extract_sequence":
        sequence = native["sequence"]
        selected = {role: _captured(work["capture"], role) for role in ("sequence", "residue_map", "single_structure")}
        if sequence["sequence_available"] and all(selected.values()):
            try:
                _require(same(selected["single_structure"], sequence["selection"]["file_identity"]), "sequence_artifact_mismatch")
                _require(_retained_bytes(store, selected["sequence"]) == sequence["alignment_sequence"].encode("ascii")
                    and _retained_bytes(store, selected["residue_map"]) == canonical(sequence).encode("utf-8"),
                    "sequence_artifact_mismatch")
                _retained_bytes(store, selected["single_structure"])
            except (ValueError, OSError) as error:
                work["issues"].append(_problem(error, stage="sequence", field="sequence"))
            else:
                files.update(sequence_file=selected["sequence"], residue_map_file=selected["residue_map"])
        work["scientific"] = {"kind": "extraction", "sequence": sequence, "metadata": native["metadata"], "descriptor": None}
    else:
        from .protein_structure_calculations import validate_recorded_protein_structure_components
        sheet_file, components_file = [result[name]["file_identity"] for name in ("sheet_file", "components_file")]
        sheet, components = _retained_json(store, sheet_file), _retained_json(store, components_file)
        _require(same(sheet, native["sheet"]) and same(components, sheet["native_baseline"])
            and same(components["parameters"], job["request"]["parameters"]), "original_commission_mismatch")
        validate_recorded_protein_structure_components(sheet, components=components)
        files.update(sheet_file=sheet_file, original_components_file=components_file, components_file=components_file)
        work["scientific"] = {"kind": "comparison", "sheet": sheet, "components": components}


def _prepare_result_worker(store_path, *, plan, policy, software, environment, cancel_event):
    from .state import Store
    # As in the existing result host, each thread owns its SQLite connection.
    with Store(store_path) as store:
        prepared = prepare_protein_structure_worker(store, plan=plan, policy=policy,
            executable=software["python_executable"], environment=environment, cancel_event=cancel_event)
        return validate_prepared_protein_structure_worker(store, prepared, plan=plan)


async def prepare_protein_structure_work(registry, name, args, *, scope, operation_key, authority, input_authority):
    """Prepare one selected operation; publication remains with the ordinary registry."""
    _require(not registry.store.db.in_transaction, "protein_structure_work_requires_no_store_transaction")
    arguments, scope = _copy(args), _copy(scope)
    context = _authenticate(registry, name, arguments, scope, operation_key, authority)
    configuration = registry._protein_structure_configuration
    catalog = protein_structure_tool_catalog(configuration)
    _require(name in catalog, "protein_structure_tool_not_configured")
    validate_schema(arguments, catalog[name]["input_schema"])
    if name == "compare_protein_structures" and arguments.get("mode") in SAVED_MODES:
        return await _prepare_saved_protein_work(registry, arguments, scope=scope,
            operation_key=operation_key, context=context, input_authority=input_authority)
    ordinal = arguments["binding_ordinal_0based"]
    _require(type(ordinal) is int, "protein_structure_binding_selection_invalid")
    selected = [row for row in configuration["bindings"] if row["resource_id"] == arguments["resource_id"]
        and row["binding_ordinal_0based"] == ordinal and row["operation"] == PROTEIN_STRUCTURE_OPERATIONS[name]]
    _require(len(selected) == 1, "protein_structure_binding_selection_invalid")
    binding = {**deepcopy(selected[0]), "policy": deepcopy(configuration["policy"])}
    request = validate_protein_structure_request(arguments["request"])
    selection = arguments["selection"]
    _require(type(selection["return_saved_sheet"]) is bool, "protein_structure_selection_invalid")
    selector = validate_protein_structure_result_selector({"version": "protein_structure_result_selector_v1",
        "acquisition": "complete_bound_bundle", "saved_sheet": None, "parameters": None,
        **selection}, request=request)
    resolved = resolve_protein_structure_operands(registry.store, context, request, returns=input_authority)
    job = {"version": "native_protein_structure_job_v1", "program": "protein_structure_python",
        "request": resolved["request"], "software": binding["software"], "inputs": resolved["input_files"],
        "outputs": output_files(request["operation"]), "environment": binding["environment"]}
    requested_job = requested_job_from_protein_structure(job)
    assignment = {"resource_id": binding["resource_id"], "resource_kind": "local", "workspace": binding["workspace"],
        "requested_job": requested_job, "constraints": {"allocation": binding["policy"]}}
    invocation = {"run_id": context.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
        "request_sha256": digest(plain(context.request))}
    root = _directory(_root(assignment, invocation))
    root.mkdir(parents=True, exist_ok=True)
    binding_control = {"version": "ordinary_protein_structure_binding_v1",
        "invocation": invocation, "tool_name": name, "arguments": arguments, "scope": scope,
        "binding_sha256": digest(binding), "requested_job_sha256": digest(requested_job), "selector": selector}
    policy = LocalJobPolicy(**binding["policy"])
    execution = await run_cancellable_native(_run_selected, assignment, operation_key,
        run_id=context.run_id, episode_id=context.episode_id, root=root, policy=policy, binding_control=binding_control)
    execution = _retain_execution_controls(registry.store, root, execution)
    execution_issue = _execution_issue(execution)
    work: PreparedProteinWork = {"version": "ordinary_protein_structure_work_v1", "tool_name": name,
        "arguments": arguments, "scope": scope, "invocation": invocation, "binding": binding,
        "requested_job": requested_job, "selector": selector, "selected_references": resolved["selected_references"],
        "plan": None, "execution": execution, "capture": None, "bundle": None, "worker": None, "scientific": None,
        "qualified_files": {name: None for name in ("native_file", "sequence_file", "residue_map_file", "sheet_file",
            "original_components_file", "components_file")},
        "selected_projections": deepcopy(selector["projections"]),
        "issues": [] if execution_issue is None else [execution_issue]}
    try:
        plan_path = root / RUN_PLAN_FILENAME
        if not plan_path.exists():
            raise ValueError("native_result_missing")
        plan = validate_protein_structure_run_plan(decode_protein_structure_json(plan_path.read_bytes(), canonical_bytes=True))
        _require(plan["identity"]["run_id"] == context.run_id and plan["identity"]["episode_id"] == context.episode_id
            and plan["identity"]["operation_key"] == operation_key and same(plan["requested_job"], requested_job),
            "original_commission_mismatch")
        if (root / "native.json").exists():
            local_protein_structure_plan(assignment, str(root / "native.json"))
        work["plan"] = plan
        capture = capture_protein_structure_plan_bundle(registry.store, plan=plan, directory=root / "capture")
        work["capture"] = capture
        work["issues"].extend(capture["failures"])
        if capture["bundle_validated"]:
            work["bundle"] = validate_protein_structure_bundle(_retained_json(registry.store, capture["bundle_file"]), plan=plan)
            work["issues"].extend(work["bundle"]["failures"])
        native_file = _captured(capture, "native_result")
        if native_file is not None:
            worker_plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
                "directory": str(root / "result-worker"), "expected_request": request,
                "expected_software": binding["software"],
                "native_result": {"file_identity": native_file,
                    "path": str(retained_protein_structure_file(registry.store, native_file))}}
            work["worker"] = await run_cancellable_native(_prepare_result_worker, registry.store.path, plan=worker_plan,
                policy=policy, software=binding["software"], environment=binding["environment"])
            work["issues"].extend(work["worker"]["prepared"]["issues"])
            if work["worker"]["result"] is not None:
                work["issues"].extend(work["worker"]["result"]["issues"])
            _qualify_science(registry.store, work)
        else:
            work["issues"].append(issue("native_result_missing", stage="native", artifact_role="native_result"))
    except ProteinOperationUnpublished:
        raise
    except AcquisitionError as error:
        # Preparation propagates only unconfirmed original worker execution;
        # terminal native failures are already retained in PreparedProteinWorker.
        raise ProteinOperationUnpublished("protein_structure_original_result_worker_unconfirmed") from error
    except (ValueError, OSError) as error:
        work["issues"].append(_problem(error))
    unique = {canonical(value): value for value in work["issues"]}
    work["issues"] = list(unique.values())
    return work


def _selected_work_contract(registry, work, authority):
    """Rebind a detached preparation to the actual current saved tool action."""
    _require(type(work) is dict and set(work) == set(PreparedProteinWork.__annotations__)
        and work["version"] == "ordinary_protein_structure_work_v1", "protein_structure_work_invalid")
    name, arguments, scope = work["tool_name"], _copy(work["arguments"]), _copy(work["scope"])
    _require(type(work["invocation"]) is dict, "protein_structure_selected_action_conflict")
    operation_key = work["invocation"].get("operation_key")
    current = authenticate_molecular_invocation(registry, name, arguments, scope, operation_key)
    _require(authority == current, "protein_structure_current_invocation_required")
    context = _authenticate(registry, name, arguments, scope, operation_key, authority)
    configuration = registry._protein_structure_configuration
    catalog = protein_structure_tool_catalog(configuration)
    _require(name in catalog, "protein_structure_tool_not_configured")
    validate_schema(arguments, catalog[name]["input_schema"])
    ordinal = arguments["binding_ordinal_0based"]
    _require(type(ordinal) is int, "protein_structure_binding_selection_invalid")
    rows = [row for row in configuration["bindings"] if row["resource_id"] == arguments["resource_id"]
        and row["binding_ordinal_0based"] == ordinal and row["operation"] == PROTEIN_STRUCTURE_OPERATIONS[name]]
    _require(len(rows) == 1, "protein_structure_binding_selection_invalid")
    binding = {**deepcopy(rows[0]), "policy": deepcopy(configuration["policy"])}
    request = validate_protein_structure_request(arguments["request"])
    _require(type(arguments["selection"]["return_saved_sheet"]) is bool, "protein_structure_selection_invalid")
    selector = validate_protein_structure_result_selector({"version": "protein_structure_result_selector_v1",
        "acquisition": "complete_bound_bundle", "saved_sheet": None, "parameters": None,
        **arguments["selection"]}, request=request)
    # Reconstruct the host compilation from literal File identities. This does
    # not resolve operands, reopen producer paths or read original input bytes.
    inputs = [{"input_id": "input_" + str(index), "role": role, "file_identity": deepcopy(identity),
        "path": str(registry.store.path / "artifacts" / identity["sha256"][:2] / identity["sha256"]),
        "staged_relative_path": "inputs/input_" + str(index)}
        for index, (role, identity) in enumerate(required_input_files(request))]
    requested_job = requested_job_from_protein_structure({"version": "native_protein_structure_job_v1",
        "program": "protein_structure_python", "request": request, "software": binding["software"],
        "inputs": inputs, "outputs": output_files(request["operation"]), "environment": binding["environment"]})
    references = [row["file_identity"]["artifact_ref"] for row in inputs]
    if request["operation"] == "compare":
        correspondence = request["correspondence"]
        if correspondence["kind"] == "retained_alignment":
            for side in ("fixed", "moving"):
                references.extend(_sequence_refs(correspondence[side + "_sequence_descriptor"]))
            alignment = correspondence["alignment"]
            references.extend([alignment["observation_ref"], alignment["source_ref"],
                alignment["native_file"]["artifact_ref"], alignment["grading_file"]["artifact_ref"]])
        transform = request["parameters"]["declared_transform"]
        if transform is not None and transform["origin"] == "received_fitted":
            references.extend(_transform_refs(transform))
    references = list(dict.fromkeys(references))
    invocation = {"run_id": context.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
        "request_sha256": digest(plain(context.request))}
    _require(all(same(work[field], expected) for field, expected in (
        ("invocation", invocation), ("binding", binding), ("requested_job", requested_job),
        ("selector", selector), ("selected_references", references), ("selected_projections", selector["projections"]))),
        "original_commission_mismatch")
    root = Path(binding["workspace"]) / ".episode-operations" / digest({
        "run": invocation["run_id"], "episode": invocation["episode_id"]}) / digest(operation_key)
    plan = validate_protein_structure_run_plan({"version": "native_protein_structure_run_plan_v1", "identity": {
        "run_id": context.run_id, "episode_id": context.episode_id, "resource_id": binding["resource_id"],
        "execution_id": str(root / "native.json"), "attempt_id": digest(operation_key),
        "operation_key": operation_key, "requested_job_sha256": digest(requested_job)},
        "requested_job": requested_job, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME),
        "policy": binding["policy"]})
    control = {"version": "ordinary_protein_structure_binding_v1", "invocation": invocation, "tool_name": name,
        "arguments": arguments, "scope": scope, "binding_sha256": digest(binding),
        "requested_job_sha256": digest(requested_job), "selector": selector}
    return _copy({"tool_name": name, "arguments": arguments, "scope": scope, "invocation": invocation,
        "binding": binding, "requested_job": requested_job, "selector": selector,
        "selected_references": references, "selected_projections": selector["projections"]}), plan, control


def _validate_retained_protein_execution(store, execution, *, plan, control):
    """Authenticate retained native controls without consulting their old paths."""
    from .native_lifecycle import VERSION
    fields = {"version", "outcome", "returncode", "metadata", "failure", "terminal", "quiescent"}
    _require(type(execution) is dict and set(execution) == fields | {"artifacts"},
        "protein_structure_execution_record_invalid")
    execution = _copy(execution)
    artifacts = execution["artifacts"]
    _require(type(artifacts) is dict and {"ordinary-tool-binding.json", "ordinary-execution.json"} <= artifacts.keys(),
        "protein_structure_execution_record_invalid")
    for name, reference in artifacts.items():
        _require(type(name) is str and name == Path(name).name, "invalid_output_path")
        _retained_control(store, reference)
    _require(same(_stored_control_json(store, artifacts["ordinary-tool-binding.json"]), control)
        and same(_stored_control_json(store, artifacts["ordinary-execution.json"]),
            {key: execution[key] for key in fields}), "original_commission_mismatch")
    _require(execution["version"] == "ordinary_protein_structure_execution_v1"
        and execution["terminal"] is True and execution["quiescent"] is True,
        "protein_structure_execution_record_invalid")
    returned = execution["outcome"] == "returned"
    _require(execution["outcome"] in ("returned", "failed"), "protein_structure_execution_record_invalid")
    if returned:
        _require(type(execution["returncode"]) is int and type(execution["metadata"]) is dict
            and execution["failure"] is None, "protein_structure_execution_record_invalid")
        metadata = execution["metadata"]
    else:
        failure = execution["failure"]
        _require(execution["returncode"] is None and execution["metadata"] is None and type(failure) is dict
            and set(failure) == {"code", "phase", "diagnostic", "operational"}
            and type(failure["code"]) is str and bool(failure["code"])
            and (failure["phase"] is None or type(failure["phase"]) is str)
            and all(failure[key] is None or type(failure[key]) is dict for key in ("diagnostic", "operational")),
            "protein_structure_execution_record_invalid")
        metadata = failure["operational"]
    root = Path(plan["identity"]["execution_id"]).parent
    fixed = {"ordinary-tool-binding.json", "ordinary-execution.json", RUN_PLAN_FILENAME,
        "invoke.json", "native.json", "stdout.log", "stderr.log"}
    if RUN_PLAN_FILENAME in artifacts:
        retained_plan = validate_protein_structure_run_plan(_stored_control_json(store, artifacts[RUN_PLAN_FILENAME]))
        _require(same(retained_plan, plan), "original_commission_mismatch")
    else:
        _require(not returned and "native.json" not in artifacts, "original_commission_mismatch")
    if "invoke.json" in artifacts:
        _require(same(_stored_control_json(store, artifacts["invoke.json"]),
            _invoke(plan["requested_job"], Path(plan["attempt_directory"]))), "original_commission_mismatch")
    if "native.json" not in artifacts:
        _require(not returned and set(artifacts) <= fixed, "protein_structure_execution_record_invalid")
        return execution, RUN_PLAN_FILENAME in artifacts
    _require({RUN_PLAN_FILENAME, "invoke.json", "stdout.log", "stderr.log"} <= artifacts.keys(),
        "protein_structure_execution_record_invalid")
    body = _stored_control_json(store, artifacts["native.json"], canonical_bytes=False)
    _require(type(body) is dict and set(body) == {"version", "unit", "command", "cwd", "stdout", "stderr", "paths",
        "metadata", "stage", "started_at", "started_monotonic_ns", "boot_id", "request_sha256"}
        and body["version"] == VERSION and body["stage"] in ("prepared", "submitting", "released"),
        "protein_structure_execution_record_invalid")
    _require(type(body["unit"]) is str and re.fullmatch(r"gene-local-job-[a-f0-9]{32}\.service", body["unit"])
        and same(body["command"], driver_argv(plan)) and body["cwd"] == str(root)
        and body["stdout"] == str(root / "stdout.log") and body["stderr"] == str(root / "stderr.log"),
        "original_commission_mismatch")
    paths = body["paths"]
    _require(type(paths) is dict and set(paths) == {"request", "ready", "release", "status", "result", "launcher"},
        "invalid_output_path")
    _require(type(paths["request"]) is str and Path(paths["request"]).parent == root
        and re.fullmatch(r"\.local-job-[a-f0-9]{32}\.request", Path(paths["request"]).name), "invalid_output_path")
    prefix = paths["request"][:-len("request")]
    _require(all(paths[name] == prefix + name for name in paths)
        and set(artifacts) <= fixed | {Path(path).name for path in paths.values()}, "invalid_output_path")
    request_name = Path(paths["request"]).name
    _require(request_name in artifacts and type(body["request_sha256"]) is str
        and re.fullmatch(r"[a-f0-9]{64}", body["request_sha256"])
        and artifacts[request_name] == "artifact_" + body["request_sha256"], "input_digest_mismatch")
    request = _stored_control_json(store, artifacts[request_name], canonical_bytes=False)
    _require(same(request, {"command": driver_argv(plan), "cwd": str(root), "file_bytes": plan["policy"]["scratch_bytes"],
        "ready_path": paths["ready"], "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": _native_environment(plan)}), "original_commission_mismatch")
    meta = body["metadata"]
    _require(type(meta) is dict and meta.get("native_lifecycle_version") == VERSION
        and same(meta.get("policy"), plan["policy"]) and type(metadata) is dict
        and all(same(metadata.get(key), value) for key, value in meta.items()), "original_commission_mismatch")
    enforcement = meta.get("enforcement", {})
    _require(type(enforcement) is dict and enforcement.get("memory") == "systemd_cgroup_v2_memory_max"
        and enforcement.get("swap") == "systemd_memory_swap_max_zero",
        "original_commission_mismatch")
    if body["stage"] == "prepared":
        _require(all(body[name] is None for name in ("started_at", "started_monotonic_ns", "boot_id")),
            "protein_structure_execution_record_invalid")
    else:
        _require(type(body["started_monotonic_ns"]) is int and body["started_monotonic_ns"] >= 0
            and type(body["started_at"]) is str and type(body["boot_id"]) is str,
            "protein_structure_execution_record_invalid")
    if body["stage"] == "released":
        cgroup = meta.get("verified_cgroup", {})
        _require(type(cgroup) is dict and type(cgroup.get("memory_max")) is int
            and cgroup["memory_max"] == plan["policy"]["memory_bytes"]
            and type(cgroup.get("memory_swap_max")) is int and cgroup["memory_swap_max"] == 0, "original_commission_mismatch")
    if returned:
        _require(body["stage"] == "released" and type(metadata.get("native_returncode")) is int
            and metadata["native_returncode"] == execution["returncode"], "protein_structure_execution_record_invalid")
        names = {key: Path(paths[key]).name for key in ("status", "result")}
        _require(set(names.values()) <= artifacts.keys(), "protein_structure_execution_record_invalid")
        status = _stored_control_json(store, artifacts[names["status"]], canonical_bytes=False)
        receipt = _stored_control_json(store, artifacts[names["result"]], canonical_bytes=False)
        _require(type(receipt) is dict and same(metadata.get("service_exit"), status)
            and type(receipt.get("native_returncode")) is int and receipt["native_returncode"] == execution["returncode"]
            and receipt.get("resource_failure") is None and receipt.get("execution_failure") is None,
            "protein_structure_execution_record_invalid")
    return execution, True


def _validate_selected_result_worker(store, prepared, *, plan, binding):
    worker = validate_prepared_protein_structure_worker(store, prepared, plan=plan)
    # The shared retained validator proves its original intent. Bind that
    # original intent also to this action's explicitly configured interpreter
    # and environment, rather than accepting another retained worker's intent.
    intent = _worker_intent(plan, executable=binding["software"]["python_executable"],
        package_root=None, environment=binding["environment"])
    _require(same(_stored_control_json(store, "artifact_" + digest(intent)), intent), "original_commission_mismatch")
    handle_ref = worker["execution"]["handle_artifact_ref"]
    if handle_ref is not None:
        body = _stored_control_json(store, handle_ref, canonical_bytes=False)
        _require(type(body) is dict and type(body.get("request_sha256")) is str, "original_commission_mismatch")
        request = _stored_control_json(store, "artifact_" + body["request_sha256"], canonical_bytes=False)
        _check_worker_handle(body, request, intent)
    return worker


def validate_prepared_protein_structure_work(registry, work, *, authority) -> PreparedProteinWork:
    """Revalidate one live preparation before publication; perform no writes or jobs.

    This is not a saved-return reader. It authenticates all retained capture
    Files, including captured inputs, while never revisiting producer paths or
    resolving operands. Scientific views are rebuilt only from retained native
    and result-worker outputs through the existing qualification helper.
    """
    if type(work) is dict and work.get("version") == SAVED_WORK_VERSION:
        context = _authenticate(registry, work["tool_name"], work["arguments"], work["scope"],
            work["invocation"]["operation_key"], authority)
        catalog = protein_structure_tool_catalog(registry._protein_structure_configuration)
        validate_schema(work["arguments"], catalog[work["tool_name"]]["input_schema"])
        if work["mode"] == "recalculate":
            _require(same(work["binding"], _saved_binding(registry._protein_structure_configuration, work["arguments"])),
                "original_commission_mismatch")
            transform = work["arguments"]["parameters"]["declared_transform"]
            expected_reader = _selected_legacy_parameter_reader(registry._protein_structure_input_authority.get(), transform)
            _require(same(work["admission"].get("parameter_reader"), expected_reader), "original_commission_mismatch")
        return validate_saved_protein_work(registry.store, work, context=context,
            input_authority=registry._protein_structure_input_authority.get())
    selected, plan, control = _selected_work_contract(registry, work, authority)
    execution, plan_available = _validate_retained_protein_execution(registry.store, work["execution"],
        plan=plan, control=control)
    _require(same(work["plan"], plan if plan_available else None), "original_commission_mismatch")
    fresh: PreparedProteinWork = {"version": "ordinary_protein_structure_work_v1", **selected,
        "plan": plan if plan_available else None, "execution": execution, "capture": None, "bundle": None,
        "worker": None, "scientific": None, "qualified_files": {name: None for name in
            ("native_file", "sequence_file", "residue_map_file", "sheet_file", "original_components_file", "components_file")},
        "issues": []}
    execution_issue = _execution_issue(execution)
    if execution_issue is not None:
        fresh["issues"].append(execution_issue)
    if work["capture"] is None:
        _require(work["bundle"] is None and work["worker"] is None, "original_commission_mismatch")
        fresh["issues"].append(issue("capture_incomplete" if plan_available else "native_result_missing",
            stage="capture", field="manifest"))
    else:
        _require(plan_available, "original_commission_mismatch")
        capture = validate_protein_structure_plan_capture(registry.store, work["capture"], plan=plan)
        fresh["capture"] = capture
        fresh["issues"].extend(capture["failures"])
        if capture["bundle_validated"]:
            fresh["bundle"] = validate_protein_structure_bundle(
                _retained_json(registry.store, capture["bundle_file"]), plan=plan)
            fresh["issues"].extend(fresh["bundle"]["failures"])
        _require(same(work["bundle"], fresh["bundle"]), "original_commission_mismatch")
        native_file = _captured(capture, "native_result")
        if native_file is None:
            _require(work["worker"] is None, "original_commission_mismatch")
            fresh["issues"].append(issue("native_result_missing", stage="native", artifact_role="native_result"))
        elif work["worker"] is None:
            fresh["issues"].append(issue("capture_incomplete", stage="capture", field="manifest", artifact_role="native_result"))
        else:
            worker_plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
                "directory": str(Path(plan["identity"]["execution_id"]).parent / "result-worker"),
                "expected_request": selected["arguments"]["request"], "expected_software": selected["binding"]["software"],
                "native_result": {"file_identity": native_file,
                    "path": str(retained_protein_structure_file(registry.store, native_file))}}
            _require(type(work["worker"]) is dict and set(work["worker"]) == {"prepared", "plan", "execution", "result"},
                "original_commission_mismatch")
            fresh["worker"] = _validate_selected_result_worker(registry.store, work["worker"]["prepared"],
                plan=worker_plan, binding=selected["binding"])
            fresh["issues"].extend(fresh["worker"]["prepared"]["issues"])
            if fresh["worker"]["result"] is not None:
                fresh["issues"].extend(fresh["worker"]["result"]["issues"])
            try:
                _qualify_science(registry.store, fresh)
            except (ValueError, OSError) as error:
                fresh["issues"].append(_problem(error))
    fresh["issues"] = list({canonical(value): value for value in fresh["issues"]}.values())
    return _copy(fresh)


def _saved_binding(configuration, arguments):
    ordinal = arguments["binding_ordinal_0based"]
    _require(type(ordinal) is int, "protein_structure_binding_selection_invalid")
    selected = [row for row in configuration["bindings"] if row["operation"] == "compare"
        and row["resource_id"] == arguments["resource_id"] and row["binding_ordinal_0based"] == ordinal]
    _require(len(selected) == 1, "protein_structure_binding_selection_invalid")
    binding = {**deepcopy(selected[0]), "policy": deepcopy(configuration["policy"])}
    _check_saved_binding(binding, arguments)
    return binding


def _check_saved_binding(binding, arguments):
    _require(type(binding) is dict and set(binding) == {"resource_id", "binding_ordinal_0based", "operation",
        "scientific_mode", "software", "environment", "workspace", "policy"}, "original_commission_mismatch")
    validate_protein_structure_bindings([{key: binding[key] for key in ("operation", "scientific_mode", "software")}])
    _require(binding["operation"] == "compare" and binding["resource_id"] == arguments["resource_id"]
        and type(arguments["binding_ordinal_0based"]) is int
        and binding["binding_ordinal_0based"] == arguments["binding_ordinal_0based"]
        and (binding["scientific_mode"] is None or binding["scientific_mode"] == arguments["parameters"]["mode"])
        and same(binding["policy"], POLICY), "original_commission_mismatch")
    _path(binding["workspace"], absolute=True)
    _environment(binding["environment"])


def _saved_worker_plan(store, arguments, invocation, binding):
    descriptor = arguments["saved_sheet"]
    root = Path(binding["workspace"]) / ".episode-operations" / digest({
        "run": invocation["run_id"], "episode": invocation["episode_id"]}) / digest(invocation["operation_key"])
    return {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
        "directory": str(root / "result-worker"), "parameters": deepcopy(arguments["parameters"]),
        "sheet": {"file_identity": deepcopy(descriptor["sheet_file"]),
            "path": str(retained_protein_structure_file(store, descriptor["sheet_file"]))},
        "original_components": {"file_identity": deepcopy(descriptor["original_components_file"]),
            "path": str(retained_protein_structure_file(store, descriptor["original_components_file"]))}}


def _selected_legacy_parameter_reader(authority, transform):
    if (transform is None or transform["origin"] != "received_fitted"
            or transform["received_from"]["saved_sheet"]["version"] != "protein_structure_saved_sheet_v1"):
        return None
    from .execution_episodes import ExecutionEpisodes
    legacy = getattr(authority, "legacy_returns", None)
    owner = getattr(legacy, "owner", None)
    _require(type(owner) is ExecutionEpisodes and legacy is owner.native_protein_structure_returns
        and legacy.results is owner.native_protein_structure_results
        and owner.store is authority.store and owner.run_id == authority.run_id,
        "protein_structure_legacy_parameter_authority_required")
    return dict(version="protein_structure_legacy_parameter_reader_v1", run_id=owner.run_id,
        directory=str(owner.directory))


def _authenticate_saved_parameters(store, context, parameters, authority, *, index, reader):
    transform = parameters["declared_transform"]
    if transform is None or transform["origin"] != "received_fitted":
        _require(reader is None, "original_commission_mismatch")
        return
    from .protein_structure_operands import authenticate_received_structure_transform
    legacy = transform["received_from"]["saved_sheet"]["version"] == "protein_structure_saved_sheet_v1"
    if not legacy:
        _require(reader is None, "original_commission_mismatch")
        authenticate_received_structure_transform(store, context, transform, returns=authority,
            before_decision_index=index)
        return
    from .execution_episodes import ExecutionEpisodes
    from .protein_structure_action_records import ProteinStructureActionRecords
    _require(type(reader) is dict and set(reader) == {"version", "run_id", "directory"}
        and reader["version"] == "protein_structure_legacy_parameter_reader_v1"
        and reader["run_id"] == context.run_id, "original_commission_mismatch")
    retained = ExecutionEpisodes.retained_protein_structure_reader(store,
        run_id=reader["run_id"], directory=reader["directory"])
    records = ProteinStructureActionRecords(store, context.run_id, legacy_returns=retained)
    value = authenticate_received_structure_transform(store, context, transform, returns=records,
        before_decision_index=index)
    if authority.legacy_returns is not None:
        _require(same(reader, _selected_legacy_parameter_reader(authority, transform)), "original_commission_mismatch")
        original = authenticate_received_structure_transform(store, context, transform, returns=authority,
            before_decision_index=index)
        _require(same(value, original), "original_commission_mismatch")


async def _prepare_saved_protein_work(registry, arguments, *, scope, operation_key, context, input_authority):
    _require(input_authority is not None and input_authority.store is registry.store
        and input_authority.run_id == context.run_id, "protein_structure_input_authority_required")
    mode = arguments["mode"]
    _validate_saved_arguments(arguments)
    index = int(operation_key.rsplit(":", 1)[1])
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        request_sha256=digest(plain(context.request)))
    work = dict(version=SAVED_WORK_VERSION, mode=mode, tool_name="compare_protein_structures",
        arguments=deepcopy(arguments), scope=deepcopy(scope), invocation=invocation,
        admission={}, binding=None, worker=None, qualified_files={}, scientific=None, issues=[], redisplay=None)
    if mode == "read_stored":
        original = input_authority.read_stored_result(context, arguments["result_ref"], before_decision_index=index)
        work["admission"] = original.pop("admission")
        work["redisplay"], work["issues"] = original, deepcopy(original["result"]["issues"])
        return work
    inputs = input_authority.saved_action_inputs(context, arguments["saved_sheet"], required_use=(
        "recalculate" if mode == "recalculate" else "select_projection"), before_decision_index=index,
        result_ref=arguments.get("result_ref"))
    work["admission"] = inputs["admission"]
    if mode == "recalculate":
        transform = arguments["parameters"]["declared_transform"]
        reader = _selected_legacy_parameter_reader(input_authority, transform)
        if reader is not None:
            work["admission"]["parameter_reader"] = reader
        _authenticate_saved_parameters(registry.store, context, arguments["parameters"], input_authority,
            index=index, reader=reader)
        binding = work["binding"] = _saved_binding(registry._protein_structure_configuration, arguments)
        plan = _saved_worker_plan(registry.store, arguments, invocation, binding)
        try:
            work["worker"] = await run_cancellable_native(_prepare_result_worker, registry.store.path,
                plan=plan, policy=LocalJobPolicy(**binding["policy"]), software=binding["software"],
                environment=binding["environment"])
        except AcquisitionError as error:
            raise ProteinOperationUnpublished("protein_structure_saved_result_worker_unconfirmed") from error
    return validate_saved_protein_work(registry.store, work, context=context, input_authority=input_authority,
        prepared=True)


def validate_saved_protein_work(store, work, *, context, input_authority, prepared=False):
    """Reconstruct one selected saved action from actual retained authority.

    This performs no fit, parsing, worker dispatch or publication. Original
    descriptor custody and newly selected parameters remain separate records.
    """
    from .protein_structure_calculations import validate_recorded_protein_structure_components
    from .protein_structure_contracts import validate_protein_structure_sheet
    _require(type(work) is dict and set(work) == set(PreparedSavedProteinWork.__annotations__)
        and work["version"] == SAVED_WORK_VERSION and work["mode"] in SAVED_MODES
        and work["tool_name"] == "compare_protein_structures", "protein_structure_work_invalid")
    arguments, mode = _copy(work["arguments"]), work["mode"]
    _validate_saved_arguments(arguments)
    _require(arguments["mode"] == mode and same(work["scope"], plain(context.scope))
        and input_authority is not None and input_authority.store is store
        and input_authority.run_id == context.run_id, "original_commission_mismatch")
    invocation = work["invocation"]
    prefix = context.run_id + ":" + context.episode_id + ":"
    key = invocation.get("operation_key")
    suffix = key[len(prefix):] if type(key) is str and key.startswith(prefix) else ""
    _require(re.fullmatch(r"0|[1-9][0-9]*", suffix) is not None, "original_commission_mismatch")
    index = int(suffix)
    _require(same(invocation, dict(run_id=context.run_id, episode_id=context.episode_id,
        operation_key=key, request_sha256=digest(plain(context.request)))), "original_commission_mismatch")
    action = store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (context.run_id, context.episode_id, index)).fetchone()
    _require(action is not None and same(json.loads(action["action"]), dict(kind="tool",
        tool=work["tool_name"], arguments=arguments)), "original_commission_mismatch")
    fresh = deepcopy(work)
    if mode == "read_stored":
        original = input_authority.read_stored_result(context, arguments["result_ref"], before_decision_index=index)
        _require(same(work["admission"], original.pop("admission")) and work["binding"] is None
            and work["worker"] is None and work["scientific"] is None and work["qualified_files"] == {}
            and same(work["redisplay"], original) and same(work["issues"], original["result"]["issues"]),
            "original_commission_mismatch")
        return fresh
    inputs = input_authority.saved_action_inputs(context, arguments["saved_sheet"], required_use=(
        "recalculate" if mode == "recalculate" else "select_projection"), before_decision_index=index,
        result_ref=arguments.get("result_ref"))
    expected_admission = deepcopy(inputs["admission"])
    if mode == "recalculate" and work["admission"].get("parameter_reader") is not None:
        expected_admission["parameter_reader"] = deepcopy(work["admission"]["parameter_reader"])
    _require(same(work["admission"], expected_admission), "original_commission_mismatch")
    original, basis = inputs["original"], inputs["basis"]
    if mode == "recalculate":
        _authenticate_saved_parameters(store, context, arguments["parameters"], input_authority,
            index=index, reader=work["admission"].get("parameter_reader"))
    files = {name: deepcopy(original[name]) for name in ("native_file", "sequence_file", "residue_map_file",
        "sheet_file", "original_components_file", "components_file")}
    scientific = None
    issues = deepcopy(original["native_issues"])
    if mode == "recalculate":
        _check_saved_binding(work["binding"], arguments)
        plan = _saved_worker_plan(store, arguments, invocation, work["binding"])
        _require(type(work["worker"]) is dict and set(work["worker"]) == {"prepared", "plan", "execution", "result"},
            "original_commission_mismatch")
        worker = _validate_selected_result_worker(store, work["worker"]["prepared"], plan=plan, binding=work["binding"])
        _require(same(worker, work["worker"]), "original_commission_mismatch")
        issues.extend(worker["prepared"]["issues"])
        result = worker["result"]
        files["components_file"] = None
        if result is not None:
            issues.extend(result["issues"])
            if result["sheet_file"] is not None and result["components_file"] is not None:
                _require(same(result["sheet_file"]["file_identity"], files["sheet_file"]), "original_commission_mismatch")
                files["components_file"] = deepcopy(result["components_file"]["file_identity"])
    else:
        _require(work["binding"] is None and work["worker"] is None, "original_commission_mismatch")
        files["components_file"] = deepcopy(basis["components_file"])
        issues.extend(basis.get("operation_issues", []))
        if same(arguments["projections"], [view["selection"] for view in basis["published"]["result"]["views"]]):
            fresh["redisplay"] = deepcopy(basis["published"])
    if files["components_file"] is not None:
        sheet = validate_protein_structure_sheet(_retained_json(store, files["sheet_file"]))
        components = validate_recorded_protein_structure_components(sheet,
            components=_retained_json(store, files["components_file"]))
        _require(same(_retained_json(store, files["original_components_file"]), sheet["native_baseline"]),
            "original_commission_mismatch")
        if mode == "recalculate":
            _require(same(components["parameters"], arguments["parameters"]), "original_commission_mismatch")
        scientific = dict(kind="comparison", sheet=sheet, components=components)
        issues.extend(sheet["parse_issues"])
        issues.extend(sheet["correspondence_issues"])
        issues.extend(components["issues"])
    issues = list({canonical(value): value for value in issues}.values())
    if not prepared:
        _require(same(work["qualified_files"], files) and (work["scientific"] is None or same(work["scientific"], scientific))
            and same(work["issues"], issues) and same(work["redisplay"], fresh["redisplay"]), "original_commission_mismatch")
    fresh.update(qualified_files=files, scientific=scientific, issues=issues)
    return fresh


def _validate_saved_arguments(arguments):
    from .protein_structure_contracts import validate_calculation_parameters, validate_saved_sheet_descriptor_v2
    from .protein_structure_result_views import validate_protein_structure_projection_selection
    mode = arguments.get("mode")
    _require(mode in SAVED_MODES, "invalid_schema")
    validate_schema(arguments, _saved_argument_schemas()[mode])
    if "result_ref" in arguments:
        _require(type(arguments["result_ref"]) is str and re.fullmatch(r"source_[a-f0-9]{24,64}",
            arguments["result_ref"]) is not None, "invalid_schema")
    if mode == "read_stored":
        return
    validate_saved_sheet_descriptor_v2(arguments["saved_sheet"])
    if mode == "recalculate":
        _require(type(arguments["binding_ordinal_0based"]) is int, "protein_structure_binding_selection_invalid")
        validate_calculation_parameters(arguments["parameters"])
    selections = [validate_protein_structure_projection_selection(value) for value in arguments["projections"]]
    _require(len({value["projection_id"] for value in selections}) == len(selections), "duplicate_selection")


__all__ = ["PROTEIN_STRUCTURE_OPERATIONS", "PROTEIN_STRUCTURE_TOOLS", "ProteinOperationUnpublished",
    "PreparedProteinWork", "normalize_protein_structure_configuration", "protein_structure_tool_catalog",
    "prepare_protein_structure_work", "validate_prepared_protein_structure_work", "SAVED_MODES",
    "SAVED_WORK_VERSION", "PreparedSavedProteinWork", "validate_saved_protein_work"]
