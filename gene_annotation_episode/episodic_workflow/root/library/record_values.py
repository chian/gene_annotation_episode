"""Original JSON conversion and identity functions private to root orchestration."""
from collections.abc import Mapping
from typing import Any
import hashlib
import json


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(kind: str, value: Any) -> str:
    return kind + "_" + hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


def finite_canonical(value):
    """Finite JSON with string keys, without coercing an unsupported value."""
    def plain(item):
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("JSON record keys must be strings")
            return {key: plain(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(child) for child in item]
        if item is None or type(item) in (str, bool, int, float):
            return item
        raise ValueError("record must contain finite JSON values")
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


