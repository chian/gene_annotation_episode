"""Explicit parent assignment through actual provider framing; no inference."""
import asyncio
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_assay_prompt import ASSAY_TASK
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from test_literature_experimental_prompt_delivery import LiteratureWire,snapshot,complete
from test_literature_ratio_integration import setup_store,binding_for


def test_explicit_parent_sources_are_receipt_bound_fixed_and_reconstructed(tmp_path):
    store,child,args,_=setup_store(tmp_path)
    try:
        original=binding_for(store,child)
        enabled=LiteratureEpisodes(original.services,rate_population=True,
            reference_parent_sources=[args['source_ref']])
        parent=replace(child,role='annotation',episode_id='root',path=(('annotation','root'),),assignment={})
        assert original.initial_decision_context(parent)=={}
        information=enabled.initial_decision_context(parent)
        assert information['reference_evidence_parent']['source_refs']==[args['source_ref']]
        assert information['literature_experimental_work']['aspect']=='reference_evidence_parent'
        assert enabled.initial_decision_context(child)=={}
        assert enabled.initial_decision_context(replace(parent,received_record_refs=(*parent.received_record_refs,'extra')))==information
        with pytest.raises(ContractError,match='not_received'):
            enabled.initial_decision_context(replace(parent,received_record_refs=()))
        descriptor=enabled.as_record()
        composition=compose_episode_bindings(enabled.services,store=store,journal=Journal(store,parent.run_id),
            execution_backend=None,descriptors=[descriptor],job_episodes=None,resource_estimator=None,
            role_credit_bindings={})
        rebuilt,=composition.bindings
        assert rebuilt.reference_parent_sources==(args['source_ref'],)
        assert rebuilt.initial_decision_context(parent)==information
    finally:store.close()


@pytest.mark.parametrize('sources',[[],['same','same'],'source',False,[None]])
def test_parent_source_binding_requires_an_explicit_unique_nonempty_roster(sources):
    with pytest.raises(ValueError,match='reference_parent_sources'):
        LiteratureEpisodes(None,rate_population=True,reference_parent_sources=sources)
    with pytest.raises(ValueError,match='reference_parent_sources'):
        LiteratureEpisodes(None,reference_parent_sources=['source'])


def test_real_provider_parent_text_survives_delta_lookup_and_restored_backend(tmp_path):
    first=snapshot()
    first.pop('literature_assignment')
    first.pop('literature_source_custody')
    first['literature_experimental_work']['aspect']='reference_evidence_parent'
    first['reference_evidence_parent']={'version':'reference_evidence_parent_v1',
        'source_refs':['source_selected'],'source_custody':[{'source_ref':'source_selected',
            'artifact_ref':'artifact_selected','text_ref':None,'version':'original'}]}
    first['goal']['objective']='Evaluate the assigned source experiments without inferring target correspondence.'
    second=deepcopy(first)
    second['child_reports']=[{'measurements':[{'component':'reported_ratio','value':None,
        'value_candidates':[1,1.12],'status':'conflicting','reference_role':'tagged_wt_complementation',
        'uncertainty_kind':'unreported'}]}]
    wire=LiteratureWire(tmp_path/'wire')
    restarted=LiteratureWire(tmp_path/'restarted')
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':2,
            'exchange_index':1,'result':{'status':'completed','text':'Selected original source qualification.'}}
    async def exercise():
        await complete(wire,state_frame(first),episode='parent')
        await complete(wire,state_frame(second,first),episode='parent')
        await complete(wire,lookup,episode='parent')
        await complete(restarted,state_frame(second),episode='parent')
    asyncio.run(exercise())
    for transport in (wire,restarted):
        for call in transport.turns_sent():
            text=call['input'][0]['text']
            assert text.startswith('TASK\n\n')
            assert REFERENCE_PARENT_TASK in text
            assert ASSAY_TASK not in text and EXPERIMENTAL_TASK not in text
            assert first['goal']['objective'] in text
            assert '\n\nSTEERING\n' in text
            assert 'PRIVATE_GOAL' not in text
    text=wire.turns_sent()[-1]['input'][0]['text']
    assert 'tagged_wt_complementation' in text and 'conflicting' in text
    assert '1.12' in text and 'unreported' in text
