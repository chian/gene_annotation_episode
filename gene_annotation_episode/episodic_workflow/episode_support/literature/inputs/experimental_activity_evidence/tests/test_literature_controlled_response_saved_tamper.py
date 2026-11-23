"""Saved v3 extractions: each test tampers one field of a valid saved record and asserts its refusal.

Constructed source text and pixels only (the v3 constructed selections); no paper,
model or native execution. Every baseline record is first shown to round-trip.
"""
from copy import deepcopy as cp
import errno
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_source_inputs as source
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_source_inputs import Fixture, CASES
ROLES = shared.PRIMITIVE_ORDER
A, B1, C, B0 = ROLES
MISSING_REF = 'source_' + 'e' * 24


def ci_uncertainty(f):
    f.args['arms'][A]['reported_uncertainty'] = cp(CASES[7]['selection']['arms'][A]['reported_uncertainty'])


def sd_uncertainty(f):
    f.args['arms'][A]['reported_uncertainty'] = cp(CASES[6]['selection']['arms'][A]['reported_uncertainty'])


def unitless_reading(f):
    f.text_measurement(B1, 'B unitless mean: 4.', '4', unit=None)


def made(modify=None, **kwargs):
    f = Fixture(kwargs.pop('index', 0), **kwargs)
    if modify is not None:
        modify(f)
    result = f.read()
    assert source.validate_controlled_response_extraction(f.args, result) == result
    return f, result


@pytest.fixture(scope='module')
def records():
    return {'base': made(), 'ci': made(ci_uncertainty), 'sd': made(sd_uncertainty), 'companion': made(companion=True), 'unselected': made(index=1), 'unitless': made(unitless_reading)}


def refused(f, record, code):
    with pytest.raises(ExperimentalContractError) as error:
        source.validate_controlled_response_extraction(f.args, record)
    assert error.value.code == code


def unavailable(witness):
    witness.update(artifact_ref=None, byte_sha256=None, canonical_locator=None, authentication='unavailable')


def source_down(r):
    record = next((s for s in r['sources'] if s['source_ref'] == 'source_b31b2904af7eb367c6d9c79b'))
    record.update(state='unavailable', artifact_ref=None, byte_sha256=None)


def both_documents(r, change):
    for row in r['covariance_document_scopes']:
        change(row['document'])


def measurement(r, role=A):
    return r['arms'][role]['measurement']


