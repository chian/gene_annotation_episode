"""Constructed pure-calculator counterexamples; no paper or runtime execution."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PIN = BASE / 'a105_controlled_response_design_056/implementation_stage_008/execution_pin_008'
sys.path.insert(0, str(PIN))
from gene_annotation_episode import literature_controlled_response_calculations as calc
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def arm(value, condition, owner, *, control=False, graph=False):
    meanings = {'endpoint': 'initial_rate', 'normalization': 'same_basis',
        'subject_construct': 'empty_control' if control else 'reference_construct',
        'condition': condition, 'physical_observation': owner}
    return {'value': value, 'threshold': None, 'relation': 'interval' if graph else 'eq',
        'approximate': graph, 'unit': 'nmol/min', 'status': 'point',
        **{key + '_id': value for key, value in meanings.items()},
        'source_observation_id': owner + ('_graph_reading' if graph else '_text_reading'),
        'origin': 'graph_derived' if graph else 'synthetic',
        'digitization_interval': {'lower': float(Fraction(str(value)) - Fraction(1, 10)), 'upper': float(Fraction(str(value)) + Fraction(1, 10))} if graph else None,
        'protein_arrangement': 'empty_vector_control' if control else 'protein_present',
        'meaning_statuses': dict.fromkeys(meanings, 'known')}


def main():
    out = HERE / 'shared_representation_probe_002'
    out.mkdir()
    baseline = {'version': calc.INPUT_VERSION,
        'arms': dict(zip(calc.PRIMITIVE_ORDER, [
            arm(10, 'factor1', 'main1'), arm(4, 'reference_condition', 'controlB', control=True),
            arm(8, 'factor0', 'main0'), arm(4, 'reference_condition', 'controlB', control=True)])),
        'relationships': {
            'condition1_target': {'status': 'known', 'canonical_id': 'factor1'},
            'condition0_target': {'status': 'known', 'canonical_id': 'factor0'},
            'condition_levels_relation': 'different',
            'condition1_control_application': 'shared_reference_assumption',
            'condition0_control_application': 'shared_reference_assumption',
            'subject_construct_across_conditions': 'same',
            'control_reference_reuse': 'same_reference_with_stated_invariance',
            'nonintended_conditions': 'matched', 'intended_factor': 'constructed_factor'},
        'covariance': None, 'variance_status': 'unknown', 'model_kind': 'none'}
    same_graph = deepcopy(baseline)
    for role in ('empty_condition1', 'empty_condition0'):
        same_graph['arms'][role] = arm(4.05, 'reference_condition', 'controlB', control=True, graph=True)
    assert same_graph['arms']['empty_condition0']['digitization_interval'] == {'lower': 3.95, 'upper': 4.15}
    mixed = deepcopy(baseline)
    mixed['arms']['empty_condition0'] = deepcopy(same_graph['arms']['empty_condition0'])
    unknown_owner = deepcopy(mixed)
    unknown_owner['arms']['empty_condition0']['physical_observation_id'] = None
    unknown_owner['arms']['empty_condition0']['meaning_statuses']['physical_observation'] = 'unknown'
    cases = {'same_text': baseline, 'same_graph': same_graph,
             'mixed_compatible_readings': mixed, 'mixed_unknown_owner': unknown_owner}
    report = {}
    for name, inputs in cases.items():
        result = calc.populate_controlled_response(inputs)
        pair1 = result['cells']['condition1_controlled_response']
        pair0 = result['cells']['condition0_controlled_response']
        cross = result['cells']['controlled_response_difference']
        if name in ('same_text', 'same_graph'):
            assert cross['value'] == .002 and cross['bound_kind'] == 'none'
        else:
            assert pair1['value'] == .006 and pair0['value'] == .00395
            assert cross['value'] is None
        if name == 'mixed_compatible_readings':
            assert 'conflicting_source_literal' in cross['unavailable_reason']
        if name == 'mixed_unknown_owner':
            assert 'conflicting_control_reuse' in cross['unavailable_reason']
        report[name] = {'inputs': inputs, 'sheet': result,
            'selected_cells': {key: result['cells'][key] for key in
                ('condition1_controlled_response', 'condition0_controlled_response', 'controlled_response_difference')}}
    # A known full covariance with a genuinely reused control has repeated
    # owner rows, not independent diagonal variances for two displays.
    covariance = {'primitive_order': list(calc.PRIMITIVE_ORDER),
        'physical_observation_ids': ['main1', 'controlB', 'main0', 'controlB'],
        'units': ['nmol/min'] * 4,
        'matrix': [[.25, 0, .1, 0], [0, .04, 0, .04],
                   [.1, 0, .25, 0], [0, .04, 0, .04]]}
    with_covariance = deepcopy(same_graph)
    with_covariance.update(covariance=covariance, variance_status='known')
    shared_sheet = calc.populate_controlled_response(with_covariance)
    assert shared_sheet['cells']['contrast_variance']['value'] == 3e-7
    mixed_covariance = deepcopy(mixed)
    mixed_covariance.update(covariance=covariance, variance_status='known')
    try:
        calc.populate_controlled_response(mixed_covariance)
    except ExperimentalContractError as error:
        assert error.code == 'shared_measurement_context_mismatch'
        covariance_error = {'code': error.code, 'field': error.field}
    else:
        raise AssertionError('mixed representations unexpectedly accepted by frozen006 alias contract')
    report['same_graph_known_covariance'] = shared_sheet
    report['mixed_known_covariance_rejection'] = covariance_error
    report['proposed_algebra_not_implemented'] = {
        'conditional_on': 'scientifically established shared physical control owner and applicable invariance; no missing/unknown identity default',
        'formula': '(A-B)-(C-B) = A-C', 'constructed_A': 10, 'constructed_C': 8,
        'difference_nmol_per_min': str(Fraction(10) - Fraction(8)),
        'difference_umol_per_min': .002,
        'reading_relation': 'Text4 lies in graph conditional digitization interval[3.95,4.15]; that interval is not sampling uncertainty.',
        'warning': 'Symbolic cancellation with retained alternative readings needs an explicit versioned contract/policy; this proof does not implement it or alter006.'}
    path = Path(calc.__file__).resolve()
    assert path.is_relative_to(PIN.resolve())
    report['verification'] = {'calculator_path': str(path), 'calculator_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'case_kind': 'constructed input dictionaries and generated graph operands, not an actual image/source reading',
        'actual_runtime_or_model_execution': False, 'runtime_observations': 0,
        'production_changes': False}
    with (out / 'RESULT_001.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'constructed_cases': len(cases), 'same_text_and_same_graph_cancel': True,
        'mixed_compatible_readings_currently_rejected': True, 'mixed_covariance_error': covariance_error,
        'known_shared_covariance_contrast_variance': 3e-7, 'new_policy_implemented': False}))


if __name__ == '__main__':
    main()
