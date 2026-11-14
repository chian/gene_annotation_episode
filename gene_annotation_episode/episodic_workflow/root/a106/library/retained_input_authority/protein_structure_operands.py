"""Read-only original operands for selected protein structure operations.

Received authority belongs to NativeProteinStructureReturns and the original
result host. This adapter checks the exact retained sequence, map, traceback,
sheet and transform relationships. It never acquires, aligns, fits, publishes,
stages, dispatches work or awards credit.
"""
from __future__ import annotations
from copy import deepcopy
import math
import sqlite3
from typing import get_args
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.alignment_site_native import immutable_record
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError, RECORD_SCHEMAS
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_acquisition import decode_protein_structure_json, retained_protein_structure_file
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_contracts import validate_protein_structure_request
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import protein_structure_contracts as a
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_calculations import validate_recorded_protein_structure_components
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_result_views import validate_protein_structure_projection_result, validate_protein_structure_projection_rows
_SUBJECTS = frozenset({'input', 'read_subject', 'feature', 'product', 'reference'})
_FAMILY = 'native_protein_structure_bundle_v1'
_CODES = frozenset(get_args(a.IssueCode))
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, v: type(v) is int).redefine('number', lambda _, v: type(v) in (int, float) and math.isfinite(v)))
_RECORD_VALIDATORS = {kind: _STRICT(RECORD_SCHEMAS[kind]) for kind in ('feature', 'product', 'reference', 'source', 'observation')}

def _fail(code, *, stage='authority', field='descriptor', role=None, artifact_role=None):
    raise ProteinStructureOperandError(a.issue(code, stage=stage, field=field, role=role, artifact_role=artifact_role))

def _require(condition, code='conflicting_identity', **where):
    if not condition:
        _fail(code, **where)

def _checked(function, *args, stage='authority', field='descriptor', code=None, artifact_role=None, **kwargs):
    """Translate only declared data failures; do not hide programming failures."""
    try:
        return function(*args, **kwargs)
    except ProteinStructureOperandError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
        name = code or (str(error) if str(error) in _CODES else 'invalid_schema')
        _fail(name, stage=stage, field=field, artifact_role=artifact_role)

def _authority(function, *args, code='original_commission_mismatch', field='receipt', **kwargs):
    try:
        return function(*args, **kwargs)
    except ProteinStructureOperandError:
        raise
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        _fail(code, field=field)

def _binding(store, context, returns):
    _require(returns is not None and getattr(returns, 'store', None) is store and (getattr(returns, 'run_id', None) == context.run_id), 'original_commission_mismatch', field='receipt')
    _authority(returns.authenticate, context, allow_unsaved=True)

def _payload(record):
    return {key: value for key, value in record.items() if key not in {'id', 'record_type', 'origin'}}

def _record(store, reference, kinds, *, field='descriptor'):
    try:
        record = store.get(reference)
    except (ContractError, KeyError, TypeError, ValueError):
        _fail('conflicting_identity', field=field)
    _require(type(record) is dict and record.get('id') == reference and (record.get('record_type') in kinds), field=field)
    kind = record['record_type']
    if kind in _RECORD_VALIDATORS:
        _checked(lambda value: _require(_RECORD_VALIDATORS[kind].is_valid(value), 'invalid_schema', field=field), _payload(record), field=field)
        _checked(immutable_record, record, code='conflicting_identity', field=field)
    return record

def is_protein_structure_sequence_operand(store, reference_ref: str) -> bool:
    """Classify only immutable typed sequence ancestry, without granting use.

    Iterative DFS validates every parent (even after finding protected material).
    Completed DAG nodes are reusable; an active node is a contradictory cycle.
    Input/read_subject leaves retain their ordinary validation at the tool.
    """
    _require(type(reference_ref) is str, 'invalid_schema')
    active, completed = (set(), {})
    stack = [(reference_ref, False, None)]
    while stack:
        reference, leaving, edges = stack.pop()
        if leaving:
            completed[reference] = any((completed[parent] for parent in edges))
            active.remove(reference)
            continue
        if reference in completed:
            continue
        _require(reference not in active)
        record = _record(store, reference, _SUBJECTS)
        kind = record['record_type']
        if kind in {'input', 'read_subject'}:
            completed[reference] = False
        elif kind == 'reference':
            source = _record(store, record['source_ref'], {'source'})
            completed[reference] = source['provider'] == 'episode.execution_result' and source['version'] == _FAMILY
        else:
            edges = [record['subject_ref']] if kind == 'feature' else record['parent_refs']
            active.add(reference)
            stack.append((reference, True, edges))
            stack.extend(((parent, False, None) for parent in reversed(edges)))
    return completed[reference_ref]

