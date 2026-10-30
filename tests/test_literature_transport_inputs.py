"""Synthetic retained bytes and committed callback operands only; no papers."""
from copy import deepcopy
import hashlib
import json
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_transport_calculations import PRIMITIVE_ORDER, populate_transport_response
from gene_annotation_episode.literature_transport_inputs import (
    CONTEXT_FIELDS, read_transport_inputs, transport_response_population_schema,
)


SOURCE = 'source_' + '1' * 24
KM_SHEET = 'source_' + '2' * 24
KM_ORIGINAL = 'source_' + '3' * 24
COVARIANCE = 'source_' + '4' * 24
OTHER = 'source_' + '5' * 24
ARTIFACT = 'artifact_' + '1' * 24
TEXT = ('µ molecule P; analyte A; purified membrane; system S; initial flux; curve C. '
        'test 10 µM; reference 40 uM. A Michaelis Menten model is stipulated. '
        'curve C; system T.')


def witness(text, quote, *, source=SOURCE, representation='original', occurrence=0):
    offset = -1
    for _ in range(occurrence + 1):
        offset = text.index(quote, offset + 1)
    return {'source_ref': source, 'representation': representation,
        'start': len(text[:offset].encode()), 'end': len(text[:offset + len(quote)].encode()), 'quote': quote}


def measurement(text, quote, number, unit, *, source=SOURCE):
    ns = quote.index(number)
    ne = ns + len(number)
    us = quote.index(unit, ne)
    return {'witness': witness(text, quote, source=source), 'number_start': ns, 'number_end': ne,
            'unit_start': us, 'unit_end': us + len(unit)}


def fixture(text=TEXT):
    sources = {SOURCE: {'artifact_ref': ARTIFACT, 'content': text.encode()}}
    quantity = {'sheet_ref': KM_SHEET, 'input_source_ref': KM_ORIGINAL, 'value': 16.5,
        'unit': 'uM', 'origin': 'reported', 'reported_uncertainty_kind': 'unspecified',
        'measurement_key': 'transport_quantity_' + 'a' * 64,
        'reported_subject_ref': 'reference_' + '1' * 24, 'analyte_ref': 'term_' + '1' * 24}
    calls = []
    def read_source(reference, representation):
        calls.append(('source', reference, representation))
        return deepcopy(sources[reference])
    def read_quantity(reference):
        calls.append(('quantity', reference))
        assert reference == KM_SHEET
        return deepcopy(quantity)
    args = {'source_ref': SOURCE, 'source_kind': 'synthetic_fixture',
        'primitives': dict.fromkeys(PRIMITIVE_ORDER[:2]), 'km_sheet_ref': None,
        'curve_contexts': dict.fromkeys(PRIMITIVE_ORDER), 'covariance_source_ref': None,
        'variance_status': 'unknown', 'observation_model': 'unknown', 'model_witnesses': []}
    return args, sources, quantity, calls, read_source, read_quantity


def read(fix):
    args, _, _, _, source_reader, quantity_reader = fix
    return read_transport_inputs(args, read_source=source_reader, read_quantity=quantity_reader)


def populated():
    fix = fixture()
    args = fix[0]
    args['primitives'] = {'substrate_test': measurement(TEXT, 'test 10 µM', '10', 'µM'),
        'substrate_reference': measurement(TEXT, 'reference 40 uM', '40', 'uM')}
    args['km_sheet_ref'] = KM_SHEET
    context = {field: witness(TEXT, quote) for field, quote in zip(CONTEXT_FIELDS,
        ('molecule P', 'analyte A', 'purified membrane', 'system S', 'initial flux', 'curve C'))}
    args['curve_contexts'] = {role: deepcopy(context) for role in PRIMITIVE_ORDER}
    args['observation_model'] = 'michaelis_menten'
    args['model_witnesses'] = [witness(TEXT, 'Michaelis Menten model')]
    return fix


def covariance(fix, matrix=None):
    first = read(fix)
    value = {'version': 'a105_transport_covariance_v1', 'primitive_order': list(PRIMITIVE_ORDER),
        'primitive_measurement_keys': [first['measurement_keys'][r] for r in PRIMITIVE_ORDER],
        'primitive_units': ['uM'] * 3,
        'covariance': matrix if matrix is not None else [[1., .25, 0.], [.25, 4., 0.], [0., 0., 9.]],
        'origin': 'synthetic'}
    fix[1][COVARIANCE] = {'artifact_ref': 'artifact_' + '4' * 24, 'content': json.dumps(value).encode()}
    fix[0]['covariance_source_ref'] = COVARIANCE
    return value


