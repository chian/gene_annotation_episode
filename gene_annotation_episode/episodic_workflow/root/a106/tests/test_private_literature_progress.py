"""Commissioned A106 progress and continuation stay distinct from scientific counts."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_literature_private_boundaries import PACKAGE as AXIS,HOMES
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a106.domain import identity

@pytest.fixture(params=HOMES)
def progress_case(request):
    cls=import_module(AXIS+'.'+request.param.replace('/','.')+'.episode').LiteratureEpisode
    role=cls.roles[0];source=identity('source','synthetic-source');proposal=identity('hypothesis','synthetic-proposal')
    task={'version':'literature_local_task_v1','evidence_axis':'A106','kind':'source_answer',
        'answer_kind':'assessment','source_refs':[source],'credit_unit':3.,
        'yield_settings':{'kind':'remaining_commissioned_credit','cutoff':.02,'uncertainty_alpha':.05}}
    assignment={'literature_task':task,'proposed_annotation_ref':proposal}
    if role=='literature_page':assignment['source_ref']=source
    elif role in {'literature_ordered','literature_targeted','literature_table'}:assignment['page']={'source_ref':source}
    schema={'type':'object','properties':{'assessments':{'type':'array','items':{'type':'string'},'x-source':'changed_assessment_refs'}}}
    request_body={'goal':{'objective':'Inspect actual source claim'},'report_contract':{'decision':'Return qualified finding',
        'measurements':{'schema':schema}},'message':{'episode_assignment':assignment,'initial_report':{}}}
    context=BindingContext('run','owner',role,((role,'owner'),),{'subject_refs':[]},assignment,request_body,())
    declaration={'credit_unit':3.,**task['yield_settings']}
    binding=cls(SimpleNamespace(),private_yield_binding=True,yield_bindings={'A106:source_answer:assessment':declaration})
    return binding,context,request.param


def test_original_task_units_and_continuation_settings_are_preserved(progress_case):
    binding,context,_=progress_case
    projector=binding.credit_projector(context)
    assert projector.as_record()=={'kind':'literature_local_task_v1','task':'A106:source_answer:assessment',
        'credit_unit':3.,'unit':'one_answer_to_original_commission','revision_credit':False,
        'activity_credit':False,'annotation_support':'separate'}
    assert binding.continuation_task(context)=='A106:source_answer:assessment'
    controller=binding.yield_controller(context,0.,'original-epoch')
    assert controller.maximum_credit==3. and controller.cost==.02
    assert controller.settings.uncertainty_alpha==.05
    assert controller.epoch=='original-epoch'


def test_private_credit_does_not_accept_changed_original_commission(progress_case):
    binding,context,_=progress_case
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='literature_task_credit_commission_mismatch'):
        binding.credit_projector(context)(SimpleNamespace(validate_scope=lambda scope:scope),{},
            known_record_refs=[],assignment={},episode_id='different-owner',run_id='run')


def test_private_controller_rejects_invented_initial_credit(progress_case):
    binding,context,_=progress_case
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='literature_commissioned_credit_capacity_invalid'):
        binding.yield_controller(context,4.,'original-epoch')
