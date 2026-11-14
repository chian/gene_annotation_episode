"""Noncallable optional task marker retains the original default composer."""
from importlib import import_module
from types import SimpleNamespace
import pytest

PREFIX='gene_annotation_episode.episodic_workflow.root.a108.'

@pytest.mark.parametrize('marker',[False,0,'private-instructions-marker'])
def test_noncallable_class_marker_uses_original_unclaimed_composer(marker):
    source=type('Unclaimed',(),{'instruction_composer':marker})();source.path=(('annotation','unclaimed'),)
    source.workflow=SimpleNamespace(is_job_source=lambda *_:False,specialist=lambda *_:None,
        permits_common_action=lambda _,action:action=='reason',native_event_information=None,decision_protocol=None,
        knowledge=SimpleNamespace(instructions='\nOriginal knowledge'),launch_instructions=SimpleNamespace(instructions='\nOriginal launch guidance'))
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    services=import_module(PREFIX+'episode_services').WorkflowServices(source.workflow)
    original=import_module(PREFIX+'runtime_prompt').instructions
    assert services.instructions(source,context)==original(source,context)
