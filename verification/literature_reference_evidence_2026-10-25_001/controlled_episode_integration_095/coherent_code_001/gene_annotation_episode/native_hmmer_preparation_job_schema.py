"""Finite HMMER preparation request shapes; relational validation is separate."""
from copy import deepcopy

from .native_hmmer_preparation_contracts import JOB_VERSION, PROGRAM_MODES, operand_contract, output_contract


def _object(properties, *, optional=False):
    return {"type": "object", "properties": properties, "required": [] if optional else list(properties), "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\x00\r\n]+$"}
NULL_TEXT = {"anyOf": [TEXT, {"type": "null"}]}
SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
COUNT = {"type": "integer", "minimum": 0}
ENVIRONMENT = {"type": "object", "propertyNames": {"allOf": [{"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"}, {"not": {"enum": ["TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"]}}]}, "additionalProperties": {"type": "string", "pattern": "^[^\x00]*$"}}
SOFTWARE_SCHEMA = _object({"executable": {**TEXT, "pattern": "^/[^\x00\r\n]+$"}, "sha256": SHA, "engine_version": {"const": "3.4"}})
FM_PRODUCER_SCHEMA = _object({"format": {"const": "hmmer_fm_3_4"}, "engine_version": {"const": "3.4"},
    "byte_order": {"enum": ["little", "big"]}, **{key: {"const": value} for key, value in
        {"uint8_bytes": 1, "uint16_bytes": 2, "uint32_bytes": 4, "uint64_bytes": 8, "int32_bytes": 4}.items()}})
FM_SOURCE_BINDING_SCHEMA = _object({"database_occurrence_id": TEXT, "source_occurrence_ids": {"type": "array", "minItems": 1, "items": TEXT},
    "source_sha256s": {"type": "array", "minItems": 1, "items": SHA}, "producer_attempt_id": TEXT})


def preparation_job_schema(program=None, mode=None):
    pairs = [(p, m) for p, modes in PROGRAM_MODES.items() for m in modes if (program is None or p == program) and (mode is None or m == mode)]
    if not pairs:
        raise ValueError("native_hmmer_preparation_unsupported_program_mode")
    if len(pairs) != 1:
        return {"anyOf": [preparation_job_schema(p, m) for p, m in pairs]}
    program, mode = pairs[0]
    required_inputs, optional_inputs = operand_contract(program, mode)
    required_outputs, optional_outputs = output_contract(program, mode)
    operand = {"anyOf": [_object({"role": {"const": role}, "ordinal": COUNT, "path": {**TEXT, "pattern": "^/[^\x00\r\n]+$"},
        "format": {"enum": sorted(formats)}, "sha256": SHA, "size_bytes": COUNT, "artifact_ref": NULL_TEXT})
        for role, formats in {**required_inputs, **optional_inputs}.items()]}
    output = {"anyOf": [_object({"role": {"const": role}, "format": {"enum": sorted(formats)},
        "relative_path": {**TEXT, "pattern": "^[^/\x00\r\n][^\x00\r\n]*$"}})
        for role, formats in {**required_outputs, **optional_outputs}.items()]}
    metadata = _object({"producer_contract": FM_PRODUCER_SCHEMA, "source_binding": FM_SOURCE_BINDING_SCHEMA}, optional=True) if program in {"makehmmerdb", "hmmerfm-exactmatch"} else _object({})
    if program == "hmmerfm-exactmatch":
        metadata["required"] = ["producer_contract"]
    result = _object({"version": {"const": JOB_VERSION}, "program": {"const": program}, "mode": {"const": mode},
        "software": SOFTWARE_SCHEMA, "environment": ENVIRONMENT, "operands": {"type": "array", "minItems": len(required_inputs), "items": operand},
        "options": {"type": "array", "items": TEXT}, "outputs": {"type": "array", "minItems": len(required_outputs), "items": output},
        "key": TEXT if (program, mode) == ("hmmfetch", "single_key") else {"type": "null"},
        "input_metadata": metadata, "grading_parameters": {"type": "object"}})
    for field, roles in (("operands", required_inputs), ("outputs", required_outputs)):
        result["properties"][field]["allOf"] = [{"contains": {"type": "object", "properties": {"role": {"const": role}}, "required": ["role"]}} for role in roles]
    return deepcopy(result)


def preparation_requested_job_schema(program=None, mode=None):
    return _object({"argv": {"type": "array", "minItems": 1, "items": deepcopy(TEXT)}, "environment": deepcopy(ENVIRONMENT),
                    "native_hmmer_preparation": preparation_job_schema(program, mode)})


NATIVE_HMMER_PREPARATION_REQUESTED_JOB_SCHEMA = preparation_requested_job_schema()