def _file(store, identity, *, format=None, role=None):
    identity = _checked(a.validate_file_identity, identity, stage='input', field='file_identity', artifact_role=role)
    _require(format is None or identity['format'] == format, 'unsupported_format', stage='input', field='file_identity', artifact_role=role)
    return _checked(retained_protein_structure_file, store, identity, stage='input', field='file_identity', artifact_role=role)

def _bytes(store, identity, *, format=None, role=None):
    path = _file(store, identity, format=format, role=role)
    try:
        raw = path.read_bytes()
    except OSError:
        _fail('retained_artifact_missing', stage='input', field='file_identity', artifact_role=role)
    import hashlib
    _require(len(raw) == identity['byte_length'] and hashlib.sha256(raw).hexdigest() == identity['sha256'], 'input_digest_mismatch', stage='input', field='file_identity', artifact_role=role)
    return raw

def _json_file(store, identity, *, format=None, role=None, canonical_bytes=True, stage='input', field='file_identity', code=None):
    raw = _bytes(store, identity, format=format, role=role)
    return _checked(decode_protein_structure_json, raw, canonical_bytes=canonical_bytes, stage=stage, field=field, code=code, artifact_role=role)

def _source(store, custody):
    if custody.get('version') == 'protein_structure_action_custody_v1':
        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_action_records import SAVED_ACTION_SOURCE_VERSION
        _checked(a.validate_protein_structure_action_custody, custody)
        source = _record(store, custody['source_ref'], {'source'})
        _require(source['origin'] == 'tool' and source['provider'] == 'episode.execution_result' and (source['version'] in {_FAMILY, SAVED_ACTION_SOURCE_VERSION}))
        return source
    source = _record(store, custody['source_ref'], {'source'})
    _require(source['origin'] == 'tool' and source['provider'] == 'episode.execution_result' and (source['version'] == _FAMILY) and (source['artifact_ref'] == custody['bundle_artifact_ref']))
    return source

def _saved_sheet(store, context, descriptor, *, returns, before_decision_index=None):
    descriptor = _checked(a.validate_saved_sheet_descriptor, descriptor)
    original = _authority(returns.authenticate_received_saved_sheet, context, descriptor, required_use=descriptor['allowed_uses'][0], code='saved_sheet_not_received', field='descriptor', **{} if before_decision_index is None else {'before_decision_index': before_decision_index})
    _source(store, descriptor['custody'])
    _require(a.same(original['custody'], descriptor['custody']) and a.same(original['sheet_file'], descriptor['sheet_file']) and a.same(original['original_components_file'], descriptor['original_components_file']), 'original_commission_mismatch', field='receipt')
    request = _checked(validate_protein_structure_request, original['request'], field='request')
    _require(request['operation'] == 'compare', 'original_commission_mismatch', field='request')
    sheet = _checked(a.validate_protein_structure_sheet, _json_file(store, descriptor['sheet_file'], format='protein_structure_comparison_sheet_v1'), field='request')
    components = _json_file(store, descriptor['original_components_file'], format='protein_structure_components_v1')
    _require(sheet['native_baseline'] is not None and a.same(components, sheet['native_baseline']) and a.same(components.get('parameters'), sheet['native_request']) and (descriptor['original_mode'] == sheet['scientific_mode']) and a.same(sheet['native_request'], request['parameters']) and a.same(sheet['input_identities']['correspondence'], request['correspondence']) and a.same(sheet['input_identities']['metadata_artifacts'], request['supplied_metadata_files']), 'original_commission_mismatch', field='request')
    for side in ('fixed', 'moving'):
        _require(a.same(sheet['sequences'][side]['selection'], request[side + '_selection']), 'original_commission_mismatch', field='request')
    _checked(validate_recorded_protein_structure_components, sheet, components=components, field='request')
    return (sheet, original)

