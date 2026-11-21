"""The A105 grading of this episode through the real runner on a real Store, without a model: the first decision is
the code-decided Jev assessment of the search results, after which ``reason`` is offered with the owner's grading
instructions; a ``reason`` unit commits the interpretation and saves its
grading sheet together; the finding is the controlled features read from the saved sheet, admitted by
``RETURN_FORM``. The whole literature subtree below this episode is linked (its bindings and settings), as a run
links it. Nothing is faked."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)

from .grading_world import SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = getattr(importlib.import_module(PACKAGE + '.episode'), 'SourceRelevanceAssessment')
PATH = EPISODE.binding_path
ROOT = PACKAGE[:PACKAGE.index('.experimental_activity_evidence') + len('.experimental_activity_evidence')]
SUBTREE = {
    'literature': 'PublishedEvidenceAssessment',
    'literature.strategy': 'EvidenceSearchStrategyImprovement',
    'literature.strategy.web_search': 'SourceRelevanceAssessment',
    'literature.strategy.web_search.page': 'SourceEvidenceExamination',
    'literature.strategy.web_search.page.table': 'TableEvidenceExtraction',
    'literature.strategy.web_search.page.report': 'SourceCoverageImprovement',
    'literature.strategy.web_search.page.chunk': 'PassageEvidenceExtraction',
}
BELOW = [getattr(importlib.import_module(ROOT + '.' + name + '.episode'), cls) for name, cls in SUBTREE.items()
         if (ROOT + '.' + name).startswith(PACKAGE)]


def linked_run(directory, world, run_id):
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                     'continuation': {cls.binding_path: SETTINGS for cls in BELOW}, 'services': {}}
    return link(BindingRegistry([cls() for cls in BELOW]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_first_decision_is_the_jev_assessment_of_every_search_result_against_the_search_goal(tmp_path):
    """Offline, without a model or Jev call: before this episode plans, its first decision is made by code:
    ``assess_search_results`` of every search result (its id, provider rank, title and description) against the Search
    Goal (the runner's goal record of this episode with the results and subject the commission requests). Every result
    is unconsumed and the one action offered is the assessment; the planner view exists only after it."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-decision')
    decision = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    task = importlib.import_module(PACKAGE + '.task')
    assert isinstance(decision, ToolCall) and decision.name == task.ASSESS
    assert decision.arguments['results'] == summary['search_result_candidates'] == [
        {'result_id': world['source'], 'provider_rank': 1, 'title': 'synthetic_a105_table',
         'description': 'provider=synthetic_a105_table'}]
    goal = decision.arguments['goal']
    assert goal == summary['jev_search_goal'] and goal['goal_id'] == run.view.goal.goal_id
    assert goal['requested_results']['commissioned_experiments'] == [{'label': 'Experiment A',
                                                                     'assay_type': 'activity_rate'}]
    assert goal['subject']['predicate'] == 'catalyzes' and goal['subject']['partner'] == 'Hydrolysis'
    assert summary['input_list'] == [world['source']] and summary['search_assessment_ref'] is None
    assert summary['search_planner_context'] is None and summary['prior_page_outcomes'] == []
    assert EPISODE.offered_actions(summary, None) == [task.ASSESS]
    assert summary['assay_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    assert list((tmp_path / 'model_calls').glob('call-*')) == []
    # After the assessment the planner is asked with the owner's grading instructions and the reasoning commit.
    assert ASSAY_GRADING_TASK in task.instructions(knowledge=None, leads=False, populations=())
    assert 'reason' in {entry['name'] for entry in task.catalog(task.offered(SETTINGS), summary['reasoning_schema'], False,
                                                              SETTINGS)}
    world['store'].close()

