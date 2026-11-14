"""Exact original Mapping-aware JSON and digest primitives for Root workers.

The existing record_values plain definer is reused. Historical public names
import these same functions; no schema, communication or episode module is
needed to serialize a worker record.
"""
import hashlib
import json
from .record_values import plain


def canonical(value):
    return json.dumps(plain(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

