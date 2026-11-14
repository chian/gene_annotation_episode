"""Read a retained kinetic log model; custody is supplied by its caller.

The wire object has the existing calculator model fields except ``source``.
That locator is constructed from actually received bytes, never from JSON IDs.
No covariance is inferred from reported spreads, counts or independence.
"""
from copy import deepcopy
import json

from .literature_binding_model_inputs import _json_object, _json_constant, _json_float
from .literature_experimental_contracts import ExperimentalContractError
from .literature_kinetic_calculations import MODEL_VERSION, kinetic_operand_keys, _model

WIRE_FIELDS = ("version", "measurement_order", "measurement_keys", "covariance",
    "variance_status", "observation_model", "log_basis", "origin")


def read_kinetic_model(source, *, inputs):
    """Bind the finite wire model to exact canonical physical estimate owners.

    ``source`` is host-authorized metadata plus retained original bytes. Source
    IDs inside the wire JSON are rejected. The whole original model byte span
    supplies the internal existing calculator locator; scientific applicability
    remains an interpreted condition supported by separately selected witnesses.
    """
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
        raise ExperimentalContractError("malformed_kinetic_model_source", "source.content") from error
    if type(wire) is not dict or set(wire) != set(WIRE_FIELDS):
        raise ExperimentalContractError("closed_fields_required", "model")
    locator = {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
        "representation": "original", "start": 0, "end": len(source["content"])}
    model = _model({**wire, "source": locator}, kinetic_operand_keys(inputs))
    return {"model": deepcopy(model), "source": locator}


__all__ = ["MODEL_VERSION", "WIRE_FIELDS", "read_kinetic_model"]
