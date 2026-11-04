"""Synthetic relative-signal representations; no primary paper is read."""
from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_ratio_calculations import (
    COMPONENTS, REASONS, populate_relative_signal,
)


UNCERTAINTY = {'kind':'unreported','magnitude':None,'count':None,'sampling_basis':'unspecified'}


def observation(value=.64, *, index=0, synthetic=False):
    text='Synthetic relative signal: 64% (variant V) of reference.'
    expression='64% (variant V)'
    start=text.index(expression)
    return {'value':value,'origin':'synthetic' if synthetic else 'reported',
        'source':{'source_ref':'source_primary','artifact_ref':'artifact_primary',
            'representation':'synthetic_fixture' if synthetic else 'primary_jats',
            'section_id':'results','paragraph_index':index,'paragraph_text':text,
            'expression':expression,'expression_start':start,'expression_end':start+len(expression)},
        'uncertainty':deepcopy(UNCERTAINTY)}


def visual(value=1.12, *, printed_label='1.12', reference='1.0', region=None, source='source_transcription'):
    return {'value':value,'origin':'visual_transcription','source':{
        'source_ref':source,'artifact_ref':'artifact_transcription',
        'representation':'retained_visual_transcription','original_source_ref':'source_image',
        'original_artifact_ref':'artifact_image','printed_label':printed_label,
        'image_region':region or [10,20,30,40],
        'reference_printed_label':reference,'reference_image_region':[1,20,9,40]},
        'uncertainty':deepcopy(UNCERTAINTY)}


def test_one_ratio_populates_three_alternative_descriptions_without_a_score():
    result=populate_relative_signal([observation()])
    cells=result['cells']
    assert tuple(cells)==COMPONENTS
    assert cells['reported_ratio']['value']==.64
    assert cells['reported_ratio']['value_candidates']==[.64]
    assert cells['reported_ratio']['origin']=='reported'
    assert cells['difference_from_reference']['value']==-.36
    assert cells['log_reported_ratio']['value']==pytest.approx(-.4462871026284195)
    assert result['candidate_set_complete'] is True
    assert result['independent_preparation_count'] is None
    assert result['annotation_credit'] is None
    for name,reason in [('calibrated_amount_ratio','amount_calibration_unreported'),
        ('amount_adjusted_effect','response_model_unreported'),
        ('source_profile_log_ratio','uncertainty_model_unreported'),
        ('source_signed_index','uncertainty_model_unreported')]:
        assert cells[name]['value'] is None
        assert cells[name]['value_candidates']==[]
        assert cells[name]['status']=='unavailable'
        assert cells[name]['unavailable_reason']==reason
    assert cells['amount_adjusted_effect']['unit'] is None  # The response endpoint's unit is unknown.
    assert cells['source_signed_index']['origin']=='proposed'


def test_conflicting_representations_are_kept_as_candidates_not_averaged():
    result=populate_relative_signal([observation(1),visual()])
    cells=result['cells']
    for name in ('reported_ratio','difference_from_reference','log_reported_ratio'):
        assert cells[name]['value'] is None
        assert cells[name]['status']=='conflicting'
        assert cells[name]['unavailable_reason']=='source_representation_conflict'
    assert cells['reported_ratio']['value_candidates']==[1,1.12]
    assert cells['difference_from_reference']['value_candidates']==pytest.approx([0,.12])
    assert cells['log_reported_ratio']['value_candidates']==pytest.approx([0,.11332868530700327])
    assert cells['reported_ratio']['origin']=='derived'
    assert result['candidate_set_complete'] is True
    assert result['independent_preparation_count'] is None


def test_same_original_visual_regions_with_different_readings_remain_conflicting():
    first=visual(1,printed_label='1.0')
    second=visual(1.12,source='copied_transcription')
    result=populate_relative_signal([first,second])
    assert len(result['observations'])==2
    assert result['cells']['reported_ratio']['value_candidates']==[1,1.12]
    assert result['cells']['reported_ratio']['status']=='conflicting'
    assert result['independent_preparation_count'] is None


def test_same_native_location_with_changed_value_is_conflict_not_a_mean():
    result=populate_relative_signal([observation(.64),observation(.65)])
    assert result['cells']['reported_ratio']['value'] is None
    assert result['cells']['reported_ratio']['status']=='conflicting'
    assert result['cells']['reported_ratio']['value_candidates']==[.64,.65]


