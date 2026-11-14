"""Actual runtime action admission excludes private literature wait/job work."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_bindings import AXIS,HOMES
from gene_annotation_episode.episodic_workflow.root.a105 import runtime


@pytest.fixture(params=HOMES)
def applicable(request):
    binding=import_module(AXIS+'.'+request.param+'.episode').LiteratureEpisode(SimpleNamespace())
    role=binding.roles[0]
    context=SimpleNamespace(role=role,scope={})
    source=SimpleNamespace(path=(('annotation','root'),(role,'original')),scope={},
        interpret_schema={'type':'object','properties':{}},_delivery_resolution_ref=None)
    return binding,context,source


def test_actual_action_schema_never_offers_wait_or_job_child(applicable):
    binding,context,source=applicable
    child=SimpleNamespace(assignment_schema=lambda role:{'type':'object'})
    workflow=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:context,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(context),
        is_job_source=lambda source:False,reasoning_action_schema=lambda source:{'type':'object','properties':{'kind':{'const':'reason'}}},
        catalog=lambda *args,**kwargs:[],annotation_child_roles=None,project_credit=SimpleNamespace(),
        scientific_process_binding=None,job_episodes=SimpleNamespace(commission_schemas=lambda schema:pytest.fail('unavailable job schema was requested')),
        episode_bindings=SimpleNamespace(for_child=lambda *args:child),services=SimpleNamespace(capabilities=lambda:()),
        root_child_return_sources=lambda *args:())
    schema=runtime.Workflow.action_schema(workflow,source)
    kinds={branch['properties']['kind']['const'] for branch in schema['properties']['selection']['anyOf']}
    assert 'wait' not in kinds and 'job_child' not in kinds
    assert 'reason' in kinds and 'redeliver_report' in kinds
    assert ('episode_child' in kinds)==bool(binding.child_roles(context.role))


def test_selected_wait_is_rejected_before_acquisition(applicable):
    binding,context,source=applicable
    workflow=SimpleNamespace(permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(context))
    with pytest.raises(ValueError,match='action_not_available_to_episode'):
        runtime.Workflow.selected(workflow,source,{'kind':'wait','condition':{}},7)
