"""Read-only original operands for selected protein structure operations.

Received authority belongs to NativeProteinStructureReturns and the original
result host. This adapter checks the exact retained sequence, map, traceback,
sheet and transform relationships. It never acquires, aligns, fits, publishes,
stages, dispatches work or awards credit.
"""
from __future__ import annotations

from copy import deepcopy
import math
import sqlite3
from typing import TYPE_CHECKING, TypedDict, get_args

from jsonschema import Draft202012Validator, validators

from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, RECORD_SCHEMAS
from .episode_receipts import EpisodeReceipts
from .execution_contracts import canonical, digest
from .native_protein_structure_acquisition import (
    decode_protein_structure_json, retained_protein_structure_file,
)
from .native_protein_structure_contracts import (
    CompareRequest, InputFile, required_input_files, validate_input_associations,
    validate_native_protein_structure_result, validate_protein_structure_request,
    validate_protein_structure_requested_job,
)
from .protein_structure_authority import ProteinStructureOperandError
from . import protein_structure_contracts as a
from .protein_structure_calculations import validate_recorded_protein_structure_components
from .protein_structure_result_views import (
    ProteinResultSelector, validate_protein_structure_projection_result,
    validate_protein_structure_projection_rows,
)
from .protein_structure_selection import validate_protein_structure_result_selector
from .tool_grading_artifacts import (
    MEDIA_TYPE as GRADING_MEDIA_TYPE, SCHEMA as GRADING_SCHEMA,
    SCHEMA_V2 as GRADING_SCHEMA_V2, validate_tool_correspondence,
)

if TYPE_CHECKING:
    from .episode_bindings import BindingContext
    from .native_protein_structure_returns import NativeProteinStructureReturns
    from .state import Store


class ResolvedComparisonOperands(TypedDict):
    request: CompareRequest
    input_files: list[InputFile]
    selected_references: list[str]


_SUBJECTS = frozenset({"input", "read_subject", "feature", "product", "reference"})
_FAMILY = "native_protein_structure_bundle_v1"
_CODES = frozenset(get_args(a.IssueCode))
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, v: type(v) is int)
    .redefine("number", lambda _, v: type(v) in (int, float) and math.isfinite(v)))
_RECORD_VALIDATORS = {kind: _STRICT(RECORD_SCHEMAS[kind])
    for kind in ("feature", "product", "reference", "source", "observation")}


def _fail(code, *, stage="authority", field="descriptor", role=None, artifact_role=None):
    raise ProteinStructureOperandError(a.issue(code, stage=stage, field=field,
        role=role, artifact_role=artifact_role))


def _require(condition, code="conflicting_identity", **where):
    if not condition:
        _fail(code, **where)


def _checked(function, *args, stage="authority", field="descriptor", code=None,
             artifact_role=None, **kwargs):
    """Translate only declared data failures; do not hide programming failures."""
    try:
        return function(*args, **kwargs)
    except ProteinStructureOperandError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
        name = code or (str(error) if str(error) in _CODES else "invalid_schema")
        _fail(name, stage=stage, field=field, artifact_role=artifact_role)


def _authority(function, *args, code="original_commission_mismatch", field="receipt", **kwargs):
    # Returns owns its original/frozen proof errors. Preserve its typed errors;
    # deliberately translate a legacy untyped proof error, never its prose.
    try:
        return function(*args, **kwargs)
    except ProteinStructureOperandError:
        raise
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        _fail(code, field=field)


def _binding(store, context, returns):
    _require(returns is not None and getattr(returns, "store", None) is store
        and getattr(returns, "run_id", None) == context.run_id,
        "original_commission_mismatch", field="receipt")
    _authority(returns.authenticate, context, allow_unsaved=True)


def _payload(record):
    return {key: value for key, value in record.items()
        if key not in {"id", "record_type", "origin"}}


