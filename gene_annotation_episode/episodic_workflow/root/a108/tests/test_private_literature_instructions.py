"""Exact original A108 instruction text through each declared task composer."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('context',[{}, {'tool_knowledge':{}}, {'launch_instruction_library':{}},
    {'tool_knowledge':{},'launch_instruction_library':{}}])
@pytest.mark.parametrize('protocol',[None,'decision_exchange_v1'])
def test_private_composer_preserves_original_instruction_text(home,context,protocol):
    runtime=import_module(AXIS+'.runtime')
    original=import_module(AXIS+'.runtime_prompt')
    binding=import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace())
    source=object.__new__(getattr(binding,'decision_source_type',runtime.DecisionSource))
    source.path=((binding.roles[0],'original'),)
    role_context=SimpleNamespace(role=binding.roles[0])
    source.workflow=SimpleNamespace(is_job_source=lambda source:False,specialist=lambda source:binding,
        binding_context=lambda source:role_context,permits_common_action=lambda source,action:action in binding.permitted_common_actions(role_context),
        knowledge=SimpleNamespace(instructions='\nOriginal selected knowledge'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal applicable launch context'),
        native_event_information=None,decision_protocol=protocol)
    source.workflow.services=SimpleNamespace(instructions=lambda source,state:original.instructions(source,state))
    assert source.instructions(context)==original.instructions(source,context)
    assert binding.instructions(role_context) in source.instructions(context)
