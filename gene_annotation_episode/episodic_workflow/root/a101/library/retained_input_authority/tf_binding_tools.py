"""Ordinary supplied-input TF actions and immutable retained publications.

The existing molecular worker owns execution. This adapter owns the selected
action's admissions, private native capture and Source-only publication. Native
scoring and retained numerical calculation remain in their existing workers.
"""
from copy import deepcopy
import json
import re
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority import tf_binding_measurements as core
_SOURCE = re.compile('^source_[0-9a-f]{24,64}$')
_ARTIFACT = re.compile('^artifact_[0-9a-f]{64}$')
_FORMATS = {'dna': ('fasta', 'raw_dna'), 'matrix': ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')}

def _require(condition, code):
    if not condition:
        raise ContractError('tf_binding_' + code)

def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'fields_invalid')

def _copy(value):
    return json.loads(canonical(value))

def _result_selection(value):
    _closed(value, 'scope scan_ids raw_threshold offset limit')
    _require(value['scope'] in ('all_retained_scans', 'selected_scan_ids'), 'selection_scope_invalid')
    _require(value['scan_ids'] is None if value['scope'] == 'all_retained_scans' else type(value['scan_ids']) is list, 'selection_scope_invalid')
    core.validate_tf_binding_selection(dict(version='tf_binding_selection_v1', scan_ids=[] if value['scan_ids'] is None else value['scan_ids'], **{key: deepcopy(value[key]) for key in ('raw_threshold', 'offset', 'limit')}))
    return _copy(value)

def _arguments(value):
    value = _copy(value)
    _require(type(value) is dict, 'arguments_invalid')
    if value.get('mode') == 'run_native':
        _closed(value, 'mode inputs scan_selection parameters selection')
        _require(type(value['inputs']) is list and bool(value['inputs']), 'inputs_invalid')
        seen, roles = (set(), set())
        for item in value['inputs']:
            _closed(item, 'input_id role format namespace reference')
            _require(type(item['input_id']) is str and bool(item['input_id']) and (item['input_id'] not in seen) and (item['role'] in _FORMATS) and (item['format'] in _FORMATS[item['role']]), 'inputs_invalid')
            pattern = _ARTIFACT if item['namespace'] == 'artifact' else _SOURCE if item['namespace'] == 'source' else None
            _require(pattern is not None and type(item['reference']) is str and (pattern.fullmatch(item['reference']) is not None), 'inputs_invalid')
            seen.add(item['input_id'])
            roles.add(item['role'])
        _require(roles == set(_FORMATS), 'dna_and_matrix_inputs_required')
        core._selection(deepcopy(value['scan_selection']))
        core._parameters(deepcopy(value['parameters']))
        _result_selection(value['selection'])
    else:
        _require(value.get('mode') in ('read_stored', 'calculate_saved'), 'mode_invalid')
        _closed(value, 'mode result_ref' if value['mode'] == 'read_stored' else 'mode result_ref selection')
        _require(type(value['result_ref']) is str and _SOURCE.fullmatch(value['result_ref']), 'source_required')
        if value['mode'] == 'calculate_saved':
            _result_selection(value['selection'])
    return value
