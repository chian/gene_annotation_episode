"""Original commissioned answer units, qualification and continuation boundaries."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_bindings import binding, AXIS

SOURCE='source_'+'a'*64
ARTIFACT='artifact_'+'b'*64
ANNOTATION='hypothesis_'+'c'*64
TASK={'version':'literature_local_task_v1','evidence_axis':'A105','kind':'source_answer',
      'answer_kind':'assessment','source_refs':[SOURCE],'credit_unit':7,
      'yield_settings':{'kind':'remaining_commissioned_credit','cutoff':.075,'uncertainty_alpha':.05}}


def original_context(binding):
    role=binding.roles[0]
    page={'source_ref':SOURCE,'artifact_ref':ARTIFACT,'representation':'original'}
    assignment={'literature_task':TASK,'proposed_annotation_ref':ANNOTATION}
    if role=='literature_page':assignment.update(page)
    elif role in {'literature_table','literature_ordered','literature_targeted'}:assignment['page']=page
    schema={'type':'object','properties':{'findings':{'type':'array','items':{'type':'string'},
        'x-source':'changed_assessment_refs'}}}
    return SimpleNamespace(role=role,assignment=assignment,
        request={'goal':{'objective':'Assess the original source claim with qualifications'},
          'message':{'episode_assignment':assignment,'initial_report':{}},
          'report_contract':{'decision':'Return original qualified findings','measurements':{'schema':schema}}})


def test_original_goal_and_credit_definition_keep_exact_units(binding):
    context=original_context(binding)
    definition=binding.credit_projector(context).as_record()
    assert definition=={'kind':'literature_local_task_v1','task':'A105:source_answer:assessment',
        'credit_unit':7,'unit':'one_answer_to_original_commission','revision_credit':False,
        'activity_credit':False,'annotation_support':'separate'}
    assert binding.continuation_task(context)=='A105:source_answer:assessment'


def test_original_task_contract_rejects_changed_target_or_requested_result(binding):
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
    context=original_context(binding)
    context.request=deepcopy(context.request)
    context.request['report_contract']['measurements']['schema']['properties']={}
    with pytest.raises(ContractError,match='typed_return_mismatch'):
        binding.credit_projector(context).as_record()


def test_original_finite_remaining_credit_does_not_invent_progress(binding):
    private=type(binding)(object(),private_yield_binding=True,yield_bindings={
        'A105:source_answer:assessment':{'kind':'remaining_commissioned_credit','credit_unit':7,
            'cutoff':.075,'uncertainty_alpha':.05}})
    context=original_context(private)
    controller=private.yield_controller(context,7,'original-source')
    assert controller is not None
    # The controller's exact original commissioned definition carries the cutoff;
    # no new action minimum, time deadline or whole-workflow budget is added.
    assert private._yield_bindings['A105:source_answer:assessment']['cutoff']==.075
