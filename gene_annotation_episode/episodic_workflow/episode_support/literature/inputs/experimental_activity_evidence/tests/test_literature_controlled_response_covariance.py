"""Source covariance documents: strict parsing, shape, owner projection and model gates (v3).

Constructed covariance text only (the constructed selections' document, edited per
test); no paper, model or native execution. Every live read is also revalidated
from its saved record, so the saved path sees the same document.
"""
from copy import deepcopy as cp
from fractions import Fraction
import json
import re
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_source_inputs as source
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_source_inputs import Fixture
ROLES = shared.PRIMITIVE_ORDER


def anchor(f, text, mapping=None):
    """Install covariance text and re-anchor every nominated label/model witness in it."""
    f.data[f.cov_ref] = text.encode()
    labels = list(re.finditer(b'"label":\\s*("(?:[^"\\\\]|\\\\.)*")', f.data[f.cov_ref]))
    for role in ROLES:
        b = f.args['covariance']['bindings'][role]
        if mapping is not None:
            index = mapping[ROLES.index(role)]
            if index is None:
                f.args['covariance']['bindings'][role] = None
                continue
            if b is None:
                b = dict(variable_index=index, label_witness=None, owner_witness=cp(f.args['arms'][role]['physical_observation']['canonical_witness']), correspondence=None)
                f.args['covariance']['bindings'][role] = b
            b['variable_index'] = index
        if b is None:
            continue
        at, end = labels[b['variable_index']].span(1)
        b['label_witness'] = dict(source_ref=f.cov_ref, representation='original', start=at, end=end, quote=f.data[f.cov_ref][at:end].decode())
        b['correspondence'] = dict(value='same', witnesses=[dict(kind='text', **b['label_witness'])])
    for name in ('variance_status', 'model_kind'):
        f.args[name] = dict(value=f.doc[name], witnesses=[f.witness(json.dumps(f.doc[name]), f.cov_ref)])
    for pair in f.args['local_pair_assignments']:
        pair['covariance_selection'] = cp(f.args['covariance'])
        pair['variance_status'] = cp(f.args['variance_status'])


def document(f, mapping=None, *, tail='', **tokens):
    """The fixture document as JSON text; `tail` is inserted before the final brace, tokens replace placeholders."""
    text = json.dumps(f.doc, indent=2)
    assert text.endswith('\n}')
    text = text[:-2] + tail + '\n}\n'
    for placeholder, token in tokens.items():
        text = text.replace('"' + placeholder + '"', token)
    anchor(f, text, mapping)
    return f


def request(f, variance, model):
    quote = 'Only the intended factor differs.'
    f.args['variance_status'] = f.interp(variance, None if variance == 'unknown' else quote)
    f.args['model_kind'] = f.interp(model, None if model == 'none' else quote)
    for pair in f.args['local_pair_assignments']:
        pair['variance_status'] = cp(f.args['variance_status'])


def read_and_resave(f):
    result = f.read()
    assert source.validate_controlled_response_extraction(f.args, result) == result
    return result


def codes(record):
    return [d['code'] for d in record['diagnostics']]


