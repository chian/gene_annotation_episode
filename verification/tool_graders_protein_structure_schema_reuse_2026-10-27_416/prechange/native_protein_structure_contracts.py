"""Closed local protein requests and immutable execution envelopes (380/003).

No acquisition, source authorization, alignment or numerical calculation lives
here. Scientific record definitions and structural validation remain in A.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
from pathlib import PurePosixPath
from typing import Literal, TypeAlias, TypedDict, get_args

from jsonschema import Draft202012Validator, validators

from .execution_contracts import canonical, digest, obj
from . import protein_structure_contracts as science
from .protein_structure_contracts import (
    FileIdentity, InventorySelection, StructureSelection, CorrespondenceInput,
    CalculationParameters, ParsedStructure, StructureInventory, StructureSequence,
    StructureMetadata, ProteinStructureSheet, State, StructuredIssue, InputRole,
    ManifestRole, ScientificMode,
)

Environment: TypeAlias = dict[str, str]
Operation: TypeAlias = Literal["inspect", "extract_sequence", "compare"]


class InspectRequest(TypedDict):
    version: Literal["protein_structure_inspect_request_v1"]
    operation: Literal["inspect"]
    structure_file: FileIdentity
    inventory: InventorySelection


class ExtractRequest(TypedDict):
    version: Literal["protein_structure_extract_request_v1"]
    operation: Literal["extract_sequence"]
    selection: StructureSelection
    supplied_metadata_files: list[FileIdentity]


class CompareRequest(TypedDict):
    version: Literal["protein_structure_compare_request_v1"]
    operation: Literal["compare"]
    fixed_selection: StructureSelection
    moving_selection: StructureSelection
    correspondence: CorrespondenceInput
    parameters: CalculationParameters
    supplied_metadata_files: list[FileIdentity]


ScientificRequest: TypeAlias = InspectRequest | ExtractRequest | CompareRequest


class ImplementationFile(TypedDict):
    module: str
    sha256: str


class Software(TypedDict):
    python_executable: str
    python_sha256: str
    python_version: str
    driver_module: Literal["gene_annotation_episode.native_protein_structure_driver"]
    worker_module: Literal["gene_annotation_episode.native_protein_structure_worker"]
    implementation_files: list[ImplementationFile]
    numpy_version: str
    biopython_version: str
    implementation: Literal["gene_annotation_episode_corrected_protein_structure_v1"]
    algorithm: Literal["unweighted_proper_rigid_ca_svd_v1"]


class InputFile(TypedDict):
    input_id: str
    role: InputRole
    file_identity: FileIdentity
    path: str
    staged_relative_path: str


class OutputFile(TypedDict):
    role: Literal["native_result", "sequence", "residue_map", "stdout", "stderr"]
    relative_path: str
    format: Literal["protein_structure_native_v1", "protein_structure_inventory_native_v1",
                    "protein_structure_sequence_native_v1", "ascii_protein_sequence_v1",
                    "protein_structure_sequence_v1", "text"]


class NativeProteinJob(TypedDict):
    version: Literal["native_protein_structure_job_v1"]
    program: Literal["protein_structure_python"]
    request: ScientificRequest
    software: Software
    inputs: list[InputFile]
    outputs: list[OutputFile]
    environment: Environment


class RequestedProteinJob(TypedDict):
    argv: list[str]
    environment: Environment
    native_protein_structure: NativeProteinJob


class NativeProteinBinding(TypedDict):
    operation: Operation
    scientific_mode: ScientificMode | None
    software: Software


class AttemptIdentity(TypedDict):
    run_id: str
    episode_id: str
    resource_id: str
    execution_id: str
    attempt_id: str
    operation_key: str
    requested_job_sha256: str


class ProteinPolicy(TypedDict):
    memory_bytes: Literal[21474836480]
    scratch_bytes: Literal[4294967296]
    wall_seconds: None


class NativeProteinRunPlan(TypedDict):
    version: Literal["native_protein_structure_run_plan_v1"]
    identity: AttemptIdentity
    requested_job: RequestedProteinJob
    attempt_directory: str
    policy: ProteinPolicy


class WorkerFile(TypedDict):
    input_id: str
    role: InputRole
    file_identity: FileIdentity
    path: str


class WorkerInput(TypedDict):
    version: Literal["protein_structure_worker_input_v1"]
    request: ScientificRequest
    software: Software
    files: list[WorkerFile]


class SuppliedBytes(TypedDict):
    input_id: str
    role: InputRole
    file_identity: FileIdentity
    data: bytes


class InspectionNative(TypedDict):
    version: Literal["protein_structure_inventory_native_v1"]
    producer: Software
    request: InspectRequest
    parsed: ParsedStructure
    inventory: StructureInventory
    state: State
    issues: list[StructuredIssue]


class ExtractionNative(TypedDict):
    version: Literal["protein_structure_sequence_native_v1"]
    producer: Software
    request: ExtractRequest
    parsed: ParsedStructure
    sequence: StructureSequence
    metadata: StructureMetadata
    state: State
    issues: list[StructuredIssue]


class ComparisonNative(TypedDict):
    version: Literal["protein_structure_native_v1"]
    producer: Software
    request: CompareRequest
    sheet: ProteinStructureSheet | None
    state: State
    issues: list[StructuredIssue]


NativeProteinResult: TypeAlias = InspectionNative | ExtractionNative | ComparisonNative


class ManifestFile(TypedDict):
    kind: Literal["input", "control", "output"]
    role: ManifestRole
    input_id: str | None
    format: str
    relative_path: str
    state: Literal["present", "absent"]
    sha256: str | None
    byte_length: int | None


class MeasuredDuration(TypedDict):
    seconds: float | None
    kind: Literal["worker_wall", "driver_wall", "unmeasured"]
    source: Literal["monotonic_clock", "none"]


class NativeProteinBundle(TypedDict):
    version: Literal["native_protein_structure_bundle_v1"]
    identity: AttemptIdentity
    requested_job: RequestedProteinJob
    software: Software
    driver_argv: list[str]
    worker_argv: list[str] | None
    realized_environment: Environment
    files: list[ManifestFile]
    returncode: int | None
    native_status: Literal["complete", "partial", "failed"]
    started_at: str
    finished_at: str
    measured_duration: MeasuredDuration
    failures: list[StructuredIssue]
    sealed: Literal[True]


class CompiledJob(TypedDict):
    argv: list[str]
    environment: Environment
    outputs: list[OutputFile]


class ProteinToolInformation(TypedDict):
    name: str
    description: str
    resources: Literal["local"]
    instructions: str


class ProteinResourceToolContract(ProteinToolInformation):
    input_schema: dict
    invocation_route: dict


DRIVER_MODULE = "gene_annotation_episode.native_protein_structure_driver"
WORKER_MODULE = "gene_annotation_episode.native_protein_structure_worker"
RUN_PLAN_FILENAME = "protein-structure-plan.json"
ATTEMPT_DIRECTORY_NAME = "protein-structure-attempt"
BUNDLE_FILENAME = "bundle.json"
WORKER_INPUT_FILENAME = "worker-input.json"
OWNER_FILENAME = ".native-protein-structure-owner.json"
STARTED_FILENAME = ".native-protein-structure-started.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
NATIVE_FORMATS = {"inspect": "protein_structure_inventory_native_v1",
    "extract_sequence": "protein_structure_sequence_native_v1", "compare": "protein_structure_native_v1"}

_TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
_NULL = {"type": "null"}
_COUNT = {"type": "integer", "minimum": 0}
_ENV = {"type": "object", "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
        "additionalProperties": {"type": "string", "pattern": "^[^\\u0000]*$"}}


def _ref(name):
    return {"$ref": "#/$defs/" + name}


def _array(item, **kwargs):
    return {"type": "array", "items": item, **kwargs}


def _nullable(item):
    return {"anyOf": [item, _NULL]}


def _definitions():
    definitions = science.protein_structure_schema_definitions()
    own = {
        "InspectRequest": obj({"version": {"const": "protein_structure_inspect_request_v1"},
            "operation": {"const": "inspect"}, "structure_file": _ref("FileIdentity"), "inventory": _ref("InventorySelection")}),
        "ExtractRequest": obj({"version": {"const": "protein_structure_extract_request_v1"},
            "operation": {"const": "extract_sequence"}, "selection": _ref("StructureSelection"),
            "supplied_metadata_files": _array(_ref("FileIdentity"))}),
        "CompareRequest": obj({"version": {"const": "protein_structure_compare_request_v1"}, "operation": {"const": "compare"},
            "fixed_selection": _ref("StructureSelection"), "moving_selection": _ref("StructureSelection"),
            "correspondence": _ref("CorrespondenceInput"), "parameters": _ref("CalculationParameters"),
            "supplied_metadata_files": _array(_ref("FileIdentity"))}),
        "Software": obj({"python_executable": _TEXT, "python_sha256": _SHA, "python_version": _TEXT,
            "driver_module": {"const": DRIVER_MODULE}, "worker_module": {"const": WORKER_MODULE},
            "implementation_files": _array(obj({"module": _TEXT, "sha256": _SHA}), minItems=1),
            "numpy_version": _TEXT, "biopython_version": _TEXT,
            "implementation": {"const": "gene_annotation_episode_corrected_protein_structure_v1"},
            "algorithm": {"const": "unweighted_proper_rigid_ca_svd_v1"}}),
        "InputFile": obj({"input_id": _TEXT, "role": _ref("InputRole"), "file_identity": _ref("FileIdentity"),
            "path": _TEXT, "staged_relative_path": _TEXT}),
        "OutputFile": obj({"role": {"enum": ["native_result", "sequence", "residue_map", "stdout", "stderr"]},
            "relative_path": _TEXT, "format": {"enum": [*NATIVE_FORMATS.values(), "ascii_protein_sequence_v1", "protein_structure_sequence_v1", "text"]}}),
        "AttemptIdentity": obj({**{name: _TEXT for name in ("run_id", "episode_id", "resource_id", "execution_id", "operation_key")},
            "attempt_id": _SHA, "requested_job_sha256": _SHA}),
        "WorkerFile": obj({"input_id": _TEXT, "role": _ref("InputRole"), "file_identity": _ref("FileIdentity"), "path": _TEXT}),
        "ManifestFile": obj({"kind": {"enum": ["input", "control", "output"]}, "role": _ref("ManifestRole"),
            "input_id": _nullable(_TEXT), "format": _TEXT, "relative_path": _TEXT,
            "state": {"enum": ["present", "absent"]}, "sha256": _nullable(_SHA), "byte_length": _nullable(_COUNT)}),
    }
    own["ScientificRequest"] = {"oneOf": [_ref(name) for name in ("InspectRequest", "ExtractRequest", "CompareRequest")]}
    own["NativeProteinJob"] = obj({"version": {"const": "native_protein_structure_job_v1"}, "program": {"const": "protein_structure_python"},
        "request": _ref("ScientificRequest"), "software": _ref("Software"), "inputs": _array(_ref("InputFile"), minItems=1),
        "outputs": _array(_ref("OutputFile"), minItems=3), "environment": _ENV})
    own["RequestedProteinJob"] = obj({"argv": _array(_TEXT, minItems=1), "environment": _ENV, "native_protein_structure": _ref("NativeProteinJob")})
    own["NativeProteinBinding"] = obj({"operation": {"enum": list(NATIVE_FORMATS)}, "scientific_mode": _nullable(_ref("ScientificMode")), "software": _ref("Software")})
    own["NativeProteinRunPlan"] = obj({"version": {"const": "native_protein_structure_run_plan_v1"},
        "identity": _ref("AttemptIdentity"), "requested_job": _ref("RequestedProteinJob"), "attempt_directory": _TEXT,
        "policy": obj({k: {"const": v} for k, v in POLICY.items()})})
    own["WorkerInput"] = obj({"version": {"const": "protein_structure_worker_input_v1"}, "request": _ref("ScientificRequest"),
        "software": _ref("Software"), "files": _array(_ref("WorkerFile"), minItems=1)})
    shared = {"producer": _ref("Software"), "state": _ref("State"), "issues": _array(_ref("StructuredIssue"))}
    own["InspectionNative"] = obj({**shared, "version": {"const": NATIVE_FORMATS["inspect"]}, "request": _ref("InspectRequest"),
        "parsed": _ref("ParsedStructure"), "inventory": _ref("StructureInventory")})
    own["ExtractionNative"] = obj({**shared, "version": {"const": NATIVE_FORMATS["extract_sequence"]}, "request": _ref("ExtractRequest"),
        "parsed": _ref("ParsedStructure"), "sequence": _ref("StructureSequence"), "metadata": _ref("StructureMetadata")})
    own["ComparisonNative"] = obj({**shared, "version": {"const": NATIVE_FORMATS["compare"]}, "request": _ref("CompareRequest"),
        "sheet": _nullable(_ref("ProteinStructureSheet"))})
    own["NativeProteinResult"] = {"oneOf": [_ref(name) for name in ("InspectionNative", "ExtractionNative", "ComparisonNative")]}
    own["NativeProteinBundle"] = obj({"version": {"const": "native_protein_structure_bundle_v1"}, "identity": _ref("AttemptIdentity"),
        "requested_job": _ref("RequestedProteinJob"), "software": _ref("Software"), "driver_argv": _array(_TEXT, minItems=1),
        "worker_argv": _nullable(_array(_TEXT, minItems=1)), "realized_environment": _ENV, "files": _array(_ref("ManifestFile")),
        "returncode": _nullable({"type": "integer"}), "native_status": {"enum": ["complete", "partial", "failed"]},
        "started_at": _TEXT, "finished_at": _TEXT,
        "measured_duration": obj({"seconds": _nullable({"type": "number", "minimum": 0}),
            "kind": {"enum": ["worker_wall", "driver_wall", "unmeasured"]}, "source": {"enum": ["monotonic_clock", "none"]}}),
        "failures": _array(_ref("StructuredIssue")), "sealed": {"const": True}})
    if set(own) & set(definitions):
        raise RuntimeError("protein_structure_definition_owner_conflict")
    return {**definitions, **own}


def protein_structure_execution_schema(type_name: str, *, bindings=None) -> dict:
    """A self-contained local schema resource, safe inside larger alternatives."""
    definitions = _definitions()
    _require(type_name in definitions)
    root = _ref(type_name)
    if bindings is not None:
        _require(type_name == "RequestedProteinJob")
        alternatives = []
        for binding in validate_protein_structure_bindings(bindings):
            request = {"properties": {"operation": {"const": binding["operation"]}}}
            if binding["scientific_mode"] is not None:
                request["properties"]["parameters"] = {"properties": {"mode": {"const": binding["scientific_mode"]}}}
            alternatives.append({"allOf": [_ref(type_name), {"properties": {"native_protein_structure": {
                "properties": {"software": {"const": binding["software"]}, "request": request}}}}]})
        root = {"oneOf": alternatives}
    # jsonschema's oneOf exhaustiveness check evolves directly into later
    # alternatives instead of descending into their resource. An explicit
    # applicator boundary makes it enter this inner, content-addressed resource
    # even on that branch. Both complete resources keep A's definitions intact;
    # no parent definitions or external registry are required.
    # The inner resource inherits the public document's dialect. Repeating
    # $schema there would make jsonschema.evolve replace a caller's strict
    # integer/finite-number validator with the ordinary dialect validator.
    resource = {"$defs": definitions, **root}
    resource["$id"] = "urn:gene-annotation:protein-structure:schema:" + digest(resource)
    document = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": deepcopy(definitions), "allOf": [resource]}
    document["$id"] = "urn:gene-annotation:protein-structure:schema:" + digest(document)
    return document


_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, v: type(v) is int)
    .redefine("number", lambda _, v: type(v) in (int, float) and math.isfinite(v)))


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


def _checked(value, type_name):
    # Validate original Python types before detaching; canonicalization must not
    # silently turn tuples or integer-like floating values into declared types.
    def plain(v):
        _require(type(v) in (dict, list, str, int, float, bool, type(None)))
        if type(v) is dict:
            _require(all(type(k) is str and "\0" not in k for k in v))
            for x in v.values():
                plain(x)
        elif type(v) is list:
            for x in v:
                plain(x)
        elif type(v) is str:
            _require("\0" not in v)
        elif type(v) is float:
            _require(math.isfinite(v))
    plain(value)
    _require(_STRICT(protein_structure_execution_schema(type_name)).is_valid(value))
    return deepcopy(value)


def _path(value, *, absolute):
    _require(type(value) is str and bool(value) and not any(c in value for c in "\0\n\r\\"), "invalid_output_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts and value not in (".", "/"), "invalid_output_path")
    return path


def _overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def _unique(values, code="duplicate_selection"):
    _require(len({canonical(v) for v in values}) == len(values), code)


def validate_protein_structure_software(value: Software) -> Software:
    value = _checked(value, "Software")
    _path(value["python_executable"], absolute=True)
    _unique([row["module"] for row in value["implementation_files"]])
    _require(all(row["module"].startswith("gene_annotation_episode.") and
        all(part.isidentifier() for part in row["module"].split(".")) for row in value["implementation_files"]), "software_identity_mismatch")
    _require({DRIVER_MODULE, WORKER_MODULE} <= {r["module"] for r in value["implementation_files"]}, "software_identity_mismatch")
    return value


def validate_protein_structure_request(value: ScientificRequest) -> ScientificRequest:
    value = _checked(value, "ScientificRequest")
    if value["operation"] == "inspect":
        science.validate_file_identity(value["structure_file"])
        _require(value["structure_file"]["format"] in ("pdb_3x_text", "pdbx_mmcif_text"), "unsupported_format")
        science.validate_inventory_selection(value["inventory"])
        _require(value["structure_file"]["format"] != "pdb_3x_text" or value["inventory"]["blocks"]["kind"] == "all", "unselected_data_block")
        return value
    metadata = value["supplied_metadata_files"]
    _unique(metadata)
    for f in metadata:
        science.validate_file_identity(f)
        _require(f["format"] == "protein_structure_metadata_v1", "unsupported_format")
    selections = [("single", value["selection"])] if value["operation"] == "extract_sequence" else [(side, value[side + "_selection"]) for side in ("fixed", "moving")]
    for role, selection in selections:
        science.validate_structure_selection(selection)
        _require(selection["structure_role"] == role, "conflicting_identity")
        evidence = selection["semantics_evidence"]
        _require(evidence is None or any(science.same(evidence["file_identity"], f) for f in metadata), "metadata_join_conflict")
    if value["operation"] == "compare":
        corr = science.validate_correspondence_input(value["correspondence"])
        params = science.validate_calculation_parameters(value["parameters"])
        transform = params["declared_transform"]
        if transform is not None:
            for side in ("fixed", "moving"):
                _require(science.same(transform[side + "_selection"], value[side + "_selection"]), "invalid_transform")
            received = transform["received_from"]
            _require(received is None or "use_transform" in received["saved_sheet"]["allowed_uses"], "saved_sheet_not_received")
        if corr["kind"] == "retained_alignment":
            for side in ("fixed", "moving"):
                descriptor = corr[side + "_sequence_descriptor"]
                rebound = deepcopy(descriptor["selection"])
                rebound["structure_role"] = side
                _require(science.same(rebound, value[side + "_selection"]), "sequence_artifact_mismatch")
                _require("structure_correspondence" in descriptor["allowed_uses"], "sequence_not_received")
    return value


def validate_native_protein_structure_result(value: NativeProteinResult) -> NativeProteinResult:
    value = _checked(value, "NativeProteinResult")
    request = validate_protein_structure_request(value["request"])
    validate_protein_structure_software(value["producer"])
    operation = request["operation"]
    _require(value["version"] == NATIVE_FORMATS[operation])
    if operation == "compare":
        sheet = value["sheet"]
        if sheet is None:
            _require(value["state"] != "complete" and bool(value["issues"]))
        else:
            science.validate_protein_structure_sheet(sheet)
            _require(science.same(sheet["native_request"], request["parameters"]), "original_commission_mismatch")
            _require(science.same(sheet["input_identities"]["correspondence"], request["correspondence"]), "original_commission_mismatch")
            _require(science.same(sheet["input_identities"]["metadata_artifacts"], request["supplied_metadata_files"]), "metadata_join_conflict")
            for side in ("fixed", "moving"):
                _require(science.same(sheet["sequences"][side]["selection"], request[side + "_selection"]), "original_commission_mismatch")
            _require(sheet["native_baseline"] is not None, "native_result_missing")
            _require(value["state"] == sheet["native_baseline"]["state"], "conflicting_identity")
    else:
        parsed = science.validate_parsed_structure(value["parsed"])
        expected_file = request["structure_file"] if operation == "inspect" else request["selection"]["file_identity"]
        _require(science.same(parsed["file_identity"], expected_file), "input_digest_mismatch")
        if operation == "inspect":
            inventory = science.validate_structure_inventory(value["inventory"])
            _require(science.same(inventory["file_identity"], expected_file) and science.same(inventory["selection"], request["inventory"]), "original_commission_mismatch")
            records = [parsed, inventory]
        else:
            sequence = science.validate_structure_sequence(value["sequence"])
            metadata = science.validate_structure_metadata(value["metadata"])
            _require(science.same(sequence["selection"], request["selection"]) and science.same(metadata["selection"], request["selection"]), "original_commission_mismatch")
            _require(science.same([m["file_identity"] for m in metadata["supplied_metadata"]], request["supplied_metadata_files"]), "metadata_join_conflict")
            records = [parsed, sequence, metadata]
        _require((value["state"] == "complete") == all(r["state"] == "complete" for r in records), "conflicting_identity")
        _require(all(any(science.same(i, received) for received in value["issues"]) for r in records for i in r["issues"]), "conflicting_identity")
    return value


def required_input_files(request: ScientificRequest) -> list[tuple[str, FileIdentity]]:
    """Exact operand role/file multiset; no source traversal or implicit input."""
    request = validate_protein_structure_request(request)
    operation = request["operation"]
    if operation == "inspect":
        return [("single_structure", request["structure_file"])]
    if operation == "extract_sequence":
        rows = [("single_structure", request["selection"]["file_identity"])]
    else:
        rows = [(side + "_structure", request[side + "_selection"]["file_identity"]) for side in ("fixed", "moving")]
        corr = request["correspondence"]
        if corr["kind"] == "explicit_map":
            rows.append(("explicit_map", corr["map_file"]))
        else:
            rows += [("alignment_native", corr["alignment"]["native_file"]), ("alignment_grading", corr["alignment"]["grading_file"])]
            for side in ("fixed", "moving"):
                descriptor = corr[side + "_sequence_descriptor"]
                rows += [(side + "_sequence", descriptor["sequence_file"]), (side + "_residue_map", descriptor["residue_map_file"])]
        transform = request["parameters"]["declared_transform"]
        if transform is not None and transform["received_from"] is not None:
            received = transform["received_from"]
            rows += [("received_transform_components", received["components_file"]), ("received_transform_sheet", received["saved_sheet"]["sheet_file"])]
    rows += [("supplied_metadata", f) for f in request["supplied_metadata_files"]]
    return deepcopy(rows)


def validate_input_associations(request, inputs):
    expected = required_input_files(request)
    actual = [(row["role"], row["file_identity"]) for row in inputs]
    _unique(actual)
    _require(sorted(canonical(v) for v in actual) == sorted(canonical(v) for v in expected), "original_commission_mismatch")
    _require([r["input_id"] for r in inputs] == ["input_" + str(i) for i in range(len(inputs))])
    for row in inputs:
        science.validate_file_identity(row["file_identity"])


def output_files(operation: Operation) -> list[OutputFile]:
    _require(operation in NATIVE_FORMATS)
    rows = [{"role": "native_result", "relative_path": "result.json", "format": NATIVE_FORMATS[operation]},
        {"role": "stdout", "relative_path": "stdout.log", "format": "text"},
        {"role": "stderr", "relative_path": "stderr.log", "format": "text"}]
    if operation == "extract_sequence":
        rows += [{"role": "sequence", "relative_path": "sequence.txt", "format": "ascii_protein_sequence_v1"},
            {"role": "residue_map", "relative_path": "residue-map.json", "format": "protein_structure_sequence_v1"}]
    return rows


def _environment(value):
    _require(Draft202012Validator(_ENV).is_valid(value))
    _require(not ({"HOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR", "PYTHONPYCACHEPREFIX", "PYTHONHOME", "PYTHONUSERBASE"} & value.keys()), "invalid_output_path")
    _require(value.get("PYTHONDONTWRITEBYTECODE", "1") == "1", "invalid_output_path")


def validate_protein_structure_job(value: NativeProteinJob) -> NativeProteinJob:
    value = _checked(value, "NativeProteinJob")
    validate_protein_structure_request(value["request"])
    validate_protein_structure_software(value["software"])
    _environment(value["environment"])
    validate_input_associations(value["request"], value["inputs"])
    paths = []
    for index, row in enumerate(value["inputs"]):
        paths.append(_path(row["path"], absolute=True))
        _require(row["staged_relative_path"] == "inputs/input_" + str(index), "invalid_output_path")
    for i, path in enumerate(paths):
        for j in range(i + 1, len(paths)):
            other = paths[j]
            if path == other:
                # Different selected chains/models or sequence roles can use
                # the same retained bytes. Staging remains distinct per input.
                _require(science.same(value["inputs"][i]["file_identity"],
                                      value["inputs"][j]["file_identity"]), "invalid_output_path")
            else:
                _require(not _overlap(path, other), "invalid_output_path")
    _require(science.same(value["outputs"], output_files(value["request"]["operation"])), "invalid_output_path")
    return value


def compile_protein_structure_job(job: NativeProteinJob, *, input_paths: dict[str, str] | None = None,
                                  output_directory: str = ".") -> CompiledJob:
    job = validate_protein_structure_job(job)
    root = PurePosixPath(output_directory)
    if output_directory != ".":
        _path(output_directory, absolute=True)
    if input_paths is not None:
        _require(type(input_paths) is dict and set(input_paths) == {r["input_id"] for r in job["inputs"]}, "original_commission_mismatch")
        _require(output_directory != ".", "invalid_output_path")
        for row in job["inputs"]:
            path = _path(input_paths[row["input_id"]], absolute=True)
            _require(path == root / row["staged_relative_path"], "invalid_output_path")
    argv = [job["software"]["python_executable"], "-B", "-m", job["software"]["worker_module"],
        "--request-json", str(root / WORKER_INPUT_FILENAME), "--output-json", str(root / "result.json")]
    return {"argv": argv, "environment": deepcopy(job["environment"]), "outputs": deepcopy(job["outputs"])}


def requested_job_from_protein_structure(job: NativeProteinJob) -> RequestedProteinJob:
    job = validate_protein_structure_job(job)
    compiled = compile_protein_structure_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_protein_structure": job}


def validate_protein_structure_requested_job(value: RequestedProteinJob) -> RequestedProteinJob:
    value = _checked(value, "RequestedProteinJob")
    _require(science.same(value, requested_job_from_protein_structure(value["native_protein_structure"])), "original_commission_mismatch")
    return value


def validate_protein_structure_bindings(value: list[NativeProteinBinding]) -> list[NativeProteinBinding]:
    _require(type(value) is list and bool(value))
    result = [_checked(row, "NativeProteinBinding") for row in value]
    _unique(result)
    for row in result:
        validate_protein_structure_software(row["software"])
        _require((row["operation"] == "compare") == (row["scientific_mode"] is not None))
    return result


def driver_argv(plan: NativeProteinRunPlan) -> list[str]:
    software = plan["requested_job"]["native_protein_structure"]["software"]
    return [software["python_executable"], "-B", "-m", software["driver_module"],
        str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME)]


def realized_environment(job, attempt_directory):
    root = _path(attempt_directory, absolute=True)
    return {**job["environment"], "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(root / "tmp"),
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache"),
        "PIP_CACHE_DIR": str(root / "cache" / "pip")}


def validate_protein_structure_run_plan(value: NativeProteinRunPlan) -> NativeProteinRunPlan:
    value = _checked(value, "NativeProteinRunPlan")
    request = validate_protein_structure_requested_job(value["requested_job"])
    owner = value["identity"]
    execution = _path(owner["execution_id"], absolute=True)
    attempt = _path(value["attempt_directory"], absolute=True)
    _require(execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME, "original_commission_mismatch")
    _require(owner["attempt_id"] == digest(owner["operation_key"]) and owner["requested_job_sha256"] == digest(request), "original_commission_mismatch")
    _require(execution.parent.name == digest(owner["operation_key"]) and
        execution.parent.parent.name == digest({"run": owner["run_id"], "episode": owner["episode_id"]}) and
        execution.parent.parent.parent.name == ".episode-operations", "original_commission_mismatch")
    _require(type(value["policy"]["memory_bytes"]) is int and type(value["policy"]["scratch_bytes"]) is int)
    for row in request["native_protein_structure"]["inputs"]:
        _require(not _overlap(_path(row["path"], absolute=True), execution.parent), "invalid_output_path")
    return value


def manifest_files(job: NativeProteinJob) -> list[dict]:
    rows = [{"kind": "input", "role": r["role"], "input_id": r["input_id"],
             "format": r["file_identity"]["format"], "relative_path": r["staged_relative_path"]} for r in job["inputs"]]
    rows += [{"kind": "control", "role": "run_plan", "input_id": None,
              "format": "native_protein_structure_run_plan_v1", "relative_path": RUN_PLAN_FILENAME},
             {"kind": "control", "role": "worker_input", "input_id": None,
              "format": "protein_structure_worker_input_v1", "relative_path": WORKER_INPUT_FILENAME}]
    rows += [{"kind": "output", "input_id": None, **r} for r in job["outputs"]]
    return rows


def validate_protein_structure_bundle(value: NativeProteinBundle, *, plan: NativeProteinRunPlan) -> NativeProteinBundle:
    plan = validate_protein_structure_run_plan(plan)
    value = _checked(value, "NativeProteinBundle")
    job = plan["requested_job"]["native_protein_structure"]
    _require(science.same(value["identity"], plan["identity"]) and science.same(value["requested_job"], plan["requested_job"])
        and science.same(value["software"], job["software"]), "original_commission_mismatch")
    _require(value["driver_argv"] == driver_argv(plan) and value["realized_environment"] == realized_environment(job, plan["attempt_directory"]), "original_commission_mismatch")
    expected_command = compile_protein_structure_job(job, output_directory=plan["attempt_directory"])["argv"]
    _require(value["worker_argv"] is None or value["worker_argv"] == expected_command, "original_commission_mismatch")
    _require(value["worker_argv"] is not None or value["returncode"] is None, "conflicting_identity")
    expected = manifest_files(job)
    _require(len(value["files"]) == len(expected), "capture_incomplete")
    by_input = {r["input_id"]: r["file_identity"] for r in job["inputs"]}
    for row, original in zip(value["files"], expected):
        _require(all(science.same(row[k], v) for k, v in original.items()), "original_commission_mismatch")
        if row["state"] == "present":
            _require(row["sha256"] is not None and row["byte_length"] is not None, "capture_incomplete")
            if row["kind"] == "input":
                f = by_input[row["input_id"]]
                _require(row["sha256"] == f["sha256"] and row["byte_length"] == f["byte_length"], "input_digest_mismatch")
        else:
            _require(row["sha256"] is None and row["byte_length"] is None and
                any(f["artifact_role"] == row["role"] for f in value["failures"]), "capture_incomplete")
    try:
        start, finish = [datetime.fromisoformat(value[k].replace("Z", "+00:00")) for k in ("started_at", "finished_at")]
        _require(start.tzinfo is not None and finish.tzinfo is not None and finish >= start)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid_schema") from error
    duration = value["measured_duration"]
    if duration["kind"] == "unmeasured":
        _require(duration["seconds"] is None and duration["source"] == "none")
    else:
        _require(duration["seconds"] is not None and duration["source"] == "monotonic_clock")
        _require(duration["kind"] != "worker_wall" or value["worker_argv"] is not None)
    if value["worker_argv"] is None or value["returncode"] is None:
        _require(bool(value["failures"]), "native_process_failed")
    if value["native_status"] == "complete":
        _require(value["returncode"] == 0 and all(r["state"] == "present" for r in value["files"])
            and not value["failures"], "capture_incomplete")
    else:
        _require(bool(value["failures"]), "native_process_failed")
    return value


def validate_protein_structure_worker_input(value: WorkerInput) -> WorkerInput:
    value = _checked(value, "WorkerInput")
    validate_protein_structure_request(value["request"])
    validate_protein_structure_software(value["software"])
    validate_input_associations(value["request"], value["files"])
    for row in value["files"]:
        _path(row["path"], absolute=True)
    _unique([r["path"] for r in value["files"]], "invalid_output_path")
    return value


NATIVE_PROTEIN_STRUCTURE_JOB_SCHEMA = protein_structure_execution_schema("NativeProteinJob")
NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA = protein_structure_execution_schema("RequestedProteinJob")
