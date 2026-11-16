"""Synthetic count literals; no source paper, model or independence inference."""
from copy import deepcopy
import json
import math
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_validation import validate_saved_kinetic
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_kinetic_inputs import Source, SOURCE_REF, fixture

def count_fixture(expression, numeral=None, *, prefix='', suffix=' independent experiments.'):
    text = 'Synthetic π count: ' + prefix + expression + suffix
    source, selection = fixture(extra=text)
    selection['numerator']['uncertainty']['count'] = source.number(text, expression if numeral is None else numeral)
    return (source, selection)

def read_count(expression, numeral=None, **kw):
    source, selection = count_fixture(expression, numeral, **kw)
    before = deepcopy(selection)
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert selection == before
    assert result['calculation_inputs']['numerator']['value'] == 8
    assert result['calculation_inputs']['denominator']['value'] == 2
    sheet = populate_kinetic_contrast(result['calculation_inputs'])
    assert sheet['cells']['parameter_difference']['value'] == 6
    assert sheet['cells']['parameter_ratio']['value'] == 4
    assert sheet['cells']['log_parameter_contrast']['value'] == pytest.approx(math.log(4), rel=1e-14)
    assert sheet['cells']['source_profile_log_ratio']['value'] is None
    assert sheet['independent_preparation_count'] is None
    assert validate_saved_kinetic(selection, result, sheet) == (result, sheet)
    json.dumps(result, allow_nan=False)
    return result['operands']['numerator']['uncertainty']

@pytest.mark.parametrize('expression,expected', [('one', 1), ('three', 3), ('nineteen', 19), ('twenty', 20), ('twenty-one', 21), ('TWENTY ONE', 21), ('ninety-nine', 99), ('one hundred', 100), ('one hundred and three', 103), ('one hundred three', 103), ('nine hundred ninety-nine', 999), ('one thousand', 1000), ('one thousand and three', 1003), ('one thousand three', 1003), ('one thousand one hundred and three', 1103), ('two hundred thousand and three', 200003), ('one million', 1000000), ('two million three thousand four', 2003004), ('nine hundred ninety-nine million nine hundred ninety-nine thousand nine hundred ninety-nine', 999999999), ('three\nindependent', None)])
def test_finite_cardinal_grammar_expected_integer(expression, expected):
    result = read_count(expression)
    count = result['count']
    assert count['raw_number'] == expression
    assert result['canonical']['count'] == expected
    assert count['status'] == ('exact' if expected is not None else 'unsupported')
    assert count['notation'] == ('english_cardinal' if expected is not None else 'unsupported')

@pytest.mark.parametrize('expression', ['3', '0003', '23', '100003'])
def test_decimal_counts_keep_canonical_integer_and_source_literal(expression):
    result = read_count(expression)
    assert result['canonical']['count'] == int(expression)
    assert result['count']['raw_number'] == expression
    assert result['count']['notation'] == 'decimal_digits'

@pytest.mark.parametrize('expression,numeral,relation,approximate', [('at least three', 'three', 'ge', False), ('at most three', 'three', 'le', False), ('greater than three', 'three', 'gt', False), ('less than three', 'three', 'lt', False), ('no more than three', 'three', 'le', False), ('about three', 'three', 'point', True), ('~> three', 'three', 'gt', True), ('three or more', 'three', 'ge', False), ('three and below', 'three', 'le', False), ('not at least three', 'three', 'unresolved', False), ('no greater than three', 'three', 'unresolved', False), ('never more than three', 'three', 'unresolved', False), ('three or fewer', 'three', 'le', False), ('three or above', 'three', 'ge', False), ('< > three', 'three', 'unresolved', False), ('at least 3', '3', 'ge', False)])
def test_qualified_counts_are_partial_not_exact_sample_sizes(expression, numeral, relation, approximate):
    result = read_count(expression, numeral)
    assert result['canonical']['count'] is None
    assert result['count']['value'] == 3
    assert result['count']['status'] == 'qualified'
    assert result['count']['relation'] == relation
    assert result['count']['approximate'] is approximate
    assert result['count']['unavailable_reason'] == 'exact_count_qualified'

@pytest.mark.parametrize('expression,numeral', [('three or four', 'three'), ('three or four', 'three or four'), ('three to four', 'three'), ('three to four', 'three to four'), ('between three and four', 'three'), ('between three and four', 'four'), ('3–4', '3–4')])
def test_ranges_and_alternatives_do_not_select_or_average_endpoints(expression, numeral):
    result = read_count(expression, numeral)
    assert result['canonical']['count'] is None
    assert result['count']['value'] is None
    assert result['count']['status'] == 'range_or_alternatives'

