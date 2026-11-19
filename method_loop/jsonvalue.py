"""The one implementation of canonical JSON, closed copies and JSON equality for the method and its consumers."""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json


def canonical(value):
    """Finite JSON text with string keys, sorted and compact, without coercing an unsupported value."""
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


def content_digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def closed_copy(value, what, error):
    """A plain JSON copy of ``value``; ``error(what + '_must_be_closed_json')`` is raised when it is not JSON."""
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError) as cause:
        raise error(what + '_must_be_closed_json') from cause


def same_json(left, right):
    """Equal JSON values; a number equals the same number whatever its JSON spelling (6 and 6.0), a boolean
    never equals a number, tuples and lists compare alike."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(same_json(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


__all__ = ['canonical', 'closed_copy', 'content_digest', 'same_json']
