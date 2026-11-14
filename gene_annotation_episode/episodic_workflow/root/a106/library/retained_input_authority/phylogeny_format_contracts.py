"""Pure validators for the frozen phylogeny stored-format contracts.

Validation does not authenticate custody or read source bytes. The byte readers
check their supplied digests. These checks establish closed shapes, native
token/value consistency and internal references for saved-object calculations.
The returned object is detached; callers' objects are never modified.
"""
from __future__ import annotations
import re
_LOCATION_KEYS = frozenset({'artifact', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive', 'xml_path'})

def _fail(code):
    raise ValueError('phylogeny_' + code)

def _shape(value, keys, code):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)

def _text(value, *, nonempty=False):
    return type(value) is str and (bool(value) or not nonempty)

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def _artifact(value):
    _shape(value, {'raw_artifact_ref', 'source_ref', 'sha256'}, 'artifact_invalid')
    if not _text(value['raw_artifact_ref'], nonempty=True) or not _text(value['source_ref'], nonempty=True) or (not _text(value['sha256'])) or (re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        _fail('artifact_invalid')

def _location(value, *, artifact=None):
    _shape(value, _LOCATION_KEYS, 'source_location_invalid')
    _artifact(value['artifact'])
    if artifact is not None and value['artifact'] != artifact:
        _fail('source_artifact_conflict')
    present = False
    for start, end, minimum in (('byte_start_0based', 'byte_end_0based_exclusive', 0), ('line_start_1based', 'line_end_1based_inclusive', 1)):
        a, b = (value[start], value[end])
        if a is None and b is None:
            continue
        if not _integer(a, minimum) or not _integer(b, minimum) or b < a:
            _fail('source_location_invalid')
        present = True
    path = value['xml_path']
    if path is not None:
        if not _text(path, nonempty=True) or not path.startswith('/'):
            _fail('source_location_invalid')
        present = True
    if not present:
        _fail('source_location_missing')