def _record(store, reference, kinds, *, field="descriptor"):
    try:
        record = store.get(reference)
    except (ContractError, KeyError, TypeError, ValueError):
        _fail("conflicting_identity", field=field)
    _require(type(record) is dict and record.get("id") == reference
        and record.get("record_type") in kinds, field=field)
    kind = record["record_type"]
    if kind in _RECORD_VALIDATORS:
        # Shape first: missing typed links are malformed, not ordinary leaves.
        _checked(lambda value: _require(_RECORD_VALIDATORS[kind].is_valid(value),
            "invalid_schema", field=field), _payload(record), field=field)
        _checked(immutable_record, record, code="conflicting_identity", field=field)
    return record


def is_protein_structure_sequence_operand(store, reference_ref: str) -> bool:
    """Classify only immutable typed sequence ancestry, without granting use.

    Iterative DFS validates every parent (even after finding protected material).
    Completed DAG nodes are reusable; an active node is a contradictory cycle.
    Input/read_subject leaves retain their ordinary validation at the tool.
    """
    _require(type(reference_ref) is str, "invalid_schema")
    active, completed = set(), {}
    stack = [(reference_ref, False, None)]
    while stack:
        reference, leaving, edges = stack.pop()
        if leaving:
            completed[reference] = any(completed[parent] for parent in edges)
            active.remove(reference)
            continue
        if reference in completed:
            continue
        _require(reference not in active)
        record = _record(store, reference, _SUBJECTS)
        kind = record["record_type"]
        if kind in {"input", "read_subject"}:
            completed[reference] = False
        elif kind == "reference":
            source = _record(store, record["source_ref"], {"source"})
            completed[reference] = (source["provider"] == "episode.execution_result"
                and source["version"] == _FAMILY)
        else:
            edges = ([record["subject_ref"]] if kind == "feature" else record["parent_refs"])
            active.add(reference)
            stack.append((reference, True, edges))
            stack.extend((parent, False, None) for parent in reversed(edges))
    return completed[reference_ref]


def _file(store, identity, *, format=None, role=None):
    identity = _checked(a.validate_file_identity, identity, stage="input",
        field="file_identity", artifact_role=role)
    _require(format is None or identity["format"] == format, "unsupported_format",
        stage="input", field="file_identity", artifact_role=role)
    return _checked(retained_protein_structure_file, store, identity, stage="input",
        field="file_identity", artifact_role=role)


def _bytes(store, identity, *, format=None, role=None):
    path = _file(store, identity, format=format, role=role)
    try:
        raw = path.read_bytes()
    except OSError:
        _fail("retained_artifact_missing", stage="input", field="file_identity", artifact_role=role)
    # Retained lookup checked the file before opening. Recheck these actual read
    # bytes too; a changed file cannot pass through the lookup/read interval.
    import hashlib
    _require(len(raw) == identity["byte_length"] and hashlib.sha256(raw).hexdigest() == identity["sha256"],
        "input_digest_mismatch", stage="input", field="file_identity", artifact_role=role)
    return raw


def _json_file(store, identity, *, format=None, role=None, canonical_bytes=True,
               stage="input", field="file_identity", code=None):
    raw = _bytes(store, identity, format=format, role=role)
    return _checked(decode_protein_structure_json, raw, canonical_bytes=canonical_bytes,
        stage=stage, field=field, code=code, artifact_role=role)


def _source(store, custody):
    source = _record(store, custody["source_ref"], {"source"})
    _require(source["origin"] == "tool" and source["provider"] == "episode.execution_result"
        and source["version"] == _FAMILY and source["artifact_ref"] == custody["bundle_artifact_ref"])
    # The host read view has already proved the exact ordinary publisher payload.
    # Do not reconstruct it from this deliberately smaller scientific view.
    return source


def _sequence_refs(descriptor):
    return [descriptor["reference_ref"], descriptor["sequence_file"]["artifact_ref"],
        descriptor["residue_map_file"]["artifact_ref"], descriptor["structure_file"]["artifact_ref"],
        *_custody_refs(descriptor["custody"])]


