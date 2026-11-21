"""The A110 head's decision schema, checked offline against the model endpoint's rules for a strict output schema
(``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model call.

The head cannot be stepped to its first model decision in a world yet: the first unit its ``decide`` names is the
lookup ``process_entry``, which is not placed and raises. The schema is therefore built with the head's own schema
function (``output_schema``, which ``decide`` sends unchanged) for every action a decision can offer: every tool,
the knowledge lookups and every child slot. The arguments of an action travel as JSON text, so the argument schemas
(``argument_schema``) are shown to the model and validated by the head, never sent as output schema. The model is
not asked."""
from episode_runtime import ModelRequest
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, measures, violations)

from .. import task


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    names = [*task.TOOL_DEFINITIONS, *(entry['name'].replace('.', '_') for entry in task.knowledge_catalog()),
             *task.CHILD_SLOTS]
    request = ModelRequest(task.MODEL_ROLE, task.scientific_guidance(), {}, task.output_schema(names))
    _, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema))
    found = violations(schema)
    assert found == [], found
    assert schema['properties']['selection']['enum'] == names
    # one outstanding job, by its handoff row: the monitor is commissioned on it
    jobs = [{'handoff_ref': 'row_' + '1' * 64}]
    assert all(task.argument_schema(name, jobs)['type'] == 'object' for name in names)
    assert task.argument_schema('monitor', jobs)['properties']['handoff_ref'] == {'enum': ['row_' + '1' * 64]}
    assert task.commissionable(names, []) == [name for name in names if name != 'monitor']
