"""The A101 head's first model request, checked offline against the model endpoint's rules for a strict output
schema (``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model
call, before any unit. The head is linked in its real world (``a101_world``) with the public API and stepped with
``EpisodeRun.next_decision``: ``decide`` builds the request the model would be sent; the model is not asked."""
import asyncio

from episode_runtime import ModelRequest
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, measures, violations)

from .. import task
from .a101_world import linked, world


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    held = world(tmp_path / 'world', ['sequence.align', 'sequence.inspect'])
    request = asyncio.run(linked(held, 'a101-decision-schema').next_decision())
    assert isinstance(request, ModelRequest)
    text, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema), 'INPUT', len(text))
    found = violations(schema)
    assert found == [], found
    assert len(text) <= INPUT_CHARACTERS
    options = schema['properties']['selection']['anyOf']
    children = {option['properties']['slot']['enum'][0]: option for option in options
                if option['properties']['kind']['enum'] == ['episode_child']}
    # a child is offered while this episode holds what its commission is chosen from: no outstanding job (monitor,
    # results) and no bound API resource (launch) in this world; the resource children have no controlled commission
    assert set(children) == {task.LITERATURE, task.HEAD}
    # every commission is controlled fields the endpoint enforces: no assignment and no message of the model, and
    # an objective only as one value of the commissioned child's fixed vocabulary (never text)
    for option in children.values():
        assert not {'assignment', 'message'} & set(option['properties'])
    assert 'objective' not in children[task.HEAD]['properties']
    literature = children[task.LITERATURE]['properties']
    assert literature['objective']['enum'] == task.LITERATURE_OBJECTIVE['enum']
    assert 'objective' in children[task.LITERATURE]['required']
    assert literature['question_context_refs'] == {'type': 'array', 'minItems': 1, 'items': {
        'type': 'string', 'minLength': 1}}
    assert 'source_refs' not in literature          # this episode holds no source record yet
    subjects = held['assignment']['scope']['subject_refs']
    assert literature['scope']['anyOf'][0]['properties']['subject_refs']['items']['enum'] == subjects
    recursive = children[task.HEAD]['properties']
    assert 'revision_position' not in recursive     # no completed process.revise unit yet
    assert recursive['evidence_refs']['items'] == {'type': 'string', 'minLength': 1}
    # a child that declares no selectable return field is offered without a selection
    assert {slot for slot, option in children.items() if 'selection' not in option['properties']} == \
        {slot for slot in children if not task.SELECTABLE[slot]} == {'literature'}
    # the reasoning commit is the tool ``reason``, its arguments carried as JSON text
    reason, = [option for option in options if option['properties'].get('tool', {}).get('enum') == ['reason']]
    assert reason['properties']['arguments']['type'] == 'string'
    held['store'].close()
