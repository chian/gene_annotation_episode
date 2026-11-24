"""The A107 head's decision schema, checked offline against the model endpoint's rules for a strict output schema
(``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model call.

The head's ``decide`` reads its selected tools from the declared services ``tool_catalog`` and ``tool_library``,
which nothing implements yet, so the head cannot be stepped to its first decision in a world. The schema is built
with the head's own schema functions (``action_schema``, ``transport``) on real operands: the reasoning schema of a
real Store, the A107 registry's own operation contracts as the selected tools, the head's ``process.revise`` and the
process and knowledge lookups (what ``offered_catalog`` adds), and every child slot. The model is not asked."""
from episode_runtime import ModelRequest
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, measures, violations)
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import (
    catalog as registry_catalog)

from .. import task


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    with Store(tmp_path / 'store') as store:
        # one outstanding job, by its handoff row: the monitor is offered on it
        summary = {'reasoning_schema': store.reasoning_schema(),
                   'outstanding_jobs': [{'handoff_ref': 'row_' + '1' * 64}]}
    catalog = [*({'name': name, **entry} for name, entry in registry_catalog().items()),
               {'name': 'process.revise', 'description': task.PROCESS_REVISE_DESCRIPTION,
                'input_schema': task.REVISION_ARGUMENTS}, *task.process_catalog(), *task.knowledge_catalog()]
    request = ModelRequest('REASONING', task.instructions(), {'prompt': 'TASK'},
                           task.transport(task.action_schema(catalog, summary)))
    _, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema))
    found = violations(schema)
    assert found == [], found
    options = schema['properties']['selection']['anyOf']
    children = {option['properties']['slot']['enum'][0] for option in options
                if option['properties']['kind']['enum'] == ['child']}
    assert children == set(task.CHILD_SLOTS)
