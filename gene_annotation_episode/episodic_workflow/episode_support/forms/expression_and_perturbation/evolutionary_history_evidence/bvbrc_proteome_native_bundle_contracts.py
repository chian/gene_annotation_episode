"""Closed pure contracts for retained GenomeComparison provider construction.

These validators check saved shapes, copies, identities and source relationships.
They never parse input bytes, reconstruct joins/sheets, calculate scores, project
facts, or establish custody. The execution host authenticates retained artifacts.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.evolutionary_history_evidence.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_data_contracts import ProteomeDataError, _plain, _Validator, validate_proteome_data
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_native_contracts import NativeValidationError, validate_native_projection
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.bvbrc_proteome_native_parameter_contracts import _FAILURES, BINDING_DETAILS, BINDING_CODES, ProteomeNativeBundleError, _require, _DOCUMENT, _schema
BINDING_INPUT_KINDS = {code: details[0] for code, details in BINDING_DETAILS.items()}
PURE_REQUIRED_INPUT_KINDS = {'complete_artifact_bytes': 'output_bytes', 'exact_input_fasta': 'input_bytes', 'identifier_mapping': 'scientific_metadata', 'complete_input_membership': 'scientific_metadata', 'producer_manifest': 'task_manifest', 'directional_blast_report': 'output_bytes', 'feature_metadata': 'scientific_metadata', 'genome_metadata': 'scientific_metadata', 'coordinate_convention': 'scientific_metadata', 'native_producer_version': 'byte_version_evidence', 'requested_calculation_field': 'parser_binding', 'complete_bytes': 'input_bytes', 'original_parameters': 'original_task', 'exact_executed_fasta': 'input_bytes', 'execution_input_witness': 'task_manifest', 'complete_membership': 'scientific_metadata', 'occurrence_mapping': 'byte_version_evidence', 'feature_sequence': 'scientific_metadata', 'representation_correspondence': 'scientific_metadata', 'directional_report': 'output_bytes', 'producer_execution_facts': 'task_manifest', 'valid_parameters': 'parser_binding', 'valid_saved_sheet': 'parser_binding'}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def _pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')

def _error_path(error):
    if hasattr(error, 'path'):
        return error.path
    return error.diagnostics[0]['path'] if hasattr(error, 'diagnostics') else ''
_PURE_CODES = frozenset(_DOCUMENT['$defs']['SheetPReason']['enum']) | frozenset(_DOCUMENT['$defs']['NativeDiagnostic']['properties']['code']['enum'])

@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))

def validate_shape(name, value, *, code='parameters_invalid', path=''):
    try:
        _plain(value)
        canonical(value).encode('utf-8')
        error = next(_validator(name).iter_errors(value), None)
        if error is not None:
            location = path
            for token in error.absolute_path:
                location = _pointer(location, token)
            raise ProteomeNativeBundleError('proteome_' + code, location)
    except (ProteomeDataError, RecursionError, UnicodeError, ValueError) as error:
        if isinstance(error, ProteomeNativeBundleError):
            raise
        raise ProteomeNativeBundleError('proteome_' + code, path + getattr(error, 'path', '')) from error
    return deepcopy(value)

def _checked(function, name, value, code, path):
    try:
        return function(name, value)
    except (ContractValidationError, ProteomeDataError, NativeValidationError) as error:
        raise ProteomeNativeBundleError('proteome_' + code, path + _error_path(error)) from error

def validate_supplied_data(value: dict) -> dict:
    """Validate the selected closed operand description, retaining no authority."""
    result = validate_shape('SuppliedData', value, code='supplied_data_invalid')
    inventories, snapshots = (set(), set())
    for name in ('inventories', 'feature_snapshots', 'genome_snapshots', 'sequence_snapshots'):
        key = 'inventory_key' if name == 'inventories' else 'snapshot_key'
        seen = inventories if name == 'inventories' else snapshots
        for index, row in enumerate(result[name]):
            _require(row[key] not in seen, 'supplied_data_ambiguous', f'/{name}/{index}/{key}')
            seen.add(row[key])
    return result
_RESULTS = {'native_document': ('native_results', 'NativeProjectionResult'), 'original_input_index': ('input_index_result', 'InputIndexResult'), 'inventory': ('inventory_results', 'ProteinInventoryResult'), 'feature_snapshot': ('feature_results', 'FeatureSnapshotResult'), 'genome_snapshot': ('genome_results', 'GenomeSnapshotResult'), 'sequence_snapshot': ('sequence_results', 'FeatureSequenceSnapshotResult')}
_SELECTIONS = {'inventory': 'inventories', 'feature_snapshot': 'feature_snapshots', 'genome_snapshot': 'genome_snapshots', 'sequence_snapshot': 'sequence_snapshots'}
_SUBMITTED_PARAMETER_POINTER = '/prepared/native_operands/call/rpc_request/params/1'

def _selected_data(saved):
    evidence = saved['parameters']['supplied_data_evidence']
    if evidence is None:
        return None
    rows = [row for row in saved['supplied_values'] if row['evidence'] == evidence]
    if len(rows) != 1:
        return None
    try:
        return validate_supplied_data(rows[0]['value'])
    except ProteomeNativeBundleError:
        return None

def _at(value, pointer):
    current = value
    for token in pointer.lstrip('/').split('/') if pointer else []:
        token = token.replace('~1', '/').replace('~0', '~')
        if type(current) is dict and token in current:
            current = current[token]
        elif type(current) is list and re.fullmatch('0|[1-9][0-9]*', token) and (int(token) < len(current)):
            current = current[int(token)]
        else:
            raise ProteomeNativeBundleError('proteome_saved_identity_conflict', pointer)
    return current

def _index_task(saved):
    result = saved['input_index_result']
    if result is None or result['value'] is None:
        return
    index, task = (result['value'], saved['original_task'])
    source = index['parameter_source']
    if source['kind'] == 'effective':
        effective = task['effective_parameters']
        _require(effective is not None, 'saved_identity_conflict', '/original_task/effective_parameters')
        evidence = effective['evidence']
        field = source['source_field']
        _require((field['source_ref'], field['sha256'], field['pointer']) == (evidence['content']['source_ref'], evidence['content']['sha256'], evidence['pointer']), 'saved_identity_conflict', '/input_index_result/value/parameter_source')
        parameters = effective['value']
    else:
        _require(source['source_field']['source_ref'] == task['submission_source_ref'] and source['source_field']['pointer'] == _SUBMITTED_PARAMETER_POINTER, 'saved_identity_conflict', '/input_index_result/value/parameter_source')
        parameters = task['submitted_parameters']
    _require(parameters.get('reference_genome_index') == index['reference_original_index'], 'saved_identity_conflict', '/input_index_result/value/reference_original_index')
    for entry in index['inputs']:
        _require(canonical(_at(parameters, entry['parameter_pointer'])) == canonical(entry['value']), 'saved_identity_conflict', '/input_index_result/value/inputs')
    for snapshot in index['run_parameter_snapshots']:
        original = task['submitted_parameters'] if snapshot['kind'] == 'submitted' else task['effective_parameters']['value'] if task['effective_parameters'] is not None else None
        _require(original is not None, 'saved_identity_conflict', '/input_index_result/value/run_parameter_snapshots')
        if snapshot['kind'] == 'submitted':
            field = snapshot['source_field']
            _require(field['source_ref'] == task['submission_source_ref'] and field['pointer'] == _SUBMITTED_PARAMETER_POINTER, 'saved_identity_conflict', '/input_index_result/value/run_parameter_snapshots')
        for name in ('min_ident', 'min_seq_cov', 'min_positives', 'max_e_val'):
            cell = snapshot[name]
            if cell['presence'] == 'value':
                _require(name in original and canonical(original[name]) == canonical(cell['value']), 'saved_identity_conflict', '/input_index_result/value/run_parameter_snapshots')
            elif cell['presence'] == 'omitted':
                _require(name not in original, 'saved_identity_conflict', '/input_index_result/value/run_parameter_snapshots')
            elif cell['presence'] == 'explicit_null':
                _require(name in original and original[name] is None, 'saved_identity_conflict', '/input_index_result/value/run_parameter_snapshots')

def _validate_result(name, result, path):
    if name == 'NativeProjectionResult':
        validate_shape('NativeNativeProjectionResult', result, code='saved_sheet_invalid', path=path)
        _require((result['status'] == 'invalid') == (result['value'] is None), 'saved_sheet_invalid', path)
        _require(result['status'] != 'ok' or not any((d['severity'] == 'error' for d in result['diagnostics'])), 'saved_sheet_invalid', path)
        if result['value'] is not None:
            try:
                validate_native_projection(result['value'])
            except NativeValidationError as error:
                raise ProteomeNativeBundleError('proteome_saved_sheet_invalid', path + '/value' + error.path) from error
    else:
        _checked(validate_proteome_data, name, result, 'saved_sheet_invalid', path)

def _validate_resolution(saved, supplied):
    outcomes = saved['input_resolution']
    seen, accounted = (set(), {name: set() for name, _ in _RESULTS.values()})
    for i, row in enumerate(outcomes):
        path = f'/input_resolution/{i}'
        kind, selection_index = (row['selector_kind'], row['selection_index'])
        _require((kind, selection_index) not in seen, 'saved_identity_conflict', path)
        seen.add((kind, selection_index))
        _require(len(row['requirement_ids']) == len(set(row['requirement_ids'])), 'saved_identity_conflict', path)
        _require(set(row['requirement_ids']) <= {r['requirement_id'] for r in saved['requirements']}, 'saved_sheet_invalid', path)
        if kind == 'native_document':
            choices = saved['parameters']['native_documents']
        elif kind == 'original_input_index':
            choices = [supplied['original_input_index']] if supplied is not None and supplied['original_input_index'] is not None else []
        else:
            choices = supplied[_SELECTIONS[kind]] if supplied is not None else []
        _require(selection_index < len(choices), 'saved_sheet_invalid', path)
        choice = choices[selection_index]
        name, _ = _RESULTS[kind]
        index = row['result_index']
        if index is None:
            _require(row['state'] not in {'resolved', 'partial'}, 'saved_sheet_invalid', path)
            _require(bool(row['requirement_ids']), 'saved_sheet_invalid', path + '/requirement_ids')
            continue
        results = ([saved[name]] if saved[name] is not None else []) if kind == 'original_input_index' else saved[name]
        _require(index < len(results) and index not in accounted[name], 'saved_identity_conflict', path)
        accounted[name].add(index)
        result, value = (results[index], results[index]['value'])
        _require(row['state'] == ('invalid' if value is None else 'resolved' if result['status'] == 'ok' else 'partial'), 'saved_sheet_invalid', path)
        if value is None:
            continue
        if kind == 'native_document':
            binding = value['source']['content']
            _require(choice['declared_format']['format'] == value['format'] and choice['source_contract'] == value['source_contract'], 'saved_identity_conflict', path)
            if 'source_ref' in choice:
                _require(choice['source_ref'] == binding['source_ref'] and choice['raw_artifact_ref'] == binding['artifact_ref'], 'saved_identity_conflict', path)
            _require(choice['declared_format']['version'] is None and choice['declared_format']['mode'] is None and (value['source_contract']['deployment_match'] == 'unobserved'), 'saved_identity_conflict', path)
        elif kind == 'original_input_index':
            _require(choice['mode'] == 'construct' and value['parameter_source'] == choice['parameter_source'], 'saved_identity_conflict', path)
            if value['parameter_source']['kind'] == 'submitted':
                field, content = (value['parameter_source']['source_field'], row['content'])
                _require(content is not None and content['artifact_field'] == 'request_ref' and (content['artifact_ref'] == 'artifact_' + content['sha256']) and ((content['source_ref'], content['sha256']) == (field['source_ref'], field['sha256'])), 'saved_identity_conflict', path + '/content')
            continue
        else:
            key = 'inventory_key' if kind == 'inventory' else 'snapshot_key'
            _require(choice['mode'] == 'raw' and value[key] == choice[key] and (value['format'] == choice['declared_format']), 'saved_identity_conflict', path)
            binding = value['source']['content']
            source = choice['source']
            if source['kind'] == 'supplied_snapshot':
                _require(binding == source['content'] and value['source']['body_complete'] is True and (value['source']['object_complete'] == 'unknown'), 'saved_identity_conflict', path)
            elif source['kind'] == 'acquired_artifact':
                _require((source['source_ref'], source['raw_artifact_ref']) == (binding['source_ref'], binding['artifact_ref']), 'saved_identity_conflict', path)
            else:
                _require(value['source']['body_complete'] is True and value['source']['object_complete'] == 'yes', 'saved_identity_conflict', path)
        _require(row['content'] == binding, 'saved_identity_conflict', path + '/content')
    for kind, (name, _) in _RESULTS.items():
        results = ([saved[name]] if saved[name] is not None else []) if kind == 'original_input_index' else saved[name]
        _require(accounted[name] == set(range(len(results))), 'saved_sheet_invalid', '/' + name)
    _require({index for kind, index in seen if kind == 'native_document'} == set(range(len(saved['parameters']['native_documents']))), 'saved_sheet_invalid', '/input_resolution')

__all__ = ['ProteomeNativeBundleError', 'BINDING_CODES', 'BINDING_INPUT_KINDS', 'PURE_REQUIRED_INPUT_KINDS', 'validate_supplied_data']
