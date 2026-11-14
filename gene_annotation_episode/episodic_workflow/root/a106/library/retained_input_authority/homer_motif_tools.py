"""Ordinary HOMER actions and immutable Source-only retained views.

Native execution, numerical calculation and publication have distinct owners.
Reading an admitted result authenticates its original action and literal packet;
it neither repeats the calculation nor opens the original deployment or inputs.
"""
import json
import re
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.homer_motif_contracts import OPERATION, validate_homer_selector
TOOL = OPERATION
_SOURCE = re.compile('^source_[0-9a-f]{24,64}$')
_ARTIFACT = re.compile('^artifact_[0-9a-f]{64}$')
_INPUTS = (('target_bed', 'bed'), ('reference_fasta', 'fasta'), ('background_bed', 'bed'))

def _require(condition, code):
    if not condition:
        raise ContractError('homer_motif_' + code)

def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'fields_invalid')

def _copy(value):
    return json.loads(canonical(value))

def _native():
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import native_homer_execution
    return native_homer_execution

def _initial_selection(value):
    _closed(value, 'series offset limit')
    _require(type(value['series']) is list and type(value['offset']) is int and (value['offset'] >= 0) and (type(value['limit']) is int) and (value['limit'] >= 0), 'selection_invalid')
    seen = set()
    for item in value['series']:
        _require(type(item) is dict, 'selection_invalid')
        if item.get('role') == 'denovo_pwm':
            _closed(item, 'role motif_length')
            _require(type(item['motif_length']) is int and item['motif_length'] >= 1, 'selection_invalid')
        else:
            _closed(item, 'role')
            _require(item['role'] in ('known_results', 'denovo_combined_pwm', 'denovo_nonredundant_pwm'), 'selection_invalid')
        key = canonical(item)
        _require(key not in seen, 'selection_invalid')
        seen.add(key)
    return _copy(value)

def _arguments(value):
    value = _copy(value)
    _require(type(value) is dict, 'arguments_invalid')
    mode = value.get('mode')
    if mode == 'run_native':
        _closed(value, 'mode inputs parameters selection')
        _require(type(value['inputs']) is list and len(value['inputs']) == 3, 'inputs_invalid')
        for item, (role, _) in zip(value['inputs'], _INPUTS):
            _closed(item, 'role namespace reference')
            pattern = _ARTIFACT if item['namespace'] == 'artifact' else _SOURCE if item['namespace'] == 'source' else None
            _require(item['role'] == role and pattern is not None and (type(item['reference']) is str) and (pattern.fullmatch(item['reference']) is not None), 'inputs_invalid')
        _native().validate_homer_arguments(value['parameters'])
        _initial_selection(value['selection'])
        _require(all((item.get('role') != 'denovo_pwm' or item['motif_length'] in value['parameters']['motif_lengths'] for item in value['selection']['series'])), 'unrequested_motif_length')
    else:
        _require(mode in ('read_stored', 'calculate_saved'), 'mode_invalid')
        _closed(value, 'mode result_ref' if mode == 'read_stored' else 'mode result_ref selector')
        _require(type(value['result_ref']) is str and _SOURCE.fullmatch(value['result_ref']), 'source_required')
        if mode == 'calculate_saved':
            validate_homer_selector(value['selector'])
    return value

def homer_capture_reference_restriction(store, context, reference, namespace):
    """Classify only a real ordinary producer's private capture; grant nothing."""
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.molecular_reference_privacy import molecular_capture_reference_restriction
    return molecular_capture_reference_restriction(store, context, reference, namespace, provider=TOOL)