def calculate(parsed):
    return populate_transport_response({**{name: parsed[name] for name in (
        'values', 'curve_keys', 'measurement_keys', 'covariance', 'variance_status', 'observation_model')},
        'origin': 'synthetic'})


def test_all_unknown_exact_contract_and_no_mutation_or_original_km_read():
    fix = fixture()
    before = deepcopy(fix[:3])
    parsed = read(fix)
    assert set(parsed) == {'version', 'source_ref', 'source_kind', 'primitive_order', 'values', 'curve_keys',
        'measurement_keys', 'primitive_observations', 'curve_contexts', 'covariance', 'covariance_origin',
        'variance_status', 'observation_model', 'model_witnesses', 'source_refs', 'km_quantity'}
    assert parsed['version'] == 'a105_transport_inputs_v1'
    assert parsed['primitive_order'] == list(PRIMITIVE_ORDER)
    for field in ('values', 'curve_keys', 'measurement_keys', 'primitive_observations', 'curve_contexts'):
        assert parsed[field] == dict.fromkeys(PRIMITIVE_ORDER)
    assert parsed['covariance'] is parsed['covariance_origin'] is parsed['km_quantity'] is None
    assert parsed['source_refs'] == [SOURCE]
    assert fix[3] == [('source', SOURCE, 'original')]
    assert fix[:3] == before


def test_selected_concentrations_and_authoritative_km_supply_common_curve_calculator():
    fix = populated()
    before = deepcopy(fix[:3])
    parsed = read(fix)
    assert parsed['values'] == {'substrate_test': 10., 'substrate_reference': 40., 'km': 16.5}
    assert parsed['km_quantity'] == fix[2] == parsed['primitive_observations']['km']
    assert parsed['km_quantity']['reported_uncertainty_kind'] == 'unspecified'
    assert parsed['source_refs'] == [SOURCE, KM_SHEET]
    assert ('source', KM_ORIGINAL, 'original') not in fix[3]
    assert ('source', KM_SHEET, 'original') not in fix[3]
    assert fix[3].count(('quantity', KM_SHEET)) == 1
    for role in PRIMITIVE_ORDER[:2]:
        observation = parsed['primitive_observations'][role]
        assert observation['role'] == role and observation['unit'] == 'uM'
        assert observation['measurement_key'].startswith('literature_measurement_')
    sheet = calculate(parsed)
    assert sheet['cells']['condition_response']['value'] == 113 / 212
    assert sheet['cells']['condition_response_variance']['unavailable_reason'] == 'primitive_covariance_not_supplied'
    assert fix[:3] == before
    parsed['km_quantity']['value'] = 0
    parsed['primitive_observations']['km']['unit'] = 'changed'
    parsed['curve_contexts']['km']['curve']['quote'] = 'changed'
    assert fix[2]['value'] == 16.5 and fix[2]['unit'] == 'uM'
    assert fix[0]['curve_contexts']['km']['curve']['quote'] == 'curve C'


def test_closed_detached_schema_and_nullable_contexts():
    fix = populated()
    validate_schema(fix[0], transport_response_population_schema())
    validate_schema(fixture()[0], transport_response_population_schema())
    schema = transport_response_population_schema()
    schema['properties']['source_kind']['enum'].append('bad')
    assert 'bad' not in transport_response_population_schema()['properties']['source_kind']['enum']
    fix[0]['curve_contexts']['km']['curve'] = None
    with pytest.raises(ContractError):
        validate_schema(fix[0], transport_response_population_schema())


