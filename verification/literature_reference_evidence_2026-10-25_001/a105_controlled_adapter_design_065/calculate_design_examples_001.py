"""Synthetic expected interface examples through frozen006, not a new reader.

No paper, source interpretation, model, native repository or episode is run.
Graph operands and reconciled operands here are explicitly proposed parsed
fixtures; they are NOT captured outputs of an implemented v2 adapter.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PIN = BASE / 'a105_controlled_response_design_056/implementation_stage_008/execution_pin_008'
sys.path.insert(0, str(PIN))
from gene_annotation_episode import literature_controlled_response_calculations as calc


def emit(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def graph(arm, value, lower, upper):
    result = deepcopy(arm)
    result.update(value=value, relation='interval', approximate=True,
                  origin='graph_derived', digitization_interval={'lower': lower, 'upper': upper})
    result['source_observation_id'] += '_constructed_graph'
    return result


def main():
    fixture = json.loads((BASE / 'a105_controlled_response_design_056/implementation_stage_008/SYNTHETIC_EXAMPLES_008.json').read_text())
    ordinary = deepcopy(fixture['ordinary']['extraction']['calculation_inputs'])
    shared = deepcopy(fixture['shared_control']['extraction']['calculation_inputs'])
    p1, e1, p0, e0 = calc.PRIMITIVE_ORDER
    mixed = deepcopy(ordinary)
    mixed['arms'][p1] = graph(mixed['arms'][p1], 11.95, 11.85, 12.05)
    shared_graph = deepcopy(shared)
    shared_graph['arms'][p1] = graph(shared_graph['arms'][p1], 11.95, 11.85, 12.05)
    shared_graph['arms'][e1] = graph(shared_graph['arms'][e1], 1.95, 1.85, 2.05)
    shared_graph['arms'][e0] = deepcopy(shared_graph['arms'][e1])
    partial = deepcopy(mixed)
    partial['arms'][e1] = None
    partial.update(covariance=None, variance_status='unknown', model_kind='none')
    invalid = deepcopy(mixed)
    invalid.update(covariance=None, variance_status='unknown', model_kind='none')
    reconciled = deepcopy(shared_graph)
    for role in (e1, e0):
        reconciled['arms'][role] = deepcopy(shared['arms'][e1])
    # Keep nominal original readings separately. Their one canonical reported
    # point must be installed by an explicitly adopted reconciliation function.
    alias = deepcopy(shared_graph)
    alias['arms'][e0] = deepcopy(shared['arms'][e1])
    alias.update(covariance=None, variance_status='unknown', model_kind='none')
    inputs = {'all_text_distinct': ordinary, 'mixed_graph_text': mixed,
              'shared_graph_control': shared_graph, 'one_control_unavailable': partial,
              'reported_point_graph_alias_after_proposed_reconciliation': reconciled,
              'full_source_covariance_invalid': invalid,
              'unreconciled_mixed_alias_DIAGNOSTIC_ONLY': alias}
    cases = {}
    for name, value in inputs.items():
        calc.validate_controlled_response_inputs(value)
        cases[name] = {'synthetic_only': True, 'input_origin': 'proposed parsed fixture, not new reader output',
                       'inputs': value, 'actual_frozen006_sheet': calc.populate_controlled_response(value)}
    def cell(case, component):
        return cases[case]['actual_frozen006_sheet']['cells'][component]
    effect = 'controlled_response_difference'
    assert cell('all_text_distinct', effect)['value'] == .006
    assert cell('mixed_graph_text', effect)['value'] == .00595
    assert cell('mixed_graph_text', effect)['lower'] == .00585
    assert cell('mixed_graph_text', effect)['upper'] == .00605
    assert cell('mixed_graph_text', 'contrast_variance')['value'] == 1.7e-6
    assert cell('shared_graph_control', effect)['value'] == .00695
    assert cell('shared_graph_control', effect)['lower'] == .00685
    assert cell('shared_graph_control', effect)['upper'] == .00705
    assert cell('shared_graph_control', 'contrast_variance')['value'] == 1.36e-6
    assert cell('one_control_unavailable', effect)['value'] is None
    assert cell('one_control_unavailable', 'condition0_controlled_response')['value'] == .004
    assert cell('reported_point_graph_alias_after_proposed_reconciliation', effect)['value'] == .00695
    assert cell('reported_point_graph_alias_after_proposed_reconciliation', 'contrast_variance')['value'] == 1.36e-6
    assert cell('unreconciled_mixed_alias_DIAGNOSTIC_ONLY', effect)['status'] == 'conflicting'
    assert cell('full_source_covariance_invalid', effect)['value'] == .00595
    assert cell('full_source_covariance_invalid', 'contrast_variance')['value'] is None
    for row in cases.values():
        assert row['actual_frozen006_sheet']['cells']['source_profile_log_ratio']['value'] is None
    # Full original N=6, with role projection [3,1,4,1]. Two unused variables
    # deliberately have the same label; actual positions keep them distinct.
    labels = ['unused','shared empty','unused','protein one','protein zero','other']
    variances = [9, .25, 4, 1, .36, 16]
    matrix = [[variances[i] if i == j else 0 for j in range(6)] for i in range(6)]
    indices = [3, 1, 4, 1]
    projected = [[matrix[i][j] for j in indices] for i in indices]
    assert projected == shared['covariance']['matrix']
    full_source = {'version':'controlled_response_covariance_source_v1',
        'variables':[{'label':label,'unit':'nmol/min/mg','description':'Constructed physical owner '+str(i)} for i,label in enumerate(labels)],
        'covariance':matrix, 'origin':'synthetic', 'variance_status':'known','model_kind':'none'}
    # These expected fields are proposed v2 source/meaning results, not produced
    # by any existing reader with a graph response unit.
    expected_uncertainty = {'statistic':'sd','magnitude':.0006,'interval':None,
        'confidence_level':None,'count':3,'repetition_basis':'technical_measurements','estimate_basis':'unknown'}
    emit('EXAMPLES_001.json', {'scope':'frozen006 calculations over synthetic proposed parsed inputs; no v2 reader execution',
        'cases':cases, 'constructed_full_N_covariance_source':full_source,'source_projection_indices':indices,
        'projected_covariance':projected, 'expected_graph_arm_reported_uncertainty_NOT_ACTUAL_V2_OUTPUT':expected_uncertainty,
        'proposed_alias_reconciliation':{'method':'reported_point_graph_check','reported_point':'2',
            'graph_nominal':'1.95','graph_conditional_bounds':['1.85','2.05'],'canonical_point':'2',
            'sampling_precision_gained':False,'additional_observations':0,
            'status':'proposal only; exact-domain/unit/owner verification must precede future canonicalization'},
        'point_free_alternative_NOT_SUPPORTED_BY_006':{'domains':[['1.85','2.05'],['1.90','2.10']],
            'intersection':['1.90','2.05'],'canonical_point':None,'requires_separately_versioned_input_calculator':True}})
    table = ['# Constructed expected controlled-response cells065','',
        'Actual frozen006 calculations; all inputs below are proposed parsed fixtures, not captured v2 source-reader outputs. No primary source or model execution.','',
        '|case|d1|d0|e|conditional e bounds|V|', '|---|---:|---:|---:|---|---:|']
    for name in inputs:
        a,b,c,v = (cell(name,key) for key in ('condition1_controlled_response','condition0_controlled_response',effect,'contrast_variance'))
        table.append(f"|{name}|{a['value']}|{b['value']}|{c['value']}|[{c['lower']},{c['upper']}]|{v['value']}|")
    table += ['', 'Rates are umol/min/mg; V is (umol/min/mg)^2. Graph bounds are conditional digitization domains, not sampling CIs. S/B stay unavailable.', '',
        'Full source N=6 projects actual indices [3,1,4,1]; one shared owner cancels. Expected graph-arm reported SD0.6 nmol/min/mg converts to0.0006 umol/min/mg, n3 technical measurements. This spread is not the joint source C.', '',
        'The unreconciled mixed-alias row diagnoses frozen006 behavior; it is not the proposed final scientific result. The reconciled row shows an explicitly proposed canonical reported point after checking the graph domain. No new reader/reconciler or covariance parser was executed.', '']
    with (HERE / 'EXPECTED_CELLS_001.md').open('x') as stream:stream.write('\n'.join(table))
    imports = []
    for name,module in tuple(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module,'__file__',None):
            path = Path(module.__file__).resolve(); assert path.is_relative_to(PIN.resolve())
            imports.append({'module':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    emit('CALCULATION_RECEIPT_001.json', {'actual_project_imports':imports,'cases':len(cases),
        'new_v2_reader_calls':0,'model_calls':0,'runtime_observations':0,'new_scientific_scoring_policy_adopted':False})
    print(json.dumps({'synthetic_expected_cases':len(cases),'actual_frozen006_calls':len(cases),'v2_reader_calls':0,'runtime_observations':0}))


if __name__ == '__main__':
    main()
