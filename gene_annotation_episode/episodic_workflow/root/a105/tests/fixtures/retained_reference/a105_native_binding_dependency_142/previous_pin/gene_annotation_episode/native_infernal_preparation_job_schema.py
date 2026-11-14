"""Typed callable request shapes for the preparation compiler.

The compiler additionally checks mode/role relationships and exact argv. These
schemas describe data, not a scoring language or an execution decision.
"""
from copy import deepcopy

from .infernal_preparation_schema import PROGRAM_MODES
from .native_infernal_preparation_contracts import JOB_VERSION, operand_contract, output_contract


def _object(properties, *, optional=False):
    return {"type": "object", "properties": properties,
            "required": [] if optional else list(properties), "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\x00\r\n]+$"}
NULL_TEXT = {"anyOf": [TEXT, {"type": "null"}]}
SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
COUNT = {"type": "integer", "minimum": 0}
ENVIRONMENT = {"type": "object", "propertyNames": {"allOf": [
    {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
    {"not": {"enum": ["TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"]}}]},
    "additionalProperties": {"type": "string", "pattern": "^[^\x00]*$"}}
SOFTWARE_SCHEMA = _object({"executable": {**TEXT, "pattern": "^/[^\x00\r\n]+$"},
    "sha256": SHA, "engine_version": NULL_TEXT})
_BINDING = _object({"artifact_ref": TEXT, "artifact_sha256": SHA,
    "source_artifact_ref": TEXT, "source_sha256": SHA, "expected_attempt_id": TEXT,
    "actual_attempt_id": TEXT, "staged_source_stem": TEXT, "actual_relative_path": TEXT,
    "regular_file": {"type": "boolean"}})
_PARTITION = _object({"artifact_ref": TEXT, "source_model_artifact_ref": TEXT,
    "source_model_sha256": SHA, "partition_index": {"type": "integer", "minimum": 1},
    "partition_count": {"type": "integer", "minimum": 1},
    "requested_megabases": {"type": "number", "exclusiveMinimum": 0},
    "settings": {"type": "object", "additionalProperties": {
        "type": ["string", "number", "boolean", "null"]}}})
_PARAMETERS = _object({
    "artifact_bindings": {"type": "array", "items": _BINDING},
    "partition_requests": {"type": "array", "items": _PARTITION},
    **{key: {"type": ["number", "null"]} for key in (
        "search_space_mb", "evalue", "pvalue", "score_bits", "rounding_absolute_tolerance",
        "requested_megabases")},
    **{key: {"type": ["integer", "null"], "minimum": 1}
       for key in ("partition_index", "partition_count")},
}, optional=True)


def preparation_job_schema(program=None, mode=None):
    """Describe one selected mode, or the complete finite set of supported modes."""
    pairs = [(p, m) for p, modes in PROGRAM_MODES.items() for m in sorted(modes)
             if program is None or p == program if mode is None or m == mode]
    if not pairs:
        raise ValueError("native_infernal_preparation_unsupported_program_mode")
    if len(pairs) != 1:
        return {"anyOf": [preparation_job_schema(p, m) for p, m in pairs]}
    program, mode = pairs[0]
    required_inputs, optional_inputs = operand_contract(program, mode)
    required_outputs, optional_outputs = output_contract(program, mode)
    inputs, outputs = {**required_inputs, **optional_inputs}, {**required_outputs, **optional_outputs}
    operand = {"anyOf": [_object({"role": {"const": role}, "ordinal": COUNT,
        "path": {**TEXT, "pattern": "^/[^\x00\r\n]+$"}, "format": {"enum": sorted(formats)},
        "sha256": SHA, "size_bytes": COUNT, "artifact_ref": NULL_TEXT})
        for role, formats in inputs.items()]}
    output = {"anyOf": [_object({"role": {"const": role}, "format": {"enum": sorted(formats)},
        "relative_path": {**TEXT, "pattern": "^[^/\x00\r\n][^\x00\r\n]*$"}})
        for role, formats in outputs.items()]}
    parameter_names = ({"artifact_bindings"} if program in {"cmconvert", "cmfetch", "cmpress"}
        else set() if program == "cmemit" else set(_PARAMETERS["properties"]) - {"artifact_bindings"})
    parameters = _object({key: deepcopy(_PARAMETERS["properties"][key])
        for key in sorted(parameter_names)}, optional=True)
    result = _object({"version": {"const": JOB_VERSION}, "program": {"const": program},
        "mode": {"const": mode}, "software": SOFTWARE_SCHEMA, "environment": ENVIRONMENT,
        "operands": {"type": "array", "minItems": len(required_inputs), "items": operand},
        "options": {"type": "array", "items": TEXT},
        "outputs": {"type": "array", "minItems": len(required_outputs), "items": output},
        "key": TEXT if (program, mode) == ("cmfetch", "single_key") else {"type": "null"},
        "grading_parameters": parameters})
    for field, required_roles in (("operands", required_inputs), ("outputs", required_outputs)):
        result["properties"][field]["allOf"] = [{"contains": {"type": "object",
            "properties": {"role": {"const": role}}, "required": ["role"]}}
            for role in required_roles]
    return deepcopy(result)


def preparation_requested_job_schema(program=None, mode=None):
    return _object({"argv": {"type": "array", "minItems": 1, "items": deepcopy(TEXT)},
        "environment": deepcopy(ENVIRONMENT),
        "native_infernal_preparation": preparation_job_schema(program, mode)})


NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA = preparation_requested_job_schema()