def test_equal_values_from_distinct_locations_do_not_create_replication():
    rows=[observation(.64,index=0),observation(.64,index=1)]
    result=populate_relative_signal(rows)
    assert len(result['observations'])==2
    assert result['cells']['reported_ratio']['value']==.64
    assert result['cells']['reported_ratio']['value_candidates']==[.64]
    assert result['independent_preparation_count'] is None
    assert result['cells']['source_profile_log_ratio']['value'] is None


def test_exact_duplicate_copies_are_collapsed_but_inputs_are_not_mutated():
    one=observation(synthetic=True)
    rows=[one,deepcopy(one)]
    original=deepcopy(rows)
    result=populate_relative_signal(rows)
    assert result['cells']['reported_ratio']['origin']=='synthetic'
    assert result['observations']==[one]
    result['observations'][0]['source']['paragraph_text']='changed output only'
    assert rows==original


@pytest.mark.parametrize('rows,expected,reason',[
    ([],[],'no_ratio_observations'),
    ([observation(None)],[],'source_measurement_unavailable'),
    ([observation(.64),observation(None,index=1)],[.64],'source_measurement_unavailable'),
    ([observation(1),visual(),observation(None,index=2)],[1,1.12],'incomplete_conflicting_representations'),
])
def test_missing_representation_keeps_known_candidates_without_a_full_point(rows,expected,reason):
    result=populate_relative_signal(rows)
    assert result['candidate_set_complete'] is False
    cell=result['cells']['reported_ratio']
    assert cell['value'] is None
    assert cell['value_candidates']==expected
    assert cell['status']=='unavailable'
    assert cell['unavailable_reason']==reason
    assert result['cells']['difference_from_reference']['value'] is None
    assert result['cells']['log_reported_ratio']['value'] is None


def test_native_zero_is_retained_while_log_calibration_and_function_remain_unknown():
    result=populate_relative_signal([observation(0)])
    assert result['cells']['reported_ratio']['value']==0
    assert result['cells']['difference_from_reference']['value']==-1
    log=result['cells']['log_reported_ratio']
    assert log['value'] is None and log['value_candidates']==[]
    assert log['unavailable_reason']=='zero_reported_ratio'
    assert result['cells']['calibrated_amount_ratio']['value'] is None
    assert result['cells']['source_signed_index']['value'] is None


def test_zero_conflicting_with_positive_ratio_does_not_create_log_zero_pseudocount():
    result=populate_relative_signal([observation(0),observation(.64,index=1)])
    assert result['cells']['reported_ratio']['status']=='conflicting'
    assert result['cells']['log_reported_ratio']['status']=='unavailable'
    assert result['cells']['log_reported_ratio']['value'] is None
    assert result['cells']['log_reported_ratio']['value_candidates']==[math.log(.64)]
    assert result['cells']['log_reported_ratio']['unavailable_reason']=='zero_reported_ratio'


@pytest.mark.parametrize('ratio',[1,1.12,2,1e-300,1e300])
def test_ratio_domain_is_nonnegative_signal_not_bounded_quality_weight(ratio):
    result=populate_relative_signal([observation(ratio)])
    assert result['cells']['reported_ratio']['value']==ratio
    assert result['cells']['log_reported_ratio']['value']==math.log(ratio)
    assert result['cells']['source_signed_index']['value'] is None
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('value',[True,False,float('nan'),float('inf'),-float('inf'),'0.64',{},10**1000])
def test_nonfinite_or_non_numeric_source_ratio_is_rejected(value):
    with pytest.raises(ExperimentalContractError,match='finite_number_required'):
        populate_relative_signal([observation(value)])


def test_negative_ratio_is_not_positive_evidence_or_missing():
    with pytest.raises(ExperimentalContractError,match='nonnegative_ratio_required'):
        populate_relative_signal([observation(-.1)])


@pytest.mark.parametrize('rows',[None,{},tuple(),[{}]])
def test_closed_observation_list_and_fields_are_required(rows):
    with pytest.raises(ExperimentalContractError):
        populate_relative_signal(rows)


