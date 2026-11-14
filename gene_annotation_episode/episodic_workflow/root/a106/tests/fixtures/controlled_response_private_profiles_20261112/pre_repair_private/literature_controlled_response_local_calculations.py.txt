"""Independent source-response raw and two-reading numerical components.

This parsed-data calculator performs no acquisition or four-arm projection.
Full retained source covariance is checked before taking any pair marginal.
"""
from __future__ import annotations

from copy import deepcopy as cp
import hashlib
import json
from jsonschema import Draft202012Validator

from . import literature_controlled_response_calculations as arithmetic
from . import literature_controlled_response_owner_calculations as owner
from . import literature_controlled_response_inputs as shared
from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS


def controlled_response_local_arguments_schema():
    from .literature_controlled_response_v3_inputs import _schemas
    return cp(_schemas()['LOCAL_INPUT_SCHEMA_007'])


def _result_schema():
    from .literature_controlled_response_v3_inputs import _schemas
    return cp(_schemas()['LOCAL_OUTPUT_SCHEMA_007'])


def _schema_check(schema, value, code):
    try:
        Draft202012Validator(schema).validate(value)
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ExperimentalContractError(code, 'inputs') from error
    except Exception as error:
        if error.__class__.__module__.split('.')[0] != 'jsonschema':
            raise
        raise ExperimentalContractError(code, 'inputs') from error


def _key(reading):
    return reading['role'], reading['reading_key']


def _document(document):
    """Recompute full-N validity and compare retained lexical/exact source facts."""
    state = document['document_state']
    raw = document['raw_text']
    if raw is None:
        if (state == 'available' or document['source_validation'] != 'unassessed'
                or document['variables'] or document['matrix_tokens'] is not None
                or document['exact_matrix'] is not None or document['source_model'] is not None):
            shared._fail('local_covariance_document_mismatch', 'source_covariances')
        if state == 'unavailable' and (document['artifact_ref'] is not None or document['byte_sha256'] is not None):
            shared._fail('local_covariance_document_mismatch', 'source_covariances')
        return None, 'unassessed'
    if (not document['artifact_ref'] or hashlib.sha256(raw.encode()).hexdigest() != document['byte_sha256']):
        shared._fail('local_covariance_document_mismatch', 'source_covariances')
    parser = shared._JSON(raw)
    parsed = None
    try:
        parsed = parser.load()
        shared._source_model_shape(parsed)
    except shared._CovarianceError as error:
        actual = 'unassessed' if error.code == 'unsupported_covariance_representation' else 'invalid'
        expected_state = 'unsupported_format' if actual == 'unassessed' else 'available'
        model = None
        if isinstance(parsed, dict) and parsed.get('version') == shared.COVARIANCE_VERSION:
            candidate = {k: parsed.get(k) for k in ('origin', 'variance_status', 'model_kind')}
            if (candidate['origin'] in ('reported', 'derived', 'synthetic') and
                    candidate['variance_status'] in ('known', 'estimated', 'unknown') and
                    candidate['model_kind'] in ('none', 'known_joint_normal_source_means')):
                model = candidate
        if (document['source_validation'] != actual or state != expected_state or document['variables']
                or document['matrix_tokens'] is not None or document['exact_matrix'] is not None
                or document['source_model'] != model):
            shared._fail('local_covariance_document_mismatch', 'source_covariances')
        return None, actual
    matrix = parsed['covariance']
    actual = ('valid' if all(matrix[i][j] == matrix[j][i] for i in range(len(matrix)) for j in range(len(matrix)))
              and shared._psd(matrix) else 'invalid')
    tokens = [[parser.tokens[('covariance', i, j)] for j in range(len(matrix))] for i in range(len(matrix))]
    if (state != 'available' or document['source_validation'] != actual
            or document['matrix_tokens'] != tokens
            or document['exact_matrix'] != [[shared._rational(v) for v in row] for row in matrix]
            or document['source_model'] != {k: parsed[k] for k in ('origin', 'variance_status', 'model_kind')}
            or len(document['variables']) != len(parsed['variables'])):
        shared._fail('local_covariance_document_mismatch', 'source_covariances')
    for index, (variable, source) in enumerate(zip(document['variables'], parsed['variables'])):
        unit = shared._plain_unit(source['unit'])
        native = next((u for u in RATE_UNITS if shared._plain_unit(u) == unit), None) if unit else None
        if (variable['index'] != index or any(variable[k] != source[k] for k in ('label', 'unit', 'description'))
                or variable['native_registry_unit'] != native
                or variable['exact_scale'] != (shared._rational(unit[1]) if unit else None)):
            shared._fail('local_covariance_document_mismatch', 'source_covariances.variables')
        for field in ('label', 'unit', 'description'):
            witness = variable[field + '_witness']
            nomination = shared._json_witness(document['source_ref'], parser, ('variables', index, field))
            wanted = {'kind': 'text', **nomination}
            locator = {'kind': 'text', 'source_ref': document['source_ref'],
                'artifact_ref': document['artifact_ref'], 'byte_sha256': document['byte_sha256'],
                'start': nomination['start'], 'end': nomination['end']}
            if (witness['selection'] != wanted or witness['canonical_locator'] != locator
                    or witness['artifact_ref'] != document['artifact_ref'] or witness['byte_sha256'] != document['byte_sha256']
                    or witness['authentication'] != 'exact_utf8_byte_span'):
                shared._fail('local_covariance_document_mismatch', 'source_covariances.variables')
    return matrix, actual


