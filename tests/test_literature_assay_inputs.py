"""Synthetic source spans and covariance only; no primary paper is read."""
from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.literature_assay_inputs import (
    ASSAY_LITERAL_FIELDS, PRIMITIVE_ORDER,
    assay_arguments_schema, read_assay_inputs,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


SOURCE = 'source_' + '1' * 24
COVARIANCE_SOURCE = 'source_' + '2' * 24
OTHER_SOURCE = 'source_' + '3' * 24
ARTIFACT = 'artifact_' + '1' * 24
TEXT = ('µ Assayed molecule P from organism O, genotype G, construct C; purified preparation; condition A. '
        'Oxygen consumption from a single preparation. Deliberately tested substrate. '
        'net rate 1.00 uM/min; contaminant 0.15 uM/min; recovery 1.00 fraction; '
        'amount 1.00 uM; test condition rate 2.00 uM/min; reference condition rate 1.60 uM/min; '
        'distinct residual 0.0625 per_min_squared. A known normal sampling model is stipulated in this synthetic fixture.')


def witness(text, quote, *, source=SOURCE, representation='original', occurrence=0):
    offset = -1
    for _ in range(occurrence + 1):
        offset = text.index(quote, offset + 1)
    return {'source_ref': source, 'representation': representation,
            'start': len(text[:offset].encode()), 'end': len(text[:offset + len(quote)].encode()), 'quote': quote}


def measurement(text, quote, number, unit, *, source=SOURCE, representation='original'):
    evidence = witness(text, quote, source=source, representation=representation)
    ns = quote.index(number)
    ne = ns + len(number)
    us = quote.index(unit, ne) if unit else ne
    return {'witness': evidence, 'number_start': ns, 'number_end': ne,
            'unit_start': us, 'unit_end': us + len(unit)}


def fixtures(text=TEXT):
    sources = {SOURCE: {'artifact_ref': ARTIFACT, 'content': text.encode('utf-8')}}
    def read_source(reference, representation):
        assert representation in ('original', 'text')
        return deepcopy(sources[reference])
    args = {'source_ref': SOURCE, 'source_kind': 'synthetic_fixture',
        'assay': {**dict.fromkeys(ASSAY_LITERAL_FIELDS),
                  'endpoint': {'value': 'unknown', 'witnesses': []},
                  'arrangement': {'value': 'unknown', 'witnesses': []}},
        'primitives': dict.fromkeys(PRIMITIVE_ORDER), 'covariance_source_ref': None,
        'distinct_residual_variance': None, 'variance_status': 'unknown',
        'observation_model': 'none', 'model_witnesses': []}
    return args, sources, read_source


def populated():
    args, sources, reader = fixtures()
    for field, quote in [('molecule', 'molecule P'), ('organism', 'organism O'),
        ('genotype', 'genotype G'), ('construct', 'construct C'), ('preparation', 'purified preparation'),
        ('condition', 'condition A'), ('intended_variable', 'tested substrate')]:
        args['assay'][field] = witness(TEXT, quote)
    args['assay']['endpoint'] = {'value': 'oxygen_consumption', 'witnesses': [witness(TEXT, 'Oxygen consumption')]}
    args['assay']['arrangement'] = {'value': 'single_preparation', 'witnesses': [witness(TEXT, 'single preparation')]}
    for role, quote, number, unit in [
        ('q', 'net rate 1.00 uM/min', '1.00', 'uM/min'),
        ('g', 'contaminant 0.15 uM/min', '0.15', 'uM/min'),
        ('k', 'recovery 1.00 fraction', '1.00', 'fraction'),
        ('E', 'amount 1.00 uM', '1.00', 'uM'),
        ('u', 'test condition rate 2.00 uM/min', '2.00', 'uM/min'),
        ('v', 'reference condition rate 1.60 uM/min', '1.60', 'uM/min')]:
        args['primitives'][role] = measurement(TEXT, quote, number, unit)
    args['distinct_residual_variance'] = measurement(TEXT, 'distinct residual 0.0625 per_min_squared', '0.0625', 'per_min_squared')
    return args, sources, reader


def add_covariance(args, sources, reader, matrix=None):
    first = read_assay_inputs(args, read_source=reader)
    diagonal = [.04, .0225, .0025, .01, .01, .01]
    payload = {'version': 'a105_primitive_covariance_v1', 'primitive_order': list(PRIMITIVE_ORDER),
        'primitive_measurement_keys': [first['primitive_observations'][role]['measurement_key'] for role in PRIMITIVE_ORDER],
        'primitive_units': [first['primitive_observations'][role]['raw_unit'] for role in PRIMITIVE_ORDER],
        'covariance': matrix or [[diagonal[i] if i == j else 0 for j in range(6)] for i in range(6)],
        'origin': 'synthetic'}
    sources[COVARIANCE_SOURCE] = {'artifact_ref': 'artifact_' + '2' * 24,
                                 'content': json.dumps(payload).encode()}
    args['covariance_source_ref'] = COVARIANCE_SOURCE
    return payload


def test_all_null_preserves_unknowns_authorizes_root_and_has_no_side_effects():
    args, sources, reader = fixtures()
    before = deepcopy(args), deepcopy(sources)
    result = read_assay_inputs(args, read_source=reader)
    assert result['values'] == dict.fromkeys(PRIMITIVE_ORDER)
    assert result['covariance'] is result['covariance_origin'] is None
    assert result['distinct_residual_variance'] is None
    assert result['primitive_order'] == list(PRIMITIVE_ORDER)
    assert result['source_refs'] == [SOURCE]
    assert result['assay']['endpoint'] == {'kind': 'source_interpretation', 'value': 'unknown', 'witnesses': []}
    assert (args, sources) == before
    result['values']['q'] = 500
    assert args['primitives']['q'] is None


def test_literals_are_anchored_and_interpretations_are_not_automatic_semantic_proof():
    args, sources, reader = populated()
    result = read_assay_inputs(args, read_source=reader)
    assert result['values'] == {'q': 1, 'g': .15, 'k': 1, 'E': 1, 'u': 2, 'v': 1.6}
    assert result['assay']['molecule']['value'] == 'molecule P'
    assert result['assay']['molecule']['witness']['artifact_ref'] == ARTIFACT
    assert result['assay']['endpoint']['kind'] == 'source_interpretation'
    assert result['distinct_residual_variance'] == .0625
    assert result['distinct_residual_observation']['unit'] == 'per_min_squared'
    for role in PRIMITIVE_ORDER:
        row = result['primitive_observations'][role]
        assert row['role'] == role
        assert row['measurement_key'].startswith('literature_measurement_')
        raw = sources[SOURCE]['content'][row['witness']['start']:row['witness']['end']]
        assert raw.decode() == row['witness']['quote']
    result['assay']['molecule']['witness']['quote'] = 'changed'
    assert args['assay']['molecule']['quote'] == 'molecule P'


def test_tool_schema_is_closed_and_detached():
    args, sources, reader = populated()
    validate_schema(args, assay_arguments_schema())
    first = assay_arguments_schema()
    first['properties']['assay']['properties']['endpoint']['properties']['value']['enum'].append('bad')
    assert 'bad' not in assay_arguments_schema()['properties']['assay']['properties']['endpoint']['properties']['value']['enum']


@pytest.mark.parametrize('kind', ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture'])
def test_declared_source_origin_preserved_without_validity_inference(kind):
    args, _, reader = fixtures()
    args['source_kind'] = kind
    assert read_assay_inputs(args, read_source=reader)['source_kind'] == kind


@pytest.mark.parametrize('field', ['arguments', 'assay', 'primitives', 'witness', 'measurement'])
def test_unknown_keys_rejected(field):
    args, _, reader = populated()
    target = {'arguments': args, 'assay': args['assay'], 'primitives': args['primitives'],
              'witness': args['primitives']['q']['witness'], 'measurement': args['primitives']['q']}[field]
    target['unexpected'] = 1
    with pytest.raises(ExperimentalContractError, match='closed_fields_required'):
        read_assay_inputs(args, read_source=reader)


@pytest.mark.parametrize('field', ['source_kind', 'variance_status', 'observation_model'])
def test_unknown_values_rejected(field):
    args, _, reader = fixtures()
    args[field] = 'unsupported'
    with pytest.raises(ExperimentalContractError):
        read_assay_inputs(args, read_source=reader)


@pytest.mark.parametrize('change', [
    {'start': True}, {'end': False}, {'start': -1}, {'end': 10**6},
    {'start': 5, 'end': 4}, {'quote': 'fabricated source text'}, {'representation': 'guessed'},
])
def test_witness_identity_and_literal_bytes_checked(change):
    args, _, reader = populated()
    args['assay']['molecule'].update(change)
    with pytest.raises(ExperimentalContractError):
        read_assay_inputs(args, read_source=reader)


def test_source_offsets_are_utf8_bytes_not_character_offsets():
    args, _, reader = populated()
    args['assay']['molecule']['start'] -= 1
    args['assay']['molecule']['end'] -= 1
    with pytest.raises(ExperimentalContractError, match='source_quote_mismatch'):
        read_assay_inputs(args, read_source=reader)
    args, _, reader = fixtures()
    args['assay']['molecule'] = {'source_ref': SOURCE, 'representation': 'original', 'start': 1, 'end': 2, 'quote': 'µ'}
    with pytest.raises(ExperimentalContractError, match='utf8_boundary'):
        read_assay_inputs(args, read_source=reader)


def test_callback_authority_failure_propagates_without_new_fetch_or_repair():
    args, _, _ = fixtures()
    def denied(*_):
        raise PermissionError('not received')
    with pytest.raises(PermissionError, match='not received'):
        read_assay_inputs(args, read_source=denied)


@pytest.mark.parametrize('answer,witness_count', [('oxygen_consumption', 0), ('conflicting', 0), ('conflicting', 1)])
def test_interpretation_requires_actual_witnesses(answer, witness_count):
    args, _, reader = fixtures()
    args['assay']['endpoint'] = {'value': answer, 'witnesses': [witness(TEXT, 'Oxygen consumption')] * witness_count}
    with pytest.raises(ExperimentalContractError, match='interpretation_witness_required'):
        read_assay_inputs(args, read_source=reader)


def test_duplicate_quotes_do_not_supply_two_conflict_witnesses():
    args, _, reader = fixtures()
    quote = witness(TEXT, 'Oxygen consumption')
    args['assay']['endpoint'] = {'value': 'conflicting', 'witnesses': [quote, deepcopy(quote)]}
    with pytest.raises(ExperimentalContractError, match='interpretation_witness_required'):
        read_assay_inputs(args, read_source=reader)
    args['assay']['endpoint']['witnesses'][1] = witness(TEXT, 'single preparation')
    assert read_assay_inputs(args, read_source=reader)['assay']['endpoint']['value'] == 'conflicting'


@pytest.mark.parametrize('role,text,quote,number,unit,value,canonical', [
    ('q', 'rate 2 mM/min', 'rate 2 mM/min', '2', 'mM/min', 2000, 'uM/min'),
    ('g', 'rate 2 nM/min', 'rate 2 nM/min', '2', 'nM/min', .002, 'uM/min'),
    ('u', 'rate −2 µM/min', 'rate −2 µM/min', '−2', 'µM/min', -2, 'uM/min'),
    ('v', 'rate 2 μM/min', 'rate 2 μM/min', '2', 'μM/min', 2, 'uM/min'),
    ('E', 'amount 180 nM', 'amount 180 nM', '180', 'nM', .18, 'uM'),
    ('E', 'amount 1e-3 mM', 'amount 1e-3 mM', '1e-3', 'mM', 1, 'uM'),
    ('k', 'recovery .98', 'recovery .98', '.98', '', .98, 'dimensionless'),
    ('k', 'recovery 1.0 dimensionless', 'recovery 1.0 dimensionless', '1.0', 'dimensionless', 1., 'dimensionless'),
])
def test_explicit_unit_conversions(role, text, quote, number, unit, value, canonical):
    args, _, reader = fixtures(text)
    args['primitives'][role] = measurement(text, quote, number, unit)
    result = read_assay_inputs(args, read_source=reader)['primitive_observations'][role]
    assert result['value'] == value
    assert result['unit'] == canonical
    assert result['raw_number'] == number and result['raw_unit'] == unit


@pytest.mark.parametrize('text,number,unit,error', [
    ('rate <1 uM/min', '1', 'uM/min', 'censored_or_approximate_point'),
    ('rate greater than 1 uM/min', '1', 'uM/min', 'censored_or_approximate_point'),
    ('rate less than 1 uM/min', '1', 'uM/min', 'censored_or_approximate_point'),
    ('rate approximately 1 uM/min', '1', 'uM/min', 'censored_or_approximate_point'),
    ('rate ≈1 uM/min', '1', 'uM/min', 'censored_or_approximate_point'),
    ('rate 100 uM/min', '00', 'uM/min', 'partial_numeric_token'),
    ('rate 1e-3 uM/min', '1', 'uM/min', 'measurement_unit_not_adjacent'),
    ('rate 1 umol/min', '1', 'umol/min', 'incompatible_primitive_unit'),
    ('rate 1 uM/min/mg', '1', 'uM/min', 'partial_unit_token'),
    ('rate 1e309 uM/min', '1e309', 'uM/min', 'finite_number_required'),
    ('rate 1e-999 uM/min', '1e-999', 'uM/min', 'numerical_model_range'),
    ('rate 1.5 ± .2 uM/min', '1.5', 'uM/min', 'measurement_unit_not_adjacent'),
    ('rate 1.5 ± .2 uM/min', '.2', 'uM/min', 'censored_or_approximate_point'),
])
def test_nonpoints_wrong_dimensions_and_partial_tokens_are_not_measured_rates(text, number, unit, error):
    args, _, reader = fixtures(text)
    args['primitives']['q'] = measurement(text, text, number, unit)
    with pytest.raises(ExperimentalContractError, match=error):
        read_assay_inputs(args, read_source=reader)


def test_bound_outside_a_cherry_picked_quote_is_still_not_an_observed_point():
    text = 'rate <1 uM/min'
    args, _, reader = fixtures(text)
    args['primitives']['q'] = measurement(text, '1 uM/min', '1', 'uM/min')
    with pytest.raises(ExperimentalContractError, match='censored_or_approximate_point'):
        read_assay_inputs(args, read_source=reader)


@pytest.mark.parametrize('field,value', [('number_start', True), ('unit_end', -1), ('number_end', 999), ('unit_start', 0)])
def test_measurement_offset_relationships(field, value):
    args, _, reader = populated()
    args['primitives']['q'][field] = value
    with pytest.raises(ExperimentalContractError):
        read_assay_inputs(args, read_source=reader)


def test_full_covariance_literal_owners_origin_and_native_units_are_preserved():
    args, sources, reader = populated()
    payload = add_covariance(args, sources, reader)
    result = read_assay_inputs(args, read_source=reader)
    assert result['covariance'] == payload['covariance']
    assert result['covariance_origin'] == 'synthetic'
    assert result['source_refs'] == [SOURCE, COVARIANCE_SOURCE]


def test_covariance_converts_both_primitive_axes():
    args, sources, reader = populated()
    text = TEXT.replace('amount 1.00 uM', 'amount 1000 nM')
    sources[SOURCE]['content'] = text.encode()
    # All following offsets must reference the actual changed representation.
    for role, item in args['primitives'].items():
        quote = item['witness']['quote']
        if role == 'E':
            args['primitives'][role] = measurement(text, 'amount 1000 nM', '1000', 'nM')
        else:
            args['primitives'][role]['witness'] = witness(text, quote)
    args['distinct_residual_variance']['witness'] = witness(text, args['distinct_residual_variance']['witness']['quote'])
    matrix = [[0.0] * 6 for _ in range(6)]
    matrix[3][3] = 40000
    matrix[0][3] = matrix[3][0] = 20
    add_covariance(args, sources, reader, matrix)
    result = read_assay_inputs(args, read_source=reader)
    assert result['values']['E'] == 1
    assert result['covariance'][3][3] == .04
    assert result['covariance'][0][3] == result['covariance'][3][0] == .02


@pytest.mark.parametrize('mutation,error', [
    (lambda p: p.update(version='wrong'), 'covariance_version_mismatch'),
    (lambda p: p.update(primitive_order=list(reversed(PRIMITIVE_ORDER))), 'covariance_primitive_order_mismatch'),
    (lambda p: p['primitive_measurement_keys'].__setitem__(0, 'wrong'), 'covariance_measurement_owner_mismatch'),
    (lambda p: p['primitive_units'].__setitem__(0, 'mM/min'), 'covariance_primitive_unit_mismatch'),
    (lambda p: p.update(covariance=[[0]]), 'six_by_six_covariance_required'),
    (lambda p: p['covariance'][0].__setitem__(0, True), 'finite_number_required'),
    (lambda p: p['covariance'][0].__setitem__(0, math.inf), 'finite_number_required'),
    (lambda p: p.update(extra=1), 'closed_fields_required'),
    (lambda p: p.update(origin='guessed'), 'unknown_covariance_origin'),
])
def test_covariance_boundary_checks(mutation, error):
    args, sources, reader = populated()
    payload = add_covariance(args, sources, reader)
    mutation(payload)
    sources[COVARIANCE_SOURCE]['content'] = json.dumps(payload).encode()
    with pytest.raises(ExperimentalContractError, match=error):
        read_assay_inputs(args, read_source=reader)


def test_covariance_does_not_fill_a_missing_primitive():
    args, sources, reader = populated()
    add_covariance(args, sources, reader)
    args['primitives']['q'] = None
    with pytest.raises(ExperimentalContractError, match='complete_covariance_owners_required'):
        read_assay_inputs(args, read_source=reader)


def test_same_source_measurement_shared_across_roles_keeps_identity_and_requires_joint_consistency():
    args, sources, reader = populated()
    args['primitives']['u'] = deepcopy(args['primitives']['q'])
    result = read_assay_inputs(args, read_source=reader)
    assert result['primitive_observations']['q']['measurement_key'] == result['primitive_observations']['u']['measurement_key']
    assert result['covariance'] is None
    payload = add_covariance(args, sources, reader)
    with pytest.raises(ExperimentalContractError, match='shared_measurement_covariance_mismatch'):
        read_assay_inputs(args, read_source=reader)
    for j in range(6):
        payload['covariance'][4][j] = payload['covariance'][0][j]
    for i in range(6):
        payload['covariance'][i][4] = payload['covariance'][i][0]
    sources[COVARIANCE_SOURCE]['content'] = json.dumps(payload).encode()
    assert read_assay_inputs(args, read_source=reader)['covariance'][4][4] == .04


def test_equal_numbers_at_distinct_source_locations_do_not_become_same_measurement():
    args, _, reader = populated()
    result = read_assay_inputs(args, read_source=reader)
    assert result['values']['q'] == result['values']['E'] == 1
    assert result['primitive_observations']['q']['measurement_key'] != result['primitive_observations']['E']['measurement_key']


@pytest.mark.parametrize('status,model', [('known', 'none'), ('estimated', 'none'), ('unknown', 'known_normal_nonnegative_presence')])
def test_nondefault_model_assumption_needs_actual_witness(status, model):
    args, _, reader = populated()
    args.update(variance_status=status, observation_model=model)
    with pytest.raises(ExperimentalContractError, match='model_witness_required'):
        read_assay_inputs(args, read_source=reader)
    args['model_witnesses'] = [witness(TEXT, 'known normal sampling model')]
    result = read_assay_inputs(args, read_source=reader)
    assert result['variance_status'] == status and result['observation_model'] == model
    assert result['model_witnesses'][0]['artifact_ref'] == ARTIFACT


def test_duplicate_json_covariance_keys_are_rejected():
    args, sources, reader = populated()
    add_covariance(args, sources, reader)
    sources[COVARIANCE_SOURCE]['content'] = b'{"version":"one","version":"two"}'
    with pytest.raises(ExperimentalContractError, match='duplicate_json_key'):
        read_assay_inputs(args, read_source=reader)


def test_empty_recovery_unit_cannot_hide_reported_concentration_unit():
    text = 'concentration 1 uM'
    args, _, reader = fixtures(text)
    args['primitives']['k'] = measurement(text, text, '1', '')
    with pytest.raises(ExperimentalContractError, match='dimensional_unit_omitted'):
        read_assay_inputs(args, read_source=reader)


@pytest.mark.parametrize('text', ['rate &lt;1 uM/min', 'rate &#60;1 uM/min',
    'rate &gt;<italic>1 uM/min</italic>', 'rate less than or equal to 1 uM/min'])
def test_encoded_or_long_form_source_bound_is_not_promoted_to_point(text):
    args, _, reader = fixtures(text)
    args['primitives']['q'] = measurement(text, '1 uM/min', '1', 'uM/min')
    with pytest.raises(ExperimentalContractError, match='censored_or_approximate_point'):
        read_assay_inputs(args, read_source=reader)


def test_plain_number_at_xml_element_start_is_not_a_greater_than_bound():
    text = '<article><p>1 uM/min</p></article>'
    args, _, reader = fixtures(text)
    args['primitives']['q'] = measurement(text, '1 uM/min', '1', 'uM/min')
    assert read_assay_inputs(args, read_source=reader)['values']['q'] == 1


def test_dimensionless_point_followed_by_sentence_period_is_a_point():
    text = 'Recovery .98. More details follow.'
    args, _, reader = fixtures(text)
    args['primitives']['k'] = measurement(text, '.98', '.98', '')
    assert read_assay_inputs(args, read_source=reader)['values']['k'] == .98


@pytest.mark.parametrize('text', ['recovery 98%', 'recovery 98 percent', 'variance 98 per_min_squared',
    'activity 98 min^-2', 'rate 98 mM/min'])
def test_empty_recovery_unit_does_not_hide_a_percent_or_other_dimensional_quantity(text):
    args, _, reader = fixtures(text)
    args['primitives']['k'] = measurement(text, text, '98', '')
    with pytest.raises(ExperimentalContractError, match='dimensional_unit_omitted'):
        read_assay_inputs(args, read_source=reader)


def test_original_text_aliases_of_same_artifact_are_one_measurement_with_shared_covariance():
    args, sources, reader = populated()
    args['primitives']['u'] = deepcopy(args['primitives']['q'])
    args['primitives']['u']['witness']['representation'] = 'text'
    result = read_assay_inputs(args, read_source=reader)
    assert result['primitive_observations']['q']['measurement_key'] == result['primitive_observations']['u']['measurement_key']
    payload = add_covariance(args, sources, reader)
    with pytest.raises(ExperimentalContractError, match='shared_measurement_covariance_mismatch'):
        read_assay_inputs(args, read_source=reader)
    for j in range(6):
        payload['covariance'][4][j] = payload['covariance'][0][j]
    for i in range(6):
        payload['covariance'][i][4] = payload['covariance'][i][0]
    sources[COVARIANCE_SOURCE]['content'] = json.dumps(payload).encode()
    assert read_assay_inputs(args, read_source=reader)['covariance'][4][4] == .04


def test_source_selected_numerical_graph_supplies_the_existing_correction_calculator():
    from gene_annotation_episode.literature_activity_calculations import populate_corrected_activity
    args, sources, reader = populated()
    add_covariance(args, sources, reader)
    args['variance_status'] = 'known'
    args['observation_model'] = 'known_normal_nonnegative_presence'
    args['model_witnesses'] = [witness(TEXT, 'known normal sampling model')]
    parsed = read_assay_inputs(args, read_source=reader)
    sheet = populate_corrected_activity({name: parsed[name] for name in (
        'values', 'covariance', 'variance_status', 'distinct_residual_variance', 'observation_model')})
    assert sheet['cells']['corrected_activity']['value'] == .68
    assert sheet['cells']['effect_variance']['value'] == .11124225
    assert sheet['cells']['source_presence_index']['value'] == pytest.approx(.7775614860794028)
    # Removing a source operand does not turn its missing value into zero.
    args['primitives']['g'] = None
    args['covariance_source_ref'] = None
    parsed = read_assay_inputs(args, read_source=reader)
    sheet = populate_corrected_activity({name: parsed[name] for name in (
        'values', 'covariance', 'variance_status', 'distinct_residual_variance', 'observation_model')})
    assert sheet['cells']['corrected_activity']['value'] is None
    assert sheet['cells']['corrected_activity']['unavailable_reason'] == 'correction_inputs_not_supplied'