@pytest.mark.parametrize('change',[
    {'kind':'sd','magnitude':.1,'count':3,'sampling_basis':'unspecified'},
    {'kind':'unreported','magnitude':.1,'count':None,'sampling_basis':'unspecified'},
    {'kind':'unreported','magnitude':None,'count':3,'sampling_basis':'unspecified'},
    {'kind':'unreported','magnitude':None,'count':None,'sampling_basis':'biological_preparations'},
    {'kind':'unreported','magnitude':None,'count':None,'sampling_basis':'unspecified','extra':None},
])
def test_band_ratio_uncertainty_cannot_borrow_another_panel_definition(change):
    row=observation()
    row['uncertainty']=change
    with pytest.raises(ExperimentalContractError):
        populate_relative_signal([row])


@pytest.mark.parametrize('field,value',[
    ('expression_start',True),('expression_start',-1),('expression_end',1000),
    ('paragraph_index',-1),('paragraph_index',1.5),('expression','false literal'),
    ('section_id',''),('source_ref',''),('representation','invented'),
])
def test_native_locator_relationships_are_validated(field,value):
    row=observation()
    row['source'][field]=value
    with pytest.raises(ExperimentalContractError):
        populate_relative_signal([row])


def test_native_locator_does_not_accept_unknown_fields_or_wrong_origin():
    row=observation()
    row['source']['extra']='not a declared locator'
    with pytest.raises(ExperimentalContractError,match='closed_fields_required'):
        populate_relative_signal([row])
    row=observation()
    row['origin']='synthetic'
    with pytest.raises(ExperimentalContractError,match='source_origin_mismatch'):
        populate_relative_signal([row])


def test_visual_ratio_is_numerator_over_its_actual_printed_reference():
    row=visual(.64,printed_label='1.28',reference='2.0')
    result=populate_relative_signal([row])
    assert result['cells']['reported_ratio']['value']==.64
    assert result['cells']['reported_ratio']['origin']=='visual_transcription'


@pytest.mark.parametrize('field,value',[
    ('image_region',[0,0,0,2]),('image_region',[0,3,1,2]),('image_region',[False,0,1,2]),
    ('image_region',[0,0,1]),('reference_image_region',[1,0,1,2]),
    ('original_artifact_ref',''),('printed_label','<1.0'),('printed_label','1.0 ± 0.1'),
    ('printed_label','nan'),('printed_label','1e-999'),('reference_printed_label','0'),
    ('reference_printed_label','-1'),
])
def test_visual_locator_labels_reference_and_regions_are_validated(field,value):
    row=visual()
    row['source'][field]=value
    with pytest.raises(ExperimentalContractError):
        populate_relative_signal([row])


def test_visual_numeric_value_cannot_disagree_with_its_printed_ratio():
    with pytest.raises(ExperimentalContractError,match='visual_ratio_mismatch'):
        populate_relative_signal([visual(.9)])


def test_visual_missing_point_retains_witnesses_and_does_not_force_a_number():
    result=populate_relative_signal([visual(None)])
    assert result['cells']['reported_ratio']['value'] is None
    assert result['candidate_set_complete'] is False
    assert result['observations'][0]['source']['reference_printed_label']=='1.0'


def test_all_unavailable_reasons_are_declared_closed_codes():
    for rows in ([],[observation()],[observation(0)],[observation(1),visual()],
                 [observation(1),visual(),observation(None,index=1)]):
        result=populate_relative_signal(rows)
        assert all(cell['unavailable_reason'] is None or cell['unavailable_reason'] in REASONS
                   for cell in result['cells'].values())
        assert all(cell['conditional_on']==[] for cell in result['cells'].values())



def test_transformed_candidate_values_are_unique_without_erasing_input_conflict():
    result=populate_relative_signal([observation(1e-300),observation(2e-300,index=1)])
    difference=result['cells']['difference_from_reference']
    assert difference['value_candidates']==[-1.0]
    assert difference['value'] is None
    assert difference['status']=='conflicting'


@pytest.mark.parametrize('number,reference',[('1e308','1e-308'),('1e-308','1e308')])
def test_visual_ratio_overflow_or_nonzero_underflow_is_not_a_finite_signal(number,reference):
    with pytest.raises(ExperimentalContractError,match='numerical_model_range'):
        populate_relative_signal([visual(None,printed_label=number,reference=reference)])
