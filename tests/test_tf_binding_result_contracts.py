"""Engineering controls for the TF typed Source-group boundary.

The reused score/model bytes are explicit synthetic observations. These tests
exercise data validation only and make no native-run or Source-custody claim.
"""
from copy import deepcopy
import hashlib
import json
import math

import pytest

from gene_annotation_episode import tf_binding_measurements as core
from gene_annotation_episode import tf_binding_result_contracts as contracts
from test_tf_binding_measurements import engineered_sheet, selection


SOURCE = 'source_' + 'c' * 24


@pytest.fixture(scope='module')
def records():
    sheet = engineered_sheet()
    components = core.calculate_tf_binding_components(sheet, selection(sheet))
    returned = core.project_tf_binding_return(components, SOURCE)
    value = {key: item for key, item in returned.items() if key not in ('version', 'source_ref')}
    return components, returned, value


def nodes(value, path=()):
    if type(value) is dict:
        yield path, value
        for key, child in value.items(): yield from nodes(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value): yield from nodes(child, path + (index,))


def test_exact_value_and_return_roundtrip_retains_all_original_public_data(records):
    _, returned, value = records
    checked_value = contracts.validate_tf_binding_value(value)
    checked_return = contracts.validate_tf_binding_return(returned)
    assert checked_value == value and checked_return == returned
    assert contracts.tf_binding_return(value, source_ref=SOURCE) == returned
    assert 'version' not in checked_value and 'source_ref' not in checked_value
    checked_value['hits'][0]['score']['value'] = 99
    assert value['hits'][0]['score']['value'] == 2.


def test_value_validation_uses_no_source_substitution_or_scientific_work(records, monkeypatch):
    _, _, value = records
    def forbidden(*args, **kwargs): raise AssertionError('validation attempted custody construction or calculation')
    monkeypatch.setattr(contracts, 'validate_tf_binding_return', forbidden)
    monkeypatch.setattr(core.locations, 'location', forbidden)
    monkeypatch.setattr(core, 'calculate_tf_binding_components', forbidden)
    monkeypatch.setattr(core, 'project_tf_binding_return', forbidden)
    monkeypatch.setattr(core, 'tf_binding_model_normalization_issues', forbidden)
    monkeypatch.setattr(core, '_relative_normalization', forbidden)
    assert contracts.validate_tf_binding_value(value) == value
    assert core.validate_tf_binding_public_value(value) == value


def test_only_actual_top_source_is_semantic_and_input_associations_stay_opaque():
    schema = contracts.tf_binding_result_schema('Return')
    semantic = [(path, node) for path, node in nodes(schema)
        if node.get('format') in ('reference', 'identifier', 'accession')]
    assert [path for path, _ in semantic] == [('$defs', 'Return', 'properties', 'source_ref')]
    assert semantic[0][1]['x-reference-namespace'] == 'source'
    inputs = schema['$defs']['Input']['properties']
    for key in ('artifact_id', 'upstream_source_id'):
        assert all('format' not in node and 'x-reference-namespace' not in node for _, node in nodes(inputs[key]))
    assert all(not isinstance(node.get('format'), str) and 'x-reference-namespace' not in node
        for _, node in nodes(contracts.tf_binding_result_schema('Value')))