def validate_controlled_response_local_inputs(inputs):
    _schema_check(controlled_response_local_arguments_schema(), inputs, 'local_input_schema_invalid')
    readings = {}
    for row in inputs['readings']:
        key = _key(row['reading'])
        if key in readings:
            shared._fail('duplicate_local_reading_selector', 'readings')
        if row['arm'] is None and key[1] is not None:
            shared._fail('absent_companion_reading', 'readings')
        owner._validate_arm(row['arm'], 'readings.arm')
        if row['arm'] is not None:
            origin = row['arm']['origin']
            if ((row['source_kind'] == 'synthetic_fixture') != (origin == 'synthetic')
                    or row['measurement_method'] == 'graph' and origin not in ('graph_derived', 'synthetic')
                    or row['measurement_method'] == 'text' and origin == 'graph_derived'):
                shared._fail('local_reading_origin_mismatch', 'readings')
        readings[key] = row
    for role in shared.PRIMITIVE_ORDER:
        if (role, None) not in readings:
            shared._fail('local_primary_roster_mismatch', 'readings')
    pair_keys = set()
    for pair in inputs['pairs']:
        if pair['pair_key'] in pair_keys:
            shared._fail('duplicate_local_pair_key', 'pairs')
        pair_keys.add(pair['pair_key'])
        for name, prefix in (('protein', 'protein_'), ('control', 'empty_')):
            if _key(pair[name]) not in readings:
                shared._fail('local_reading_selector_unresolved', 'pairs.' + name)
            if pair[name]['role'] != prefix + pair['condition']:
                shared._fail('local_pair_role_mismatch', 'pairs.' + name)
        target = pair['target']
        if (target['status'] == 'known') != (target['canonical_id'] is not None):
            shared._fail('meaning_identity_mismatch', 'pairs.target')
        index = pair['covariance_index']
        if index is not None and index >= len(inputs['source_covariances']):
            shared._fail('local_covariance_index_unresolved', 'pairs.covariance_index')
        if index is None and (pair['protein_binding'] is not None or pair['control_binding'] is not None):
            shared._fail('local_covariance_binding_without_document', 'pairs')
    documents = {}
    for document in inputs['source_covariances']:
        _document(document)
        key = document['source_ref']
        if key in documents and documents[key] != document:
            shared._fail('local_covariance_document_conflict', 'source_covariances')
        documents[key] = document
    return cp(inputs)


def _qualifications(arms):
    result = set()
    if any(a and a['origin'] == 'synthetic' for a in arms): result.add('synthetic_fixture')
    if any(a and a['approximate'] for a in arms): result.add('approximate_source_reading')
    if any(a and a['digitization_interval'] is not None for a in arms): result.add('conditional_digitization')
    return result


def _dependency(selectors, arms, *, numeric=True, covariance_index=None, bindings=(), model=False):
    return {'scientific_readings': cp(selectors), 'numeric_readings': cp(selectors) if numeric else [],
        'uncertainty_readings': [], 'covariance_index': covariance_index,
        'covariance_owner_ids': list(dict.fromkeys(b['resolved_owner_id'] for b in bindings if b and b['resolved_owner_id'])),
        'source_variable_indices': list(dict.fromkeys(b['source_variable_index'] for b in bindings if b and b['source_variable_index'] is not None)),
        'model_readings': cp(selectors) if model else [],
        'unresolved_readings': [cp(s) for s, a in zip(selectors, arms) if a is None or any(v != 'known' for v in a['meaning_statuses'].values())],
        'numeric_fields': [{'reading': cp(s), 'fields': (['value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval'] if numeric else
            ['relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval_presence'])} for s in selectors],
        'full_source_covariance_required': covariance_index is not None}