@pytest.mark.parametrize('kind', ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture'])
def test_source_kind_is_declared_origin_not_a_quality_judgment(kind):
    fix = fixture()
    fix[0]['source_kind'] = kind
    assert read(fix)['source_kind'] == kind


@pytest.mark.parametrize('level', ['arguments', 'primitives', 'curve_contexts', 'context', 'witness', 'measurement'])
def test_closed_input_fields(level):
    fix = populated()
    args = fix[0]
    targets = {'arguments': args, 'primitives': args['primitives'], 'curve_contexts': args['curve_contexts'],
        'context': args['curve_contexts']['km'], 'witness': args['curve_contexts']['km']['curve'],
        'measurement': args['primitives']['substrate_test']}
    targets[level]['unexpected'] = 1
    with pytest.raises(ExperimentalContractError, match='closed_fields_required'):
        read(fix)


@pytest.mark.parametrize('field', ['source_kind', 'variance_status', 'observation_model'])
def test_unknown_interpretation_enums_rejected(field):
    fix = fixture()
    fix[0][field] = 'unsupported'
    with pytest.raises(ExperimentalContractError):
        read(fix)


def test_curve_identity_full_sha256_exact_canonical_ownership_and_aliases():
    fix = populated()
    parsed = read(fix)
    context = parsed['curve_contexts']['km']
    canonical = {field: {key: context[field][key] for key in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}
                 for field in CONTEXT_FIELDS}
    expected = 'transport_curve_' + hashlib.sha256(json.dumps(canonical, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert set(parsed['curve_keys'].values()) == {expected}
    assert len(expected) == len('transport_curve_') + 64
    for item in fix[0]['curve_contexts']['substrate_test'].values():
        item['representation'] = 'text'
    assert read(fix)['curve_keys']['substrate_test'] == expected
    # Reordered dictionary construction does not change the canonical key.
    fix[0]['curve_contexts']['km'] = dict(reversed(list(fix[0]['curve_contexts']['km'].items())))
    assert read(fix)['curve_keys']['km'] == expected


@pytest.mark.parametrize('field', CONTEXT_FIELDS)
def test_each_context_field_affects_identity_without_number_or_paper_aliasing(field):
    fix = populated()
    original = read(fix)['curve_keys']['km']
    if field == 'curve':
        fix[0]['curve_contexts']['km'][field] = witness(TEXT, 'curve C', occurrence=1)
    else:
        fix[0]['curve_contexts']['km'][field] = None
    assert read(fix)['curve_keys']['km'] != original


def test_curve_identity_includes_source_and_artifact_and_unknown_is_null():
    fix = populated()
    original = read(fix)['curve_keys']['km']
    fix[1][OTHER] = {'artifact_ref': ARTIFACT, 'content': TEXT.encode()}
    fix[0]['curve_contexts']['km']['curve']['source_ref'] = OTHER
    assert read(fix)['curve_keys']['km'] != original
    assert read(fix)['source_refs'] == [SOURCE, OTHER, KM_SHEET]
    fix[0]['curve_contexts']['km']['curve']['source_ref'] = SOURCE
    fix[1][SOURCE]['artifact_ref'] = 'artifact_' + '9' * 24
    assert read(fix)['curve_keys']['km'] != original
    fix[0]['curve_contexts']['km'] = None
    assert read(fix)['curve_keys']['km'] is None


def test_different_system_blocks_response_but_preserves_supported_native_and_single_arm_cells():
    fix = populated()
    fix[0]['curve_contexts']['substrate_reference']['experimental_system'] = witness(TEXT, 'system T')
    sheet = calculate(read(fix))
    assert sheet['cells']['condition_response']['value'] is None
    assert sheet['cells']['condition_response']['unavailable_reason'] == 'different_kinetic_curves'
    assert sheet['cells']['reference_saturation']['value'] is None
    assert sheet['cells']['test_saturation']['value'] == 10 / 26.5
    assert sheet['cells']['substrate_reference']['value'] == 40
    fix[0]['curve_contexts']['substrate_reference'] = None
    assert calculate(read(fix))['cells']['condition_response']['unavailable_reason'] == 'kinetic_curve_identity_not_supplied'


@pytest.mark.parametrize('change', [{'start': True}, {'start': -1}, {'end': 999999},
    {'quote': 'invented'}, {'representation': 'guessed'}, {'start': 1, 'end': 2, 'quote': 'µ'}])
def test_witness_bytes_utf8_boundaries_and_offsets_checked(change):
    fix = populated()
    fix[0]['curve_contexts']['km']['curve'].update(change)
    with pytest.raises(ExperimentalContractError):
        read(fix)


def test_present_context_requires_curve_witness_but_other_fields_can_be_unknown():
    fix = fixture()
    fix[0]['curve_contexts']['km'] = dict.fromkeys(CONTEXT_FIELDS)
    with pytest.raises(ExperimentalContractError, match='kinetic_curve_witness_required'):
        read(fix)
    fix[0]['curve_contexts']['km']['curve'] = witness(TEXT, 'curve C')
    parsed = read(fix)
    assert parsed['curve_keys']['km'] is not None
    assert parsed['values']['km'] is None
    assert parsed['curve_contexts']['km']['molecule'] is None


@pytest.mark.parametrize('text,number,unit,value', [
    ('amount 1e-2 mM', '1e-2', 'mM', 10), ('amount 10000 nM', '10000', 'nM', 10),
    ('amount 10 μM', '10', 'μM', 10), ('amount −10 uM', '−10', 'uM', -10),
])
def test_concentration_uses_existing_literal_parser_and_unit_conversion(text, number, unit, value):
    fix = fixture(text)
    fix[0]['primitives']['substrate_test'] = measurement(text, text, number, unit)
    observation = read(fix)['primitive_observations']['substrate_test']
    assert observation['value'] == value and observation['unit'] == 'uM'
    assert observation['raw_number'] == number and observation['raw_unit'] == unit


@pytest.mark.parametrize('text,quote,number,unit,error', [
    ('amount <10 uM', '10 uM', '10', 'uM', 'censored_or_approximate_point'),
    ('amount about 10 uM', '10 uM', '10', 'uM', 'censored_or_approximate_point'),
    ('amount ≈10 uM', '10 uM', '10', 'uM', 'censored_or_approximate_point'),
    ('amount 100 uM', '100 uM', '00', 'uM', 'partial_numeric_token'),
    ('amount 10 uM/min', '10 uM/min', '10', 'uM', 'partial_unit_token'),
    ('amount 10 mg', '10 mg', '10', 'mg', 'incompatible_primitive_unit'),
    ('amount 1e309 uM', '1e309 uM', '1e309', 'uM', 'finite_number_required'),
    ('amount 1e-999 uM', '1e-999 uM', '1e-999', 'uM', 'numerical_model_range'),
    ('amount 1e-323 nM', '1e-323 nM', '1e-323', 'nM', 'numerical_model_range'),
])
def test_partial_censored_approximate_and_nonrepresentable_concentrations_rejected(text, quote, number, unit, error):
    fix = fixture(text)
    fix[0]['primitives']['substrate_test'] = measurement(text, quote, number, unit)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize('mutation,error', [
    (lambda q: q.update(extra=1), 'closed_fields_required'),
    (lambda q: q.update(sheet_ref=OTHER), 'quantity_sheet_ref_mismatch'),
    (lambda q: q.update(unit='mM'), 'quantity_unit_mismatch'),
    (lambda q: q.update(value=True), 'finite_number_required'),
    (lambda q: q.update(value=math.inf), 'finite_number_required'),
    (lambda q: q.update(value=None), 'finite_number_required'),
    (lambda q: q.update(measurement_key=''), 'nonempty_source_token_required'),
])
def test_authoritative_quantity_shape_is_defensive_but_reader_never_infers_it(mutation, error):
    fix = populated()
    mutation(fix[2])
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


def test_callback_authority_errors_propagate_without_repair_or_fallback_reads():
    fix = populated()
    def denied(*_):
        raise PermissionError('not actually received')
    with pytest.raises(PermissionError, match='not actually received'):
        read_transport_inputs(fix[0], read_source=fix[4], read_quantity=denied)
    assert all(call[1] == SOURCE for call in fix[3])
    with pytest.raises(PermissionError, match='not actually received'):
        read_transport_inputs(fix[0], read_source=denied, read_quantity=fix[5])


@pytest.mark.parametrize('status,model', [('known', 'unknown'), ('estimated', 'unknown'), ('unknown', 'michaelis_menten')])
def test_model_or_variance_interpretation_requires_actual_source_witness(status, model):
    fix = fixture()
    fix[0].update(variance_status=status, observation_model=model)
    with pytest.raises(ExperimentalContractError, match='model_witness_required'):
        read(fix)
    fix[0]['model_witnesses'] = [witness(TEXT, 'Michaelis Menten model')]
    assert read(fix)['variance_status'] == status
    fix[0]['model_witnesses'][0]['quote'] = 'invented'
    with pytest.raises(ExperimentalContractError, match='source_quote_mismatch'):
        read(fix)


def test_canonical_covariance_is_not_rescaled_from_native_concentration_unit():
    fix = populated()
    text = TEXT.replace('test 10 µM', 'test 10000 nM')
    fix[1][OTHER] = {'artifact_ref': 'artifact_' + '5' * 24, 'content': text.encode()}
    fix[0]['primitives']['substrate_test'] = measurement(text, 'test 10000 nM', '10000', 'nM', source=OTHER)
    original = covariance(fix)
    fix[0]['variance_status'] = 'known'
    parsed = read(fix)
    assert parsed['covariance'] == original['covariance']
    assert parsed['values']['substrate_test'] == 10
    assert parsed['covariance_origin'] == 'synthetic'
    assert parsed['source_refs'] == [SOURCE, OTHER, COVARIANCE, KM_SHEET]
    assert calculate(parsed)['cells']['condition_response_variance']['value'] > 0


@pytest.mark.parametrize('mutation,error', [
    (lambda p: p.update(version='wrong'), 'covariance_version_mismatch'),
    (lambda p: p.update(primitive_order=list(reversed(PRIMITIVE_ORDER))), 'covariance_primitive_order_mismatch'),
    (lambda p: p['primitive_measurement_keys'].__setitem__(0, 'wrong'), 'covariance_measurement_owner_mismatch'),
    (lambda p: p['primitive_units'].__setitem__(0, 'nM'), 'covariance_primitive_unit_mismatch'),
    (lambda p: p.update(covariance=[[0]]), 'three_by_three_covariance_required'),
    (lambda p: p['covariance'][0].__setitem__(0, True), 'finite_number_required'),
    (lambda p: p['covariance'][0].__setitem__(0, '1'), 'finite_number_required'),
    (lambda p: p['covariance'][0].__setitem__(0, math.inf), 'finite_number_required'),
    (lambda p: p.update(extra=1), 'closed_fields_required'),
    (lambda p: p.update(origin='inferred'), 'unknown_covariance_origin'),
])
def test_covariance_exact_ownership_shape_units_and_numeric_boundary(mutation, error):
    fix = populated()
    payload = covariance(fix)
    mutation(payload)
    fix[1][COVARIANCE]['content'] = json.dumps(payload).encode()
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize('raw,error', [
    (b'{"version":"one","version":"two"}', 'duplicate_json_key'),
    (b'{"nested":{"x":1,"x":2}}', 'duplicate_json_key'),
    (b'{"x":NaN}', 'finite_number_required'), (b'{"x":Infinity}', 'finite_number_required'),
    (b'{"x":1e999}', 'finite_number_required'), (b'{"x":1e-999}', 'numerical_model_range'),
    (b'{"x":-1e-999}', 'numerical_model_range'), (b'\xff', 'covariance_json_required'),
    (b'{} trailing', 'covariance_json_required'),
])
def test_covariance_strict_json_no_duplicate_nonfinite_or_lexical_underflow(raw, error):
    fix = populated()
    covariance(fix)
    fix[1][COVARIANCE]['content'] = raw
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize('missing', PRIMITIVE_ORDER)
def test_covariance_requires_all_actual_operand_owners(missing):
    fix = populated()
    covariance(fix)
    if missing == 'km':
        fix[0]['km_sheet_ref'] = None
    else:
        fix[0]['primitives'][missing] = None
    with pytest.raises(ExperimentalContractError, match='complete_covariance_owners_required'):
        read(fix)


def test_covariance_extreme_json_integer_does_not_escape_range_check():
    fix = populated()
    payload = covariance(fix)
    payload['covariance'][0][0] = 10**400
    fix[1][COVARIANCE]['content'] = json.dumps(payload).encode()
    with pytest.raises(ExperimentalContractError, match='finite_number_required'):
        read(fix)


@pytest.mark.parametrize('matrix,error', [
    ([[1, 1, 0], [0, 1, 0], [0, 0, 1]], 'symmetric_covariance_required'),
    ([[1, 2, 0], [2, 1, 0], [0, 0, 1]], 'positive_semidefinite_covariance_required'),
])
def test_psd_and_symmetry_are_calculator_responsibilities(matrix, error):
    fix = populated()
    covariance(fix, matrix)
    parsed = read(fix)
    assert parsed['covariance'] == matrix
    with pytest.raises(ExperimentalContractError, match=error):
        calculate(parsed)


def test_physical_alias_is_preserved_and_calculator_rejects_inconsistent_covariance():
    fix = populated()
    fix[0]['primitives']['substrate_reference'] = deepcopy(fix[0]['primitives']['substrate_test'])
    covariance(fix)
    parsed = read(fix)
    assert parsed['measurement_keys']['substrate_test'] == parsed['measurement_keys']['substrate_reference']
    with pytest.raises(ExperimentalContractError, match='shared_measurement_covariance_mismatch'):
        calculate(parsed)


def test_distinct_equal_concentrations_have_distinct_physical_owners():
    text = 'test 10 uM; reference 10 uM'
    fix = fixture(text)
    fix[0]['primitives'] = {'substrate_test': measurement(text, 'test 10 uM', '10', 'uM'),
        'substrate_reference': measurement(text, 'reference 10 uM', '10', 'uM')}
    parsed = read(fix)
    assert parsed['values']['substrate_test'] == parsed['values']['substrate_reference']
    assert parsed['measurement_keys']['substrate_test'] != parsed['measurement_keys']['substrate_reference']
