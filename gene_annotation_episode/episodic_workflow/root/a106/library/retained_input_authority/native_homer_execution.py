"""One selected ordinary HOMER reservation and non-cancelling observation.

The authenticated caller owns the action lease and received-input authority.
This module owns no Source, receipt, grant, episode or scientific calculator.
Closed metadata validators do not inspect a current deployment or workspace.
"""
import re
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_flux_balance_storage import decode_json

def _require(condition, code):
    if not condition:
        raise ValueError('ordinary_homer_' + code)

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)

def _copy(value):
    return decode_json(canonical(value).encode('utf-8'))

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def validate_homer_arguments(value):
    value = _copy(value)
    _closed(value, ('window_bp', 'motif_lengths', 'num_motifs', 'threads', 'strand', 'statistic', 'normalization', 'motif_set'), 'arguments_fields_invalid')
    lengths = value['motif_lengths']
    _require(_integer(value['window_bp'], 1) and type(lengths) is list and bool(lengths) and all((_integer(n, 1) for n in lengths)) and (len(set(lengths)) == len(lengths)) and _integer(value['num_motifs']) and _integer(value['threads'], 1) and (value['strand'] in ('both', 'forward')) and (value['statistic'] in ('binomial', 'hypergeometric')), 'arguments_invalid')
    norm = value['normalization']
    _closed(norm, ('composition', 'oligo_length', 'max_iterations', 'neutral'), 'normalization_invalid')
    _require(norm['composition'] in ('gc', 'cpg', 'none') and _integer(norm['oligo_length']) and _integer(norm['max_iterations'], 1) and (type(norm['neutral']) is bool), 'normalization_invalid')
    _require(type(value['motif_set']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', value['motif_set']) is not None, 'motif_set_invalid')
    return value
