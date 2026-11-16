"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library import protein_structure_contracts as science

DRIVER_MODULE = "gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_driver"
WORKER_MODULE = "gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_worker"
_RECORDED_MODULE_PAIRS = ((DRIVER_MODULE, WORKER_MODULE),)
RUN_PLAN_FILENAME = "protein-structure-plan.json"
ATTEMPT_DIRECTORY_NAME = "protein-structure-attempt"
BUNDLE_FILENAME = "bundle.json"
WORKER_INPUT_FILENAME = "worker-input.json"
OWNER_FILENAME = ".native-protein-structure-owner.json"
STARTED_FILENAME = ".native-protein-structure-started.json"
POLICY = {'memory_bytes': 5368709120, 'scratch_bytes': 4294967296}
_RECORDED_MEMORY_BYTES = (5368709120,)
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


def validate_recorded_protein_policy(value, *, code="original_commission_mismatch"):
    """Validate stored allocation values without selecting a launch policy."""
    _require(type(value) is dict and set(value) == {"memory_bytes", "scratch_bytes"},
        code)
    _require(type(value["memory_bytes"]) is int and value["memory_bytes"] in _RECORDED_MEMORY_BYTES
        and type(value["scratch_bytes"]) is int and value["scratch_bytes"] == POLICY["scratch_bytes"],
        code)
    return deepcopy(value)


def _definitions(*, action_custody=False):
    definitions = science.protein_structure_schema_definitions(action_custody=action_custody)
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
        "Software": obj({"python_executable": _TEXT, "python_version": _TEXT,
            "driver_module": {"enum": [pair[0] for pair in _RECORDED_MODULE_PAIRS]},
            "worker_module": {"enum": [pair[1] for pair in _RECORDED_MODULE_PAIRS]},
            "implementation_files": _array(obj({"module": _TEXT}), minItems=1),
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
    own["Software"]["oneOf"] = [
        {"properties": {"driver_module": {"const": driver}, "worker_module": {"const": worker}}}
        for driver, worker in _RECORDED_MODULE_PAIRS]
    own["ScientificRequest"] = {"oneOf": [_ref(name) for name in ("InspectRequest", "ExtractRequest", "CompareRequest")]}
    own["NativeProteinJob"] = obj({"version": {"const": "native_protein_structure_job_v1"}, "program": {"const": "protein_structure_python"},
        "request": _ref("ScientificRequest"), "software": _ref("Software"), "inputs": _array(_ref("InputFile"), minItems=1),
        "outputs": _array(_ref("OutputFile"), minItems=3), "environment": _ENV})
    own["RequestedProteinJob"] = obj({"argv": _array(_TEXT, minItems=1), "environment": _ENV, "native_protein_structure": _ref("NativeProteinJob")})
    own["NativeProteinBinding"] = obj({"operation": {"enum": list(NATIVE_FORMATS)}, "scientific_mode": _nullable(_ref("ScientificMode")), "software": _ref("Software")})
    own["NativeProteinRunPlan"] = obj({"version": {"const": "native_protein_structure_run_plan_v1"},
        "identity": _ref("AttemptIdentity"), "requested_job": _ref("RequestedProteinJob"), "attempt_directory": _TEXT,
        "policy": obj({"memory_bytes": {"enum": list(_RECORDED_MEMORY_BYTES)},
            "scratch_bytes": {"const": POLICY["scratch_bytes"]}})})
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


def protein_structure_execution_schema(type_name: str, *, bindings=None, action_custody=False) -> dict:
    """A self-contained local schema resource, safe inside larger alternatives."""
    definitions = _definitions(action_custody=action_custody)
    _require(type_name in definitions)
    root = _ref(type_name)
    if bindings is not None:
        _require(type_name == "RequestedProteinJob")
        alternatives = []
        from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_contracts import validate_protein_structure_bindings
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
    # The inner resource contains module-owned schema fragments. Callers may
    # edit their exported document without changing another schema or validator.
    return deepcopy(document)


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


NATIVE_PROTEIN_STRUCTURE_JOB_SCHEMA = protein_structure_execution_schema("NativeProteinJob")
NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA = protein_structure_execution_schema("RequestedProteinJob")