@pytest.mark.parametrize('expression', ['triplicate', 'a', 'single', 'dozen', '3.0', '3.5', 'one billion', 'one thousand thousand', 'one million one million', 'and three', 'one-hundred', 'twenty zero', 'one hundred and zero', 'one thousand and one hundred', 'twenty--one'])
def test_unsupported_count_language_retains_source_and_parameters(expression):
    result = read_count(expression)
    assert result['canonical']['count'] is None
    assert result['count']['status'] == 'unsupported'
    assert result['count']['raw_number'] == expression
    assert result['count']['unavailable_reason'] == 'unsupported_count_literal'

@pytest.mark.parametrize('expression', ['zero', '0', '-3'])
def test_nonpositive_reported_integer_is_retained_without_zero_fallback(expression):
    result = read_count(expression)
    assert result['canonical']['count'] is None
    assert result['count']['status'] == 'not_positive'
    assert result['count']['value'] == (0 if expression in ('zero', '0') else -3)

@pytest.mark.parametrize('expression,numeral', [('threefold', 'three'), ('thirty-three', 'three'), ('one hundred and three', 'three'), ('twenty three', 'three'), ('three.0', 'three'), ('3.0', '3'), ('-3', '3'), ('minus three', 'three'), ('three point five', 'three'), ('one and a half', 'one')])
def test_clipped_count_selector_remains_repairable_caller_error(expression, numeral):
    source, selection = count_fixture(expression, numeral)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)

@pytest.mark.parametrize('expression,numeral', [('three nM', 'three'), ('3 nM', '3'), ('three%', 'three'), ('SD three', 'three'), ('three × two', 'three')])
def test_wrong_quantity_role_and_arithmetic_are_not_missing_count_science(expression, numeral):
    source, selection = count_fixture(expression, numeral)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)

def test_inline_markup_outside_narrow_witness_retains_qualification_and_utf8_boundaries():
    source, selection = count_fixture('at least <i>three</i>', 'three')
    selection['numerator']['uncertainty']['count'] = source.number('three', 'three')
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    reading = extraction['operands']['numerator']['uncertainty']['count']
    assert reading['status'] == 'qualified' and reading['relation'] == 'ge'
    witness = reading['selector']['witness']
    assert source.raw[witness['start']:witness['end']] == b'three'
    assert extraction['calculation_inputs']['numerator']['uncertainty']['count'] is None

def test_following_separate_technical_count_is_not_a_range_or_independence():
    result = read_count('three', suffix=' independent experiments with four technical measurements each.')
    assert result['canonical']['count'] == 3
    assert result['canonical']['repetition_basis'] == 'unspecified'

@pytest.mark.parametrize('basis', ['unspecified', 'technical_measurements', 'biological_preparations'])
def test_written_count_does_not_invent_covariance_or_independence_from_basis(basis):
    source, selection = count_fixture('three')
    unc = selection['numerator']['uncertainty']
    unc['repetition_basis'] = {'value': basis, 'witnesses': [] if basis == 'unspecified' else [source.witness('three independent experiments.')]}
    result = read_kinetic_inputs(selection, read_source=source.read)
    canonical = result['calculation_inputs']['numerator']['uncertainty']
    assert canonical['count'] == 3 and canonical['repetition_basis'] == basis
    calculated = populate_kinetic_contrast(result['calculation_inputs'])
    assert calculated['independent_preparation_count'] is None
    assert calculated['cells']['log_contrast_variance']['value'] is None


@pytest.mark.parametrize('change', ['quote', 'offset', 'authorization'])
def test_count_custody_and_caller_authorization_still_fail(change):
    source, selection = count_fixture('three')
    count = selection['numerator']['uncertainty']['count']
    if change == 'quote':
        count['witness']['quote'] = 'wrong source'
    elif change == 'offset':
        count['witness']['start'] += 1
    else:
        count['witness']['source_ref'] = 'source_' + 'b' * 24
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)



@pytest.mark.parametrize('target', ['raw_word', 'status', 'canonical_count', 'boolean_value', 'relation'])
def test_detached_count_associations_reject_tampering_without_reinterpretation(target, monkeypatch):
    source, selection = count_fixture('three')
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    sheet = populate_kinetic_contrast(extraction['calculation_inputs'])
    unc = extraction['operands']['numerator']['uncertainty']
    if target == 'raw_word':
        unc['count']['raw_number'] = 'four'
    elif target == 'status':
        unc['count']['status'] = 'qualified'
    elif target == 'canonical_count':
        unc['canonical']['count'] = 99
    elif target == 'boolean_value':
        unc['count']['value'] = True
    else:
        unc['count']['relation'] = 'ge'
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs._count_reading', lambda *_: pytest.fail('No saved reinterpretation'))
    with pytest.raises(ExperimentalContractError, match='kinetic_saved_mismatch'):
        validate_saved_kinetic(selection, extraction, sheet)
