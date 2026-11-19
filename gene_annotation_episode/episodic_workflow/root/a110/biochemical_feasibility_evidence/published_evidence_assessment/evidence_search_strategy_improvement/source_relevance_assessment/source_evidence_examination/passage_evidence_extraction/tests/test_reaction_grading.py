"""The A110 literature reaction grading of this episode through the real runner on a real Store: the first decision
(the episode's own ``decide``, the model not asked) offers the reaction graders with the owner's grader
instructions, and the populate tool runs as a real tool unit on the held reaction world
(``episode_support/literature/storage/tests/reaction_world.py``); the return is admitted by the episode's own form.
Nothing is faked."""
import asyncio
import importlib

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.reaction_world import (
    held_world)

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}


def linked_run(directory, store, entry):
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                    directory),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, entry, run_id='a110-passage-grading',
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_next_decision_and_a_populate_unit_and_the_admitted_return(tmp_path):
    store, entry, arguments, paper = held_world(tmp_path, requested=['resource_coverage'], selection='spans')
    run = linked_run(tmp_path, store, entry)
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['family'] == 'reaction' and EPISODE.credit(summary, run.view.records) == 0
    assert isinstance(request, ModelRequest)
    assert {'literature_reaction_populate', 'literature_reaction_source_populate'} <= {
        item['name'] for item in request.context['tools']}
    assert all(grader['question'] in request.instructions for grader in EXPERIMENT_TYPES.values())
    envelope = {'scope': entry['assignment']['scope'], 'page_source_ref': paper['id']}
    unit = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {**envelope, 'arguments': arguments})))
    assert unit['outcome']['status'] == 'completed', unit['outcome']
    sheet_ref = unit['outcome']['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    [features] = summary['reaction_sheets']
    assert features['sheet_refs'] == [sheet_ref] and features['resource_coverage'] == pytest.approx(.6)
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    assert EPISODE.return_form.select(()).record_refs(result) == (sheet_ref,)
    store.close()
