"""Store-free, one-attempt MUSCLE invocation over an exact supplied FASTA File.

The ordinary owner authenticates action/admission/runtime selection. This leaf
copies bytes and declares actual files; it does not parse an alignment, calculate
conservation, publish a Source or establish complete intended row membership.
"""
from __future__ import annotations
from copy import deepcopy
PERMUTATIONS = ('none', 'abc', 'acb', 'bca')
NATIVE_UNSIGNED_MAX = 4294967295

def _require(condition, code):
    if not condition:
        raise ValueError('muscle_alignment_' + code)

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields.split()), code)

def validate_muscle_alignment_parameters(value):
    """Validate explicit native unsigned parameters; infer no defaults."""
    _closed(value, 'threads randseed perturb perm consiters refineiters', 'parameters_invalid')
    for key in ('threads', 'randseed', 'perturb', 'consiters', 'refineiters'):
        _require(type(value[key]) is int and (1 if key in ('threads', 'randseed') else 0) <= value[key] <= NATIVE_UNSIGNED_MAX, 'parameter_invalid_' + key)
    _require(type(value['perm']) is str and value['perm'] in PERMUTATIONS, 'parameter_invalid_perm')
    return deepcopy(value)
