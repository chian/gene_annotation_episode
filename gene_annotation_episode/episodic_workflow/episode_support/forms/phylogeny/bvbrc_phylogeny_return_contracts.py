"""A104 private saved-phylogeny return contracts and relationship checks.

Schemas are packaged runtime assets. Validation proves shape and relationships
within the supplied value; the custody host must authenticate every referenced
record, byte artifact, selected action and receiving episode separately.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from threading import Lock

from jsonschema import Draft202012Validator, ValidationError, validators


_DOCUMENT = json.loads(Path(__file__).with_name("bvbrc_phylogeny_return_schemas.json").read_text())
_DEFINITIONS = _DOCUMENT["$defs"]

# This remembers only successful pure shape/relationship checks, never source
# contents, possession, selected actions, file integrity or episode authority.
# Digests rather than values keep closed episode data out of this small cache.
_VALIDATION_CACHE_SIZE = 512
_VALIDATED_CONTRACTS = OrderedDict()
_VALIDATION_CACHE_LOCK = Lock()


def _validation_key(schema, value):
    try:
        encoded = json.dumps((schema, value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).digest()
    except (TypeError, ValueError, OverflowError, RecursionError):
        # A cache is optional. In particular, JSON's integer serialization limit
        # must not change which values the original validator accepts.
        return None


def _already_validated(key):
    if key is None:
        return False
    with _VALIDATION_CACHE_LOCK:
        if key not in _VALIDATED_CONTRACTS:
            return False
        _VALIDATED_CONTRACTS.move_to_end(key)
        return True


def _remember_validated(key):
    if key is not None:
        with _VALIDATION_CACHE_LOCK:
            _VALIDATED_CONTRACTS[key] = None
            _VALIDATED_CONTRACTS.move_to_end(key)
            if len(_VALIDATED_CONTRACTS) > _VALIDATION_CACHE_SIZE:
                _VALIDATED_CONTRACTS.popitem(last=False)


class ContractValidationError(ValueError):
    """A stable code and JSON pointers, without echoing potentially secret data."""

    def __init__(self, code, path="", *, contract=None):
        self.code = code
        self.diagnostics = [{"code": code, "path": path}]
        if contract is not None:
            self.diagnostics[0]["contract"] = contract
        super().__init__(code)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _finite_json(value, path="", ancestors=None):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractValidationError("nonfinite_number", path)
        return
    if type(value) not in (dict, list):
        raise ContractValidationError("not_plain_json", path)
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ContractValidationError("recursive_json", path)
    ancestors.add(id(value))
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractValidationError("nonstring_json_key", path)
            _finite_json(child, _pointer(path, key), ancestors)
    else:
        for index, child in enumerate(value):
            _finite_json(child, _pointer(path, index), ancestors)
    ancestors.remove(id(value))


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _enum(validator, options, instance, schema):
    if not any(_same(instance, option) for option in options):
        yield ValidationError("value does not match a declared enum member")


def _const(validator, expected, instance, schema):
    if not _same(instance, expected):
        yield ValidationError("value does not match the declared constant")


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, {"enum": _enum, "const": _const},
                               type_checker=_TYPES)


def contract_schema(name: str) -> dict:
    """Return a detached schema with exactly its transitively reachable defs."""
    if type(name) is not str or name not in _DEFINITIONS:
        raise ContractValidationError("unknown_appservice_contract")
    reachable = set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                ref = node["$ref"]
                if not ref.startswith("#/$defs/") or ref[8:] not in _DEFINITIONS:
                    raise RuntimeError("invalid_packaged_appservice_schema_reference")
                key = ref[8:]
                if key not in reachable:
                    reachable.add(key)
                    visit(_DEFINITIONS[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    root = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(root)
    root["$defs"] = {key: deepcopy(value) for key, value in _DEFINITIONS.items() if key in reachable}
    return root


def _require(condition, code, path):
    if not condition:
        raise ContractValidationError(code, path)


def _unique(rows, field, path):
    values = [row[field] for row in rows]
    _require(len(values) == len(set(values)), "duplicate_" + field, path)


def _relations(name, value, path):
    if name == "AdapterResult":
        _unique(value["missing_requirements"], "requirement_id", _pointer(path, "missing_requirements"))


def _walk(schema, value, validator, path=""):
    if "$ref" in schema:
        name = schema["$ref"][8:]
        _relations(name, value, path)
        _walk(_DEFINITIONS[name], value, validator, path)
        return
    if schema.get("pattern") == "^(|/.*)$":
        _require(re.search(r"~(?![01])", value) is None, "invalid_json_pointer", path)
    for keyword in ("oneOf", "anyOf", "allOf"):
        for branch in schema.get(keyword, []):
            if validator.evolve(schema=branch).is_valid(value):
                _walk(branch, value, validator, path)
    if type(value) is dict:
        for key, child in value.items():
            child_schema = schema.get("properties", {}).get(key, schema.get("additionalProperties"))
            if type(child_schema) is dict:
                _walk(child_schema, child, validator, _pointer(path, key))
    elif type(value) is list:
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(value):
            child_schema = prefix[index] if index < len(prefix) else schema.get("items")
            if type(child_schema) is dict:
                _walk(child_schema, child, validator, _pointer(path, index))


def validate_contract(name: str, value: object):
    """Validate plain finite JSON plus pure relationships; return a fresh copy."""
    schema = contract_schema(name)
    try:
        _finite_json(value)
        key = _validation_key(schema, value)
        if _already_validated(key):
            return deepcopy(value)
        validator = _Validator(schema)
        error = next(validator.iter_errors(value), None)
        if error is not None:
            path = ""
            for token in error.absolute_path:
                path = _pointer(path, token)
            raise ContractValidationError("contract_shape_invalid", path, contract=name)
        _walk(schema, value, validator)
        _remember_validated(key)
        return deepcopy(value)
    except RecursionError as error:
        raise ContractValidationError("json_nesting_too_deep") from error