BASE = {
    'saved_extraction_schema_invalid': lambda r: r.update(version='unrecognized_version'),
    'saved_selection_mismatch-extraction': lambda r: r['selection']['relationships']['nonintended_conditions'].update(value='unknown', witnesses=[]),
    'saved_duplicate_source': lambda r: r['sources'].append(cp(r['sources'][0])),
    'saved_source_identity_mismatch-blank_artifact': lambda r: r['sources'][0].update(artifact_ref=' '),
    'artifact_content_conflict': lambda r: r['sources'][1].update(artifact_ref=r['sources'][0]['artifact_ref']),
    'saved_source_state_mismatch': lambda r: r['sources'][0].update(state='unavailable'),
    'saved_source_roster_mismatch': lambda r: r['sources'].pop(),
    'saved_image_roster_mismatch': lambda r: r.update(images=[]),
    'unavailable_witness_identity_mismatch': lambda r: r['arms'][A]['context']['subject'].update(authentication='unavailable'),
    'saved_witness_identity_mismatch': lambda r: r['arms'][A]['context']['subject']['canonical_locator'].update(start=144),
    'saved_source_identity_mismatch-unavailable_source': source_down,
    'saved_covariance_scope_roster_mismatch': lambda r: r['covariance_document_scopes'].pop(),
    'saved_selection_mismatch-scope_document': lambda r: r['covariance_document_scopes'][0].update(document=None),
    'saved_covariance_source_mismatch': lambda r: r['covariance_document_scopes'][0]['document'].update(source_ref='source_' + 'f' * 24),
    'saved_covariance_document_conflict': lambda r: r['covariance_document_scopes'][1]['document'].update(source_validation='unassessed'),
    'saved_selection_mismatch-arm': lambda r: r['arms'].update({A: None}),
    'saved_meaning_identity_mismatch': lambda r: r['arms'][A]['meanings']['endpoint'].update(canonical_id='controlled_endpoint_' + '0' * 24),
    'saved_selection_mismatch-meaning': lambda r: r['arms'][A]['meanings']['endpoint'].update(witnesses=[]),
    'saved_interpretation_mismatch': lambda r: r['arms'][A]['protein_arrangement'].update(effective_value='unknown'),
    'saved_selection_mismatch-interpretation': lambda r: r['arms'][A]['protein_arrangement'].update(witnesses=[]),
    'saved_measurement_identity_mismatch': lambda r: measurement(r).update(reading_status='ambiguous'),
    'saved_measurement_identity_mismatch-observation': lambda r: measurement(r).update(source_observation_id='controlled_source_token_' + '0' * 24),
    'saved_canonical_display_mismatch': lambda r: measurement(r)['canonical_display'].update(value=0.011),
    'saved_selection_mismatch-candidates': lambda r: measurement(r).update(candidates=[]),
    'saved_selection_mismatch-measurement': lambda r: measurement(r)['selection']['literal']['candidates'][0].update(number_end=9),
    'saved_numeric_literal_mismatch': lambda r: measurement(r)['candidates'][0].update(native_value=11.0),
    'saved_numeric_literal_mismatch-relation': lambda r: measurement(r)['candidates'][0].update(relation='unresolved'),
    'saved_numeric_location_mismatch': lambda r: measurement(r)['candidates'][0].update(raw_expression='1'),
    'saved_numeric_state_mismatch': lambda r: measurement(r)['candidates'][0].update(status='unsupported'),
    'saved_unavailable_number_mismatch': lambda r: unavailable(measurement(r)['candidates'][0]['witness']),
    'saved_selection_mismatch-number': lambda r: measurement(r)['candidates'][0]['selection'].update(number_end=9),
    'saved_unit_literal_mismatch': lambda r: measurement(r)['unit'].update(raw_unit='umol/min'),
    'saved_unit_scale_mismatch': lambda r: measurement(r)['unit'].update(exact_scale={'numerator': '1', 'denominator': '1'}),
    'saved_unit_registry_mismatch': lambda r: measurement(r)['unit'].update(native_registry_unit='umol/min'),
    'saved_selection_mismatch-unit_absent': lambda r: measurement(r).update(unit=None),
    'saved_selection_mismatch-unit_selection': lambda r: measurement(r)['unit']['selection'].update(end=700, start=691),
    'saved_graph_measurement_mismatch-text_arm': lambda r: r['arms'][A].update(graph_details=cp(r['arms'][B0]['graph_details'])),
    'saved_selection_mismatch-uncertainty': lambda r: r['arms'][A]['reported_uncertainty']['selection'].update(statistic={'value': 'unknown', 'witnesses': []}),
    'saved_uncertainty_projection_mismatch': lambda r: r['arms'][A]['reported_uncertainty']['canonical'].update(statistic='unknown'),
    'saved_operand_projection_mismatch': lambda r: r['arms'][A]['calculation_operand'].update(value=11.0),
    'saved_covariance_source_mismatch-raw_text': lambda r: both_documents(r, lambda d: d.update(raw_text=d['raw_text'] + ' ')),
    'saved_covariance_document_mismatch': lambda r: both_documents(r, lambda d: d.update(source_validation='invalid')),
    'saved_source_projection_mismatch': lambda r: r.update(diagnostics=[]),
}


@pytest.mark.parametrize('name', list(BASE))
def test_one_tampered_field_of_a_saved_extraction_is_refused(records, name):
    f, result = records['base']
    record = cp(result)
    BASE[name](record)
    refused(f, record, name.split('-')[0])


def test_saved_measurement_checks_must_be_callable(records):
    f, result = records['base']
    with pytest.raises(ExperimentalContractError, match='saved_measurement_checks_required'):
        shared.validate_controlled_response_saved_science(f.args, cp(result), measurement_checks=None)


def test_saved_arm_for_an_unnominated_role_is_refused():
    def absent(f):
        f.args['arms'][A] = None
        f.args['covariance']['bindings'][A] = None
    f, result = made(absent, local=False)
    record = cp(result)
    record['arms'][A] = cp(record['arms'][C])
    refused(f, record, 'saved_selection_mismatch')


@pytest.mark.parametrize('change', [lambda r: r.update(companion_extractions=[]), lambda r: r['companion_extractions'][0].update(reading_key='A-other')], ids=['missing', 'renamed'])
def test_saved_companion_roster_is_the_nominated_roster(records, change):
    f, result = records['companion']
    record = cp(result)
    change(record)
    refused(f, record, 'saved_companion_roster_mismatch')


