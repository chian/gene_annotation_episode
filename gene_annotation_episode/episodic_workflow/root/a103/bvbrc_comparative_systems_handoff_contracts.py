"""Data-only frozen ComparativeSystems shapes and finite detached JSON helpers.

Shape validation establishes neither host custody nor scientific interpretation.
All consumers use the same packaged definitions; this module imports none of
their implementations and never reads a verification directory at runtime.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from jsonschema.validators import extend

__all__ = ("schema", "validate_shape", "canonical_sha256")

_DEFINITIONS = json.loads(Path(__file__).with_name(
    "bvbrc_comparative_systems_handoff_schemas.json").read_text(encoding="utf-8"))["$defs"]
_TYPE_CHECKER = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda _checker, value: type(value) is int,
    "number": lambda _checker, value: type(value) in (int, float),
    "boolean": lambda _checker, value: type(value) is bool,
    "object": lambda _checker, value: type(value) is dict,
    "array": lambda _checker, value: type(value) is list,
})
_Validator = extend(Draft202012Validator, type_checker=_TYPE_CHECKER)


def _references(value):
    if type(value) is dict:
        if "$ref" in value:
            yield value["$ref"].removeprefix("#/$defs/")
        for child in value.values():
            yield from _references(child)
    elif type(value) is list:
        for child in value:
            yield from _references(child)


def schema(name: str) -> dict:
    """Return a detached Draft2020-12 schema with its data-only closure."""
    if type(name) is not str or name not in _DEFINITIONS:
        raise ValueError("comparative_systems_unknown_schema")
    needed, pending = {name}, [name]
    while pending:
        for reference in _references(_DEFINITIONS[pending.pop()]):
            if reference not in needed:
                needed.add(reference)
                pending.append(reference)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/" + name,
            "$defs": {key: deepcopy(value) for key, value in _DEFINITIONS.items()
                      if key in needed}}


def _finite_copy(value):
    active = set()

    def copy(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float:
            if not math.isfinite(item):
                raise ValueError("comparative_systems_nonfinite_number")
            return item
        if kind not in (dict, list) or id(item) in active:
            raise ValueError("comparative_systems_non_json_value")
        active.add(id(item))
        try:
            if kind is list:
                return [copy(child) for child in item]
            if any(type(key) is not str for key in item):
                raise ValueError("comparative_systems_non_json_key")
            return {key: copy(child) for key, child in item.items()}
        finally:
            active.remove(id(item))

    try:
        return copy(value)
    except RecursionError as error:
        raise ValueError("comparative_systems_non_json_value") from error


@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(schema(name))


def validate_shape(name: str, value: object) -> dict:
    """Reject invalid shapes/non-JSON values and return a detached value."""
    if type(name) is not str or name not in _DEFINITIONS:
        raise ValueError("comparative_systems_unknown_schema")
    result = _finite_copy(value)
    try:
        _validator(name).validate(result)
    except ValidationError as error:
        location = "/" + "/".join(str(part) for part in error.absolute_path)
        raise ValueError("comparative_systems_shape_invalid:" + name + ":" + location) from error
    return result


def canonical_sha256(value: object) -> str:
    """Hash finite JSON using the frozen UTF-8 canonical byte convention."""
    copied = _finite_copy(value)
    try:
        encoded = json.dumps(copied, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError) as error:
        raise ValueError("comparative_systems_invalid_digest_value") from error
    return hashlib.sha256(encoded).hexdigest()
