"""The A103 head's first model request, checked offline against the model endpoint's rules for a strict output
schema (``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model
call. The head is linked in its real world (``a103_world``) with the public API and stepped with
``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit`` through the lookups its ``decide`` makes first; the model is
not asked."""
import asyncio

from episode_runtime import ModelRequest, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, measures, violations)

from .a103_world import linked, world


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    held = world(tmp_path / 'world')
    run = linked(held, 'a103-decision-schema')
    request = asyncio.run(run.next_decision())
    while isinstance(request, ToolCall):
        asyncio.run(run.run_unit(request))
        request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    text, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema), 'INPUT', len(text))
    found = violations(schema)
    assert found == [], found
    assert len(text) <= INPUT_CHARACTERS
    held['store'].close()
