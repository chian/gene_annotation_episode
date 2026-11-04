from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.infernal_preparation_calculations import calculate_infernal_statistics
from gene_annotation_episode.infernal_preparation_schema import value
from test_infernal_preparation_statistics import native_stat, operation, payload, populate, retained


def by_key(result):
    return {r['record_key']: r for r in result['rows']}


def outcome(row, name):
    return next(c['outcome'] for c in row['checks'] if c['check'] == name)


def calibration_sheet(case='cmcalibrate_tiny', mode='calibrate', **settings):
    return populate(operation('cmcalibrate',mode,**settings),
        {'models':[retained(case,'original.cm','models','infernal_cm_ascii')]},
        {'calibrated_models':[retained(case,'model.cm','calibrated_models','infernal_cm_ascii')],
         'stdout':[retained(case,'stdout.txt','stdout','infernal_stdout')]})


def test_native_paired_fraction_keeps_actual_numerator_and_denominator():
    sheet = native_stat('cmstat_summary','summary')
    result = calculate_infernal_statistics(sheet,parameters={})
    row = result['rows'][0]
    assert row['components']['paired_consensus_numerator']['value'] == 8
    assert row['components']['consensus_length_denominator']['value'] == 12
    assert row['components']['paired_consensus_fraction']['value'] == 2/3
    assert outcome(row,'summary_header_counts_consistent') == 'pass'
    invalid = deepcopy(sheet)
    invalid['native_rows'][0]['values']['base_pairs']['value'] = 7
    row = calculate_infernal_statistics(invalid,parameters={})['rows'][0]
    assert row['components']['paired_consensus_fraction']['state'] == 'invalid'
    assert outcome(row,'paired_topology_coherent') == 'fail'
    invalid = deepcopy(sheet)
    invalid['native_rows'][0]['values']['nseq']['value'] = 4
    row = calculate_infernal_statistics(invalid,parameters={})['rows'][0]
    assert outcome(row,'summary_header_counts_consistent') == 'fail'


def test_native_calibration_fit_residual_preserves_header_precision():
    sheet = calibration_sheet(**{'-L':.01})
    result = by_key(calculate_infernal_statistics(sheet,parameters={}))
    source = next(r for r in sheet['native_rows'] if r['kind']=='calibration' and r['identity']==dict(algorithm='cm_local_cyk',source='model_header',name='fixture246'))
    row = result[source['record_key']]
    expected = -2.53576-math.log(10)/.44855
    assert row['components']['mu_extrap_calculated']['value'] == pytest.approx(expected,abs=1e-12)
    assert row['components']['mu_extrap_residual']['value'] == pytest.approx(expected+7.66916,abs=1e-12)
    assert row['components']['actual_calibration_nt']['value'] == 10000
    assert row['components']['total_calibration_chunk_count']['value'] == 1
    assert outcome(row,'calibration_fit_consistent') == 'pass'
    assert outcome(row,'calibration_length_consistent') == 'pass'
    assert row['components']['mu_extrap_residual']['value'] == pytest.approx(3.292845735636263e-6,abs=1e-12)


@pytest.mark.parametrize('case,mode,settings', [('cmstat_E','scores_at_evalue',{'-E':.01,'-Z':10}),
    ('cmstat_P','scores_at_pvalue',{'-P':.01}), ('cmstat_T','evalues_at_score',{'-T':10,'-Z':10}),
    ('cmstat_hmm_E','scores_at_evalue',{'-E':.01,'-Z':10,'--hmmonly':True}),
    ('cmstat_hmm_T','evalues_at_score',{'-T':10,'-Z':10,'--hmmonly':True})])
def test_native_cm_hmm_conversions_have_independent_known_formula(case, mode, settings):
    sheet = native_stat(case,mode,**settings)
    result = calculate_infernal_statistics(sheet,parameters={})
    first = result['rows'][0]['components']
    model = sheet['input_records'][0]
    if case.startswith('cmstat_hmm'):
        fit = next(s for s in model['filter_hmm']['stats'] if s['algorithm']=='FORWARD')
        mu, lam = fit['location']['value'], fit['scale']['value']
        count = 10e6/model['filter_hmm']['fields']['MAXL']['value']
    else:
        fit = model['calibration']['ECMLI']
        mu, lam = -8.38171,.36791
        count = 3812000
    if mode == 'scores_at_evalue':
        assert first['score_at_evalue']['value'] == pytest.approx(mu-math.log(.01/count)/lam,abs=1e-10)
        assert abs(first['native_conversion_residual']['value']) < .005
        assert first['native_rounding_half_width']['value'] == .005
    elif mode == 'scores_at_pvalue':
        assert first['score_at_pvalue']['value'] == pytest.approx(mu-math.log(.01)/lam,abs=1e-10)
    else:
        assert first['evalue_at_score']['value'] == pytest.approx(count*math.exp(-lam*(10-mu)),rel=1e-12)
        assert first['native_conversion_residual']['unit'] == 'expected_count'


