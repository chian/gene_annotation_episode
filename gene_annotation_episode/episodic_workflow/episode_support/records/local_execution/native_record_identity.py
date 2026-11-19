"""Private original finite native record encoding and identity."""
import hashlib
import json
import math

def finite_json_copy(value):
    def check(item):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise ValueError('native_infernal_finite_json_required')
    check(value)
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))

def native_record_digest(value):
    return hashlib.sha256(json.dumps(finite_json_copy(value), sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