def authenticate_received_structure_transform(store, context, transform: a.DeclaredTransform, *, returns, before_decision_index=None) -> a.ProteinStructureComponents:
    _binding(store, context, returns)
    if a._contains_action_custody(transform):
        return _authenticate_action_structure_transform(store, context, transform, returns=returns, before_decision_index=before_decision_index)
    transform = _checked(a.validate_declared_transform_record, transform, field='rotation')
    _require(transform['origin'] == 'received_fitted' and transform['received_from'] is not None, 'invalid_transform', field='rotation')
    received = transform['received_from']
    cutoff = {} if before_decision_index is None else {'before_decision_index': before_decision_index}
    descriptor = received['saved_sheet']
    _authority(returns.authenticate_received_saved_sheet, context, descriptor, required_use='use_transform', code='saved_sheet_not_received', field='descriptor', **cutoff)
    sheet, original = _saved_sheet(store, context, descriptor, returns=returns, before_decision_index=before_decision_index)
    projections = _authority(returns.received_transform_projections, context, transform, code='invalid_transform', field='rotation', **cutoff)
    _require(bool(projections), 'invalid_transform', field='rotation')
    host = returns.owner.native_protein_structure_results
    calculation = _authority(host.read_result_authority, received['calculation_custody'], scope=plain(context.scope))
    _source(store, received['calculation_custody'])
    _require(a.same(calculation['custody'], received['calculation_custody']) and a.same(calculation['sheet_file'], descriptor['sheet_file']) and a.same(calculation['original_components_file'], descriptor['original_components_file']) and a.same(calculation['request'], original['request']) and a.same(calculation['software'], original['software']) and a.same(calculation['components_file'], received['components_file']), 'invalid_transform', field='rotation')
    components = _json_file(store, received['components_file'], format='protein_structure_components_v1', role='received_transform_components')
    components = _checked(validate_recorded_protein_structure_components, sheet, components=components, field='rotation')
    selected_parameters = calculation['selector']['parameters']
    if selected_parameters is None:
        selected_parameters = calculation['request']['parameters']
    _require(components['calculation_id'] == received['calculation_id'] and a.same(components['parameters'], selected_parameters) and (components['transform']['state'] == 'identifiable_fit'), 'invalid_transform', field='rotation')
    for side in ('fixed', 'moving'):
        _require(a.same(transform[side + '_selection'], sheet['sequences'][side]['selection']), 'invalid_transform', field='rotation')
    for field, declared in (('rotation', 'rotation'), ('translation', 'translation_A')):
        cell = components['transform'][field]
        _require(cell['state'] == 'present' and a.same(cell['value'], transform[declared]), 'invalid_transform', field=field)
    for value in projections:
        projection = _checked(validate_protein_structure_projection_result, value, field='rotation')
        _require(any((a.same(projection, row) for row in calculation['facts']['execution_protein_structure_projections'])), 'original_commission_mismatch', field='receipt')
        identity = {'calculation_id': components['calculation_id'], 'input_numerical_sha256': components['input_numerical_sha256'], 'components_file': received['components_file']}
        if projection['family'] != 'transform' or not a.same(projection['calculation'], identity) or (not a.same(projection['custody'], received['calculation_custody'])):
            continue
        delivery = projection['delivery']
        if delivery['kind'] == 'values':
            rows = delivery['rows']
        else:
            table = _json_file(store, delivery['table_file'], format='protein_structure_projection_table_v1')
            _require(type(table) is dict and set(table) == {'version', 'rows'} and (table['version'] == 'protein_structure_projection_table_v1'), 'invalid_transform', field='rotation')
            rows = table['rows']
            envelope = {key: deepcopy(projection[key]) for key in ('projection_id', 'family', 'selection', 'coordinate_set', 'requested_count', 'matched_count', 'returned_count', 'omitted_count', 'state', 'issues', 'qualifications')}
            envelope.update(version='protein_structure_projection_rows_v1', rows=rows, calculation_id=components['calculation_id'])
            _checked(validate_protein_structure_projection_rows, envelope, field='rotation', code='invalid_transform')
        for row in rows:
            if row['identity']['kind'] != 'transform':
                continue
            fields = {cell['field']: cell['value'] for cell in row['values']}
            if not {'rotation', 'translation'} <= fields.keys():
                continue
            for field in ('rotation', 'translation'):
                _require(a.same(fields[field], components['transform'][field]), 'invalid_transform', field=field)
            return deepcopy(components)
    _fail('invalid_transform', field='rotation')