def test_hmm_p_three_actual_algorithm_fits_and_no_glocal_viterbi_invention():
    sheet = native_stat('cmstat_hmm_P','scores_at_pvalue',new=True,**{'--hmmonly':True,'-P':.01})
    result = calculate_infernal_statistics(sheet,parameters={})
    values = [r['components']['score_at_pvalue']['value'] for r in result['rows']]
    assert values[:3] == pytest.approx([3.77,-1.26,3.46],abs=.005)
    assert values[3] is None
    model = sheet['input_records'][0]
    gf = model['efp7gf']
    assert values[2] == pytest.approx(gf['location']['value']-math.log(.01)/gf['scale']['value'],abs=1e-12)


def test_exact_synthetic_known_answers_saved_recalculation_without_tool(monkeypatch):
    sheet = native_stat()
    fit = sheet['input_records'][0]['calibration']['ECMLI']
    for key, number in dict(mu_extrap=5.,lambda_=2.,calibration_dbsize_nt=10000,random_hit_count=20).items():
        key = 'lambda' if key == 'lambda_' else key
        fit[key]['value'],fit[key]['native_token'] = number,None
    saved = json.loads(json.dumps(sheet))
    original = json.dumps(saved,sort_keys=True)
    import gene_annotation_episode.infernal_preparation_models as models
    import gene_annotation_episode.infernal_preparation_statistics as stats
    import socket
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError('saved calculation tried acquisition or native execution')
    monkeypatch.setattr(models,'extract_infernal_models',forbidden)
    monkeypatch.setattr(stats,'populate_infernal_statistics_sheet',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    result = calculate_infernal_statistics(saved,parameters=dict(search_space_mb=1,evalue=2000*math.exp(-2),pvalue=math.exp(-4),score_bits=6))
    row = result['rows'][0]
    c = row['components']
    assert c['effective_random_hit_count']['value'] == 2000
    assert c['score_at_evalue']['value'] == pytest.approx(6,abs=1e-12)
    assert c['score_at_pvalue']['value'] == pytest.approx(7,abs=1e-12)
    assert c['evalue_at_score']['value'] == pytest.approx(270.6705664732254,abs=1e-10)
    assert outcome(row,'native_conversion_consistent') == 'not_applicable'
    assert json.dumps(saved,sort_keys=True) == original
    changed = calculate_infernal_statistics(saved,parameters=dict(search_space_mb=2,evalue=2000*math.exp(-2)))
    assert changed['rows'][0]['components']['score_at_evalue']['value'] == pytest.approx(6+math.log(2)/2,abs=1e-12)


@pytest.mark.parametrize('kind',['GA','NC','TC'])
def test_actual_cutoff_header_vs_native_threshold_edge_is_not_repaired(kind):
    sheet = native_stat('cmstat_'+kind+'_present','evalues_at_'+kind.lower(),new=True,**{'-Z':10})
    result = calculate_infernal_statistics(sheet,parameters={})
    assert sheet['input_records'][0]['fields'][kind]['value'] == 10
    threshold = sheet['native_rows'][0]['values']['threshold_bits']['value']
    assert threshold == (10 if kind=='GA' else 0)
    assert outcome(result['rows'][0],'native_cutoff_consistent') == ('pass' if kind=='GA' else 'fail')
    if kind != 'GA':
        assert any(i['field']=='threshold_bits' for i in result['issues'])


def test_missing_calibration_and_nonfinite_math_do_not_make_fake_numbers():
    sheet = native_stat()
    sheet['input_records'][0]['calibration']['ECMLI'] = None
    row = calculate_infernal_statistics(sheet,parameters={})['rows'][0]
    assert row['components']['score_at_evalue']['state'] == 'missing'
    sheet = native_stat('cmstat_T','evalues_at_score',**{'-Z':10,'-T':10})
    result = calculate_infernal_statistics(sheet,parameters={'score_bits':1e300})
    assert result['rows'][0]['components']['evalue_at_score']['state'] == 'invalid'
    assert any(i['code'].endswith('underflow') for i in result['issues'])
    json.dumps(result,allow_nan=False)


def test_predictions_are_not_observations_or_annotation_confidence():
    p = retained('cmcalibrate_memreq_without_cpu_env','stdout.txt','stdout','infernal_stdout')
    m = retained('cmcalibrate_memreq_without_cpu_env','model.cm','models','infernal_cm_ascii')
    sheet = populate(operation('cmcalibrate','memory_estimate'),{'models':[m]},{'stdout':[p]})
    result = calculate_infernal_statistics(sheet,parameters={})
    assert [r['components']['predicted_bytes']['value'] for r in result['rows']] == [72100000,288400000]
    assert all(r['components']['predicted_bytes']['basis']=='native_prediction' for r in result['rows'])
    assert 'confidence' not in json.dumps(result)


def merge_sheet():
    inputs = {'models':[retained('cmcalibrate_merge','original.cm','models','infernal_cm_ascii')],
              'partition_scores':[retained('cmcalibrate_merge','part.1','partition_scores','infernal_partition_scores',ref='part1'),
                                  retained('cmcalibrate_merge','part.2','partition_scores','infernal_partition_scores',ref='part2')]}
    outputs = {'calibrated_models':[retained('cmcalibrate_merge','model.cm','calibrated_models','infernal_cm_ascii')],
               'stdout':[retained('cmcalibrate_merge','stdout.txt','stdout','infernal_stdout')]}
    sheet = populate(operation('cmcalibrate','merge_scores',**{'-L':.02,'--ptot':2,'--seed':181,'--tailp':.1}),inputs,outputs)
    requests = [dict(artifact_ref='part'+str(p),source_model_artifact_ref='models',source_model_sha256=inputs['models'][0]['artifact']['sha256'],
        partition_index=p,partition_count=2,requested_megabases=.02,settings={'--part':p,'--ptot':2,'-L':.02,'--seed':181,'--tailp':.1}) for p in (1,2)]
    return sheet,requests


def test_merge_requires_actual_complete_unique_requests_and_retains_all_arrays():
    sheet,requests = merge_sheet()
    result = by_key(calculate_infernal_statistics(sheet,parameters={'partition_requests':requests}))
    parts = [r for r in sheet['native_rows'] if r['kind']=='partition']
    assert len(parts) == 8
    assert sum(len(r['series']) for r in parts) == sum([6330,6207,8366,7127])
    for r in parts:
        calculated = result[r['record_key']]
        assert outcome(calculated,'partition_request_binding') == 'pass'
        assert outcome(calculated,'partition_population_complete') == 'pass'
        assert outcome(calculated,'partition_settings_consistent') == 'pass'
        assert calculated['components']['partition_chunk_count']['value'] == 1
        assert calculated['components']['total_calibration_chunk_count']['value'] == 2
        assert calculated['components']['actual_calibration_nt']['value'] == 10000
    for r in sheet['native_rows']:
        if r['kind']=='calibration' and r['identity']['source']=='model_header':
            assert outcome(result[r['record_key']],'partition_merged_hit_counts') == 'pass'
    absent = by_key(calculate_infernal_statistics(sheet,parameters={}))
    assert outcome(absent[parts[0]['record_key']],'partition_request_binding') == 'unknown'
    assert outcome(absent[parts[0]['record_key']],'partition_population_complete') == 'unknown'
    assert absent[parts[0]['record_key']]['components']['partition_chunk_count']['state']=='missing'
    duplicate = calculate_infernal_statistics(sheet,parameters={'partition_requests':[requests[0],requests[0]]})
    assert any(i['code'].endswith('partition_population_invalid') for i in duplicate['issues'])
    mixed = deepcopy(requests)
    mixed[1]['settings']['--seed'] = 7
    mixed_result = calculate_infernal_statistics(sheet,parameters={'partition_requests':mixed})
    assert any(i['code'].endswith('partition_settings_mismatch') for i in mixed_result['issues'])


def test_partition_cyclic_allocation_is_not_whole_requested_population():
    sheet,requests = merge_sheet()
    result = calculate_infernal_statistics(sheet,parameters={'requested_megabases':.045,'partition_index':2,'partition_count':3})
    row = next(r for r in result['rows'] if '#partition/' in r['record_key'])
    assert row['components']['total_calibration_chunk_count']['value'] == 5
    assert row['components']['partition_chunk_count']['value'] == 2
    assert row['components']['actual_calibration_nt']['value'] == 20000


@pytest.mark.parametrize('parameters',[{'pvalue':0},{'pvalue':1.1},{'evalue':True},{'search_space_mb':float('inf')},{'other':1},
                                      {'partition_count':2.5},{'partition_count':2,'partition_index':3}])
def test_invalid_parameters_are_api_errors(parameters):
    with pytest.raises(ValueError):
        calculate_infernal_statistics(native_stat(),parameters=parameters)


def test_invalid_fit_missing_denominator_and_wrong_units_are_not_results():
    sheet = native_stat()
    sheet['input_records'][0]['calibration']['ECMLI']['lambda']['value'] = 0
    row = calculate_infernal_statistics(sheet,parameters={})['rows'][0]
    assert row['components']['score_at_evalue']['state']=='invalid'
    sheet = native_stat('cmstat_hmm_E','scores_at_evalue',**{'-E':.01,'-Z':10,'--hmmonly':True})
    sheet['input_records'][0]['filter_hmm']['fields']['MAXL'] = value(state='missing',unit='nt')
    row = calculate_infernal_statistics(sheet,parameters={})['rows'][0]
    assert row['components']['score_at_evalue']['state']=='missing'
    sheet = native_stat()
    sheet['native_rows'][0]['values']['threshold_bits']['unit']='count'
    with pytest.raises(ValueError,match='units'):
        calculate_infernal_statistics(sheet,parameters={})


def test_wrong_partition_source_and_changed_merge_settings_cannot_validate_merge():
    sheet, requests = merge_sheet()
    requests[0]['source_model_sha256']='a'*64
    result = calculate_infernal_statistics(sheet,parameters={'partition_requests':requests})
    assert any(i['code'].endswith('partition_request_mismatch') for i in result['issues'])
    assert all(c['outcome']!='pass' for r in result['rows'] for c in r['checks'] if c['check']=='partition_merged_hit_counts')
    sheet, requests = merge_sheet()
    sheet['operation']['settings']['--tailp']=.2
    result = calculate_infernal_statistics(sheet,parameters={'partition_requests':requests})
    assert any(i['code'].endswith('partition_settings_mismatch') for i in result['issues'])


def test_native_g_precision_retains_suppressed_trailing_zeros():
    sheet = native_stat('cmstat_T','evalues_at_score',**{'-Z':10,'-T':10})
    native = sheet['native_rows'][0]['values']['evalue']
    native['value'],native['native_token'] = 1.0,'1'
    result = calculate_infernal_statistics(sheet,parameters={})
    assert result['rows'][0]['components']['native_rounding_half_width']['value'] == pytest.approx(.000005)


def test_a_single_selected_partition_does_not_require_its_sibling_jobs():
    sheet,requests = merge_sheet()
    sheet['operation']=operation('cmcalibrate','partition_scores',**{'--part':1,'--ptot':2,'-L':.02,'--seed':181,'--tailp':.1})
    sheet['native_rows']=[r for r in sheet['native_rows'] if r['kind']=='partition' and r['locator']['artifact_ref']=='part1']
    result=calculate_infernal_statistics(sheet,parameters={'partition_requests':[requests[0]]})
    assert all(outcome(r,'partition_population_complete')=='pass' for r in result['rows'])
    assert all(outcome(r,'partition_request_binding')=='pass' for r in result['rows'])
    assert not result['issues']


@pytest.mark.parametrize('megabases',[1e306,1e308])
def test_extreme_finite_partition_arithmetic_is_diagnosed_without_nonfinite_json(megabases):
    sheet,_ = merge_sheet()
    result=calculate_infernal_statistics(sheet,parameters={'requested_megabases':megabases,'partition_index':1,'partition_count':1})
    row=next(r for r in result['rows'] if '#partition/' in r['record_key'])
    assert row['components']['actual_calibration_nt']['state']=='invalid'
    assert any(i['code'].endswith('overflow') for i in result['issues'])
    json.dumps(result,allow_nan=False)
