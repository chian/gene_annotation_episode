"""The A102 head's decision schema, checked offline against the model endpoint's rules for a strict output schema
(``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model call.

The head cannot be stepped to its first decision in a world yet: its ``internal_summary`` reads the finding progress
through ``project_finding_progress``, which opens ``read_snapshot`` on the record reader it is handed (a reader has
none). The schema is therefore built with the head's own schema functions (``offered``, ``selection_schema`` and the
strict transport ``decide`` applies) on real operands: the reasoning schema of a real Store, the head's own tools
with the knowledge lookups, and every child slot offered while no job is outstanding (the monitor is offered only for
a held outstanding job). No library tool is selected (their contracts come from the
``tool_catalog`` service, which nothing implements). The model is not asked."""
from episode_runtime import ModelRequest
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import strict_output_schema
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, measures, violations)

from .. import task


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    with Store(tmp_path / 'store') as store:
        summary = {'reasoning_schema': store.reasoning_schema(), 'selection': {'child_tool_info': []},
                   'outstanding_jobs': []}
    names = task.offered(summary, {'knowledge_library_directory': str(tmp_path)})
    schema = task.selection_schema(names, summary, task.library_catalog(None, names['library']))
    request = ModelRequest('REASONING', task.instructions(knowledge=None, launch_library=None), {},
                           strict_output_schema(schema, open_records_as_text=True,
                                                argument_transport_error=task.TRANSPORT_ERROR))
    _, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema))
    found = violations(schema)
    assert found == [], found
    options = schema['properties']['selection']['anyOf']
    assert {option['properties']['slot']['enum'][0] for option in options
            if option['properties']['kind']['enum'] == ['child']} == set(task.CHILD_SLOTS) - {'monitor'}
    assert {option['properties']['tool']['enum'][0] for option in options
            if option['properties']['kind']['enum'] == ['tool']} == set(names['own'])