def _custody_refs(custody):
    return [custody[key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref")]


def _saved_refs(descriptor):
    return [*_custody_refs(descriptor["custody"]), descriptor["sheet_file"]["artifact_ref"],
        descriptor["original_components_file"]["artifact_ref"]]


def _sequence(store, context, descriptor, *, required_use, returns):
    descriptor = _checked(a.validate_structure_sequence_descriptor, descriptor)
    _require(required_use in descriptor["allowed_uses"], "sequence_not_received")
    original = _authority(returns.authenticate_received_sequence, context, descriptor,
        required_use=required_use, code="sequence_not_received", field="descriptor")
    _source(store, descriptor["custody"])
    _require(a.same(original["custody"], descriptor["custody"]),
        "original_commission_mismatch", field="receipt")
    request = _checked(validate_protein_structure_request, original["request"], field="request")
    _require(request["operation"] == "extract_sequence", "original_commission_mismatch", field="request")
    _require(a.same(request["selection"], descriptor["selection"]),
        "sequence_artifact_mismatch", stage="sequence", field="sequence")
    for field in ("sequence_file", "residue_map_file"):
        _require(a.same(original[field], descriptor[field]),
            "sequence_artifact_mismatch", stage="sequence", field="sequence" if field == "sequence_file" else "residue_map")
    _require(original["native_file"] is not None, "original_commission_mismatch", field="receipt")
    native = _json_file(store, original["native_file"], format="protein_structure_sequence_native_v1", role="native_result")
    native = _checked(validate_native_protein_structure_result, native, stage="sequence", field="sequence")
    _require(a.same(native["request"], request) and a.same(native["producer"], original["software"]),
        "original_commission_mismatch", field="request")
    sequence = native["sequence"]
    _require(a.same(sequence["selection"], descriptor["selection"])
        and sequence["sequence_available"] and sequence["sequence_length"] == descriptor["sequence_length"],
        "sequence_artifact_mismatch", stage="sequence", field="sequence")
    _file(store, descriptor["structure_file"], role="single_structure")
    raw_map = _bytes(store, descriptor["residue_map_file"], format="protein_structure_sequence_v1", role="residue_map")
    _require(raw_map == canonical(sequence).encode("utf-8"), "sequence_artifact_mismatch",
        stage="sequence", field="residue_map")
    raw_sequence = _bytes(store, descriptor["sequence_file"], format="ascii_protein_sequence_v1", role="sequence")
    _require(raw_sequence == sequence["alignment_sequence"].encode("ascii"), "sequence_artifact_mismatch",
        stage="sequence", field="sequence")
    reference = _record(store, descriptor["reference_ref"], {"reference"})
    expected = {"reference_type": "protein", "source_ref": descriptor["custody"]["source_ref"],
        "accession": "structure_sequence_" + digest(sequence), "label": "Structure-derived protein sequence",
        "sequence_ref": descriptor["sequence_file"]["artifact_ref"], "molecule": "protein",
        "length": descriptor["sequence_length"], "term_refs": [], "context_refs": [], "anchor": None}
    _require(reference["origin"] == "tool" and a.same(_payload(reference), expected))
    return deepcopy(sequence)


def authenticate_structure_sequence_reference(store, context, reference_ref, *, returns) -> a.StructureSequenceDescriptor:
    _binding(store, context, returns)
    _require(is_protein_structure_sequence_operand(store, reference_ref), "sequence_not_received")
    # Descriptors identify original reference records. An ancestor's descriptor
    # cannot authorize a product or feature, including an identical full wrapper.
    _require(_record(store, reference_ref, _SUBJECTS)["record_type"] == "reference", "sequence_not_received")
    candidates = _authority(returns.received_sequence_descriptors, context, reference_ref,
        code="sequence_not_received", field="descriptor")
    for candidate in candidates:
        descriptor = _checked(a.validate_structure_sequence_descriptor, candidate)
        _require(descriptor["reference_ref"] == reference_ref)
        if "sequence_align" not in descriptor["allowed_uses"]:
            continue
        _sequence(store, context, descriptor, required_use="sequence_align", returns=returns)
        return deepcopy(descriptor)
    _fail("sequence_not_received")


def authenticate_selected_alignment(store, context, alignment, *, fixed, moving,
                                    orientation, returns) -> a.AlignmentSnapshot:
    _binding(store, context, returns)
    alignment = _checked(a.validate_alignment_descriptor, alignment, stage="correspondence", field="alignment")
    _require(orientation in ("fixed_is_query", "fixed_is_reference"), "invalid_schema",
        stage="correspondence", field="alignment")
    fixed_sequence = _sequence(store, context, fixed, required_use="structure_correspondence", returns=returns)
    moving_sequence = _sequence(store, context, moving, required_use="structure_correspondence", returns=returns)
    query, reference = (fixed, moving) if orientation == "fixed_is_query" else (moving, fixed)
    qseq, rseq = ((fixed_sequence, moving_sequence) if orientation == "fixed_is_query" else (moving_sequence, fixed_sequence))
    mismatch = {"stage": "correspondence", "field": "alignment"}
    _require(alignment["query_reference_ref"] == query["reference_ref"]
        and alignment["reference_reference_ref"] == reference["reference_ref"], "alignment_operand_mismatch", **mismatch)
    _authority(returns.authenticate_received_alignment, context, alignment,
        code="alignment_not_received", field="alignment")
    observation = _record(store, alignment["observation_ref"], {"observation"})
    source = _record(store, alignment["source_ref"], {"source"})
    operands = list(dict.fromkeys([query["reference_ref"], reference["reference_ref"]]))
    _require(observation["origin"] == "tool" and observation["kind"] == "alignment"
        and observation["source_ref"] == source["id"] and source["origin"] == "tool"
        and source["provider"] == "biopython.alignment"
        and source["artifact_ref"] == alignment["native_file"]["artifact_ref"]
        and observation["subject_refs"] == [query["reference_ref"]]
        and observation["source_subject_refs"] == [reference["reference_ref"]]
        and observation["dependencies"] == operands, "alignment_operand_mismatch", **mismatch)
    if "operand_refs" in source:
        _require(source["operand_refs"] == operands, "alignment_operand_mismatch", **mismatch)
    try:
        operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
            (alignment["original_operation_key"],)).fetchone()
    except sqlite3.Error:
        operation = None
    _require(operation is not None, "alignment_operand_mismatch", **mismatch)
    arguments = _checked(decode_protein_structure_json, operation["arguments"].encode("utf-8"),
        code="alignment_operand_mismatch", **mismatch)
    expected_args = {"query_ref": query["reference_ref"], "reference_ref": reference["reference_ref"],
        "molecule": "protein", "mode": alignment["mode"]}
    outcome = _checked(decode_protein_structure_json, operation["result"].encode("utf-8"),
        code="alignment_operand_mismatch", **mismatch)
    _require(operation["name"] == "sequence.align" and a.same(arguments, expected_args)
        and outcome.get("operation_ref") == operation["id"] and outcome.get("status") in ("completed", "partial")
        and all(ref in outcome.get("record_refs", []) for ref in (source["id"], observation["id"])),
        "alignment_operand_mismatch", **mismatch)
    native = _json_file(store, alignment["native_file"], format="biopython_pairwise_json",
        role="alignment_native", canonical_bytes=False, stage="correspondence", field="traceback", code="invalid_traceback")
    candidates = []
    for ref in source.get("auxiliary_artifact_refs", []):
        try:
            metadata = store.get(ref)
        except (ValueError, KeyError):
            _fail("conflicting_identity", field="file_identity")
        if metadata.get("media_type") == GRADING_MEDIA_TYPE:
            candidates.append(ref)
    _require(candidates == [alignment["grading_file"]["artifact_ref"]], "alignment_operand_mismatch", **mismatch)
    grading_format = alignment["grading_file"]["format"]
    _require(grading_format in {GRADING_SCHEMA, GRADING_SCHEMA_V2}, "unsupported_format", **mismatch)
    grading = _json_file(store, alignment["grading_file"], format=grading_format,
        role="alignment_grading", canonical_bytes=False, stage="correspondence", field="traceback", code="invalid_traceback")
    version = grading.get("schema") if type(grading) is dict else None
    fields = {"schema", "provider", "native_artifact_ref", "grading"}
    if version == GRADING_SCHEMA_V2:
        fields.add("correspondence")
    _require(type(grading) is dict and set(grading) == fields
        and version in {GRADING_SCHEMA, GRADING_SCHEMA_V2},
        "alignment_operand_mismatch" if grading_format == GRADING_SCHEMA else "invalid_traceback",
        stage="correspondence", field="alignment" if grading_format == GRADING_SCHEMA else "traceback")
    _require(version == grading_format and grading["provider"] == source["provider"]
        and grading["native_artifact_ref"] == source["artifact_ref"], "alignment_operand_mismatch", **mismatch)
    _require(type(grading["grading"]) is dict and set(grading["grading"]) == {"sheet", "scores"}
        and type(grading["grading"]["scores"]) is dict
        and grading["grading"]["scores"].get("schema") == "biopython_pairwise_scores_v1",
        "invalid_traceback", stage="correspondence", field="traceback")
    if version == GRADING_SCHEMA_V2:
        _checked(validate_tool_correspondence, grading["grading"], grading["correspondence"],
            admission=False, stage="correspondence", field="traceback", code="invalid_traceback")
    snapshot = _checked(a.validate_alignment_snapshot, {"descriptor": alignment,
        "native_result": native, "pairwise_sheet": grading["grading"]["sheet"]},
        stage="correspondence", field="traceback", code="invalid_traceback")
    _require(native["query_length"] == query["sequence_length"]
        and native["reference_length"] == reference["sequence_length"]
        and native["mode"] == alignment["mode"] and source["version"] == native["biopython_version"],
        "alignment_operand_mismatch", **mismatch)
    for row in snapshot["pairwise_sheet"]["residue_correspondence"]:
        for side, sequence in (("query", qseq), ("reference", rseq)):
            position = row[side + "_position"]
            _require(position is None or (position < sequence["sequence_length"]
                and row[side + "_symbol"] == sequence["alignment_sequence"][position]),
                "invalid_traceback", stage="correspondence", field="traceback")
    return snapshot


def _known(store, context):
    """The existing receipt-prefix query, read without constructing a writer."""
    lineage, seen, current, through = [], set(), context.episode_id, None
    try:
        while current is not None:
            _require(current not in seen, "original_commission_mismatch", field="receipt")
            seen.add(current)
            lineage.append({"episode_id": current, "through": through})
            manifest = EpisodeReceipts.read_manifest(store.db, context.run_id, current)
            current, through = manifest["parent_episode_id"], manifest["through_receipt_index"]
        sql = """SELECT DISTINCT receipts.record_ref FROM runtime_record_receipts receipts
            JOIN json_each(?) ancestor ON receipts.episode_id=json_extract(ancestor.value,'$.episode_id')
            WHERE receipts.run_id=? AND (json_extract(ancestor.value,'$.through') IS NULL
                OR receipts.receipt_index<=json_extract(ancestor.value,'$.through'))"""
        params = [canonical(lineage), context.run_id]
        if context.role in {"launch", "launch_local", "launch_hpc", "launch_api", "results"}:
            sql += " AND (receipts.episode_id<>? OR receipts.receipt_kind='initial')"
            params.append(context.episode_id)
        return {row[0] for row in store.db.execute(sql, params)}
    except (ValueError, KeyError, sqlite3.Error) as error:
        if isinstance(error, ProteinStructureOperandError):
            raise
        _fail("original_commission_mismatch", field="receipt")


def _received_reference(store, context, reference, *, returns, known):
    _require(reference in known, "original_commission_mismatch", field="receipt")
    # Specialized denial runs before ordinary receipt visibility. Old recursive
    # source expansion cannot turn hidden protein bytes into an input grant.
    for port in (returns.resolve_received, returns.retained_reference_access):
        decision = _authority(port, context, reference, None)
        _require(decision is None or type(decision) is bool, "original_commission_mismatch", field="receipt")
        if decision is not None:
            _require(decision, "original_commission_mismatch", field="receipt")
            return


def _resolve_request(store, context, request, *, returns):
    request = _checked(validate_protein_structure_request, request, field="request")
    known = _known(store, context)
    authorized, references = set(), []
    if request["operation"] == "compare":
        corr = request["correspondence"]
        if corr["kind"] == "retained_alignment":
            authenticate_selected_alignment(store, context, corr["alignment"],
                fixed=corr["fixed_sequence_descriptor"], moving=corr["moving_sequence_descriptor"],
                orientation=corr["orientation"], returns=returns)
            for side in ("fixed", "moving"):
                descriptor = corr[side + "_sequence_descriptor"]
                selected = _sequence_refs(descriptor)
                references.extend(selected)
                authorized.update(selected)
            alignment = corr["alignment"]
            selected = [alignment["observation_ref"], alignment["source_ref"],
                alignment["native_file"]["artifact_ref"], alignment["grading_file"]["artifact_ref"]]
            references.extend(selected)
            authorized.update(selected)
        transform = request["parameters"]["declared_transform"]
        if transform is not None and transform["origin"] == "received_fitted":
            authenticate_received_structure_transform(store, context, transform, returns=returns)
            selected = _transform_refs(transform)
            references.extend(selected)
            authorized.update(selected)
    files = []
    for i, (role, identity) in enumerate(required_input_files(request)):
        reference = identity["artifact_ref"]
        # Metadata must be an explicit received file even when its identity
        # happens to be another authorized operand or source auxiliary.
        if reference not in authorized or role == "supplied_metadata":
            _received_reference(store, context, reference, returns=returns, known=known)
        path = _file(store, identity, role=role)
        files.append({"input_id": "input_" + str(i), "role": role, "file_identity": deepcopy(identity),
            "path": str(path), "staged_relative_path": "inputs/input_" + str(i)})
    _checked(validate_input_associations, request, files, field="request")
    return request, files, list(dict.fromkeys([f["file_identity"]["artifact_ref"] for f in files] + references))


def resolve_comparison_operands(store, context, request, *, returns) -> ResolvedComparisonOperands:
    _binding(store, context, returns)
    request = _checked(validate_protein_structure_request, request, field="request")
    _require(request["operation"] == "compare", "invalid_schema", field="request")
    request, files, references = _resolve_request(store, context, request, returns=returns)
    return {"request": request, "input_files": files, "selected_references": references}


def validate_protein_structure_job_inputs(store, context, assignment: dict, *, returns) -> list[str]:
    if not (type(assignment) is dict and type(assignment.get("requested_job")) is dict
            and "native_protein_structure" in assignment["requested_job"]):
        return []
    _binding(store, context, returns)
    requested = _checked(validate_protein_structure_requested_job, assignment["requested_job"], field="request")
    job = requested["native_protein_structure"]
    _, files, references = _resolve_request(store, context, job["request"], returns=returns)
    expected = {(row["role"], canonical(row["file_identity"])): row for row in files}
    # C validates ids/staged paths and the role/file multiset. Preserve selected
    # order and insist that every source path is this exact retained Store path.
    for row in job["inputs"]:
        match = expected[(row["role"], canonical(row["file_identity"]))]
        _require(row["path"] == match["path"], "invalid_output_path", stage="input",
            field="file_identity", artifact_role=row["role"])
    return references


def _saved_sheet(store, context, descriptor, *, returns):
    descriptor = _checked(a.validate_saved_sheet_descriptor, descriptor)
    # This common validator proves receipt of the descriptor, not selection of
    # a new operation. The caller enforces its particular use separately.
    original = _authority(returns.authenticate_received_saved_sheet, context, descriptor,
        required_use=descriptor["allowed_uses"][0], code="saved_sheet_not_received", field="descriptor")
    _source(store, descriptor["custody"])
    _require(a.same(original["custody"], descriptor["custody"])
        and a.same(original["sheet_file"], descriptor["sheet_file"])
        and a.same(original["original_components_file"], descriptor["original_components_file"]),
        "original_commission_mismatch", field="receipt")
    request = _checked(validate_protein_structure_request, original["request"], field="request")
    _require(request["operation"] == "compare", "original_commission_mismatch", field="request")
    sheet = _checked(a.validate_protein_structure_sheet,
        _json_file(store, descriptor["sheet_file"], format="protein_structure_comparison_sheet_v1"), field="request")
    components = _json_file(store, descriptor["original_components_file"], format="protein_structure_components_v1")
    _require(sheet["native_baseline"] is not None and a.same(components, sheet["native_baseline"])
        and a.same(components.get("parameters"), sheet["native_request"])
        and descriptor["original_mode"] == sheet["scientific_mode"]
        and a.same(sheet["native_request"], request["parameters"])
        and a.same(sheet["input_identities"]["correspondence"], request["correspondence"])
        and a.same(sheet["input_identities"]["metadata_artifacts"], request["supplied_metadata_files"]),
        "original_commission_mismatch", field="request")
    for side in ("fixed", "moving"):
        _require(a.same(sheet["sequences"][side]["selection"], request[side + "_selection"]),
            "original_commission_mismatch", field="request")
    _checked(validate_recorded_protein_structure_components, sheet, components=components, field="request")
    return sheet, original


def validate_saved_structure_sheet_operand(store, context, descriptor, *, returns) -> a.ProteinStructureSheet:
    _binding(store, context, returns)
    return _saved_sheet(store, context, descriptor, returns=returns)[0]


def _transform_refs(transform):
    received = transform["received_from"]
    return [*_saved_refs(received["saved_sheet"]), received["components_file"]["artifact_ref"],
        *_custody_refs(received["calculation_custody"])]


def authenticate_received_structure_transform(store, context, transform: a.DeclaredTransform, *, returns) -> a.ProteinStructureComponents:
    _binding(store, context, returns)
    transform = _checked(a.validate_declared_transform_record, transform, field="rotation")
    _require(transform["origin"] == "received_fitted" and transform["received_from"] is not None,
        "invalid_transform", field="rotation")
    received = transform["received_from"]
    descriptor = received["saved_sheet"]
    _authority(returns.authenticate_received_saved_sheet, context, descriptor,
        required_use="use_transform", code="saved_sheet_not_received", field="descriptor")
    sheet, original = _saved_sheet(store, context, descriptor, returns=returns)
    projections = _authority(returns.received_transform_projections, context, transform,
        code="invalid_transform", field="rotation")
    _require(bool(projections), "invalid_transform", field="rotation")
    host = returns.owner.native_protein_structure_results
    calculation = _authority(host.read_result_authority, received["calculation_custody"], scope=plain(context.scope))
    _source(store, received["calculation_custody"])
    _require(a.same(calculation["custody"], received["calculation_custody"])
        and a.same(calculation["sheet_file"], descriptor["sheet_file"])
        and a.same(calculation["original_components_file"], descriptor["original_components_file"])
        and a.same(calculation["request"], original["request"])
        and a.same(calculation["software"], original["software"])
        and a.same(calculation["components_file"], received["components_file"]),
        "invalid_transform", field="rotation")
    components = _json_file(store, received["components_file"], format="protein_structure_components_v1",
        role="received_transform_components")
    components = _checked(validate_recorded_protein_structure_components, sheet, components=components, field="rotation")
    selected_parameters = calculation["selector"]["parameters"]
    if selected_parameters is None:
        selected_parameters = calculation["request"]["parameters"]
    _require(components["calculation_id"] == received["calculation_id"]
        and a.same(components["parameters"], selected_parameters)
        and components["transform"]["state"] == "identifiable_fit", "invalid_transform", field="rotation")
    for side in ("fixed", "moving"):
        _require(a.same(transform[side + "_selection"], sheet["sequences"][side]["selection"]),
            "invalid_transform", field="rotation")
    for field, declared in (("rotation", "rotation"), ("translation", "translation_A")):
        cell = components["transform"][field]
        _require(cell["state"] == "present" and a.same(cell["value"], transform[declared]),
            "invalid_transform", field=field)
    for value in projections:
        projection = _checked(validate_protein_structure_projection_result, value, field="rotation")
        _require(any(a.same(projection, row) for row in calculation["facts"]["execution_protein_structure_projections"]),
            "original_commission_mismatch", field="receipt")
        identity = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"], "components_file": received["components_file"]}
        if (projection["family"] != "transform" or not a.same(projection["calculation"], identity)
                or not a.same(projection["custody"], received["calculation_custody"])):
            continue
        delivery = projection["delivery"]
        if delivery["kind"] == "values":
            rows = delivery["rows"]
        else:
            table = _json_file(store, delivery["table_file"], format="protein_structure_projection_table_v1")
            _require(type(table) is dict and set(table) == {"version", "rows"}
                and table["version"] == "protein_structure_projection_table_v1", "invalid_transform", field="rotation")
            rows = table["rows"]
            envelope = {key: deepcopy(projection[key]) for key in (
                "projection_id", "family", "selection", "coordinate_set", "requested_count", "matched_count",
                "returned_count", "omitted_count", "state", "issues", "qualifications")}
            envelope.update(version="protein_structure_projection_rows_v1", rows=rows,
                calculation_id=components["calculation_id"])
            _checked(validate_protein_structure_projection_rows, envelope, field="rotation", code="invalid_transform")
        for row in rows:
            if row["identity"]["kind"] != "transform":
                continue
            fields = {cell["field"]: cell["value"] for cell in row["values"]}
            if not {"rotation", "translation"} <= fields.keys():
                continue
            for field in ("rotation", "translation"):
                _require(a.same(fields[field], components["transform"][field]), "invalid_transform", field=field)
            return deepcopy(components)
    _fail("invalid_transform", field="rotation")


def validate_protein_structure_selected_inputs(store, context, selector: ProteinResultSelector, *, handoff_ref: str, returns) -> list[str]:
    _binding(store, context, returns)
    selector = _checked(validate_protein_structure_result_selector, selector, field="request")
    if context.role == "results":
        assignment = plain(context.assignment)
        _require(assignment.get("version") == "execution_results_assignment_v1"
            and assignment.get("handoff_ref") == handoff_ref and a.same(assignment.get("selector"), selector),
            "original_commission_mismatch", field="request")
    _received_reference(store, context, handoff_ref, returns=returns, known=_known(store, context))
    _record(store, handoff_ref, {"source"}, field="receipt")
    if selector["acquisition"] == "complete_bound_bundle":
        # The result host owns the original qualified target/request. This
        # selection adds no saved-input or source-auxiliary grant.
        return [handoff_ref]
    descriptor = selector["saved_sheet"]
    _require(descriptor["custody"]["handoff_ref"] == handoff_ref,
        "original_commission_mismatch", field="request")
    _authority(returns.authenticate_received_saved_sheet, context, descriptor,
        required_use="recalculate", code="saved_sheet_not_received", field="descriptor")
    _, original = _saved_sheet(store, context, descriptor, returns=returns)
    _checked(validate_protein_structure_result_selector, selector, request=original["request"], field="request")
    references = _saved_refs(descriptor)
    transform = selector["parameters"]["declared_transform"]
    if transform is not None and transform["origin"] == "received_fitted":
        authenticate_received_structure_transform(store, context, transform, returns=returns)
        references.extend(_transform_refs(transform))
    return list(dict.fromkeys(references))


__all__ = ["ResolvedComparisonOperands", "ProteinStructureOperandError",
    "is_protein_structure_sequence_operand", "authenticate_structure_sequence_reference",
    "authenticate_selected_alignment", "resolve_comparison_operands",
    "validate_saved_structure_sheet_operand", "authenticate_received_structure_transform",
    "validate_protein_structure_job_inputs", "validate_protein_structure_selected_inputs"]
