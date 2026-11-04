"""Native subscoring arithmetic and deterministic routing, no model calls."""
from copy import deepcopy
import math
from pathlib import Path

import pytest

from gene_annotation_episode.a101_scoring import (A101ScoringUnavailable,
    comparison_weight, compile_native_sheet, route_native_grading)


def row(bits=50, algorithm='hmmer', extent=(0,10), **kwargs):
    return {'algorithm':algorithm, 'bits':bits, 'reference_paired_count':10,
        'reference_length':10, 'target_intervals':[list(extent)],
        'alignment_identity':1, **kwargs}


def test_native_exponential_scale_geometry_and_duplicate_maxima():
    native = row()
    expected = 1-math.exp(-1)
    assert comparison_weight(native)['weight'] == pytest.approx(expected)
    assert compile_native_sheet([native],supplied_length=10)['value'] == pytest.approx(expected)
    assert compile_native_sheet([native,native,deepcopy(native)],supplied_length=10)['value'] == pytest.approx(expected)
    assert compile_native_sheet([row(extent=(0,5))],supplied_length=10)['value'] == pytest.approx(expected/2)
    # A new reference on unobserved positions can add actual correspondence.
    assert compile_native_sheet([row(extent=(0,5)),row(extent=(5,10))],supplied_length=10)['value'] == pytest.approx(expected)


def test_declared_tools_are_averaged_and_required_regions_are_geometric():
    rows = [row(),row(bits=40,algorithm='blast',alignment_identity=0)]
    expected = (1-math.exp(-1))*0.75
    result=compile_native_sheet(rows,supplied_length=10)
    assert result['profile']==['blast','hmmer']
    assert result['value']==pytest.approx(expected)
    assert result['function_specific_index']['value'] is None
    assert result['full_target_index']['value'] is None
    assert compile_native_sheet([row(extent=(0,5))],supplied_length=10,regions=[[0,5],[5,10]])['value']==0
    # Overlapping requests merge; no extra independent requirement is created.
    assert len(compile_native_sheet([row()],supplied_length=10,regions=[[0,7],[3,10]])['regions'])==1


@pytest.mark.parametrize('change,code',[
    ({'bits':None},'native_bits_unavailable'),
    ({'bits':float('nan')},'native_bits_unavailable'),
    ({'reference_paired_count':11},'reference_denominator_unavailable'),
    ({'algorithm':'unknown'},'unsupported_score_profile'),
    ({'algorithm':'blast','alignment_identity':None},'invalid_fraction'),
])
def test_unavailable_or_invalid_operands_are_not_zero_imputed(change,code):
    with pytest.raises(A101ScoringUnavailable,match=code):
        comparison_weight(row(**change))


def test_zero_and_negative_bits_are_actual_zero_native_strength():
    assert comparison_weight(row(bits=0))['weight']==0
    assert comparison_weight(row(bits=-5))['weight']==0
    assert compile_native_sheet([],supplied_length=10)['value']==0


def hmmer_grading():
    # Explicit small synthetic numerical fixture with a deletion and insertion.
    domain={'record_key':'native-domain','target_name':'reference',
        'alignment':{'model':'AB.CD','aseq':'AXY-D'}}
    scores={'record_key':'native-domain','intervals':{'model':[0,4],'sequence':[0,4]},
        'paired_positions':3,'sequence_length':4,'model_length':4,
        'native_domain_score_bits':50,'native_independent_evalue':1e-10,
        'sequence_identity_fraction':2/3}
    return {'sheet':{'schema':'hmmer_search_sheet_v1', 'operation':{'program':'phmmer'},
        'domains':[domain]}, 'scores':{'schema':'hmmer_search_scores_v1','domains':[scores]}}


def test_hmmer_route_preserves_query_profile_orientation_and_paired_positions():
    grade=hmmer_grading()
    populated,=route_native_grading(grade)
    assert populated['target_intervals']==[[0,1],[1,2],[3,4]]
    assert populated['target_symbols']==[(0,'A'),(1,'B'),(3,'D')]
    assert populated['reference_length']==4
    assert populated['reference_paired_count']==3
    assert compile_native_sheet([populated],supplied_length=4)['value']==pytest.approx((1-math.exp(-1))*.75*.75)
    grade['sheet']['operation']['program']='hmmsearch'
    populated,=route_native_grading(grade)
    assert populated['target_intervals']==[[0,1],[1,2],[3,4]]
    assert populated['target_symbols']==[(0,'A'),(1,'X'),(3,'D')]


def test_unknown_profile_and_unmapped_iterated_query_are_explicit():
    with pytest.raises(A101ScoringUnavailable,match='unsupported_score_profile'):
        route_native_grading({'sheet':{'schema':'unknown'}})
    grade=hmmer_grading();grade['sheet']['operation']['program']='jackhmmer'
    with pytest.raises(A101ScoringUnavailable,match='original_query_mapping_unavailable'):
        route_native_grading(grade)


