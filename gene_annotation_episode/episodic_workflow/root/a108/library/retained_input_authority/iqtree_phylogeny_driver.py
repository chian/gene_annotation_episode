"""Store-free IQ-TREE LG/UFBoot invocation over an exact aligned FASTA File.

The ordinary owner selects and authenticates the supplied-alignment or explicit
MUSCLE-to-IQ-TREE route. This leaf receives the actual aligned File for either
route. It neither aligns sequences nor substitutes an inference algorithm.
"""
from __future__ import annotations
from copy import deepcopy
INT_MAX = 2147483647

def _require(condition, code):
    if not condition:
        raise ValueError('iqtree_phylogeny_' + code)

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields.split()), code)

def validate_iqtree_parameters(value):
    """The selected model and bootstrap method have no inferred alternatives."""
    _closed(value, 'model bootstrap_replicates threads seed', 'parameters_invalid')
    _require(type(value['model']) is str and value['model'] == 'LG', 'model_invalid')
    _require(type(value['bootstrap_replicates']) is int and value['bootstrap_replicates'] == 1000, 'bootstrap_replicates_invalid')
    for name in ('threads', 'seed'):
        _require(type(value[name]) is int and 1 <= value[name] <= INT_MAX, 'parameter_invalid_' + name)
    return deepcopy(value)
