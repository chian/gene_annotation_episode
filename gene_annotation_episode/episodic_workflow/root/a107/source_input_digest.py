"""Private A107 source input metadata digest."""
import hashlib
import json
import math
from copy import deepcopy

def _require(condition):
    if not condition:
        raise ValueError("molecular_sequence_received_input_invalid")


def _copy(value):
    def check(item):
        kind = type(item)
        if kind is str:
            item.encode("utf-8"); return
        if item is None or kind in (int, bool): return
        if kind is float:
            _require(math.isfinite(item)); return
        if kind is list:
            for child in item: check(child)
            return
        if kind is dict:
            for key, child in item.items():
                _require(type(key) is str); check(key); check(child)
            return
        _require(False)
    try:
        check(value)
        return deepcopy(value)
    except (UnicodeError, RecursionError) as error:
        raise ValueError("molecular_sequence_received_input_invalid") from error


def input_record_digest(value):
    value = _copy(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