def _pair_science(pair, arms):
    reasons = {'missing_arm'} if any(a is None for a in arms) else set()
    for meaning in ('endpoint', 'normalization'): reasons |= arithmetic._identity_reasons(arms, meaning)
    if len({RATE_UNITS[a['unit']][0] for a in arms if a and a['unit']}) > 1:
        reasons.add('incompatible_unit_dimension')
    for a, allowed in zip(arms, (('protein_present',), ('protein_free_control', 'empty_vector_control'))):
        if a and a['protein_arrangement'] not in allowed:
            reasons.add({'unknown': 'unknown_protein_arrangement', 'conflicting': 'conflicting_protein_arrangement'}.get(a['protein_arrangement'], 'incompatible_control_arrangement'))
    target, application = pair['target'], pair['control_application']
    if target['status'] != 'known': reasons.add(target['status'] + '_condition_correspondence')
    if application in ('unknown', 'conflicting'): reasons.add(application + '_control_application')
    for i, a in enumerate(arms):
        if a is None: continue
        state = a['meaning_statuses']['condition']
        if state != 'known': reasons.add(state + '_condition_correspondence')
        elif target['status'] == 'known' and (i == 0 or application == 'matched_condition_control') and a['condition_id'] != target['canonical_id']:
            reasons.add('different_condition_correspondence')
    if pair['joint_admissibility'] != 'compatible': reasons.add(pair['joint_admissibility'] + '_joint_applicability')
    if pair['scope_state'] in ('unknown', 'conflicting'): reasons.add('local_scope_unresolved')
    if all(arms):
        a, b = arms
        if a['physical_observation_id'] is not None and a['physical_observation_id'] == b['physical_observation_id']:
            reasons |= owner._context_reasons(a, b)
        if a['source_observation_id'] is not None and a['source_observation_id'] == b['source_observation_id'] and all(x['physical_observation_id'] is not None for x in arms) and a['physical_observation_id'] != b['physical_observation_id']:
            reasons.add('conflicting_source_owner_binding')
    return reasons


def _variance(pair, arms, documents):
    reasons = _pair_science(pair, arms)
    if any(a and a['unit'] is None for a in arms): reasons.add('unknown_unit')
    if any(a and a['status'] == 'bound' for a in arms): reasons.add('unresolved_censoring_model')
    if any(a and a['status'] in ('ambiguous', 'conflicting', 'unsupported') for a in arms):
        reasons |= set().union(*(arithmetic._operand_reasons(a) for a in arms))
    if any(a and a['meaning_statuses']['physical_observation'] != 'known' for a in arms): reasons.add('unknown_covariance_owner')
    index = pair['covariance_index']
    if index is None:
        return None, reasons | {'unknown_covariance'}
    document, matrix, validation = documents[index]
    if validation != 'valid': reasons.add('source_full_covariance_invalid' if validation == 'invalid' else 'source_covariance_unassessed')
    if pair['variance_status'] == 'unknown' or document['source_model'] is None or document['source_model']['variance_status'] != pair['variance_status']:
        reasons.add('unknown_covariance')
    if document['source_model'] and document['source_model']['origin'] == 'synthetic' and any(a and a['origin'] != 'synthetic' for a in arms):
        reasons.add('unknown_covariance')
    bindings = [pair['protein_binding'], pair['control_binding']]
    indices, scales = [], []
    for binding, arm in zip(bindings, arms):
        if binding is None or binding['state'] != 'known':
            reasons.add('local_covariance_binding_conflicting' if binding and binding['state'] == 'conflicting' else 'local_covariance_binding_unknown')
            continue
        i = binding['source_variable_index']
        if (type(i) is not int or i >= len(document['variables']) or binding['selection'] is None
                or binding['selection']['variable_index'] != i or arm is None
                or binding['resolved_owner_id'] != arm['physical_observation_id'] or binding['resolved_owner_id'] is None
                or binding['label_witness'] != document['variables'][i]['label_witness']
                or binding['owner_witness'] is None or binding['owner_witness']['canonical_locator'] is None
                or binding['correspondence'] is None or binding['correspondence']['effective_value'] != 'same'
                or binding['correspondence']['selection'] != binding['selection']['correspondence']
                or binding['owner_witness']['selection'] != binding['selection']['owner_witness']
                or binding['label_witness']['selection'] != {'kind': 'text', **binding['selection']['label_witness']}):
            reasons.add('local_covariance_binding_conflicting')
            continue
        variable = document['variables'][i]
        unit = variable['native_registry_unit']
        if unit is None or arm['unit'] is None:
            reasons.add('unknown_unit'); continue
        if RATE_UNITS[unit][0] != RATE_UNITS[arm['unit']][0]:
            reasons.add('incompatible_unit_dimension'); continue
        indices.append(i); scales.append(shared._fraction(variable['exact_scale']))
    if reasons: return None, reasons
    i, j = indices; a, b = scales
    if i == j and arms[0]['physical_observation_id'] != arms[1]['physical_observation_id']:
        return None, {'local_covariance_binding_conflicting'}
    if arms[0]['physical_observation_id'] == arms[1]['physical_observation_id']:
        if any(a * matrix[i][k] != b * matrix[j][k] for k in range(len(matrix))):
            return None, {'local_covariance_binding_conflicting'}
    return a*a*matrix[i][i] + b*b*matrix[j][j] - 2*a*b*matrix[i][j], set()


