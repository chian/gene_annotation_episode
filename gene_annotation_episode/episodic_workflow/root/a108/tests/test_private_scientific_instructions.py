"""Private scientific task keeps original reasoning, waiting and context guidance."""
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.a108 import runtime,runtime_prompt
from .test_private_sample_context_evidence import scientific_binding


@pytest.mark.parametrize('protocol',[None,'decision_exchange_v1'])
@pytest.mark.parametrize('native_events',[None,object()])
def test_scientific_composer_preserves_wait_and_reason(protocol,native_events):
    binding=scientific_binding()
    binding.instructions=lambda context:'Original controlled scientific assignment instructions'
    binding.validate_context=lambda context:None
    source=object.__new__(getattr(binding,'decision_source_type',runtime.DecisionSource))
    source.path=(('sample_context_evidence','original'),)
    context=SimpleNamespace(role='sample_context_evidence')
    source.workflow=SimpleNamespace(is_job_source=lambda source:False,specialist=lambda source:binding,
        binding_context=lambda source:context,
        permits_common_action=lambda source,action:action in binding.permitted_common_actions(context),
        knowledge=SimpleNamespace(instructions='Original selected knowledge'),
        launch_instructions=SimpleNamespace(instructions='Original selected launch instructions'),
        native_event_information=native_events,decision_protocol=protocol)
    source.workflow.services=SimpleNamespace(instructions=lambda source,value:runtime_prompt.instructions(source,value))
    inputs={'tool_knowledge':{},'launch_instruction_library':{}}
    actual=source.instructions(inputs)
    assert actual==runtime_prompt.instructions(source,inputs)
    assert 'Waiting only reports readiness and earns no scientific credit.' in actual
    assert ('native_event_targets input' in actual)==(native_events is not None)
