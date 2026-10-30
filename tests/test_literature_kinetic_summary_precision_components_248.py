"""Actual public summary and labelled synthetic contrasts; no provider calls."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_summary_precision_inputs import (
    ASSUMPTIONS, summary_precision_arguments_schema, summary_precision_extraction_schema,
    read_kinetic_summary_precision_inputs, validate_kinetic_summary_precision_extraction,
)
from gene_annotation_episode.literature_kinetic_summary_precision_calculations import (
    COMPONENTS, populate_kinetic_summary_precision, validate_kinetic_summary_precision_inputs,
    summary_precision_inputs_schema, summary_precision_sheet_schema,
)
from gene_annotation_episode.literature_kinetic_summary_precision_prompt import (
    KINETIC_SUMMARY_PRECISION_TASK, SUMMARY_PRECISION_OPERATION_DESCRIPTION,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_components_248'
PAPER = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242/sources'


def saved(name):
    return json.loads((FIXTURES / name).read_text())


def rational(value):
    value = Fraction(str(value))
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def paper_source(reference, representation):
    assert reference == '@elife2015AP'
    raw = (PAPER / ('elife-06181-v2.pdf' if representation == 'original' else 'elife-06181-v2.txt')).read_bytes()
    return {'artifact_ref': 'sha256_' + hashlib.sha256(raw).hexdigest(), 'content': raw}


def actual_selection():
    return saved('ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json')


def actual():
    return read_kinetic_summary_precision_inputs(actual_selection(), read_source=paper_source)


def synthetic(case='fully_units_known'):
    packet = next(v for v in saved('SYNTHETIC_PARTIAL_IO_002.json') if v['case'] == case)
    source = saved('SYNTHETIC_' + case.upper() + '_SOURCE_002.json')
    raw = source['text'].encode()
    def read(reference, representation):
        assert reference == '@synthetic248'
        return {'artifact_ref': source['artifact_ref'], 'content': raw}
    return deepcopy(packet['selection']), read


def synth_extraction(case='fully_units_known'):
    selection, read = synthetic(case)
    return read_kinetic_summary_precision_inputs(selection, read_source=read)


def nonsd_source(statistic):
    """Explicitly labelled synthetic non-SD source, not SD relabelled as SEM."""
    selection, _ = synthetic()
    labels = {'sem': 'Reported standard error 0.2 s^-1.',
              'ci': 'Reported 95% confidence interval [9.0,11.0] s^-1.',
              'unspecified': 'Reported spread 0.2 s^-1.',
              'unreported': 'Uncertainty unreported.'}
    text = ('Parameter kcat. Construct SYNTH-A.\nCentral estimate 10 s^-1.\n'
            + labels[statistic] + '\nThe mean uses four independent preparation estimates.\n')
    def w(quote):
        start = text.index(quote)
        return {'source_ref': '@synthetic248', 'representation': 'text',
                'start': len(text[:start].encode()), 'end': len(text[:start+len(quote)].encode()), 'quote': quote}
    def num(quote, token):
        start = quote.index(token)
        return {'witness': w(quote), 'number_start': start, 'number_end': start+len(token)}
    row = selection['kinetic_selection']['numerator']
    row['parameter_kind'] = {'value': 'kcat', 'witnesses': [w('Parameter kcat.')]}
    row['subject'] = {k: None for k in row['subject']}
    row['subject']['construct'] = w('SYNTH-A')
    row['context'] = {k: None for k in row['context']}
    row['measurement'] = {'number': num('Central estimate 10 s^-1.', '10'), 'unit': w('s^-1')}
    row['qualification'] = {'value': 'reported_point', 'witnesses': [w('Central estimate 10 s^-1.')]}
    u = row['uncertainty']
    u['statistic'] = {'value': statistic, 'witnesses': [w(labels[statistic])]}
    u['magnitude'] = num(labels[statistic], '0.2') if statistic in ('sem', 'unspecified') else None
    u['interval'] = None
    u['confidence_level'] = None
    if statistic == 'ci':
        u['interval'] = {'witness': w('[9.0,11.0]'), 'lower_start': 1, 'lower_end': 4, 'upper_start': 5, 'upper_end': 9}
        u['confidence_level'] = w('95%')
    u['unit'] = w('s^-1') if statistic != 'unreported' else None
    u['unit_relationship'] = {'value': 'explicit_unit' if u['unit'] else 'unknown', 'witnesses': [w(labels[statistic])] if u['unit'] else []}
    u['count'] = num('The mean uses four independent preparation estimates.', 'four')
    u['repetition_basis'] = {'value': 'biological_preparations', 'witnesses': [w('four independent preparation estimates')]}
    u['estimate_basis'] = {'value': 'unknown', 'witnesses': []}
    inter = selection['interpretation']
    for key in inter:
        if key not in ('source_count_meaning', 'statistical_count'):
            inter[key] = {'state': 'unknown', 'witnesses': []}
    inter['row_footnote_applicability'] = {'state': 'source_supported', 'witnesses': [w(labels[statistic])]}
    inter['source_count_meaning'] = {'value': 'both_same_count', 'witnesses': [w('The mean uses four independent preparation estimates.')]}
    raw = text.encode()
    def read(reference, representation):
        return {'artifact_ref': 'sha256_'+hashlib.sha256(raw).hexdigest(), 'content': raw}
    return selection, read


def number_token(source, quote, token):
    start = source.index(quote)
    witness = {'source_ref': '@elife2015AP', 'representation': 'text',
        'start': len(source[:start].encode()), 'end': len(source[:start+len(quote)].encode()), 'quote': quote}
    ns = quote.index(token)
    return {'witness': witness, 'number_start': ns, 'number_end': ns + len(token)}


def edit_count(inputs, count):
    value = deepcopy(inputs)
    reading = value['source_count']
    reading.update(raw_number=str(count), value=count, notation='decimal_digits')
    selector = reading['selector']
    selector.update(number_start=0, number_end=len(str(count)))
    selector['witness']['quote'] = str(count)
    return value


def test_reviewed_schemas_and_task_are_exact_and_accessors_detach():
    for function, filename in (
        (summary_precision_arguments_schema, 'SELECTION_SCHEMA_002.json'),
        (summary_precision_extraction_schema, 'EXTRACTION_SCHEMA_004.json'),
        (summary_precision_inputs_schema, 'CALCULATION_INPUTS_SCHEMA_004.json'),
        (summary_precision_sheet_schema, 'SHEET_SCHEMA_004.json')):
        assert function() == saved(filename)
        mutated = function(); mutated['properties'].clear()
        assert function() == saved(filename)
    assert KINETIC_SUMMARY_PRECISION_TASK.encode() == (FIXTURES / 'TASK_PROPOSAL_001.txt').read_bytes()
    assert len(KINETIC_SUMMARY_PRECISION_TASK.strip().split('\n\n')) == 5
    assert 'formula_code' not in KINETIC_SUMMARY_PRECISION_TASK
    assert 'source_cells' not in SUMMARY_PRECISION_OPERATION_DESCRIPTION


def test_actual_source_count_and_conditional_precision_match_independent_oracle():
    extraction = actual()
    sheet = populate_kinetic_summary_precision(extraction['calculation_inputs'])
    source, scenario = sheet['source_cells'], sheet['scenario_cells']
    assert source['reported_parameter']['source_exact_value'] == rational(Fraction(93, 500000))
    assert source['reported_sd']['value'] == .000006
    assert source['reported_parameter']['origin'] == source['reported_sd']['origin'] == 'derived'
    assert source['independent_preparation_count']['origin'] == 'reported'
    assert source['independent_preparation_count']['value'] == 2
    assert source['statistical_estimator_count']['value'] is None
    assert source['mean_standard_error']['value'] is None
    assert scenario['statistical_estimator_count']['value'] == 2
    assert scenario['mean_variance']['source_exact_value'] == rational(Fraction(9, 500000000000))
    assert scenario['mean_standard_error']['value'] == pytest.approx(4.242640687119285e-6)
    assert scenario['relative_mean_standard_error']['value'] == pytest.approx(.022809896167307983)
    assert scenario['mean_interval_lower']['value'] == pytest.approx(2.201535646790624*.00006)
    assert scenario['mean_interval_upper']['value'] == pytest.approx(3.998464353209376*.00006)
    assert scenario['mean_interval_t_multiplier']['value'] == pytest.approx(12.706204736174707)
    assert scenario['mean_standard_error']['source_exact_value'] is None
    assert scenario['mean_interval_t_multiplier']['source_exact_value'] is None
    assert extraction['calculation_inputs']['assessments']['statistical_count_matches_sd'] == 'unknown'
    assert extraction['calculation_inputs']['assessments'][ASSUMPTIONS[1]] == 'unknown'
    assert len(scenario['mean_standard_error']['stipulated_assumptions']) == 4
    assert len(scenario['mean_interval_lower']['stipulated_assumptions']) == 6
    assert sheet['contribution']['independence_inferred'] is False
    assert sheet['contribution']['physical_measurement_id'] is None
    assert sheet['total_uncertainty'] is sheet['assay_error_probability'] is sheet['annotation_credit'] is None
    validate_schema(sheet, summary_precision_sheet_schema())


def test_both_preparation_to_estimator_relationships_are_required():
    data = actual()['calculation_inputs']
    for missing in ASSUMPTIONS[:2]:
        changed = deepcopy(data)
        changed['scenario']['stipulated_assumptions'].remove(missing)
        sheet = populate_kinetic_summary_precision(changed)
        assert sheet['source_cells']['independent_preparation_count']['value'] == 2
        assert sheet['scenario_cells']['statistical_estimator_count']['value'] is None
        assert sheet['scenario_cells']['mean_standard_error']['value'] is None
        if missing == ASSUMPTIONS[1]:
            assert sheet['scenario_cells']['statistical_estimator_count']['unavailable_reason'] == 'sd_preparation_estimator_ownership_unknown'
        assert sheet['inputs']['assessments'][missing] == 'unknown'


def test_normality_and_central_mean_identity_not_needed_for_se():
    data = actual()['calculation_inputs']
    for excluded in ['normal_sampling_units', 'equal_weight_arithmetic_mean']:
        data['scenario']['stipulated_assumptions'].remove(excluded)
    sheet = populate_kinetic_summary_precision(data)
    assert sheet['scenario_cells']['mean_standard_error']['value'] == pytest.approx(4.242640687119285e-6)
    assert sheet['scenario_cells']['relative_mean_standard_error']['value'] is None
    assert sheet['scenario_cells']['mean_interval_lower']['value'] is None
    assert sheet['scenario_cells']['mean_interval_t_multiplier']['unavailable_reason'] == 'normality_unknown'


@pytest.mark.parametrize('case', ['missing_central_value', 'missing_parameter_unit',
                                 'fully_units_known', 'both_units_missing', 'different_native_time_units'])
def test_independent_sd_units_preserve_valid_partials(case):
    extraction = synth_extraction(case)
    data = extraction['calculation_inputs']
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['independent_preparation_count']['value'] == 4
    assert cells['statistical_estimator_count']['value'] == 4
    if case == 'both_units_missing':
        assert cells['reported_sd']['value'] is None
        assert cells['mean_standard_error']['unavailable_reason'] == 'source_uncertainty_unit_unavailable'
    else:
        assert cells['reported_sd']['value'] == 12
        assert cells['mean_variance']['value'] == 36
        assert cells['mean_variance']['unit'] == 'per_min_squared'
        assert cells['mean_standard_error']['value'] == 6
    if case in ('missing_central_value', 'missing_parameter_unit'):
        assert data['canonical_unit'] is data['canonical_scale_exact'] is None
        assert cells['reported_parameter']['value'] is None
        assert cells['relative_reported_sd']['value'] is None
        assert cells['relative_mean_standard_error']['value'] is None
    elif case != 'both_units_missing':
        assert cells['reported_parameter']['value'] == 600
        assert cells['relative_reported_sd']['value'] == .02
        assert cells['relative_mean_standard_error']['value'] == .01


def test_partial_interval_width_survives_absent_central_value():
    data = synth_extraction('missing_central_value')['calculation_inputs']
    data['assessments']['normal_sampling_units'] = 'source_supported'
    data['interval_request'] = 'student_t_95'
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['mean_interval_df']['value'] == 3
    assert cells['mean_interval_halfwidth']['value'] == pytest.approx(6*3.182446305284263)
    assert cells['mean_interval_lower']['value'] is None
    assert cells['mean_interval_lower']['unavailable_reason'] == 'source_measurement_unreported'


def test_actual_contrasting_construct_does_not_inherit_hash_preparation_count():
    selection = actual_selection()
    text = paper_source('@elife2015AP', 'text')['content'].decode()
    row = next(line for line in text.splitlines() if 'D101A/E322Y/K328A ' in line and '1.1 (0.1)' in line)
    parameter = number_token(text, row, '1.1')
    spread = number_token(text, row, '0.1')
    record = selection['kinetic_selection']['numerator']
    record['measurement']['number'] = parameter
    record['subject']['construct'] = number_token(text, 'D101A/E322Y/K328A', 'D101A/E322Y/K328A')['witness']
    record['qualification']['witnesses'] = [parameter['witness']]
    unc = record['uncertainty']
    unc['magnitude'] = spread
    generic = 'activities are standard deviations from duplicate with the same or independent enzyme preparations'
    foot = number_token(text, generic, 'standard deviations')['witness']
    unc['statistic']['witnesses'] = [foot]
    unc['unit_relationship']['witnesses'] = [spread['witness'], record['measurement']['unit']]
    unc['count'] = None
    unc['repetition_basis'] = {'value': 'unspecified', 'witnesses': []}
    record['context']['preparation'] = None
    inter = selection['interpretation']
    inter['row_footnote_applicability'] = {'state': 'source_supported', 'witnesses': [parameter['witness'], foot]}
    inter['source_count_meaning'] = {'value': 'unknown', 'witnesses': []}
    selection['scenario'] = None
    result = populate_kinetic_summary_precision(read_kinetic_summary_precision_inputs(selection, read_source=paper_source)['calculation_inputs'])
    assert result['source_cells']['reported_parameter']['value'] == .000066
    assert result['source_cells']['reported_sd']['value'] == .000006
    assert result['source_cells']['relative_reported_sd']['value'] == pytest.approx(1/11)
    assert result['source_cells']['independent_preparation_count']['value'] is None
    assert result['scenario_cells'] is None


@pytest.mark.parametrize('kind', ['unknown', 'conflicting'])
def test_unresolved_parameter_kind_retains_source_and_count_partials(kind):
    selection, read = synthetic()
    meaning = selection['kinetic_selection']['numerator']['parameter_kind']
    meaning['value'] = kind
    if kind == 'conflicting':
        meaning['witnesses'].append(selection['kinetic_selection']['numerator']['uncertainty']['statistic']['witnesses'][0])
    selection['interval_request'] = 'student_t_95'
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    assert extraction['kinetic_extraction']['operands']['numerator']['number']['raw_number'] == '10'
    assert 'source_parameter_kind_' + kind in extraction['kinetic_extraction']['operands']['numerator']['unavailable_reasons']
    data = extraction['calculation_inputs']
    assert data['source_parameter_reason'] == 'source_parameter_kind_' + kind
    assert data['canonical_unit'] is data['sd_canonical_unit'] is None
    cells = populate_kinetic_summary_precision(data)['source_cells']
    for name in ['source_summary_count', 'independent_preparation_count', 'statistical_estimator_count']:
        assert cells[name]['value'] == 4
    for name in ['reported_parameter', 'reported_sd', 'mean_variance', 'mean_standard_error', 'relative_reported_sd']:
        assert cells[name]['value'] is None
        assert cells[name]['unavailable_reason'] == 'source_parameter_kind_' + kind
    assert cells['mean_interval_df']['value'] == 3
    assert cells['mean_interval_confidence_level']['value'] == .95
    assert validate_kinetic_summary_precision_extraction(extraction, read_source=read) == extraction


@pytest.mark.parametrize('statistic', ['sem', 'unspecified', 'unreported', 'ci'])
def test_non_sd_source_extraction_is_retained_without_inversion(statistic):
    selection, read = nonsd_source(statistic)
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    assert extraction['kinetic_extraction']['operands']['numerator']['uncertainty']['canonical']['statistic'] == statistic
    if statistic in ('sem', 'unspecified'):
        assert extraction['kinetic_extraction']['operands']['numerator']['uncertainty']['magnitude']['raw_number'] == '0.2'
    if statistic == 'ci':
        retained = extraction['kinetic_extraction']['operands']['numerator']['uncertainty']
        assert retained['canonical']['interval'] == [540, 660]
        assert retained['canonical']['confidence_level'] == .95
    assert extraction['calculation_inputs']['sd_native_exact'] is None
    cells = populate_kinetic_summary_precision(extraction['calculation_inputs'])['source_cells']
    assert cells['reported_parameter']['value'] == 600
    assert cells['statistical_estimator_count']['value'] == 4
    for name in ['reported_sd', 'mean_variance', 'mean_standard_error']:
        assert cells[name]['unavailable_reason'] == 'reported_statistic_not_sd'


def test_technical_count_never_becomes_physical_preparation_count():
    data = synth_extraction()['calculation_inputs']
    data['repetition_basis'] = 'technical_measurements'
    data['source_count_meaning'] = 'technical_measurement_count'
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['independent_preparation_count']['value'] is None
    assert cells['statistical_estimator_count']['value'] == 4
    assert cells['mean_standard_error']['value'] == 6


def test_n1_zero_sd_and_zero_center_have_distinct_partial_behavior():
    data = synth_extraction()['calculation_inputs']
    cells = populate_kinetic_summary_precision(edit_count(data, 1))['source_cells']
    assert cells['independent_preparation_count']['value'] == 1
    assert cells['mean_standard_error']['unavailable_reason'] == 'insufficient_estimator_count'
    zero = deepcopy(data); zero['sd_native_exact'] = rational(0)
    zero['interval_request'] = 'student_t_95'; zero['assessments']['normal_sampling_units'] = 'source_supported'
    cells = populate_kinetic_summary_precision(zero)['source_cells']
    assert cells['mean_standard_error']['value'] == cells['mean_variance']['value'] == 0
    assert cells['mean_interval_halfwidth']['unavailable_reason'] == 'positive_sd_required_for_student_t'
    zero = deepcopy(data); zero['parameter_native_exact'] = rational(0)
    cells = populate_kinetic_summary_precision(zero)['source_cells']
    assert cells['mean_standard_error']['value'] == 6
    assert cells['relative_reported_sd']['unavailable_reason'] == 'zero_parameter_for_relative_precision'


def test_sample_variance_underflow_does_not_destroy_representable_se():
    data = synth_extraction()['calculation_inputs']
    data['sd_native_exact'] = rational('1e-200')
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['reported_sd']['value'] == 6e-199
    assert cells['mean_variance']['value'] is None
    assert cells['mean_variance']['unavailable_reason'] == 'numerical_model_range'
    assert cells['mean_standard_error']['value'] == 3e-199


def test_separate_statistical_count_is_authenticated_and_must_match_sd():
    selection, read = synthetic()
    selection['interpretation']['statistical_count'] = deepcopy(selection['kinetic_selection']['numerator']['uncertainty']['count'])
    selection['interpretation']['statistical_count_matches_sd'] = {'state': 'source_supported', 'witnesses': deepcopy(selection['interpretation']['source_count_meaning']['witnesses'])}
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    assert populate_kinetic_summary_precision(extraction['calculation_inputs'])['source_cells']['statistical_estimator_count']['value'] == 4
    data = deepcopy(extraction['calculation_inputs'])
    separate = data['source_statistical_count']; separate['raw_number'] = '3'; separate['value'] = 3
    separate['selector'].update(number_start=0, number_end=1); separate['selector']['witness']['quote'] = '3'
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['statistical_estimator_count']['unavailable_reason'] == 'statistical_count_conflicting'


def test_contradiction_is_not_overridden_by_scenario_and_unrelated_normality_does_not_erase_se():
    data = actual()['calculation_inputs']
    data['assessments']['normal_sampling_units'] = 'source_contradicted'
    cells = populate_kinetic_summary_precision(data)['scenario_cells']
    assert cells['mean_standard_error']['value'] is not None
    assert cells['mean_interval_t_multiplier']['unavailable_reason'] == 'scenario_assumption_conflicts_with_source'
    data['assessments']['sample_sd_n_minus_one'] = 'conflicting'
    cells = populate_kinetic_summary_precision(data)['scenario_cells']
    assert cells['mean_standard_error']['unavailable_reason'] == 'scenario_assumption_conflicts_with_source'


@pytest.mark.parametrize('mutation', ['negative_sd', 'bool_rational', 'noncanonical_rational', 'wrong_scale', 'wrong_dimension', 'redundant_assumption'])
def test_invalid_detached_inputs_fail_precisely(mutation):
    data = synth_extraction()['calculation_inputs']
    if mutation == 'negative_sd': data['sd_native_exact'] = rational(-1)
    elif mutation == 'bool_rational': data['sd_native_exact']['numerator'] = True
    elif mutation == 'noncanonical_rational': data['sd_native_exact'] = {'numerator': '2', 'denominator': '10'}
    elif mutation == 'wrong_scale': data['sd_scale_exact'] = rational(7)
    elif mutation == 'wrong_dimension': data['sd_canonical_unit'] = 'uM'
    else: data['scenario'] = {'version': 'a105_summary_precision_scenario_v1', 'count_rule': 'source_statistical_count', 'stipulated_assumptions': ['sample_sd_n_minus_one']}
    with pytest.raises(ExperimentalContractError):
        validate_kinetic_summary_precision_inputs(data)


def test_witness_and_detached_tampering_are_rejected_and_repeats_do_not_enlarge_n():
    selection, read = synthetic()
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    again = read_kinetic_summary_precision_inputs(selection, read_source=read)
    assert again == extraction
    assert populate_kinetic_summary_precision(again['calculation_inputs'])['contribution'] == populate_kinetic_summary_precision(extraction['calculation_inputs'])['contribution']
    bad = deepcopy(extraction); bad['calculation_inputs']['parameter_native_exact'] = rational(9)
    with pytest.raises(ExperimentalContractError, match='detached_source_operand_mismatch'):
        validate_kinetic_summary_precision_extraction(bad, read_source=read)
    selection['interpretation']['source_count_meaning']['witnesses'][0]['quote'] += '!'
    with pytest.raises(ExperimentalContractError, match='source_quote_mismatch'):
        read_kinetic_summary_precision_inputs(selection, read_source=read)


@pytest.mark.parametrize('group', ['source_cells', 'scenario_cells'])
@pytest.mark.parametrize('name', COMPONENTS)
def test_named_output_cell_formula_and_unit_domains_cannot_be_swapped(group, name):
    sheet = populate_kinetic_summary_precision(actual()['calculation_inputs'])
    schema = summary_precision_sheet_schema()
    changed = deepcopy(sheet); changed[group][name]['formula_code'] = 'summary_precision_' + COMPONENTS[(COMPONENTS.index(name)+1) % len(COMPONENTS)]
    with pytest.raises(ContractError): validate_schema(changed, schema)
    changed = deepcopy(sheet)
    changed[group][name]['unit'] = 'per_min' if sheet[group][name]['unit'] in ('count', 'dimensionless') else 'count'
    with pytest.raises(ContractError): validate_schema(changed, schema)


def remap_synthetic_source(selection, old_source, replacements):
    """Rebuild actual synthetic byte selectors after controlled literal edits."""
    new_source = old_source
    for a, b in replacements:
        new_source = new_source.replace(a, b)
    def visit(value):
        if isinstance(value, dict):
            if set(value) >= {'source_ref', 'representation', 'start', 'end', 'quote'}:
                oldquote = value['quote']; newquote = oldquote
                for a, b in replacements: newquote = newquote.replace(a, b)
                start = new_source.index(newquote)
                return {**value, 'quote': newquote, 'start': len(new_source[:start].encode()), 'end': len(new_source[:start+len(newquote)].encode())}
            if set(value) == {'witness', 'number_start', 'number_end'}:
                token = value['witness']['quote'][value['number_start']:value['number_end']]
                for a, b in replacements: token = token.replace(a, b)
                witness = visit(value['witness']); ns = witness['quote'].index(token)
                return {'witness': witness, 'number_start': ns, 'number_end': ns+len(token)}
            return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list): return [visit(v) for v in value]
        return value
    new_selection = visit(selection)
    raw = new_source.encode()
    def read(reference, representation):
        return {'artifact_ref': 'sha256_'+hashlib.sha256(raw).hexdigest(), 'content': raw}
    return new_selection, read


@pytest.mark.parametrize('replacement,status', [('at least four', 'qualified'), ('four to six', 'range_or_alternatives'), ('dozen', 'unsupported')])
def test_source_count_qualifications_remain_partial_not_statistical_n(replacement, status):
    selection, _ = synthetic()
    text = saved('SYNTHETIC_FULLY_UNITS_KNOWN_SOURCE_002.json')['text']
    # Change all repeated count representations together, then select the
    # numeral inside a qualified phrase rather than the qualification itself.
    selection, read = remap_synthetic_source(selection, text, [('four', replacement)])
    if replacement == 'at least four':
        selection['kinetic_selection']['numerator']['uncertainty']['count']['number_start'] += len('at least ')
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    assert extraction['calculation_inputs']['source_count']['status'] == status
    cells = populate_kinetic_summary_precision(extraction['calculation_inputs'])['source_cells']
    assert cells['reported_parameter']['value'] == 600
    assert cells['reported_sd']['value'] == 12
    assert cells['source_summary_count']['value'] is None
    assert cells['statistical_estimator_count']['value'] is None
    assert cells['mean_standard_error']['value'] is None


def test_supported_count_is_not_erased_by_unrelated_unknown_extra_count():
    selection, read = synthetic()
    selection['interpretation']['statistical_count'] = deepcopy(selection['kinetic_selection']['numerator']['uncertainty']['count'])
    # A separately selected count's SD relationship stays unknown. It adds no support.
    extraction = read_kinetic_summary_precision_inputs(selection, read_source=read)
    sheet = populate_kinetic_summary_precision(extraction['calculation_inputs'])
    assert sheet['source_cells']['statistical_estimator_count']['value'] == 4
    assert sheet['inputs']['assessments']['statistical_count_matches_sd'] == 'unknown'


def test_se_underflow_does_not_erase_representable_relative_se():
    data = synth_extraction()['calculation_inputs']
    # A very large exact source count permits a smaller representable mean SE;
    # here we instead use the smallest float-scale magnitude before SD scaling.
    data['sd_native_exact'] = rational('1e-327')
    data['parameter_native_exact'] = rational('1e-327')
    # The detached exact contract retains the rational; source reader itself
    # rejects such printed underflow, so this is a pure numerical-domain fixture.
    cells = populate_kinetic_summary_precision(data)['source_cells']
    assert cells['mean_standard_error']['value'] is None
    assert cells['mean_standard_error']['unavailable_reason'] == 'numerical_model_range'
    assert cells['relative_mean_standard_error']['value'] == .5