def populate_controlled_response_local(inputs):
    """Populate each real reading and nominated pair; never infer independence."""
    inputs = validate_controlled_response_local_inputs(inputs)
    roster = {_key(r['reading']): r for r in inputs['readings']}
    documents = [(d, *_document(d)) for d in inputs['source_covariances']]
    raw = []
    for row in inputs['readings']:
        arm, selector = row['arm'], row['reading']
        reasons = arithmetic._operand_reasons(arm)
        cell = arithmetic._cell(arithmetic._range(arm) if not reasons else None, arithmetic._unit([arm]),
            'source_response', [arm], reasons=reasons, qualifications=_qualifications([arm]), raw=True)
        if arm is None: cell['origin'] = None
        raw.append({'reading': cp(selector), 'cell': cell, 'reported_uncertainty': cp(row['reported_uncertainty']),
            'dependencies': _dependency([selector], [arm])})
    pairs = []
    for pair in inputs['pairs']:
        selectors = [pair['protein'], pair['control']]
        arms = [roster[_key(s)]['arm'] for s in selectors]
        reasons = _pair_science(pair, arms) | set().union(*(arithmetic._operand_reasons(a) for a in arms))
        qualifications = _qualifications(arms)
        if pair['control_application'] == 'shared_reference_assumption': qualifications.add('shared_reference_assumption')
        difference = arithmetic._cell(arithmetic._linear(arms, (1, -1)) if not reasons else None,
            arithmetic._unit(arms), 'condition_control_difference', arms, reasons=reasons, qualifications=qualifications)
        variance, variance_reasons = _variance(pair, arms, documents)
        variance_qualifications = qualifications | ({'estimated_covariance'} if pair['variance_status'] == 'estimated' else set())
        unit = arithmetic._unit(arms)
        variance_cell = arithmetic._cell(arithmetic._point(variance), '('+unit+')^2' if unit else None,
            'local_joint_covariance', arms, reasons=variance_reasons, qualifications=variance_qualifications)
        se_cell = arithmetic._cell(arithmetic._point(arithmetic._sqrt(variance)) if variance is not None else None,
            unit, 'local_square_root_variance', arms, reasons=variance_reasons, qualifications=variance_qualifications)
        bindings = [pair['protein_binding'], pair['control_binding']]
        covariance_dependency = _dependency(selectors, arms, numeric=False, covariance_index=pair['covariance_index'], bindings=bindings)
        pairs.append({'pair_key': pair['pair_key'], 'difference': difference, 'variance': variance_cell,
            'standard_uncertainty': se_cell, 'dependencies': {'difference': _dependency(selectors, arms),
                'variance': cp(covariance_dependency), 'standard_uncertainty': cp(covariance_dependency)}})
    result = {'version': 'controlled_response_local_sheet_v1', 'inputs': cp(inputs), 'raw': raw, 'pairs': pairs,
        'full_covariance_checks': [{'covariance_index': i, 'source_validation': validity, 'document_state': d['document_state']}
            for i, (d, matrix, validity) in enumerate(documents)]}
    _schema_check(_result_schema(), result, 'local_sheet_schema_invalid')
    return result


def validate_controlled_response_local_sheet(inputs, sheet):
    _schema_check(_result_schema(), sheet, 'local_sheet_schema_invalid')
    expected = populate_controlled_response_local(inputs)
    if json.dumps(sheet, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        shared._fail('local_sheet_reconstruction_mismatch', 'sheet')
    return cp(sheet)


__all__ = ['controlled_response_local_arguments_schema', 'validate_controlled_response_local_inputs',
    'populate_controlled_response_local', 'validate_controlled_response_local_sheet']
