"""Constructed reported-limit arithmetic; no papers, provider or inference."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import math
import re
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_rate_domains import VERSION, NAMESPACE, rate_source_domain_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository, SOURCE_DOMAIN_RECEIVED, rate_source_cells_schema
from .unit_world import in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_rate_native_inputs import synthetic_case, read_case, calculate
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_rate_native_storage import setup_native_store

def operands(reference='12', test='< .3', **kwargs):
    raw, args = synthetic_case(reference=reference, test=test, reference_unit=kwargs.pop('reference_unit', 'umol/min/mg'), test_unit=kwargs.pop('test_unit', 'umol/min/mg'), **kwargs)
    for role, token in (('reference', reference), ('test', test)):
        numeric = re.search('[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:e[-+]?\\d+)?', token)
        selected = args['arms'][role]['rate']['number']
        selected['number_start'] += numeric.start()
    return (raw, args)

def sheet(reference='12', test='< .3', *, mutate=None, **kwargs):
    raw, args = operands(reference, test, **kwargs)
    if mutate:
        mutate(args)
    extraction = read_case(raw, args)
    rows = {r['arm']: r for r in extraction['rows']}
    return populate_rate_contrast(extraction, reference_arm='reference', test_arm='test', reference_condition=rows['reference']['condition'], test_condition=rows['test']['condition'], dependence=args['dependence']['value'], observation_model=args['observation_model']['value'], native_bound_version=VERSION)

def domain(result, name):
    return result['native_bound_arithmetic']['components'][name]['reported_domain']

@pytest.mark.parametrize('comparator,bound,inclusive', [('<', 'lt', False), ('<=', 'le', True), ('>', 'gt', False), ('>=', 'ge', True)])
def test_positive_point_reference_preserves_all_four_comparators(comparator, bound, inclusive):
    result = sheet(test=comparator + ' .3')
    cells = result['cells']
    for name, value in (('rate_difference', 11.7), ('retained_fraction', 0.025), ('fractional_decrease', 0.975)):
        assert cells[name]['value'] is None
        assert cells[name]['threshold'] == pytest.approx(value)
        expected = bound if name == 'retained_fraction' else {'lt': 'gt', 'le': 'ge', 'gt': 'lt', 'ge': 'le'}[bound]
        assert cells[name]['bound'] == expected
        d = domain(result, name)
        assert d['lower_inclusive'] if expected == 'ge' else d['upper_inclusive'] if expected == 'le' else not d['lower_inclusive'] and (not d['upper_inclusive'])
    assert cells['reference_rate']['value'] == 12
    assert cells['test_rate']['threshold'] == 0.3
    for name in ('reference_mean_se', 'test_mean_se', 'difference_se', 'signed_profile_log_ratio', 'source_signed_index'):
        assert cells[name]['value'] is None
    assert result['profile_diagnostics'] is None
    assert result['model']['dependence'] == 'unknown'

def test_negative_reference_reverses_ratio_but_not_difference():
    result = sheet('-12', '<= .3')
    assert result['cells']['retained_fraction']['bound'] == 'ge'
    assert result['cells']['retained_fraction']['threshold'] == pytest.approx(-0.025)
    assert result['cells']['fractional_decrease']['bound'] == 'le'
    assert result['cells']['fractional_decrease']['threshold'] == pytest.approx(1.025)
    assert result['cells']['rate_difference']['bound'] == 'ge'

@pytest.mark.parametrize('reference,test,expected', [('> 2', '3', (0, False, 1.5, False)), ('>= 2', '3', (0, False, 1.5, True)), ('< -2', '3', (-1.5, False, 0, False)), ('<= -2', '3', (-1.5, True, 0, False)), ('> 0', '>= 0', (0, True, None, False)), ('< 0', '> 3', (None, False, 0, False)), ('> 2', '< 3', (None, False, 1.5, False)), ('>= 2', '<= 3', (None, False, 1.5, True))])
def test_censored_denominators_keep_finite_or_one_sided_images(reference, test, expected):
    result = sheet(reference, test)
    d = domain(result, 'retained_fraction')
    assert (d['lower'], d['lower_inclusive'], d['upper'], d['upper_inclusive']) == expected
    assert result['cells']['retained_fraction']['value'] is None
    assert d['conditioning'] == 'reported_endpoint_normalization_unit_relations'

@pytest.mark.parametrize('reference', ['0', '>= 0', '<= 0', '> -2', '< 2'])
def test_zero_or_potentially_zero_denominator_is_explicitly_undefined(reference):
    result = sheet(reference, '0')
    for name in ('retained_fraction', 'fractional_decrease'):
        assert domain(result, name)['kind'] == 'undefined'
        assert result['cells'][name]['value'] is None
        assert result['cells'][name]['unavailable_reason'] == 'zero_reference_rate'

@pytest.mark.parametrize('reference', ['> 0', '< 0', '>= 2', '<= -2'])
def test_exact_constant_images_are_identified_without_imputing_a_censored_rate(reference):
    result = sheet(reference, '0')
    assert result['cells']['reference_rate']['value'] is None
    assert result['cells']['retained_fraction']['value'] == 0
    assert result['cells']['fractional_decrease']['value'] == 1
    assert domain(result, 'retained_fraction')['kind'] == 'point'

@pytest.mark.parametrize('field,value', [('endpoint', 'unknown'), ('endpoint', 'different'), ('normalization', 'unknown'), ('normalization', 'different')])
def test_censor_does_not_mask_pair_guard(field, value):

    def mutate(args):
        args['comparison'][field + '_relation']['value'] = value
        if value == 'unknown':
            args['comparison'][field + '_relation']['witnesses'] = []
    result = sheet(mutate=mutate)
    reason = 'source_' + field + '_relationship_' + value
    for name in ('rate_difference', 'retained_fraction', 'fractional_decrease', 'difference_se', 'signed_profile_log_ratio'):
        assert result['cells'][name]['unavailable_reason'] == reason
        assert result['cells'][name]['threshold'] is None
    assert result['cells']['reference_rate']['value'] == 12
    assert result['cells']['test_rate']['threshold'] == 0.3

def test_incompatible_units_and_reused_observations_preserve_raw_cells():
    result = sheet(test_unit='umol/min')
    assert domain(result, 'rate_difference')['failure'] == 'incompatible_rate_dimensions'

    def reused(args):
        args['arms']['test']['measurement_identity'] = args['arms']['reference']['subject']
        args['arms']['reference']['measurement_identity'] = args['arms']['reference']['subject']
    assert domain(sheet(mutate=reused), 'rate_difference')['failure'] == 'reused_source_observation'
    result = sheet(test_unit='unreported')
    assert result['cells']['test_rate']['bound'] == 'lt'
    assert domain(result, 'rate_difference')['kind'] == 'unavailable'

def test_rounding_is_outward_and_overflow_underflow_do_not_become_zero():
    result = sheet('3', '< 1')
    upper = domain(result, 'retained_fraction')['upper']
    assert Fraction(upper) >= Fraction(1, 3)
    assert domain(result, 'retained_fraction')['projection'] == 'outward'
    tiny = sheet('1e300', '< 1e-300')
    d = domain(tiny, 'retained_fraction')
    assert d['upper'] == math.ulp(0.0) and d['kind'] == 'upper_bounded'
    assert tiny['cells']['retained_fraction']['value'] is None
    assert tiny['cells']['retained_fraction']['threshold'] == math.ulp(0.0)
    huge = sheet('> 1e-300', '1e300')
    d = domain(huge, 'retained_fraction')
    assert d['lower'] == 0 and (not d['lower_inclusive'])
    assert d['upper'] is None and d['kind'] == 'lower_bounded'
    assert d['failure'] == 'numerical_model_range' and d['projection'] == 'outward'
    assert huge['cells']['retained_fraction']['value'] is None
    assert huge['cells']['retained_fraction']['bound'] == 'gt'
    assert huge['native_bound_arithmetic']['components']['retained_fraction']['image']['upper'] is not None


@pytest.mark.parametrize('test,side,sign', [('> 1e300', 'lower', 1), ('< -1e300', 'upper', -1)])
def test_overflow_preserves_a_representable_strict_outer_constraint(test, side, sign):
    result = sheet('1e-300', test)
    d = domain(result, 'retained_fraction')
    assert d[side] == sign * math.nextafter(math.inf, 0)
    assert not d[side + '_inclusive']
    assert d['projection'] == 'outward' and d['failure'] == 'numerical_model_range'
    assert result['cells']['retained_fraction']['value'] is None

def test_underflow_point_remains_unknown_while_its_constraints_and_complement_survive():
    result = sheet('1e300', '1e-300')
    assert result['cells']['retained_fraction']['value'] is None
    d = domain(result, 'retained_fraction')
    assert d['lower'] == 0 and (not d['lower_inclusive'])
    assert d['upper'] == math.ulp(0.0) and (not d['upper_inclusive'])
    assert result['cells']['fractional_decrease']['value'] == 1
    assert domain(result, 'fractional_decrease')['projection'] == 'outward'


@in_unit
def test_domain_projection_receives_nothing_until_cells_are_delivered(store, ctx):
    store, owner, args = setup_native_store(store, ctx)
    repo = LiteratureRateRepository(store, owner.run_id)
    repo.populate_native(owner, args, 'selected')
    view = repo.source_domain_projection()
    assert view.received_cells(owner) == []
    assert store.table(SOURCE_DOMAIN_RECEIVED).select() == []

@in_unit
def test_new_saved_trace_rejects_versions_constraints_and_source_association_tampering(store, ctx):
    store, owner, args = setup_native_store(store, ctx, reference='> 12')
    repo = LiteratureRateRepository(store, owner.run_id)
    outcome = repo.populate_native(owner, args, 'selected')
    saved = repo.read(outcome['result']['sheet_ref'])
    request = {'arguments': args}
    for alteration in ('version', 'constraint', 'source'):
        changed = deepcopy(saved)
        trace = changed['sheet']['native_bound_arithmetic']
        if alteration == 'version':
            trace['version'] = 'unknown_version'
        elif alteration == 'constraint':
            trace['components']['retained_fraction']['reported_domain']['upper'] = 99
        else:
            trace['components']['retained_fraction']['input_rows'][0]['source_ref'] = 'source_forged'
        with pytest.raises(ContractError, match='bound_version_unsupported|saved_domain_mismatch'):
            repo._validate_native_saved(changed, request, outcome)

@pytest.mark.parametrize('field,value', [('value', True), ('value', math.inf), ('threshold', True), ('threshold', -math.inf)])
@in_unit
def test_new_saved_identified_one_cannot_be_forged_as_boolean_or_nonfinite(store, ctx, field, value):
    store, owner, _ = setup_native_store(store, ctx)
    raw, args = operands('12', '12')
    artifact = store.artifact(raw, 'text/plain')
    source = store.put('source', {'provider': 'constructed_equal_rate_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')

    def bind(value):
        if isinstance(value, dict):
            return {key: source['id'] if key == 'source_ref' else bind(child) for key, child in value.items()}
        if isinstance(value, list):
            return [bind(child) for child in value]
        return value
    args = bind(args)
    owner = replace(owner, received_record_refs=(source['id'],), assignment={**plain(owner.assignment), 'source_refs': [source['id']]})
    repo = LiteratureRateRepository(store, owner.run_id)
    outcome = repo.populate_native(owner, args, 'equal-source-rates')
    saved = repo.read(outcome['result']['sheet_ref'])
    assert saved['sheet']['cells']['retained_fraction']['value'] == 1
    changed = deepcopy(saved)
    changed['sheet']['cells']['retained_fraction'][field] = value
    altered_outcome = deepcopy(outcome)
    altered_outcome['result']['cells'] = deepcopy(changed['sheet']['cells'])
    with pytest.raises(ContractError, match='saved_numeric_type_mismatch'):
        repo._validate_native_saved(changed, {'arguments': args}, altered_outcome)
    assert repo.read(outcome['result']['sheet_ref']) == saved
