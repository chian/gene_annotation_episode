"""The A106 head's decision schema, checked offline against the model endpoint's rules for a strict output schema
(``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model call.

The head cannot be stepped to its first decision in a world yet: its ``internal_summary`` reads the finding progress
through ``project_finding_progress``, which opens ``read_snapshot`` on the record reader it is handed (a reader has
none). The schema is therefore built with the head's own schema functions (``catalog``, ``selected_catalog``,
``selection_schema`` and the strict transport ``decide`` applies) on real operands: the reasoning schema of a real
Store, the published process library frozen into the test's directory, a frozen tool library of every tool of the
A106 registry as the selected tools, the knowledge lookups, and every child slot. The model is not asked."""
from pathlib import Path

from episode_runtime import ModelRequest
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, measures, violations)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary

from .. import task
from ..goal import GOAL

# One outstanding job, by its handoff row: the monitor is offered on it.
JOBS = [{'handoff_ref': 'row_' + '1' * 64}]
LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    with Store(tmp_path / 'store') as store:
        summary = {'reasoning_schema': store.reasoning_schema()}
        available = task.ToolRegistry(store).catalog()
    library = task.PerturbationEvidenceLibrary.freeze(tmp_path / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    rows = [{'name': name, 'resources': 'local', **entry} for name, entry in available.items()]
    tools = ScientificToolLibrary.freeze(tmp_path / 'tool-library', catalog=rows)
    selection = {'version': task.SELECTION_VERSION, 'evidence_axis': library.reference('A106'),
                 'thought_pattern': thought,
                 'child_tool_info': tools.resolve_tool_info([{'name': row['name'], 'resources': row['resources']}
                                                             for row in rows])}
    entry, published = task.entry_of(library, selection)
    entries = task.catalog({'knowledge_library_directory': str(tmp_path)}, selection, summary, published)
    selected = task.selected_catalog(tools, selection)
    assert len(selected) == len(available)
    schema = task.selection_schema(entries, selected, list(task.CHILD_SLOTS), JOBS)
    request = ModelRequest('REASONING', GOAL, {}, task.generation_schema(schema))
    _, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema))
    found = violations(schema)
    assert found == [], found
    options = schema['properties']['selection']['anyOf']
    assert {option['properties']['slot']['enum'][0] for option in options
            if option['properties']['kind']['enum'] == ['child']} == set(task.CHILD_SLOTS)
