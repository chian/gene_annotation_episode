"""The A104 head's first model request, checked offline against the model endpoint's rules for a strict output
schema (``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model
call. The head is linked in its real world (``a104_world``) with the public API and stepped with
``EpisodeRun.next_decision``: ``decide`` builds the request the model would be sent; the model is not asked."""
import asyncio

from episode_runtime import ModelRequest
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, measures, violations)

from .. import task
from .a104_world import linked, world


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    held = world(tmp_path / 'world')
    request = asyncio.run(linked(held, 'a104-decision-schema').next_decision())
    assert isinstance(request, ModelRequest)
    text, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema), 'INPUT', len(text))
    found = violations(schema)
    assert found == [], found
    assert len(text) <= INPUT_CHARACTERS
    options = schema['properties']['selection']['anyOf']
    # the committed interpretation is the tool ``reason``, its arguments carried as JSON text; a child's open records too
    reason, = [option for option in options if option['properties'].get('tool', {}).get('enum') == ['reason']]
    assert reason['properties']['arguments']['type'] == 'string'
    children = [option for option in options if option['properties']['kind']['enum'] == ['episode_child']]
    assert [option['properties']['role']['enum'][0] for option in children] == list(task.OFFERED_CHILDREN)
    assert all(option['properties']['scope']['type'] == 'string' for option in children)
    held['store'].close()