@pytest.mark.parametrize('tail,code', [
    (',\n  "origin": "synthetic"', 'source_json_duplicate_key'),
    (',\n  "extra": NaN', 'source_json_nonfinite'),
    (',\n  "extra": -Infinity', 'source_json_nonfinite'),
    (',\n  "extra": "\\q"', 'unsupported_covariance_representation'),
    (',\n  "extra": {1: 2}', 'unsupported_covariance_representation'),
    (',\n  "extra": {"a" 1}', 'unsupported_covariance_representation'),
    (',\n  "extra": {"a": 1; "b": 2}', 'unsupported_covariance_representation'),
    (',\n  "extra": {"a": 1, }', 'unsupported_covariance_representation'),
    (',\n  "extra": [1; 2]', 'unsupported_covariance_representation'),
    (',\n  "extra": [1, ]', 'unsupported_covariance_representation'),
    (',\n  "extra": @', 'unsupported_covariance_representation'),
    (',\n  "extra": 1e−5', 'unsupported_covariance_representation'),
    (',\n  "extra": ' + '[' * 3000 + ']' * 3000, 'unsupported_covariance_representation'),
], ids=['duplicate_key', 'nan', 'negative_infinity', 'bad_escape', 'nonstring_key', 'missing_colon', 'object_separator', 'object_trailing_comma', 'array_separator', 'array_trailing_comma', 'bare_token', 'unicode_minus_exponent', 'nesting_depth'])
def test_strict_source_json_refuses_the_whole_document(tail, code):
    f = document(Fixture(0), tail=tail)
    result = read_and_resave(f)
    covariance = result['covariance']
    assert codes(covariance) == [code]
    assert covariance['exact_matrix'] is None and covariance['calculation_covariance'] is None
    unsupported = code == 'unsupported_covariance_representation'
    assert covariance['source_validation'] == ('unassessed' if unsupported else 'invalid')
    assert covariance['projection_state'] == ('unsupported_format' if unsupported else 'source_invalid')
    assert all((b['state'] == 'unknown' for b in covariance['bindings'].values()))
    assert result['calculation_inputs']['covariance'] is None and result['calculation_inputs']['variance_status'] == 'unknown'


def test_text_after_the_document_is_unsupported():
    f = document(Fixture(0))
    f.data[f.cov_ref] += b'trailing'
    result = read_and_resave(f)
    assert codes(result['covariance']) == ['unsupported_covariance_representation']
    assert result['covariance']['projection_state'] == 'unsupported_format'


@pytest.mark.parametrize('change,mapping,code', [
    (lambda d: d.update(variables=[]), [None] * 4, 'source_covariance_shape_invalid'),
    (lambda d: d.update(covariance=[row[:3] for row in d['covariance'][:3]]), None, 'source_covariance_shape_invalid'),
    (lambda d: d['covariance'][0].__setitem__(0, '0.25'), None, 'source_covariance_shape_invalid'),
    (lambda d: d['covariance'][3].__setitem__(3, True), None, 'source_covariance_shape_invalid'),
    (lambda d: d.update(origin='estimated'), None, 'source_covariance_origin_invalid'),
    (lambda d: d.pop('origin'), None, 'unsupported_covariance_representation'),
    (lambda d: d.update(version='unrecognized_version'), None, 'unsupported_covariance_representation'),
    (lambda d: d['variables'][3].update(description=' '), None, 'unsupported_covariance_representation'),
], ids=['no_variables', 'matrix_rows', 'string_entry', 'boolean_entry', 'origin', 'missing_field', 'version', 'blank_description'])
def test_document_shape_is_validated_before_any_matrix_use(change, mapping, code):
    f = Fixture(0)
    change(f.doc)
    document(f, mapping)
    covariance = read_and_resave(f)['covariance']
    assert codes(covariance) == [code]
    assert covariance['exact_matrix'] is None and covariance['projection_state'] in ('source_invalid', 'unsupported_format')


def test_unknown_document_variance_status_is_unsupported_and_names_no_source_model():
    f = Fixture(0)
    f.doc['variance_status'] = 'bogus'
    document(f)
    request(f, 'known', 'known_joint_normal_source_means')
    result = read_and_resave(f)
    assert codes(result['covariance']) == ['unsupported_covariance_representation']
    assert result['covariance']['source_model'] is None


@pytest.mark.parametrize('change,code,state', [
    (lambda f: f.doc['covariance'][0].__setitem__(1, 0.1), 'source_covariance_asymmetric', 'source_invalid'),
    (lambda f: f.doc['covariance'][3].__setitem__(3, -0.1), 'source_covariance_not_psd', 'source_invalid'),
])
def test_invalid_full_source_matrix_has_no_owner_projection(change, code, state):
    f = Fixture(0)
    change(f)
    covariance = read_and_resave(document(f))['covariance']
    assert codes(covariance) == [code] and covariance['projection_state'] == state and covariance['source_validation'] == 'invalid'
    assert covariance['provided_owner_projection'] == [] and covariance['calculation_covariance'] is None


