"""Approved numerical conventions on explicit synthetic structural cells."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.a102_scoring import (
    A102ScoringUnavailable, NATIVE_SCHEMA, compile_native_sheet, contrast_panel,
    feature_sheet, geometry, grade_comparison,
)


def native(*, length=100, reference_length=100, paired=90, distance=1.0,
           group='comparison-0',variant='variant-0',scope=None,supplied_length=None):
    scope=scope or [0,length]
    return {'schema':NATIVE_SCHEMA,'target_ref':'input_fixture','reference_ref':'reference_fixture',
        'supplied_length':supplied_length or length,'target_scope':scope,
        'reference_length':reference_length,'target_positions':list(range(scope[0],scope[0]+paired)),
        'reference_positions':list(range(paired)),'distances_A':[distance]*paired,
        'comparison_group':group,'variant_ref':variant,'primary':True,'atom_selection':'CA',
        'target_model':{'origin':'supplied_unknown'},'reference_model':{'origin':'experimental'},
        'target_structure_sha256':'a'*64,'reference_structure_sha256':'b'*64,
        'transform_sha256':'c'*64,'native_metrics':{'reported_rmsd_A':distance}}


def features(grade,distances=(0,1,1,2),function='hypothesis_function'):
    return {'comparison_ref':grade['variant_ref'],'function_ref':function,
        'definition_source_refs':['source_feature_definition'],
        'features':[{'physical_feature_key':f'anchor-{i}','state':'measured',
            'distance_A':distance,'transform_sha256':grade['transform_sha256'],
            'witness_refs':['observation_actual_geometry']} for i,distance in enumerate(distances)]}


def test_complete_draft_arithmetic_keeps_native_feature_and_contrast_separate():
    supporting=grade_comparison(native())
    assert supporting['components']['B']==pytest.approx(.72)
    support=feature_sheet(supporting,features(supporting))
    assert support['F']==pytest.approx(.55)
    assert support['E']==pytest.approx(.396)
    opposing=grade_comparison(native(length=125,reference_length=125,paired=100,distance=2,
        group='opposing',variant='opposing-0'))
    opposition=feature_sheet(opposing,features(opposing,(math.sqrt(3),)*4,function='hypothesis_other'))
    assert opposition['E']==pytest.approx(.1)
    panel=contrast_panel([support,opposition],function_ref='hypothesis_function',
        supporting_refs=[support['comparison_ref']],opposing_refs=[opposition['comparison_ref']],
        contrast_witness_refs=['source_incompatibility'],scope_ref='scope_declared')
    assert panel['A102_f']==pytest.approx(.296)


def test_missing_function_inputs_do_not_erase_native_correspondence():
    grade=grade_comparison(native())
    result=compile_native_sheet([grade],target_ref='input_fixture',supplied_length=100)
    assert result['value']==pytest.approx(.72)
    assert result['function_specific_index']['value'] is None
    assert grade['function_specific']['F'] is None


def test_unexamined_opposition_is_unknown_rather_than_a_zero_competitor():
    grade=grade_comparison(native())
    support=feature_sheet(grade,features(grade))
    panel=contrast_panel([support],function_ref='hypothesis_function',
        supporting_refs=[support['comparison_ref']],opposing_refs=None,
        contrast_witness_refs=[],scope_ref='scope_declared')
    assert panel['S']==pytest.approx(.396)
    assert panel['O'] is panel['A102_f'] is None


def test_unresolved_feature_and_established_absence_have_distinct_results():
    grade=grade_comparison(native())
    definition=features(grade)
    definition['features'][-1]={'physical_feature_key':'anchor-3','state':'unresolved',
        'missing_reason':'side_chain_not_observed'}
    unresolved=feature_sheet(grade,definition)
    assert unresolved['F'] is unresolved['E'] is None
    assert unresolved['F_bounds']==pytest.approx([.5,.75])
    definition['features'][-1]={'physical_feature_key':'anchor-3','state':'established_absent',
        'witness_refs':['observation_verified_deletion']}
    absent=feature_sheet(grade,definition)
    assert absent['F']==pytest.approx(.5)
    assert absent['E']==pytest.approx(.36)


def test_small_perfect_fragment_preserves_parent_scope_denominator_once():
    grade=grade_comparison(native(length=20,reference_length=200,paired=20,distance=0,
        supplied_length=200))
    result=compile_native_sheet([grade],target_ref='input_fixture',supplied_length=200)
    assert result['value']==pytest.approx(.1)
    assert result['regions'][0]['comparisons'][0]['symmetric_coverage']==pytest.approx(.1)


def test_duplicate_results_cannot_add_votes_and_unselected_variants_cannot_replace_primary():
    original=grade_comparison(native())
    duplicate=deepcopy(original)
    alternative=grade_comparison(native(paired=100,distance=0,variant='alternative'))
    alternative['primary']=False
    result=compile_native_sheet([original,duplicate,alternative],target_ref='input_fixture',supplied_length=100)
    assert result['value']==pytest.approx(.72)
    assert result['comparison_count']==1
    alternative['primary']=True
    with pytest.raises(A102ScoringUnavailable,match='primary_variant_unresolved'):
        compile_native_sheet([original,alternative],target_ref='input_fixture',supplied_length=100)


def test_self_structure_is_a_control_not_homolog_support():
    value=native()
    value['reference_structure_sha256']=value['target_structure_sha256']
    result=compile_native_sheet([grade_comparison(value)],target_ref='input_fixture',supplied_length=100)
    assert result['value']==0
    assert result['excluded'][0]['reason']=='self_structure_copy'


def test_renaming_a_coordinate_copy_does_not_make_it_independent_evidence():
    value=native()
    value.update(target_coordinate_sha256='d'*64,reference_coordinate_sha256='d'*64)
    grade=grade_comparison(value)
    assert not grade['eligible'] and grade['exclusion']=='self_coordinate_copy'


def test_self_control_feature_geometry_cannot_become_function_support():
    value=native();value['reference_structure_sha256']=value['target_structure_sha256']
    grade=grade_comparison(value);sheet=feature_sheet(grade,features(grade,(0,0,0)))
    assert sheet['F']==1 and sheet['E'] is None and not sheet['eligible']
    with pytest.raises(A102ScoringUnavailable,match='ineligible_or_nonprimary'):
        contrast_panel([sheet],function_ref=sheet['function_ref'],supporting_refs=[sheet['comparison_ref']],
            opposing_refs=[],contrast_witness_refs=[],scope_ref='same_scope')


def test_quality_metadata_does_not_become_a_similarity_weight():
    value=native();value['target_model'].update(origin='predicted',plddt=25,pae=None)
    result=grade_comparison(value)
    assert result['components']['B']==pytest.approx(.72)
    assert result['target_model']['plddt']==25
    assert result['function_specific']['E'] is None


def test_features_use_the_original_scaffold_transform_and_unique_physical_features():
    grade=grade_comparison(native());definition=features(grade)
    definition['features'][0]['transform_sha256']='d'*64
    with pytest.raises(A102ScoringUnavailable,match='scaffold_transform_conflict'):
        feature_sheet(grade,definition)
    definition=features(grade);definition['features'][-1]['physical_feature_key']='anchor-0'
    with pytest.raises(A102ScoringUnavailable,match='duplicate_physical_feature'):
        feature_sheet(grade,definition)


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True])
def test_invalid_geometry_is_an_explicit_error_not_zero_credit(bad):
    with pytest.raises(A102ScoringUnavailable):geometry([bad],100,100)


def test_raw_tm_and_dali_numbers_do_not_silently_select_another_profile():
    value=native();value['native_metrics'].update(tm_target=.99,tm_reference=.98,dali_z=14)
    grade=grade_comparison(value)
    assert grade['components']['B']==pytest.approx(.72)
    assert grade['native_metrics']['dali_z']==14
