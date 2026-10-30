"""Actual scripted presentations: full TASK, requested numerical subset and meanings."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.literature_gel_prompt import GEL_TASK
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK, SAVED_NUMERICAL_RETURN_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from literature_gel_worker_fixture_107 import make_case, run_case


def test_existing_full_tasks_are_exact_before_and_after_gel_registration():
    baseline=json.loads((Path(__file__).resolve().parents[1]/
        'verification/literature_reference_evidence_2026-10-25_001/gel_episode_integration_107/BASELINE_DEFAULT_CONTRACTS_001.json').read_text())
    assert EXPERIMENTAL_TASK==baseline['EXPERIMENTAL_TASK']
    assert SAVED_NUMERICAL_RETURN_TASK==baseline['SAVED_NUMERICAL_RETURN_TASK']
    correction=json.loads((Path(__file__).resolve().parents[1]/
        'verification/literature_reference_evidence_2026-10-25_001/a106_summary_uncertainty_119/PARENT_TASK_CORRECTION_001.json').read_text())
    assert baseline['REFERENCE_PARENT_TASK'].count(correction['before'])==1
    assert REFERENCE_PARENT_TASK==baseline['REFERENCE_PARENT_TASK'].replace(correction['before'],correction['after'],1)


@pytest.mark.parametrize('raw',[False,True])
def test_actual_own_and_received_steering_shows_only_requested_component(tmp_path,raw):
    names=['sum_darkness' if raw else 'direct_competitor_sensitive_shift']
    views=['raw_region' if raw else 'comparison']
    keys=['raw:declared:protein:band:shifted:sum_darkness' if raw else
        'comparison:declared:direct_competitor_sensitive_shift']
    store,case=make_case(tmp_path/'state',names=names,views=views,keys=keys)
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        child=[text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert child and all(GEL_TASK in text and EXPERIMENTAL_TASK in text for text in child)
        own=[text for state,text in zip(provider.contexts,provider.presented)
            if 'literature_assignment' in state and isinstance((state.get('last_local_outcome') or {}).get('result'),dict)
            and 'component_keys' in state['last_local_outcome']['result']]
        assert len(own)==1
        parent=provider.presented[-1]
        assert REFERENCE_PARENT_TASK in parent and GEL_TASK not in parent
        for text in [parent,*own]:
            steering=text.split('\n\nSTEERING\n',1)[1]
            assert 'Requested gel display components' in steering
            assert 'DNA shift' in steering and 'synthetic' in steering
            for hidden in ['sheet_ref','component_key','payload_sha256','numeric_locations',
                    'literature_gel_return_bindings','raw:declared:', 'comparison:declared:',
                    'image_byte_sha256','signal_region']:
                assert hidden not in steering
            assert ('| 80 |' in steering)==raw
            assert ('display_darkness_sum' in steering)==raw
            assert 'not_supplied' in steering
            assert 'calibrated_molecular_occupancy' in steering
    finally:store.close()


def test_unknown_and_conflicting_scientific_meanings_survive_actual_parent_steering(tmp_path):
    def alter(selected,comparison,sources):
        selected['context']['organism']={'state':'unknown','value':None,'witnesses':[]}
        selected['lanes'][1]['construct']={'state':'conflicting','value':None,
            'witnesses':deepcopy(selected['lanes'][1]['subject']['witnesses'])}
    store,case=make_case(tmp_path/'state',alter_fixture=alter)
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run'))
        parent=next(state for state in provider.contexts if state.get('child_reports'))
        row=parent['child_reports'][0]['requested_response'][0]
        assert row['cell']['value']==pytest.approx(.6)
        assert row['scientific_context']['global']['organism']['state']=='unknown'
        assert row['scientific_context']['global']['organism']['value_ref'] is None
        assert row['scientific_context']['interpretation']['status']=='conflicting'
        steering=provider.presented[-1].split('\n\nSTEERING\n',1)[1]
        assert 'unknown' in steering and 'conflicting' in steering and 'construct' in steering
    finally:store.close()


def _own_and_parent_texts(provider):
    own=[text for state,text in zip(provider.contexts,provider.presented)
        if 'literature_assignment' in state and isinstance((state.get('last_local_outcome') or {}).get('result'),dict)
        and 'component_keys' in state['last_local_outcome']['result']]
    assert len(own)==1
    return [*own,provider.presented[-1]]


def test_actual_lane_values_and_conditions_share_unambiguous_local_labels(tmp_path):
    store,case=make_case(tmp_path/'state',names=['shifted_display_fraction'],views=['lane'])
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        for text in _own_and_parent_texts(provider):
            steering=text.split('\n\nSTEERING\n',1)[1]
            assert '| Lane | Region / band | Component |' in steering
            for lane,value,condition in [('Lane 1','0.0','baseline'),('Lane 2','0.8','protein'),('Lane 3','0.2','competitor')]:
                assert f'| {lane} | lane component | shifted display fraction | {value} |' in steering
                meaning=steering.split(lane+' source meaning',1)[1].split('\n\n')[1]
                assert '| condition | known | '+condition+' |' in meaning
            assert 'lane:declared:' not in steering
    finally:store.close()


def test_actual_same_role_bands_and_comparison_roles_preserve_their_links(tmp_path):
    def alter(selected,comparison,sources):
        selected['roi_assignments'][0]['lanes'][1]['bands'].append({
            'band_id':'second host-token:shifted / α','role':'shifted','region':[1,2,2,3]})
    store,case=make_case(tmp_path/'state',alter_fixture=alter,names=['sum_darkness','direct_competitor_sensitive_shift'],
        views=['raw_region','comparison'],keys=[
            'raw:declared:protein:band:shifted:sum_darkness',
            'raw:declared:protein:band:second%20host-token%3Ashifted%20%2F%20%CE%B1:sum_darkness',
            'comparison:declared:direct_competitor_sensitive_shift'])
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        for text in _own_and_parent_texts(provider):
            steering=text.split('\n\nSTEERING\n',1)[1]
            assert '| Lane 1 | Band 1 (shifted) | sum darkness | 80 |' in steering
            assert '| Lane 1 | Band 2 (shifted) | sum darkness | 10 |' in steering
            assert 'Gel comparison lane roles' in steering
            roles=steering.split('Gel comparison lane roles',1)[1]
            for role,lane in [('baseline','Lane 2'),('protein','Lane 1'),('competitor','Lane 3')]:
                assert '| '+role+' | '+lane+' |' in roles
            protein_meaning=steering.split('Lane 1 source meaning',1)[1].split('\n\n')[1]
            assert '| condition | known | protein |' in protein_meaning
            assert 'second host-token' not in steering and 'component_key' not in steering
    finally:store.close()


def test_actual_scientific_concentrations_and_ph_remain_visible_in_requested_meanings(tmp_path):
    def alter(selected,comparison,sources):
        original=sources[('source_caption','text')]['content']
        protein='50 mM NaCl, pH 7.5'
        competitor='50 mM NaCl, pH 7.5, 20 uM competitor'
        content=original+b' Protein condition: '+protein.encode()+b'; competitor condition: '+competitor.encode()+b'.'
        sources[('source_caption','text')]['content']=content
        for index,value in [(1,protein),(2,competitor)]:
            start=content.index(value.encode(),len(original)) if index==1 else content.rindex(value.encode())
            selected['lanes'][index]['condition']={'state':'known','value':value,'witnesses':[{
                'source_ref':'source_caption','representation':'text','start':start,'end':start+len(value.encode()),'quote':value}]}
    store,case=make_case(tmp_path/'state',alter_fixture=alter)
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        for text in _own_and_parent_texts(provider):
            steering=text.split('\n\nSTEERING\n',1)[1]
            assert '| condition | known | 50 mM NaCl, pH 7.5 |' in steering
            assert '| condition | known | 50 mM NaCl, pH 7.5, 20 uM competitor |' in steering
            assert 'sum darkness' not in steering and '| 80 |' not in steering
    finally:store.close()