def _authenticate_action_structure_transform(store, context, transform, *, returns, before_decision_index=None):
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.protein_structure_action_records import VIEW_SOURCE, validate_protein_structure_action_view
    transform = _checked(a.validate_declared_transform_record, transform, field='rotation')
    _require(transform['origin'] == 'received_fitted' and transform['received_from'] is not None, 'invalid_transform', field='rotation')
    received = transform['received_from']
    cutoff = {} if before_decision_index is None else {'before_decision_index': before_decision_index}
    descriptor = received['saved_sheet']
    _require(descriptor['version'] == 'protein_structure_saved_sheet_v2' and received['calculation_custody']['version'] == 'protein_structure_action_custody_v1', 'invalid_transform', field='rotation')
    _authority(returns.authenticate_received_saved_sheet, context, descriptor, required_use='use_transform', code='saved_sheet_not_received', field='descriptor', **cutoff)
    sheet, original = _saved_sheet(store, context, descriptor, returns=returns, before_decision_index=before_decision_index)
    projections = _authority(returns.received_transform_projections, context, transform, code='invalid_transform', field='rotation', **cutoff)
    calculation = _authority(returns.read_result_authority, context, received['calculation_custody'], **cutoff)
    _source(store, received['calculation_custody'])
    _require(a.same(calculation['custody'], received['calculation_custody']) and a.same(calculation['sheet_file'], descriptor['sheet_file']) and a.same(calculation['original_components_file'], descriptor['original_components_file']) and a.same(calculation['request'], original['request']) and a.same(calculation['software'], original['software']) and a.same(calculation['components_file'], received['components_file']), 'invalid_transform', field='rotation')
    components = _json_file(store, received['components_file'], format='protein_structure_components_v1', role='received_transform_components')
    components = _checked(validate_recorded_protein_structure_components, sheet, components=components, field='rotation')
    selected_parameters = calculation['selector'].get('parameters')
    if selected_parameters is None:
        selected_parameters = calculation['request']['parameters']
    _require(components['calculation_id'] == received['calculation_id'] and a.same(components['parameters'], selected_parameters) and (components['transform']['state'] == 'identifiable_fit'), 'invalid_transform', field='rotation')
    for side in ('fixed', 'moving'):
        _require(a.same(transform[side + '_selection'], sheet['sequences'][side]['selection']), 'invalid_transform', field='rotation')
    for field, declared in (('rotation', 'rotation'), ('translation', 'translation_A')):
        cell = components['transform'][field]
        _require(cell['state'] == 'present' and a.same(cell['value'], transform[declared]), 'invalid_transform', field=field)
    for value in projections:
        projection = _checked(validate_protein_structure_action_view, value, field='rotation')
        _require(any((a.same(projection, row) for row in calculation['facts'][VIEW_SOURCE])), 'original_commission_mismatch', field='receipt')
        outcome = projection['outcome']
        if projection['source_ref'] != received['calculation_custody']['source_ref'] or projection['selection']['family'] != 'transform' or outcome['version'] == 'protein_structure_action_unavailable_v1' or (outcome['calculation_id'] != components['calculation_id']):
            continue
        if outcome['version'] == 'protein_structure_projection_rows_v1':
            rows = outcome['rows']
        else:
            table = _json_file(store, outcome['delivery']['table_file'], format='protein_structure_projection_table_v1')
            _require(type(table) is dict and set(table) == {'version', 'rows'} and (table['version'] == 'protein_structure_projection_table_v1'), 'invalid_transform', field='rotation')
            envelope = {key: deepcopy(item) for key, item in outcome.items() if key != 'delivery'}
            envelope.update(version='protein_structure_projection_rows_v1', rows=table['rows'])
            _checked(validate_protein_structure_projection_rows, envelope, field='rotation', code='invalid_transform')
            rows = table['rows']
        for row in rows:
            if row['identity']['kind'] != 'transform':
                continue
            fields = {cell['field']: cell['value'] for cell in row['values']}
            if not {'rotation', 'translation'} <= fields.keys():
                continue
            for field in ('rotation', 'translation'):
                _require(a.same(fields[field], components['transform'][field]), 'invalid_transform', field=field)
            return deepcopy(components)
    _fail('invalid_transform', field='rotation')