@pytest.mark.parametrize('change,code', [
    (lambda m: m.update(reading_status='exact'), 'saved_measurement_projection_mismatch'),
    (lambda m: m['canonical_display'].update(approximate=True), 'saved_measurement_projection_mismatch'),
], ids=['status', 'display'])
def test_unselected_measurement_record_is_fixed(records, change, code):
    f, result = records['unselected']
    assert f.args['arms'][B1]['measurement'] is None
    record = cp(result)
    change(record['arms'][B1]['measurement'])
    refused(f, record, code)


def test_absent_unit_record_cannot_claim_a_unit(records):
    f, result = records['unitless']
    unit = result['arms'][B1]['measurement']['unit']
    assert unit['selection'] is None and unit['status'] == 'unknown'
    record = cp(result)
    record['arms'][B1]['measurement']['unit']['status'] = 'supported'
    refused(f, record, 'saved_unknown_unit_mismatch')


CI = {
    'saved_selection_mismatch-interval': lambda u: u['interval']['selection'].update(lower_start=13),
    'saved_interval_literal_mismatch': lambda u: u['interval'].update(raw_values=['8', '13']),
    'saved_interval_literal_mismatch-values': lambda u: u['interval'].update(values=[8.0, 13.0]),
    'saved_confidence_literal_mismatch': lambda u: u['confidence_level'].update(value=0.9),
    'saved_count_literal_mismatch': lambda u: u['count']['reading'].update(raw_number='4'),
    'saved_count_literal_mismatch-value': lambda u: u['count']['reading'].update(value=4),
    'saved_interpretation_mismatch': lambda u: u['meanings']['statistic'].update(effective_value='sd'),
    'saved_selection_mismatch-magnitude': lambda u: u.update(magnitude={'selection': {'witness': cp(u['interval']['selection']['witness']), 'number_start': 14, 'number_end': 15}, 'witness': cp(u['interval']['witness']), 'raw_expression': '8', 'native_value': 8.0, 'relation': 'point', 'approximate': False, 'source_locator': None, 'status': 'parsed', 'diagnostics': []}),
    'saved_uncertainty_projection_mismatch': lambda u: u['canonical'].update(interval=[0.008, 0.013]),
}


@pytest.mark.parametrize('name', list(CI))
def test_one_tampered_saved_confidence_interval_field_is_refused(records, name):
    f, result = records['ci']
    canonical = result['arms'][A]['reported_uncertainty']['canonical']
    # [8, 12] nmol/min at 95%, n = 3: canonical umol/min = [8/1000, 12/1000].
    assert canonical['statistic'] == 'ci' and canonical['interval'] == [0.008, 0.012] and canonical['confidence_level'] == 0.95 and canonical['count'] == 3
    record = cp(result)
    CI[name](record['arms'][A]['reported_uncertainty'])
    refused(f, record, name.split('-')[0])


def test_saved_uncertainty_piece_absent_from_the_nomination_is_refused(records):
    f, result = records['sd']
    _, ci = records['ci']
    canonical = result['arms'][A]['reported_uncertainty']['canonical']
    # SD 1.2 nmol/min = 0.0012 umol/min.
    assert canonical['statistic'] == 'sd' and canonical['magnitude'] == 0.0012 and canonical['count'] == 3
    for key in ('interval', 'confidence_level'):
        record = cp(result)
        record['arms'][A]['reported_uncertainty'][key] = cp(ci['arms'][A]['reported_uncertainty'][key])
        refused(f, record, 'saved_selection_mismatch')
    record = cp(result)
    record['arms'][A]['reported_uncertainty']['magnitude']['native_value'] = 1.3
    refused(f, record, 'saved_numeric_literal_mismatch')


def defined_unit(f, *, missing=False):
    """A source-defined unit: 2 U/mg where one unit is 2 nmol of NADH per min."""
    endpoint, bridge, clause = ('oxidation of NADH', 'One unit was defined as 2 nmol of NADH per min.', '2 nmol of NADH per min')
    text = 'Actual alternate A optical response: 2 U/mg.'
    f.append('Definition endpoint: ' + endpoint + '.')
    f.append(bridge)
    f.text_measurement(A, text, '2', unit='U/mg')
    arm = f.args['arms'][A]

    def meaning(w):
        return {'status': 'known', 'label': w['quote'], 'witnesses': [w], 'canonical_witness': cp(w), 'canonical_correspondence': {'value': 'same', 'witnesses': [cp(w)]}}
    arm['endpoint'] = meaning(f.witness(endpoint))
    arm['physical_observation'] = meaning(f.witness(text))
    f.args['covariance']['bindings'][A]['owner_witness'] = cp(arm['physical_observation']['canonical_witness'])
    raw = f.data[f.main_ref].decode()
    plain = lambda quote, start=0: f.witness(quote, tagged=False, start=start)
    definition = {'bridge': plain(bridge), 'clause': plain(clause), 'amount': f.number(clause, '2'), 'amount_unit': plain('nmol', raw.index(bridge)), 'time_unit': plain('min', raw.index(bridge)), 'endpoint': plain(endpoint), 'endpoint_entity': plain('NADH', raw.index(endpoint)), 'definition_entity': plain('NADH', raw.index(bridge))}
    unit = f.witness('U/mg', tagged=False, start=raw.index(text))
    if missing:
        unit = {'source_ref': MISSING_REF, 'representation': 'original', 'start': 0, 'end': 4, 'quote': 'U/mg'}
    arm['measurement']['unit'] = {'kind': 'source_defined_rate_unit', 'witness': unit, 'definition': definition}


