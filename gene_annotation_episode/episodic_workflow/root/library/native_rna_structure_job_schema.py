"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import OPERATIONS, PAIR_TYPES

WORKER_MODULE = "gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_worker"
INPUT_NAMES = {"input": "input.json", "model_parameter_input": "model-parameter-input.par"}
ROLE_FORMATS = {"input": "rna_input_json_v1", "model_parameter_input": "viennarna_parameter_file",
    "native_result": "rna_native_record_json_v1", "model": "vienna_model_json_v1",
    "effective_parameters": "viennarna_parameter_file", "stdout": "text", "stderr": "text"}
_TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_NULL = {"type": "null"}
_COUNT = {"type": "integer", "minimum": 0}
_ENV = {"type": "object", "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
    "additionalProperties": {"type": "string", "pattern": "^[^\\u0000]*$"}}
_SETTINGS = {"temperature_c": {"type": "number", "exclusiveMinimum": -273.15},
    "dangles": {"type": "integer", "enum": [0, 1, 2, 3]},
    **{name: {"type": "boolean"} for name in ("noLP", "noGU", "noGUclosure", "special_hp", "logML")},
    "min_loop_size": _COUNT, "max_bp_span": {"anyOf": [{"const": -1}, {"type": "integer", "minimum": 1}]},
    "circ": {"const": False}, "gquad": {"const": False}}
MODEL_SPEC_SCHEMA = obj({"schema": {"const": "vienna_rna_model_spec_v1"}, **_SETTINGS,
    "hard_constraints": _NULL, "soft_constraints": _NULL,
    "parameters": {"oneOf": [obj({"kind": {"const": "turner2004"}, "operand_role": _NULL}),
        obj({"kind": {"const": "supplied_parameter_file"}, "operand_role": {"const": "model_parameter_input"}})]}})
SOFTWARE_SCHEMA = obj({"python_executable": _TEXT, "python_sha256": _SHA,
    "python_version": {"anyOf": [_TEXT, _NULL]}, "worker_module": {"enum": [WORKER_MODULE]},
    "worker_source_sha256": _SHA, "viennarna_distribution_version": {"anyOf": [_TEXT, _NULL]},
    "rna_module_sha256": {"anyOf": [_SHA, _NULL]}, "rna_extension_sha256": {"anyOf": [_SHA, _NULL]}})
PARAMETERS_SCHEMA = obj({"schema": {"const": "rna_calculation_parameters_v1"},
    "topology": obj({"long_stem_min_pairs": {"type": "integer", "minimum": 1},
        "include_exterior_in_loop_size_statistics": {"const": False}}),
    "pair_composition": obj({"accepted_ordered_pair_types": {"type": "array", "uniqueItems": True,
        "items": {"enum": list(PAIR_TYPES)}}, "denominator": {"const": "unambiguous_pairs"}}),
    "energy": obj({"normalization": {"enum": ["none", "per_nt"]}})})
_INPUT = obj({"role": {"enum": list(INPUT_NAMES)}, "path": _TEXT,
    "format": {"enum": [ROLE_FORMATS[r] for r in INPUT_NAMES]}, "sha256": _SHA,
    "size_bytes": _COUNT, "artifact_ref": {"anyOf": [_TEXT, _NULL]}})
_OUTPUT = obj({"role": {"enum": [r for r in ROLE_FORMATS if r not in INPUT_NAMES]},
    "format": {"enum": [ROLE_FORMATS[r] for r in ROLE_FORMATS if r not in INPUT_NAMES]}, "relative_path": _TEXT})
NATIVE_RNA_STRUCTURE_JOB_SCHEMA = obj({"version": {"const": "native_rna_structure_job_v1"},
    "program": {"const": "rna_structure_python"}, "operation": {"enum": list(OPERATIONS.values())},
    "mode": {"enum": list(OPERATIONS)}, "record_key": _TEXT, "software": SOFTWARE_SCHEMA,
    "model": {"anyOf": [MODEL_SPEC_SCHEMA, _NULL]},
    "operands": {"type": "array", "minItems": 1, "items": _INPUT},
    "outputs": {"type": "array", "minItems": 3, "items": _OUTPUT},
    "environment": _ENV, "grading_parameters": PARAMETERS_SCHEMA})
NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA = obj({
    "argv": {"type": "array", "minItems": 1, "items": _TEXT}, "environment": _ENV,
    "native_rna_structure": NATIVE_RNA_STRUCTURE_JOB_SCHEMA})


