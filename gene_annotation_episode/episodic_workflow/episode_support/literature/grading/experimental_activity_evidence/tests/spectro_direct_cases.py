"""Spectro_direct experiment records for the grader, converter and merger tests.

real_record: the published ThdF measurement (J Biol Chem 2025, PMC11795597, CC BY 4.0: the Results paragraph on the steady-state kinetics of the flavin reductase
ThdF). Only what the paragraph states is filled (Km for NADH 19.5 uM, kcat 0.21 +- 0.08 s-1 for FAD); everything else is an unavailable operand or an 'unknown' fact.
synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every criterion's supported path.
sparse_record: a record that states nothing.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_record import (
    EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable)

UNITS = {'catalytic_efficiency': 'M^-1 s^-1', 'catalytic_efficiency_spread': 'M^-1 s^-1', 'turnover': 's^-1', 'turnover_spread': 's^-1', 'specific_activity': 'U/mg', 'specific_activity_spread': 'U/mg',
         'rate_over_control': 'fold', 'rate_over_control_spread': 'fold', 'km': 'uM', 'substrate_concentration': 'uM', 'enzyme_concentration': 'nM', 'substrate_consumed_percent': 'percent',
         'wavelength': 'nm', 'extinction_coefficient': 'mM^-1 cm^-1', 'absorbance_max': 'AU', 'enzyme_mass': 'kDa', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref,
            'preparations': {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': None},
            'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES},
            'concentration_series': {'value': None, 'unit': 'uM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series'},
            'spread_kind': None, 'choice_support': {'spread_kind': None}, 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record():
    return blank_record('exp_sparse_spectro_direct', 'source_sparse', 'hypothesis_sparse_activity')


def real_record():
    record = blank_record('exp_thdf_flavin_reduction', 'source_pmc11795597', 'hypothesis_thdf_catalyzes_flavin_reduction')
    record['spans'] = {'span_km': {'locator': 'Results, kinetics paragraph', 'quote': 'KM value for NADH (19.5 μM)'},
                       'span_turnover': {'locator': 'Results, kinetics paragraph', 'quote': '0.21  ± 0.08 s−1'}}
    record['quantities']['km'] = point(19.5, 'uM', 'km', ['span_km'])
    record['quantities']['turnover'] = point(0.21, 's^-1', 'turnover', ['span_turnover'])
    record['quantities']['turnover_spread'] = point(0.08, 's^-1', 'turnover_spread', ['span_turnover'])
    record['preparations'] = {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': 'dataset_pmc11795597_table1'}
    return record


def synthetic_record(experiment_ref='exp_synthetic_spectro_direct_1', enzyme_prep='prep_enzyme_a', dataset='dataset_1', kcat=20.0, spread=1.5):
    record = blank_record(experiment_ref, 'source_synthetic', 'hypothesis_synthetic_activity')
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'analyte_preparation_ref': enzyme_prep, 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': dataset}
    values = {'catalytic_efficiency': 5.0e5, 'catalytic_efficiency_spread': 4.0e4, 'turnover': kcat, 'turnover_spread': spread, 'specific_activity': 25.0, 'specific_activity_spread': 2.0,
              'rate_over_control': 150.0, 'rate_over_control_spread': 12.0, 'km': 40.0, 'substrate_concentration': 200.0, 'enzyme_concentration': 20.0, 'substrate_consumed_percent': 5.0,
              'wavelength': 340.0, 'extinction_coefficient': 6.22, 'absorbance_max': 0.9, 'enzyme_mass': 48.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0], 'uM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['choice_support'] = {'spread_kind': 'direct'}
    record['facts'] = {name: fact('yes', refs) for name in FACTS}
    return record
