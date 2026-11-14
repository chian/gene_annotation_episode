"""New private ownership is connected to original commission and typed forms."""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_progress import progress_case
from .test_literature_private_boundaries import PACKAGE,HOMES
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain


def test_private_plan_uses_actual_original_commission_and_calculator(progress_case):
    binding,context,home=progress_case
    module=PACKAGE+'.'+home.replace('/','.')
    plan=binding.planning_context(context)
    assert plan['objective']==context.request['goal']
    assert plan['commissioned_result']==plain(context.assignment['literature_task'])
    assert plan['proposed_annotation_ref']==context.assignment['proposed_annotation_ref']
    assert plan['progress_definition']==binding.credit_projector(context).as_record()
    assert plan['planning_question']==binding.instructions(context)
    assert type(binding.credit_projector(context)).__module__==module+'.credit'
    assert type(binding.yield_controller(context,0.,'epoch')).__module__==module+'.yield_estimator'


