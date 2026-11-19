"""The A110 literature reaction grading of this episode, run through the real runner on a real Store.

The run is linked with the real runner, journal and Store (``link`` and ``EpisodeRun.next_decision`` /
``run_unit``, the public stepping API). The first decision is the episode's own ``decide``; the model is not
asked. The populate tools then run as real tool units of that Episode (journaled attempt, custody receipts of what
they wrote, ``credit`` and a controller step) on real held records: a reaction paper source, a retained
``a110_source_reaction_measurements_v1`` dataset, a source of literal witnesses and an interpretation source (the
fixtures of the old ``test_literature_reaction_storage.py`` at ``97308b94c``). Nothing is faked."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_population_contracts import (
    PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_reaction_prompt import (
    REACTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reaction_cells import (
    EVIDENCE_TYPE, FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    A110_SOURCE_LEAD, REACTION_LEAD)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.biochemical_feasibility_evidence.literature_reaction_storage import (
    CELLS, COMPONENTS, LiteratureReactionRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.reaction_world import (
    held_world, source)

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
TASK = importlib.import_module(PACKAGE + '.task')
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}


def linked_run(directory, store, entry, run_id='a110-reaction-grading'):
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                    directory),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, entry, run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_next_decision_offers_the_reaction_graders_with_the_owners_grader_instructions(tmp_path):
    store, entry, _, _ = held_world(tmp_path, requested=['reaction_comparison', 'resource_capacity'])
    run = linked_run(tmp_path, store, entry)
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = EPISODE()._summary(view)
    assert summary['family'] == 'reaction' and summary['reaction_sheets'] == []
    assert summary['investigation_finding']['retained_finding_count'] == 0
    assert EPISODE.credit(summary, view.records) == 0
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {item['name']: item for item in request.context['tools']}
    assert {'literature_reaction_populate', 'literature_reaction_source_populate'} <= set(tools)
    assert 'report' not in tools
    assert tools['literature_reaction_populate']['input_schema'] == TASK.population_input_schema()
    assert REACTION_TASK in request.instructions and REACTION_LEAD in request.instructions
    for grader in EXPERIMENT_TYPES.values():
        assert grader['question'] in request.instructions
        assert all(item in request.instructions for item in grader['considerations'])
    assert 'Signed comparisons are proposed conventions, not probabilities.' in request.instructions
    assert '"literature_reaction_populate"' in json.dumps(request.output_schema)
    assert request.context['reaction_sheets'] == []
    store.close()


def test_without_requested_reaction_cells_the_lead_is_a110_source_reading(tmp_path):
    store, entry, _, _ = held_world(tmp_path)
    run = linked_run(tmp_path, store, entry)
    request = asyncio.run(run.next_decision())
    assert A110_SOURCE_LEAD in request.instructions and REACTION_LEAD not in request.instructions
    assert EPISODE()._summary(run.view)['family'] == 'A110_source'
    store.close()


def test_the_populate_tool_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    store, entry, arguments, paper = held_world(tmp_path, requested=['reaction_comparison'])
    run = linked_run(tmp_path, store, entry)
    envelope = {'scope': entry['assignment']['scope'], 'page_source_ref': paper['id']}
    first = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {**envelope, 'arguments': arguments})))
    assert first['outcome']['status'] == 'completed', first['outcome']
    sheet_ref = first['outcome']['result']['sheet_ref']
    reader = run.view.records
    assert reader.holds(sheet_ref) and reader.receipt(sheet_ref)['how'] == 'produced'
    assert reader.get(sheet_ref)['provider'] == PROVIDER
    saved = LiteratureReactionRepository(reader).read(sheet_ref)
    assert saved['version'] == 'literature_reaction_record_v2'
    assert saved['sheet']['cells']['reaction_comparison']['value'] == pytest.approx(1 / 3)
    assert saved['sheet']['cells']['resource_capacity']['value'] == 6
    assert saved['sheet']['cells']['resource_comparison']['value'] == pytest.approx(.2)
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert set(cells) == set(COMPONENTS)
    assert cells['ratio_mean']['ratio_kind'] == 'product_pair' and 'formula' not in cells['ratio_mean']

    # The same arguments without the dataset: every cell unavailable, each with its named missing reason.
    empty = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {
        **envelope, 'arguments': {**arguments, 'data_source_ref': None}})))
    assert empty['outcome']['status'] == 'completed', empty['outcome']
    empty_ref = empty['outcome']['result']['sheet_ref']
    # A source outside the assigned page is refused as an invalid outcome that enters the iterator.
    outside = source(store, 'An unrelated source.')
    refused = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {
        **envelope, 'arguments': {**arguments, 'source_ref': outside['id']}})))
    assert refused['outcome']['status'] == 'invalid'
    assert refused['outcome']['feedback']['code'] == 'literature_source_not_received'

    view = run.view
    summary = EPISODE()._summary(view)
    sheets = summary['reaction_sheets']
    assert [features['sheet_refs'] for features in sheets] == [[sheet_ref], [empty_ref]]
    features, unavailable = sheets
    assert set(features) == set(FEATURES)
    assert features['evidence_type'] == EVIDENCE_TYPE and features['sheet_view'] == 'numerical'
    assert features['reaction_comparison'] == pytest.approx(1 / 3)
    assert features['reaction_comparison_status'] == 'populated'
    assert features['reaction_comparison_unavailable_reason'] == 'none'
    assert (features['independent_n'], features['alternative_count'], features['resource_count']) == (2, 1, 2)
    assert features['ratio_kind'] == 'product_pair' and features['budget_basis'] == 'usable_batch'
    assert features['resources_complete'] is True and features['experiment_assessed'] is False
    assert 'reaction_comparison' not in unavailable and 'independent_n' not in unavailable
    assert unavailable['reaction_comparison_status'] == 'unavailable'
    assert unavailable['ratio_mean_unavailable_reason'] == 'ratio_unreported'
    assert unavailable['ratio_kind'] == 'none' and unavailable['resource_count'] == 0
    assert EPISODE.credit(summary, view.records) == 0          # a saved sheet by itself earns nothing

    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 0.0}, ())
    admitted = EPISODE.return_form.select(()).admit(result, 'return')
    assert admitted == result and set(result) == {'credit', 'finding'}
    assert set(EPISODE.return_form.select(()).record_refs(admitted)) == {sheet_ref, empty_ref}
    assert result['finding']['retained_finding_count'] == 0 and result['finding']['finding_refs'] == []
    json.dumps(result, allow_nan=False)
    store.close()
