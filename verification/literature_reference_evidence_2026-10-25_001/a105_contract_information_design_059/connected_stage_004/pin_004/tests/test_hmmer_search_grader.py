"""Checkable native components and acquisition-free saved-sheet recalculation."""
from copy import deepcopy
import json
import math
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_search_inputs import build_hmmer_search_sheet, parse_hmmer_api_result
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores, SCALARS
from test_hmmer_search_inputs import native, synthetic_api, PAGE1


def api_sheet(payload=None,inputs=None,algorithm='phmmer'):
    return build_hmmer_search_sheet(parse_hmmer_api_result(payload or synthetic_api(algorithm),algorithm=algorithm,artifact_ref='fixture'),inputs=inputs or {})


def test_actual_api_identity_denominators_units_and_posterior_bounds():
    s = api_sheet(json.loads(PAGE1.read_text()))
    r = calculate_hmmer_search_scores(s)
    d = r['domains'][1]
    assert set(SCALARS) <= d.keys()
    assert (d['paired_positions'],d['insert_positions'],d['delete_positions'],d['alignment_columns']) == (88,2,1,91)
    assert d['api_identity_fraction'] == pytest.approx(25/89)
    assert d['consensus_identity_fraction'] == pytest.approx(25/88)
    assert d['alignment_identity_fraction'] == pytest.approx(25/91)
    assert d['sequence_identity_fraction'] is None
    assert d['native_domain_bias_bits'] == pytest.approx(.03572461009025574/math.log(2))
    assert d['native']['domain_bias_nats'] == .03572461009025574
    assert d['posterior_lower_mean'] == pytest.approx(.8277777777777777)
    assert d['posterior_upper_mean'] == pytest.approx(.9094444444444444)
    assert d['posterior_population']['observed_residues'] == 90
    assert 'elapsed' not in r['domains'][0]


def test_profile_consensus_and_actual_sequence_identity_are_separate():
    inputs={'query':{'name':'q','kind':'protein_sequence','sequence':'ACDEAAAAAA','length':10},
            'targets':[{'name':'target','kind':'protein_sequence','sequence':'AACGEAAAAAAA','length':12}]}
    d=calculate_hmmer_search_scores(api_sheet(inputs=inputs))['domains'][0]
    assert d['sequence_identity_fraction'] == 1.0
    assert d['consensus_identity_fraction'] == 1.0
    assert d['alignment_identity_fraction'] == 3/5
    assert d['api_identity_fraction'] == 3/4
    inputs['query']['sequence']='AAAAAAAAAA'
    d=calculate_hmmer_search_scores(api_sheet(inputs=inputs))['domains'][0]
    assert d['sequence_identity_fraction'] is None
    assert any(i['code']=='hmmer_alignment_operand_sequence_mismatch' for i in d['issues'])
    scan_inputs={'query':{'name':'q','kind':'protein_sequence','sequence':'AACGEAAAAAAA','length':12},
                 'targets':[{'name':'model','kind':'profile','length':10}]}
    d=calculate_hmmer_search_scores(api_sheet(inputs=scan_inputs,algorithm='hmmscan'))['domains'][0]
    assert d['consensus_identity_fraction']==1.0 and d['sequence_identity_fraction'] is None
    assert (d['model_length'],d['sequence_length'])==(10,12)


def test_native_role_inversion_gap_and_span_measurements():
    search=calculate_hmmer_search_scores(build_hmmer_search_sheet(native('hmmsearch'),inputs={}))
    scan=calculate_hmmer_search_scores(build_hmmer_search_sheet(native('hmmscan'),inputs={}))
    a=next(d for d in search['domains'] if d['target_name']=='test2')
    b=next(d for d in scan['domains'] if d['query_name']=='test2')
    for d in (a,b):
        assert (d['model_length'],d['sequence_length'])==(20,25)
        assert (d['paired_positions'],d['insert_positions'],d['delete_positions'])==(18,3,2)
        assert d['model_span_positions']==20 and d['sequence_span_residues']==21
        assert d['model_span_coverage']==1 and d['paired_model_coverage']==.9
        assert d['sequence_span_coverage']==21/25 and d['paired_sequence_coverage']==18/25
        assert d['native_domain_score_bits']==39.6
        assert d['native_domain_bias_bits']==6.1
        assert d['native_accuracy']==.94
    assert a['native_independent_evalue'] != b['native_independent_evalue']


def test_jackhmmer_rounds_are_not_independent_and_final_table_not_all_rounds():
    s=build_hmmer_search_sheet(native('jackhmmer'),inputs={})
    r=calculate_hmmer_search_scores(s)
    assert len(r['domains'])==8 and len(r['iterations'])==2
    assert all(i['dependent_round'] for i in r['iterations'])
    assert [i['native_new_targets'] for i in r['iterations']]==[4,0]
    assert [i['native_converged'] for i in r['iterations']]==[False,True]
    assert all(d['sequence_identity_fraction'] is None for d in r['domains'])
    assert [i['acquired_hit_row_count'] for i in r['iterations']]==[4,4]
    assert all(d['iteration']==2 for d in r['domains'] if d['locator']['artifact_role']=='domtblout')