def test_source_defined_unit_is_converted_once_and_its_saved_scale_is_checked():
    f, result = made(defined_unit)
    arm = result['arms'][A]
    assert arm['measurement']['unit']['status'] == 'supported' and arm['measurement']['unit']['canonical_unit'] == 'umol/min/mg'
    # 1 U = 2 nmol/min, so 2 U/mg = 4 nmol/min/mg = 0.004 umol/min/mg (exact scale 2/1000 per U/mg).
    assert shared._fraction(arm['measurement']['unit']['exact_scale']) * 1000 == 2
    assert arm['calculation_operand']['value'] == 0.004 and arm['calculation_operand']['unit'] == 'umol/min/mg'
    record = cp(result)
    record['arms'][A]['measurement']['unit']['exact_scale'] = {'numerator': '1', 'denominator': '1000'}
    refused(f, record, 'saved_unit_scale_mismatch')


def test_unavailable_source_defined_unit_round_trips_and_cannot_be_claimed_supported():
    f = Fixture(0)
    defined_unit(f, missing=True)

    def callback(reference, representation):
        if reference == MISSING_REF:
            raise FileNotFoundError(errno.ENOENT, 'constructed missing unit source')
        return f.source(reference, representation)
    result = source.read_controlled_response_inputs(f.args, read_source=callback)
    unit = result['arms'][A]['measurement']['unit']
    assert unit['status'] == 'dependency_unavailable' and unit['definition_witnesses'] is None
    assert source.validate_controlled_response_extraction(f.args, result) == result
    record = cp(result)
    record['arms'][A]['measurement']['unit']['status'] = 'supported'
    refused(f, record, 'saved_unavailable_definition_mismatch')


def test_undecodable_covariance_document_state_is_checked_on_the_saved_path():
    f = Fixture(0)
    f.data[f.cov_ref] = b'\xff\xfe constructed non-UTF-8 covariance bytes'
    result = f.read()
    assert result['covariance']['projection_state'] == 'unsupported_format' and result['covariance']['raw_text'] is None
    assert source.validate_controlled_response_extraction(f.args, result) == result
    record = cp(result)
    both_documents(record, lambda d: d.update(document_state='available'))
    refused(f, record, 'saved_covariance_invalid_state_mismatch')


def test_saved_witness_records_follow_their_nominations():
    def unknown_normalization(f):
        f.args['arms'][A]['normalization'] = {'status': 'unknown', 'label': None, 'witnesses': [], 'canonical_witness': None, 'canonical_correspondence': {'value': 'unknown', 'witnesses': []}}
    f, result = made(unknown_normalization)
    assert result['arms'][A]['meanings']['normalization']['resolved_state'] == 'unknown'
    record = cp(result)
    record['arms'][A]['meanings']['normalization']['canonical_witness'] = cp(record['arms'][A]['context']['subject'])
    refused(f, record, 'saved_selection_mismatch')
    record = cp(result)
    record['arms'][A]['protein_arrangement']['witnesses'][0] = cp(record['arms'][A]['context']['subject'])
    refused(f, record, 'saved_selection_mismatch')


def test_unsupported_complete_expression_cannot_be_saved_as_parsed():
    def expression(f):
        f.text_measurement(A, 'A complete alternate response was 1.2 × 10^3 nmol/min.', '1.2 × 10^3')
    f, result = made(expression)
    candidate = result['arms'][A]['measurement']['candidates'][0]
    assert result['arms'][A]['measurement']['reading_status'] == 'unsupported'
    assert candidate['status'] == 'unsupported' and candidate['raw_expression'] == '1.2 × 10^3' and candidate['native_value'] is None
    record = cp(result)
    record['arms'][A]['measurement']['candidates'][0]['status'] = 'parsed'
    refused(f, record, 'saved_numeric_literal_mismatch')
