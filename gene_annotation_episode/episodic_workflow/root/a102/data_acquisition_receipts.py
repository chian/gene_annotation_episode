"""The controlled Source/File confirmation shared by ordinary data getters.

Provider adapters own their requests, native representations and failure codes.
This owner only validates the four-field receipt and its reference relationships.
"""
from copy import deepcopy
import re

from .domain import ContractError


_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z", re.ASCII)
_ARTIFACT = re.compile(r"artifact_[a-f0-9]{64}\Z", re.ASCII)


def acquisition_receipt_schema(*, failure_codes):
    properties = {"acquired": {"type": "boolean"},
        "source_ref": {"type": ["string", "null"], "format": "reference", "x-reference-namespace": "source"},
        "data_ref": {"type": ["string", "null"], "format": "reference", "x-reference-namespace": "artifact"},
        "failure_code": {"type": ["string", "null"], "enum": [None, *failure_codes]}}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def validate_acquisition_receipt(value, *, failure_codes, invalid_code):
    def require(condition):
        if not condition:
            raise ContractError(invalid_code)
    require(type(value) is dict and set(value) == {"acquired", "source_ref", "data_ref", "failure_code"})
    require(type(value["acquired"]) is bool)
    require(value["source_ref"] is None or type(value["source_ref"]) is str and _SOURCE.fullmatch(value["source_ref"]) is not None)
    require(value["data_ref"] is None or type(value["data_ref"]) is str and _ARTIFACT.fullmatch(value["data_ref"]) is not None)
    if value["acquired"]:
        require(value["source_ref"] is not None and value["data_ref"] is not None and value["failure_code"] is None)
    else:
        require(value["data_ref"] is None and type(value["failure_code"]) is str and value["failure_code"] in failure_codes)
    return deepcopy(value)


__all__ = ["acquisition_receipt_schema", "validate_acquisition_receipt"]
