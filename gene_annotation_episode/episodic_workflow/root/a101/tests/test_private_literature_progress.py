"""A101 retains its actual supplied root projection and missing child-task boundary.

The original commissioned literature task schema only covered A105/A106/A108.
These tests do not supply a fabricated A101 task, unit or continuation policy.
"""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_literature_private_boundaries import PACKAGE, HOMES

@pytest.fixture(params=HOMES)
def progress_case(request):
    binding=import_module(PACKAGE+'.'+request.param.replace('/','.')+'.episode').LiteratureEpisode(SimpleNamespace())
    context=SimpleNamespace(role=binding.roles[0],path=((binding.roles[0],'original'),))
    return binding,context


def test_original_literature_has_no_invented_commissioned_units(progress_case):
    binding,context=progress_case
    assert binding.credit_projector(context) is None
    assert binding.continuation_task(context) is None
    assert binding.yield_controller(context,0.,'original-epoch') is None


def test_actual_root_projection_uses_supplied_original_calculator(progress_case):
    binding,context=progress_case
    runtime=import_module(PACKAGE+'.runtime')
    original=object()
    assert runtime.Workflow.scientific_projector_for_context(SimpleNamespace(project_credit=original),context) is original


def test_actual_child_projection_rejects_missing_original_task(progress_case):
    binding,context=progress_case
    runtime=import_module(PACKAGE+'.runtime')
    context.path=(('sequence_homology_evidence','parent'),*context.path)
    workflow=SimpleNamespace(episode_bindings=SimpleNamespace(roles=binding.roles,for_path=lambda path:binding))
    with pytest.raises(ValueError,match='scientific_task_credit_not_declared:'+context.role):
        runtime.Workflow.scientific_projector_for_context(workflow,context)