def test_posterior_characters_are_intervals_with_explicit_residue_population():
    d=calculate_hmmer_search_scores(api_sheet())['domains'][0]
    assert d['posterior_population']['observed_residues']==4
    assert d['posterior_population']['gap_columns']==1
    assert d['posterior_lower_mean']==pytest.approx((0+.95+.85+.95)/4)
    assert d['posterior_upper_mean']==pytest.approx((.05+1+.95+1)/4)
    assert d['posterior_population']['upper_endpoint_closed'] is False
    p=synthetic_api();p['result']['hits'][0]['domains'][0]['alignment_display']['ppline']='.....'
    d=calculate_hmmer_search_scores(api_sheet(p))['domains'][0]
    assert d['posterior_lower_mean'] is None and d['posterior_population']['missing_residues']==4


def test_cutoff_scopes_zero_evalue_and_negative_scores():
    inputs={'model_cutoffs':[{'name':'q','GA':{'sequence_bits':5,'domain_bits':-1},'TC':{'sequence_bits':20}}]}
    d=calculate_hmmer_search_scores(api_sheet(inputs=inputs))['domains'][0]
    assert d['native_domain_score_bits']==-2.5 and d['native_conditional_evalue']==0
    rows={(x['cutoff'],x['scope']):x for x in d['cutoff_margins']['values']}
    assert rows['GA','sequence']['margin_bits']==3
    assert rows['GA','domain']['margin_bits']==-1.5
    assert rows['TC','sequence']['margin_bits']==-12
    assert rows['TC','domain']['margin_bits'] is None
    assert all(math.isfinite(x) for x in [d['native_domain_score_bits'],d['native_conditional_evalue']])


def test_overlapping_domain_union_is_per_hit_and_not_sum():
    p=synthetic_api()
    d=deepcopy(p['result']['hits'][0]['domains'][0])
    p['result']['hits'][0]['domains'].append(d)
    r=calculate_hmmer_search_scores(api_sheet(p))
    assert len(r['domains'])==2
    assert r['hits'][0]['interval_unions']['sequence']['positions']==4
    assert r['hits'][0]['interval_unions']['model']['positions']==4
    assert r['hits'][0]['retained_domain_count']==2


def test_missing_denominator_leaves_span_and_native_score_available():
    p=synthetic_api()
    p['result']['hits'][0]['domains'][0]['alignment_display']['l']=None
    d=calculate_hmmer_search_scores(api_sheet(p))['domains'][0]
    assert d['sequence_length'] is None and d['sequence_span_coverage'] is None
    assert d['sequence_span_residues']==4 and d['paired_positions']==3
    assert d['native_domain_score_bits']==-2.5


def test_saved_sheet_recalculation_needs_no_io_network_or_execution(monkeypatch):
    s=json.loads(json.dumps(api_sheet(json.loads(PAGE1.read_text()))))
    before=deepcopy(s)
    def prohibited(*args,**kwargs): raise AssertionError('recalculation attempted external operation')
    monkeypatch.setattr('builtins.open',prohibited)
    monkeypatch.setattr(socket,'socket',prohibited)
    monkeypatch.setattr(subprocess,'Popen',prohibited)
    a=calculate_hmmer_search_scores(s)
    b=calculate_hmmer_search_scores(s,parameters={})
    assert a==b and s==before
    assert a['domains'][1]['consensus_identity_fraction']==25/88


@pytest.mark.parametrize('parameters',[{'evalue_floor':1e-100},{'foo':0}])
def test_undeclared_parameters_rejected(parameters):
    with pytest.raises(ValueError,match='hmmer_unsupported_calculator_parameters'):
        calculate_hmmer_search_scores(api_sheet(),parameters=parameters)


def test_nonfinite_sheet_rejected():
    s=api_sheet();s['domains'][0]['native']['domain_score_bits']=float('inf')
    with pytest.raises(ValueError,match='hmmer_nonfinite'):
        calculate_hmmer_search_scores(s)


def test_damaged_saved_component_keeps_other_measurements_and_siblings():
    s=api_sheet(json.loads(PAGE1.read_text()))
    s['domains'][0]['native']['domain_score_bits']='damaged'
    r=calculate_hmmer_search_scores(s)
    assert r['domains'][0]['native_domain_score_bits'] is None
    assert r['domains'][0]['paired_positions']==31
    assert r['domains'][1]['native_domain_score_bits']==pytest.approx(16.722900390625)
    assert any(i['code']=='hmmer_invalid_saved_numeric_component' for i in r['domains'][0]['issues'])


def test_table_only_occurrence_unknown_does_not_report_zero_hits():
    from gene_annotation_episode.hmmer_search_inputs import parse_hmmer_search_artifacts
    from test_hmmer_search_inputs import NATIVE
    text=(NATIVE/'hmmsearch.tblout').read_text()
    s=build_hmmer_search_sheet(parse_hmmer_search_artifacts(program='hmmsearch',artifacts={'tblout':text},artifact_refs={'tblout':'t'},engine_version='3.4'),inputs={})
    r=calculate_hmmer_search_scores(s)
    assert len(r['hits'])==4
    assert r['queries'][0]['acquired_hit_row_count'] is None


def test_invalid_display_keeps_reported_api_identity_independently():
    p=synthetic_api();p['result']['hits'][0]['domains'][0]['alignment_display']['model']='A'
    d=calculate_hmmer_search_scores(api_sheet(p))['domains'][0]
    assert d['paired_positions'] is None
    assert d['api_identity_fraction']==.75
    assert d['components']['api_identity_fraction']['denominator'] is None
