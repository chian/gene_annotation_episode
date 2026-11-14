"""Read an explicit retained four-estimate log model; no scientific inference.

The closed JSON wire is MODEL_VERSION without its self-referential ``source``.
That witness is constructed from actual retained bytes. Reporting-event witnesses
remain source locators and must be authenticated separately by the selected host.
"""
from copy import deepcopy
import json

from .literature_binding_model_inputs import _json_object, _json_constant, _json_float
from .literature_experimental_contracts import ExperimentalContractError
from .literature_binding_interaction_calculations import (
    MODEL_VERSION, binding_interaction_operand_keys, _validate_model,
)

WIRE_FIELDS = ("version", "parameter_kind", "measurement_order", "measurement_keys",
    "physical_fit_ids", "log_basis", "distribution", "variance_status", "log_covariance",
    "reporting_event", "reporting_event_source")


def read_binding_interaction_model(source, *, inputs):
    if type(source) is not dict or set(source) != {"source_ref", "artifact_ref", "content"}:
        raise ExperimentalContractError("closed_fields_required", "source")
    for field in ("source_ref", "artifact_ref"):
        if type(source[field]) is not str or not source[field].strip():
            raise ExperimentalContractError("nonempty_source_token_required", "source." + field)
    if type(source["content"]) is not bytes:
        raise ExperimentalContractError("source_bytes_required", "source.content")
    try:
        wire = json.loads(source["content"].decode("utf-8"), object_pairs_hook=_json_object,
            parse_constant=_json_constant, parse_float=_json_float)
    except ExperimentalContractError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_binding_interaction_model_source", "source.content") from error
    if type(wire) is not dict or set(wire) != set(WIRE_FIELDS):
        raise ExperimentalContractError("closed_fields_required", "model")
    locator = {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
        "kind": "utf8_span", "start": 0, "end": len(source["content"])}
    model = _validate_model({**wire, "source": locator}, inputs, binding_interaction_operand_keys(inputs))
    return {"model": deepcopy(model), "source": locator}


__all__ = ["MODEL_VERSION", "WIRE_FIELDS", "read_binding_interaction_model"]
