"""The A110 literature reaction grading of the source examination through the real runner on a real Store: its
first decision (the episode's own ``decide``, the model not asked) offers the reaction graders with the owner's
grader instructions and the three investigations; its own populate tool runs as a real tool unit on the held reaction
world (``episode_support/literature/storage/tests/reaction_world.py``); a child's real return (the ordered-reading
leaf, stepped through its own populate unit on the same world) is what ``read_from_child`` takes, credit and
controlled finding only; the parent's return is admitted by its own form. Nothing is faked."""
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
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
LEAF = importlib.import_module(PACKAGE + '.source_coverage_improvement.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
PAGE_KEYS = ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
             'prior_delivery_refs')


def page_entry(entry, requested):
    """The world's reading entry as this episode's page assignment."""
    reading = entry['assignment']
    assignment = {**reading['page'], 'scope': reading['scope'], 'finding_unit': reading['finding_unit'],
                  'received_record_refs': reading['received_record_refs'],
                  'requested_reaction_components': requested}
    return {'assignment': assignment, 'message': {'objective': 'examine'}, 'selection': []}


def bindings():
    """This episode and its three children, each its own binding."""
    children = (('source_coverage_improvement', 'SourceCoverageImprovement'),
                ('passage_evidence_extraction', 'PassageEvidenceExtraction'),
                ('table_evidence_extraction', 'TableEvidenceExtraction'))
    return [EPISODE(), *(getattr(importlib.import_module(PACKAGE + '.' + slot + '.episode'), name)()
                         for slot, name in children)]


def collaborators(directory, store, paths):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': {path: SETTINGS for path in paths}, 'services': {}}


def test_the_parent_offers_the_graders_runs_its_own_populate_unit_and_takes_only_credit_and_features(tmp_path):
    requested = ['reaction_comparison']
    store, entry, arguments, paper = held_world(tmp_path, requested=requested)
    paths = [PATH, *(binding_path for binding_path in EPISODE.child_slots.values())]
    registry = BindingRegistry(bindings())
    run = link(registry, PATH, page_entry(entry, requested), run_id='a110-see-grading',
               journal=RunJournal(tmp_path / 'journal.sqlite3'), collaborators=collaborators(tmp_path, store, paths))
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['family'] == 'reaction' and EPISODE.credit(summary, run.view.records) == 0
    assert isinstance(request, ModelRequest) and request.context['investigations'] == []
    assert {item['slot'] for item in request.context['children']} == set(EPISODE.child_slots)
    assert {'literature_reaction_populate', 'literature_reaction_source_populate'} <= {
        item['name'] for item in request.context['tools']}
    assert all(grader['question'] in request.instructions for grader in EXPERIMENT_TYPES.values())
    envelope = {'scope': entry['assignment']['scope'], 'page_source_ref': paper['id']}
    unit = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {**envelope, 'arguments': arguments})))
    assert unit['outcome']['status'] == 'completed', unit['outcome']
    own_ref = unit['outcome']['result']['sheet_ref']

    # A real child return: the leaf, run on its own entry over the same world, after one populate unit.
    child_dir = tmp_path / 'child'
    child_dir.mkdir()
    child_store, child_entry, child_arguments, child_paper = held_world(child_dir, requested=requested)
    child = link(BindingRegistry([LEAF()]), LEAF.binding_path, child_entry, run_id='a110-see-child',
                 journal=RunJournal(child_dir / 'journal.sqlite3'),
                 collaborators=collaborators(child_dir, child_store, [LEAF.binding_path]))
    asyncio.run(child.run_unit(ToolCall('literature_reaction_populate', {
        'scope': child_entry['assignment']['scope'], 'page_source_ref': child_paper['id'],
        'arguments': {**child_arguments, 'data_source_ref': None}})))
    child_result = LEAF.final_to_parent(LEAF()._summary(child.view),
                                        {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0}, ())
    child_result = LEAF.return_form.select(()).admit(child_result, 'return')
    report = EPISODE.read_from_child('source_coverage_improvement', child_result, summary, run.view.records)
    assert set(report) == {'slot', 'credit', 'finding'} and report['finding'] == child_result['finding']

    summary = EPISODE()._summary(run.view)
    [features] = summary['reaction_sheets']
    assert features['sheet_refs'] == [own_ref] and features['reaction_comparison'] == pytest.approx(1 / 3)
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    assert EPISODE.return_form.select(()).record_refs(result) == (own_ref,)
    store.close()
    child_store.close()
