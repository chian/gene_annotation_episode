"""Private composers preserve original scientific instruction text and settings."""
from importlib import import_module
from types import SimpleNamespace

import pytest

from .test_private_literature_bindings import AXIS, HOMES


@pytest.mark.parametrize('home', [*HOMES, 'scientific_process'])
@pytest.mark.parametrize('exchange', [False, True])
def test_private_instruction_composition_matches_original_capabilities(home, exchange):
    runtime = import_module(AXIS + '.runtime')
    if home == 'scientific_process':
        from .test_private_scientific_process import scientific_binding
        binding = scientific_binding()
    else:
        binding = import_module(AXIS + '.' + home + '.episode').LiteratureEpisode(SimpleNamespace())
    source = object.__new__(getattr(binding, 'decision_source_type', runtime.DecisionSource))
    role = binding.roles[0]
    source.path = ((role, 'original-invocation'),)
    specialist = SimpleNamespace(instructions=lambda context: 'Original commissioned scientific objective.',
                                 replaces_default_instructions=False)
    source.workflow = SimpleNamespace(is_job_source=lambda source: False,
        specialist=lambda source: specialist, binding_context=lambda source: 'original-context',
        permits_common_action=lambda source, action: action == 'reason' or
            action == 'wait' and role == 'scientific_process',
        knowledge=SimpleNamespace(instructions='Original tool knowledge.'),
        launch_instructions=SimpleNamespace(instructions='Original launch knowledge.'),
        native_event_information=object(),
        decision_protocol='decision_exchange_v1' if exchange else None)
    source.workflow.services = import_module(AXIS + '.episode_services').WorkflowServices(source.workflow)
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    expected = import_module(AXIS + '.runtime_prompt').instructions(source, context)
    assert source.instructions(context) == expected
    assert ('pending_child_ handle' in expected) == (role == 'scientific_process')
