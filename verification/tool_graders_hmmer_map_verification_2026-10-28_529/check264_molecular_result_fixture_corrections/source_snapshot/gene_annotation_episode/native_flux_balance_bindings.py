"""Pure local FBA capability metadata; no deployment or scoring claim."""
from copy import deepcopy

from .execution_contracts import canonical
from .flux_balance_contracts import flux_balance_schema, validate_flux_balance_record
from .native_flux_balance_contracts import validate_flux_balance_software


_VERSION = "flux_balance_local_binding_v1"
_OPERATION = "perform_flux_balance_analysis"
_MODE = "steady_state_linear_fba"
_FORMATS = ("sbml", "cobra_json")
_KEYS = {"version", "operation", "mode", "software", "model_formats"}

FLUX_BALANCE_BINDING_SCHEMA = {
    "type": "object", "properties": {
        "version": {"const": _VERSION}, "operation": {"const": _OPERATION},
        "mode": {"const": _MODE}, "software": flux_balance_schema("FBASoftware"),
        "model_formats": {"type": "array", "minItems": 1, "uniqueItems": True,
            "items": {"enum": list(_FORMATS)}},
    }, "required": ["version", "operation", "mode", "software", "model_formats"],
    "additionalProperties": False,
}


def _binding(value):
    if (type(value) is not dict or set(value) != _KEYS
            or value["version"] != _VERSION or value["operation"] != _OPERATION
            or value["mode"] != _MODE or type(value["model_formats"]) is not list
            or not value["model_formats"] or any(type(item) is not str or item not in _FORMATS
                for item in value["model_formats"])
            or len(set(value["model_formats"])) != len(value["model_formats"])):
        raise ValueError("fba_local_binding_invalid")
    software = validate_flux_balance_software(value["software"])
    return {"version": _VERSION, "operation": _OPERATION, "mode": _MODE,
        "software": software, "model_formats": deepcopy(value["model_formats"])}


def validate_flux_balance_bindings(value) -> list:
    """Validate selected metadata only; inspect no executable or input file."""
    if type(value) is not list:
        raise ValueError("fba_local_bindings_invalid")
    rows = [_binding(row) for row in value]
    if len({canonical(row) for row in rows}) != len(rows):
        raise ValueError("fba_duplicate_local_binding")
    return rows


def flux_balance_binding_accepts_job(binding, job) -> bool:
    """Match an inner selected FBAJob to one exact local binding."""
    binding = _binding(binding)
    job = validate_flux_balance_record("FBAJob", job)
    validate_flux_balance_software(job["software"])
    return (job["operation"] == binding["operation"] and job["mode"] == binding["mode"]
        and canonical(job["software"]) == canonical(binding["software"])
        and job["model_input"]["format"] in binding["model_formats"])


__all__ = ["FLUX_BALANCE_BINDING_SCHEMA", "validate_flux_balance_bindings",
    "flux_balance_binding_accepts_job"]
