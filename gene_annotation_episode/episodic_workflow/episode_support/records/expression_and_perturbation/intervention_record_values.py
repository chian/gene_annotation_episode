"""A106 finite native values and exact retained-content identities."""
import json
import math
import re
from copy import deepcopy

_CONTENT_KEYS = {"source_ref", "artifact_field", "artifact_ref", "sha256", "byte_count"}

def _require(condition, code="bvbrc_annotation_document_invalid"):
    if not condition:
        raise ValueError(code)

def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")

def _finite_json(value, active=None):
    active = set() if active is None else active
    kind = type(value)
    if value is None or kind in {bool, int}:
        return
    if kind is str:
        value.encode("utf-8")
        return
    if kind is float:
        _require(math.isfinite(value))
        return
    _require(kind in {dict, list} and id(value) not in active)
    active.add(id(value))
    try:
        if kind is dict:
            _require(all(type(key) is str for key in value))
            for key, item in value.items():
                key.encode("utf-8")
                _finite_json(item, active)
        else:
            for item in value:
                _finite_json(item, active)
    finally:
        active.remove(id(value))

def _content(value):
    _require(type(value) is dict and set(value) == _CONTENT_KEYS,
        "bvbrc_annotation_content_invalid")
    _require(type(value["source_ref"]) is str and re.fullmatch(
        r"source_[a-f0-9]{24,64}", value["source_ref"]) is not None
        and value["artifact_field"] == "artifact_ref"
        and type(value["sha256"]) is str
        and re.fullmatch(r"[a-f0-9]{64}", value["sha256"]) is not None
        and value["artifact_ref"] == "artifact_" + value["sha256"]
        and type(value["byte_count"]) is int and value["byte_count"] >= 0,
        "bvbrc_annotation_content_invalid")
    return deepcopy(value)

