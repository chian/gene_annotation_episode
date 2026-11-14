"""Scientific head offers its original reason/wait actions and excludes jobs."""
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.a108 import runtime
from .test_private_scientific_process import scientific_binding


def test_actual_scientific_schema_keeps_wait_and_reason_but_never_jobs():
    binding=scientific_binding();binding.validate_context=lambda context:None
    context=SimpleNamespace(role='scientific_process',scope={})
    source=SimpleNamespace(path=(('scientific_process','original'),),scope={},
        interpret_schema={'type':'object','properties':{}})
    child=SimpleNamespace(assignment_schema=lambda role:{'type':'object'})
    workflow=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:context,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(context),
        is_job_source=lambda source:False,reasoning_action_schema=lambda source:{'type':'object','properties':{'kind':{'const':'reason'}}},
        catalog=lambda *args,**kwargs:[],annotation_child_roles=None,project_credit=SimpleNamespace(),
        scientific_process_binding=binding,job_episodes=SimpleNamespace(commission_schemas=lambda schema:pytest.fail('unavailable job schema was requested')),
        episode_bindings=SimpleNamespace(for_child=lambda *args:child),services=SimpleNamespace(capabilities=lambda:()),
        root_child_return_sources=lambda *args:())
    schema=runtime.Workflow.action_schema(workflow,source)
    branches=schema['properties']['selection']['anyOf']
    kinds={branch['properties']['kind']['const'] for branch in branches}
    assert kinds=={'reason','wait','episode_child','redeliver_report'}
    roles={branch['properties']['role']['const'] for branch in branches if 'role' in branch['properties']}
    assert roles=={'scientific_process','literature'}