def test_blast_route_uses_native_bits_reference_denominator_and_all_column_identity():
    native={'qseq':'A-CD','hseq':'ABXD','query_from':1,'hit_from':1}
    component={'counts':{'paired_columns':3,'identical_pairs':2},
        'native_scores':{'bit_score':40,'evalue':1e-8}}
    grade={'sheet':{'schema':'blast_pairwise_sheet_v1','input':{'search':{'program':'blastp'}},
        'reference':{'length':5},'hsps':[{'hsp_index':0,'native':native,'components':component}]}}
    populated,=route_native_grading(grade)
    assert populated['alignment_identity']==.5
    assert populated['reference_paired_count']==3
    assert populated['reference_length']==5
    assert compile_native_sheet([populated],supplied_length=3)['value']==pytest.approx((1-math.exp(-1))*.6*.75)


def test_existing_blast_grader_output_populates_the_sheet_without_a_model():
    from gene_annotation_episode.blast_graders import grade_blast_result
    raw=(Path(__file__).with_name('fixtures')/'blast_grading_inputs/native_pair_result.json').read_bytes()
    grade=grade_blast_result(raw,mode='pairwise',resource='local',output_format='json2')
    rows=route_native_grading(grade)
    assert rows and all(r['algorithm']=='blast' for r in rows)
    length=grade['sheet']['query']['length']
    result=compile_native_sheet(rows,supplied_length=length)
    assert 0<result['value']<=1


def test_received_native_observation_without_a_grader_fails_explicitly(tmp_path):
    from gene_annotation_episode.a101_credit import A101SequenceCredit
    from gene_annotation_episode.state import Store
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='MACDEFGHIK',molecule='protein')['subject_refs']
        artifact=store.artifact('retained native result','text/plain')
        source=store.put('source',{'provider':'native.phmmer.alignment','accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None},origin='tool')['id']
        observed=store.put('observation',{'subject_refs':[target],'source_subject_refs':[],
            'kind':'alignment','source_ref':source,'anchor':None,'dependencies':[target],
            'measurements':[{'name':'bitscore','value':{'type':'number','value':100,'unit_ref':None}}]},origin='tool')['id']
        score=A101SequenceCredit()
        # Merely existing in shared state earns no credit.
        assert score(store,{'subject_refs':[target]},known_record_refs=[])['credit']==0
        with pytest.raises(A101ScoringUnavailable,match='native_grader_not_attached'):
            score(store,{'subject_refs':[target]},known_record_refs=[observed])


def test_database_blast_native_grader_is_routed_through_received_hsp_address(tmp_path):
    import json
    from gene_annotation_episode.a101_credit import A101SequenceCredit
    from gene_annotation_episode.blast_search import native_hsp_metadata, HSP_PROJECTION_VERSION
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
    from test_blast_graders_integration import grade_json, native_document
    grade=grade_json(_retain_correspondence=True)
    document=native_document()
    search=document['BlastOutput2'][0]['report']['results']['search']
    native=search['hits'][0]['hsps'][0]
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='ACDEFXXXXX',molecule='protein')['subject_refs']
        artifact=store.artifact(json.dumps(document).encode(),'application/json')
        retained=retain_tool_grading(store,provider='ncbi_blast',
            native_artifact_ref=artifact,grading=grade)
        source=store.put('source',{'provider':'ncbi_blast','accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
            'auxiliary_artifact_refs':[retained]},origin='tool')['id']
        reference=store.put('reference',{'reference_type':'protein','source_ref':source,
            'accession':'SYN_A','label':'Controlled native fixture','sequence_ref':None,
            'molecule':'protein','length':10,'term_refs':[],'context_refs':[]},origin='tool')['id']
        metadata=native_hsp_metadata(native,program='blastp',query_length=10,
            reference_length=10,hit_ordinal=0,hsp_ordinal=0)
        metadata['shared_projection']={'version':HSP_PROJECTION_VERSION,'grading_artifact_ref':retained,
            'native_artifact_ref':artifact,'hit_row':0,'hsp_row':0}
        observed=store.put('observation',{'subject_refs':[target],'source_subject_refs':[reference],
            'kind':'comparison','source_ref':source,'anchor':None,'dependencies':[target,reference],
            'measurements':[{'name':'bitscore','value':{'type':'number','value':10,'unit_ref':None}}],
            'operand_intervals':[{'role':role,'subject_ref':ref,'start':0,'end':5,'unit':'aa','model_unit':'aa'}
                for role,ref in [('query',target),('reference',reference)]],
            'native_blast':metadata},origin='tool')['id']
        projector=A101SequenceCredit()
        assert projector(store,{'subject_refs':[target]},known_record_refs=[])['credit']==0
        result=projector(store,{'subject_refs':[target]},known_record_refs=[observed])
        assert result['credit']==pytest.approx((1-math.exp(-.025*10))*.5*.5)
        assert result['a101_sheet']['targets'][target]['profile']==['blast']


@pytest.mark.parametrize('options,code',[
    ({'project_credit':None},'root_numeric_credit_binding_is_host_owned'),
    ({'credit_binding':{}},'root_numeric_credit_binding_is_host_owned'),
    ({'episode_record_receipts':False},'numeric_credit_requires_episode_receipts'),
])
def test_a101_workflow_cannot_silently_install_the_wrong_scorer(options,code):
    from gene_annotation_episode.a101_investigation import create_a101_workflow
    with pytest.raises(ValueError,match=code):
        create_a101_workflow(None,None,None,None,'invalid-binding',None,
            initial_known_record_refs=[],**options)
