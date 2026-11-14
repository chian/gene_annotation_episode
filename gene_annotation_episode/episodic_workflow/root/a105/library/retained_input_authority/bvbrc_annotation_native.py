"""Pure observations from a selected BV-BRC genome-annotation artifact.

The AppService host authenticates the task, response, ContentBinding and actual
bytes before this reader is called. A self-consistent descriptor here is not
custody. The reversible JSON document preserves native members, number tokens,
occurrences and unknown fields. This is not a gene caller or an annotation
confidence model. In particular, GTO features are never recast as Prodigal calls.

GTO locations are ordered [contig, begin, strand, length] tuples. Begin is
one-based and directional; checked intervals below are zero-based half-open.
Native viral producers can serialize begin as a digit string. Split and
multicontig locations remain separate, in their original order. Quality and
analysis-event fields remain native observations with no universal score or
truncation interpretation.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import re
MAX_NATIVE_DEPTH = 32
_CONTENT_KEYS = {'source_ref', 'artifact_field', 'artifact_ref', 'sha256', 'byte_count'}

def _require(condition, code='bvbrc_annotation_document_invalid'):
    if not condition:
        raise ValueError(code)

def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def _finite_json(value, active=None):
    active = set() if active is None else active
    kind = type(value)
    if value is None or kind in {bool, int}:
        return
    if kind is str:
        value.encode('utf-8')
        return
    if kind is float:
        _require(math.isfinite(value))
        return
    _require(kind in {dict, list} and id(value) not in active)
    active.add(id(value))
    try:
        if kind is dict:
            _require(all((type(key) is str for key in value)))
            for key, item in value.items():
                key.encode('utf-8')
                _finite_json(item, active)
        else:
            for item in value:
                _finite_json(item, active)
    finally:
        active.remove(id(value))

def _content(value):
    _require(type(value) is dict and set(value) == _CONTENT_KEYS, 'bvbrc_annotation_content_invalid')
    _require(type(value['source_ref']) is str and re.fullmatch('source_[a-f0-9]{24,64}', value['source_ref']) is not None and (value['artifact_field'] == 'artifact_ref') and (type(value['sha256']) is str) and (re.fullmatch('[a-f0-9]{64}', value['sha256']) is not None) and (value['artifact_ref'] == 'artifact_' + value['sha256']) and (type(value['byte_count']) is int) and (value['byte_count'] >= 0), 'bvbrc_annotation_content_invalid')
    return deepcopy(value)
