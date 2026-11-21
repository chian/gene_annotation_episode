"""The A108 head's decision schema, checked offline against the model endpoint's rules for a strict output schema
(``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model call.

The head cannot be stepped to its first decision in a world yet: its ``internal_summary`` reads the finding progress
through ``project_finding_progress``, which opens ``read_snapshot`` on the record reader it is handed (a reader has
none). The schema is therefore built with the head's own schema functions (``offered``, ``selection_schema`` and the
strict transport ``decide`` applies) on real operands: the reasoning schema of a real Store, every tool a selection
can name (the head's own ``INPUT_SCHEMAS``) as the selected tools, the knowledge lookups, and both child slots. The
model is not asked."""
from episode_runtime import ModelRequest
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, measures, violations)

from .. import task
from ..goal import GOAL


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    with Store(tmp_path / 'store') as store:
        reasoning = store.reasoning_schema()
    summary = {'reasoning_schema': reasoning, 'process': {'child_tool_info': [
        {'name': name, 'resources': 'local', 'description': name} for name in task.INPUT_SCHEMAS]}}
    names = task.offered(summary, {'knowledge_library_directory': str(tmp_path)})
    assert set(names) >= {*task.ACCESS.values(), 'reason', 'process_revise', 'knowledge_read', *task.CHILD_SLOTS}
    request = ModelRequest('REASONING', GOAL, {}, task.generation_schema(task.selection_schema(summary, names)))
    _, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema))
    found = violations(schema)
    assert found == [], found
    assert {option['properties']['tool']['enum'][0] for option in schema['properties']['selection']['anyOf']} == \
        set(names)