def test_fact_source_schema_is_exact_closed_detached_and_content_identified():
    fact, = contracts.tf_binding_fact_sources().values()
    assert set(contracts.tf_binding_fact_sources()) == {'tf_binding_outcomes'}
    report = fact['report_schema']; original = deepcopy(report)
    assert fact['type'] == 'array' and report['type'] == 'array' and report['x-source'] == contracts.FACT_SOURCE
    assert report['items'] == {'$ref': '#/$defs/Return'}
    assert report['$defs'] == contracts.tf_binding_result_schema()['$defs']
    without_id = {key: item for key, item in report.items() if key != '$id'}
    digest = hashlib.sha256(json.dumps(without_id, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assert report['$id'] == 'urn:gene-annotation:tf-binding-return:' + digest
    for _, node in nodes(report):
        if node.get('type') == 'object':
            assert node['additionalProperties'] is False and set(node['required']) == set(node['properties'])
    report['$defs']['Return']['properties']['status'] = {'const': 'invented'}
    assert contracts.tf_binding_fact_sources()[contracts.FACT_SOURCE]['report_schema'] == original
    with pytest.raises(ValueError, match='schema_kind_invalid'): contracts.tf_binding_result_schema('Sheet')


@pytest.mark.parametrize('fault', ['source_ref', 'version', 'location', 'operand_evidence', 'evidence', 'requirement_ids', 'control_ref'])
def test_public_value_rejects_source_identity_and_private_control_fields(records, fault):
    value = deepcopy(records[2])
    if fault == 'source_ref': value['source_ref'] = SOURCE
    elif fault == 'version': value['version'] = core.RETURN_VERSION
    elif fault == 'location': value['hits'][0]['score']['location'] = None
    elif fault == 'operand_evidence': value['relative_normalizations'][0]['operand_evidence'] = {}
    elif fault in ('evidence', 'requirement_ids'): value['totals']['finite_scores'][fault] = []
    else: value['control_ref'] = 'artifact_' + 'd' * 64
    with pytest.raises(ValueError, match='tf_binding_value_invalid'): contracts.validate_tf_binding_value(value)


def corrupt(value, fault):
    if fault == 'returned_count': value['totals']['returned_candidate_rows']['value'] = 0
    elif fault == 'interval': value['raw_threshold_matches'][0]['end_0based_exclusive'] += 1
    elif fault == 'score_bits': value['raw_threshold_matches'][0]['score']['bits_hex'] = '00000000'
    elif fault == 'classification': value['raw_threshold_matches'][0]['score']['classification'] = 'nan'
    elif fault == 'threshold_operand': value['numeric_authority']['threshold_binary64_hex'] = '0000000000000000'
    elif fault == 'bool_count': value['totals']['finite_scores']['value'] = True
    elif fault == 'float_integer': value['inputs'][0]['size_bytes'] = float(value['inputs'][0]['size_bytes'])
    elif fault == 'complete_failed': value['execution']['native_outcome'] = 'failed'
    elif fault == 'eligibility': value['raw_threshold_matches'][0]['model_normalization_eligible'] = 1
    elif fault == 'normalization_identity': value['relative_normalizations'][0]['normalization_id'] = 'invented'
    elif fault == 'selected_coverage': value['selected_scans'][0]['coverage']['usable_elements'] = 0
    elif fault == 'input_identity': value['inputs'][0]['artifact_id'] = 'artifact_' + '0' * 64
    else: raise AssertionError('unknown engineering fault')


@pytest.mark.parametrize('fault', ['returned_count', 'interval', 'score_bits', 'classification', 'threshold_operand',
    'bool_count', 'float_integer', 'complete_failed', 'eligibility', 'normalization_identity', 'selected_coverage', 'input_identity'])
def test_private_and_public_records_share_the_same_crossfield_authority(records, fault):
    private, public = deepcopy(records[0]), deepcopy(records[2])
    corrupt(private, fault); corrupt(public, fault)
    with pytest.raises(ValueError): core.validate_tf_binding_components(private)
    with pytest.raises(ValueError): core.validate_tf_binding_public_value(public)
    with pytest.raises(ValueError, match='tf_binding_value_invalid'): contracts.validate_tf_binding_value(public)


@pytest.mark.parametrize('source_ref', ['', 'artifact_' + 'a' * 64, 'source_' + 'a' * 23, 'source_' + 'A' * 24, True])
def test_return_requires_a_real_source_namespace_identity_syntax(records, source_ref):
    with pytest.raises(ValueError, match='tf_binding_return_invalid'):
        contracts.tf_binding_return(records[2], source_ref=source_ref)


@pytest.mark.parametrize('kind', ['nonfinite', 'invalid_normalization', 'zero_possible', 'unavailable'])
def test_public_contract_retains_extended_partial_zero_and_unavailable_distinctions(kind):
    if kind == 'nonfinite':
        sheet = engineered_sheet(dna=b'ANC', counts={'A': [1], 'C': [0], 'G': [0], 'T': [0]},
            pwm=[[1], [0], [0], [0]], pssm=[[2], [-math.inf], [-math.inf], [-math.inf]],
            rc=[[-math.inf], [-math.inf], [-math.inf], [2]], background=dict.fromkeys('ACGT', .25),
            bounds=(-math.inf, 2), scores={'+': [2, math.nan, -math.inf]}, strands=('+',))
        threshold = 0.
    elif kind == 'invalid_normalization':
        sheet = engineered_sheet(dna=b'AAA', counts=dict.fromkeys('ACGT', [1e308]),
            pwm=[[0], [0], [0], [0]], pssm=[[-math.inf]] * 4, rc=[[-math.inf]] * 4,
            background=dict.fromkeys('ACGT', .25), bounds=(-math.inf, -math.inf),
            scores={'+': [-math.inf] * 3}, strands=('+',), native_outcome='failed')
        threshold = -1e300
    elif kind == 'zero_possible':
        sheet = engineered_sheet(dna=b'G', scores={'+': [], '-': []}, scan_state='zero_possible'); threshold = 0.
    else:
        sheet = engineered_sheet(scan_state='unavailable', native_outcome='failed'); threshold = 0.
    components = core.calculate_tf_binding_components(sheet, selection(sheet, threshold))
    returned = core.project_tf_binding_return(components, SOURCE)
    assert contracts.validate_tf_binding_return(returned) == returned
    assert json.loads(json.dumps(returned, allow_nan=False)) == returned
    assert contracts.tf_binding_return({key: item for key, item in returned.items()
        if key not in ('version', 'source_ref')}, source_ref=SOURCE) == returned
    if kind == 'nonfinite':
        relative = returned['hits'][0]['relative_score']
        assert relative['value'] is None and relative['classification'] == 'nan' and relative['state'] == 'undefined'
    elif kind == 'invalid_normalization':
        assert returned['raw_threshold_matches'] and returned['hits'] == []
        assert returned['totals']['model_eligible_candidate_sites']['value'] is None
    elif kind == 'zero_possible':
        assert returned['status'] == 'complete' and returned['totals']['full_matched_scores']['value'] == 0
    else:
        assert returned['status'] == 'unavailable' and returned['totals']['full_matched_scores']['value'] is None


def test_rewrapping_a_full_return_as_a_source_free_packet_is_rejected(records):
    with pytest.raises(ValueError, match='tf_binding_value_invalid'):
        contracts.tf_binding_return(records[1], source_ref='source_' + 'e' * 24)


@pytest.mark.parametrize('background', [
    {'A': 2, 'C': 1., 'G': .5, 'T': .5},
    {'A': 0, 'C': 0., 'G': 0, 'T': 0.},
])
def test_declared_parameters_survive_saved_threshold_changes_without_normalization(background, monkeypatch):
    # These are explicitly engineered observations, including a model whose
    # zero background is invalid. Parameter retention does not repair it or
    # establish that a native producer generated these supplied score bytes.
    sheet = engineered_sheet(background=background, native_outcome='failed')
    original = deepcopy(sheet)
    expected = {'background': background, 'pseudocounts': dict.fromkeys('ACGT', 0.)}
    def forbidden(*args, **kwargs):
        raise AssertionError('retained parameter projection attempted input decoding or native preparation')
    monkeypatch.setattr(core, 'decode_tf_binding_inputs', forbidden)
    monkeypatch.setattr(core, 'populate_tf_binding_sheet', forbidden)
    first = core.calculate_tf_binding_components(sheet, selection(sheet, 2.))
    second = core.calculate_tf_binding_components(sheet, selection(sheet, 0.))
    for components in (first, second):
        returned = core.project_tf_binding_return(components, SOURCE)
        value = {key: item for key, item in returned.items() if key not in ('version', 'source_ref')}
        for actual in (components['parameters'], returned['parameters'],
                contracts.validate_tf_binding_value(value)['parameters'],
                contracts.tf_binding_return(value, source_ref=SOURCE)['parameters']):
            assert json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    assert sheet == original and first['selection']['raw_threshold'] == 2. and second['selection']['raw_threshold'] == 0.
    assert len(first['raw_threshold_matches']) == 2 and len(second['raw_threshold_matches']) == 4
    first['parameters']['pseudocounts']['A'] = 99
    assert second['parameters'] == sheet['invocation']['parameters'] == expected


def test_declared_parameter_contract_keeps_nonzero_pseudocounts_without_recalculation(records, monkeypatch):
    # This checks the literal metadata contract, not a parameter-to-score fit.
    private = deepcopy(records[0])
    expected = {'background': {'A': 3, 'C': 2., 'G': 1, 'T': 0.},
        'pseudocounts': {'A': .125, 'C': 2, 'G': 0., 'T': 4.5}}
    private['parameters'] = deepcopy(expected)
    def forbidden(*args, **kwargs): raise AssertionError('parameter validation attempted scientific work')
    monkeypatch.setattr(core, 'calculate_tf_binding_components', forbidden)
    assert core.validate_tf_binding_components(private)['parameters'] == expected
    returned = core.project_tf_binding_return(private, SOURCE)
    value = {key: item for key, item in returned.items() if key not in ('version', 'source_ref')}
    assert contracts.validate_tf_binding_return(returned)['parameters'] == expected
    assert contracts.validate_tf_binding_value(value)['parameters'] == expected
    definitions = contracts.tf_binding_result_schema()['$defs']
    assert definitions['Parameters']['required'] == ['background', 'pseudocounts']
    assert definitions['BaseParameterMap']['required'] == list('ACGT')
    assert definitions['BaseParameterMap']['additionalProperties'] is False
    assert all(node == {'type': 'number', 'minimum': 0}
        for node in definitions['BaseParameterMap']['properties'].values())


@pytest.mark.parametrize('fault', ['missing_parameters', 'extra_parameter', 'missing_background',
    'missing_pseudocounts', 'missing_base', 'extra_base', 'negative', 'boolean', 'string',
    'nan', 'positive_infinity', 'negative_infinity'])
def test_declared_parameter_fields_are_required_closed_finite_nonnegative_maps(records, fault):
    targets = (None,) if fault in ('missing_parameters', 'extra_parameter', 'missing_background',
        'missing_pseudocounts') else ('background', 'pseudocounts')
    for target in targets:
        private, value = deepcopy(records[0]), deepcopy(records[2])
        for record in (private, value):
            if fault == 'missing_parameters': del record['parameters']
            elif fault == 'extra_parameter': record['parameters']['effective_background'] = dict.fromkeys('ACGT', .25)
            elif fault == 'missing_background': del record['parameters']['background']
            elif fault == 'missing_pseudocounts': del record['parameters']['pseudocounts']
            elif fault == 'missing_base': del record['parameters'][target]['A']
            elif fault == 'extra_base': record['parameters'][target]['N'] = 0
            else:
                record['parameters'][target]['A'] = {'negative': -1., 'boolean': True, 'string': '0',
                    'nan': math.nan, 'positive_infinity': math.inf, 'negative_infinity': -math.inf}[fault]
        with pytest.raises(ValueError): core.validate_tf_binding_components(private)
        with pytest.raises(ValueError): core.validate_tf_binding_public_value(value)
        with pytest.raises(ValueError, match='tf_binding_value_invalid'): contracts.validate_tf_binding_value(value)
        with pytest.raises(ValueError, match='tf_binding_return_invalid'):
            contracts.validate_tf_binding_return(dict(version=core.RETURN_VERSION, source_ref=SOURCE, **value))