def projection(f):
    return read_and_resave(f)['covariance']


def test_conflicting_binding_correspondence_blocks_projection():
    f = document(Fixture(0))
    binding = f.args['covariance']['bindings'][ROLES[0]]
    binding['correspondence'] = dict(value='conflicting', witnesses=[cp(binding['correspondence']['witnesses'][0]), f.witness('Physical A.')])
    covariance = projection(f)
    assert covariance['bindings'][ROLES[0]]['state'] == 'conflicting'
    assert codes(covariance) == ['covariance_owner_conflicting'] and covariance['projection_state'] == 'binding_conflicting'


def test_two_owners_on_one_source_variable_conflict():
    f = document(Fixture(0), [2, 0, 2, 0])
    f.args['covariance']['bindings'][ROLES[2]]['owner_witness'] = cp(f.args['arms'][ROLES[2]]['physical_observation']['canonical_witness'])
    covariance = projection(f)
    assert codes(covariance) == ['covariance_owner_conflicting'] and covariance['projection_state'] == 'binding_conflicting'


def test_unregistered_source_unit_is_unavailable_not_rescaled():
    f = Fixture(0)
    f.doc['variables'][2]['unit'] = 'furlongs/min'
    covariance = projection(document(f))
    assert covariance['variables'][2]['diagnostics'][0]['code'] == 'source_covariance_unit_unsupported'
    assert codes(covariance) == ['source_covariance_unit_unsupported']
    assert covariance['projection_state'] == 'unavailable' and covariance['calculation_covariance'] is None


def test_source_unit_dimension_must_match_the_bound_reading():
    f = Fixture(0)
    f.doc['variables'][2]['unit'] = 'uM/min'
    covariance = projection(document(f))
    assert codes(covariance) == ['covariance_owner_dimension_conflict'] and covariance['projection_state'] == 'binding_conflicting'


def test_one_owner_bound_to_rows_of_different_dimension_conflicts():
    f = Fixture(1)
    f.doc['variables'][3]['unit'] = 'uM/min'
    document(f, [2, 0, 1, 3])
    assert f.args['arms'][ROLES[1]]['measurement'] is None and f.args['arms'][ROLES[3]]['measurement'] is None
    covariance = projection(f)
    assert codes(covariance) == ['covariance_owner_dimension_conflict'] and covariance['projection_state'] == 'binding_conflicting'


def test_one_owner_bound_to_unequal_rows_conflicts():
    f = document(Fixture(0), [2, 0, 1, 3])
    covariance = projection(f)
    assert codes(covariance) == ['covariance_shared_rows_conflicting'] and covariance['projection_state'] == 'binding_conflicting'


def test_no_known_binding_leaves_the_projection_unresolved():
    f = document(Fixture(0), [None] * 4)
    covariance = projection(f)
    assert codes(covariance) == ['covariance_owner_unresolved'] and covariance['projection_state'] == 'binding_unresolved'


def test_projected_entry_outside_float_range():
    f = Fixture(0)
    f.doc['covariance'][2][2] = 'HUGE'
    covariance = projection(document(f, HUGE='1e400'))
    assert covariance['source_validation'] == 'valid'
    assert codes(covariance) == ['covariance_projection_numeric_range'] and covariance['projection_state'] == 'numeric_range'
    assert covariance['projected_exact_matrix'][2][2] == {'numerator': str(10 ** 400), 'denominator': '1'}


def test_exact_rank_one_source_whose_float_projection_is_not_psd():
    # a = 0.100000000000000003, b = 0.3: [[a*a, a*b], [a*b, b*b]] has determinant 0 exactly,
    # but rounding each entry to the nearest double makes the determinant negative.
    a, b = (Fraction('0.100000000000000003'), Fraction('0.3'))
    exact = [[a * a, a * b], [a * b, b * b]]
    assert exact[0][0] * exact[1][1] - exact[0][1] ** 2 == 0
    rounded = [[Fraction(str(float(v))) for v in row] for row in exact]
    assert rounded[0][0] * rounded[1][1] - rounded[0][1] ** 2 < 0
    f = Fixture(0)
    f.doc['covariance'] = [['ONE', 0, 0, 0], [0, 'BB', 'AB', 0], [0, 'AB', 'AA', 0], [0, 0, 0, 'ONE']]
    for value in (a * a, a * b, b * b):
        assert (value * 10 ** 40).denominator == 1
    decimal = lambda v: '0.' + str(v.numerator * 10 ** 40 // v.denominator).rjust(40, '0')
    tokens = {'AA': decimal(a * a), 'AB': decimal(a * b), 'BB': decimal(b * b), 'ONE': '1'}
    covariance = projection(document(f, **tokens))
    # Owners in source order: B (row 0), C (row 1, holds b*b), A (row 2, holds a*a).
    assert covariance['source_validation'] == 'valid'
    assert [shared._fraction(v) for v in covariance['projected_exact_matrix'][1]] == [0, b * b, a * b]
    assert codes(covariance) == ['covariance_projection_precision_invalid'] and covariance['projection_state'] == 'precision_invalid'


def test_unbound_reading_of_a_projected_owner_must_share_its_dimension():
    f = document(Fixture(0), [2, 0, 1, None])
    f.text_measurement(ROLES[3], 'B other mean: 4 uM/min.', '4', unit='uM/min')
    assert f.args['covariance']['bindings'][ROLES[3]] is None
    covariance = projection(f)
    assert codes(covariance) == ['covariance_owner_dimension_conflict'] and covariance['projection_state'] == 'binding_conflicting'


def test_digits_beyond_double_precision_disable_the_known_normal_model():
    f = Fixture(0)
    f.doc['covariance'][2][2] = 'PRECISE'
    result = read_and_resave(document(f, PRECISE='0.16000000000000000001'))
    covariance = result['covariance']
    assert covariance['projection_state'] == 'available'
    assert codes(covariance) == ['numeric_projection_rounding']
    assert covariance['calculation_covariance']['matrix'][2][2] == 0.16
    assert codes(result['effective_model']) == ['source_model_projection_rounding']
    assert result['effective_model']['variance_status'] == 'known' and result['effective_model']['model_kind'] == 'none'


@pytest.mark.parametrize('setup,code,variance', [
    (lambda f: f.doc.update(variance_status='unknown'), 'source_variance_status_unknown', 'unknown'),
    (lambda f: f.doc.update(model_kind='none'), 'source_normal_model_unsupported', 'known'),
], ids=['source_unknown', 'source_model_none'])
def test_source_model_facts_gate_the_effective_model(setup, code, variance):
    f = Fixture(0)
    setup(f)
    document(f)
    request(f, 'known', 'known_joint_normal_source_means')
    result = read_and_resave(f)
    assert codes(result['effective_model']) == [code]
    assert result['effective_model']['variance_status'] == variance and result['effective_model']['model_kind'] == 'none'


@pytest.mark.parametrize('variance,model,code', [
    ('unknown', 'known_joint_normal_source_means', 'variance_status_not_selected'),
    ('estimated', 'known_joint_normal_source_means', 'requested_source_variance_status_conflict'),
    ('known', 'none', 'normal_model_not_selected'),
])
def test_requested_model_must_match_the_source_document(variance, model, code):
    f = document(Fixture(0))
    request(f, variance, model)
    result = read_and_resave(f)
    assert codes(result['effective_model']) == [code]
    assert result['effective_model']['model_kind'] == 'none'


def test_synthetic_covariance_cannot_serve_reported_readings():
    f = document(Fixture(0))
    f.args['arms'][ROLES[0]]['source_kind'] = 'primary_source'
    result = read_and_resave(f)
    assert codes(result['effective_model']) == ['synthetic_covariance_with_reported_operands']
    assert result['effective_model']['variance_status'] == 'unknown'
    assert result['calculation_inputs']['covariance'] is None


def test_nominated_index_outside_the_document_is_refused():
    f = document(Fixture(0))
    f.args['covariance']['bindings'][ROLES[0]]['variable_index'] = 4
    with pytest.raises(ExperimentalContractError, match='source_variable_index_out_of_bounds'):
        f.read()


def test_label_witness_must_be_the_nominated_variable_label():
    f = document(Fixture(0))
    bindings = f.args['covariance']['bindings']
    bindings[ROLES[0]]['label_witness'] = cp(bindings[ROLES[2]]['label_witness'])
    with pytest.raises(ExperimentalContractError, match='source_label_token_binding_mismatch'):
        f.read()


def test_owner_witness_must_belong_to_the_bound_role():
    f = document(Fixture(0))
    f.args['covariance']['bindings'][ROLES[0]]['owner_witness'] = cp(f.args['arms'][ROLES[2]]['physical_observation']['canonical_witness'])
    with pytest.raises(ExperimentalContractError, match='owner_witness_not_in_role'):
        f.read()


def test_owner_bound_to_two_proportional_rows_projects_once_in_source_order():
    """B is bound at row 0 (nmol/min) and row 3 (umol/min). Row 3 = row 0 / 1000 in its own unit.

    Source matrix (nmol/min rows 0-2, umol/min row 3):
        [[0.25, 0, 0, 0.00025], [0, 0.2, 0.03, 0], [0, 0.03, 0.16, 0], [0.00025, 0, 0, 0.00000025]]
    Shared-row check in canonical umol/min: (1/1000) * row0 == 1 * row3 for every column, e.g.
    column 0: 0.25 / 1000 = 0.00025; column 3: 0.00025 / 1000 = 0.00000025.
    Owners projected once each, ordered by first source row: B(0), C(1), A(2).
    Contrast A - B - C + B = A - C; variance = 0.16 + 0.2 - 2 * 0.03 = 0.30 (nmol/min)^2
    = 0.30e-6 = 3e-7 (umol/min)^2; effect = 10 - 8 = 2 nmol/min = 0.002 umol/min.
    """
    f = Fixture(0)
    f.doc['variables'][3]['unit'] = 'umol/min'
    f.doc['covariance'] = [[0.25, 0, 0, 'R03'], [0, 0.2, 0.03, 0], [0, 0.03, 0.16, 0], ['R03', 0, 0, 'R33']]
    document(f, [2, 0, 1, 3], R03='0.00025', R33='0.00000025')
    f.args['covariance']['bindings'][ROLES[3]]['owner_witness'] = cp(f.args['arms'][ROLES[3]]['physical_observation']['canonical_witness'])
    result = read_and_resave(f)
    covariance = result['covariance']
    assert covariance['projection_state'] == 'available' and codes(covariance) == []
    assert [(row['source_variable_index'], row['roles']) for row in covariance['provided_owner_projection']] == [(0, [ROLES[1], ROLES[3]]), (1, [ROLES[2]]), (2, [ROLES[0]])]
    assert covariance['calculation_covariance']['matrix'] == [[0.25, 0.0, 0.0], [0.0, 0.2, 0.03], [0.0, 0.03, 0.16]]
    assert covariance['calculation_covariance']['units'] == ['nmol/min'] * 3
    sheet = owner.populate_controlled_response_owner(result['calculation_inputs'])
    cells = sheet['cells']
    assert cells['controlled_response_difference']['value'] == 0.002 and cells['controlled_response_difference']['unit'] == 'umol/min'
    assert cells['contrast_variance']['value'] == float(Fraction(3, 10 ** 7)) and cells['contrast_variance']['unit'] == '(umol/min)^2'
    assert sheet['contrast_dependencies']['canceled_roles'] == [ROLES[1], ROLES[3]]
