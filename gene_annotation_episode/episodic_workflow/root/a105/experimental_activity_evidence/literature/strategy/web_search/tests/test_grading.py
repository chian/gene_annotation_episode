"""The A105 grading of this episode through the real runner on a real Store, without a model: the first decision is
the code-decided Jev assessment of the search results, after which ``reason`` is offered with the owner's grading
instructions; a ``reason`` unit commits the interpretation and saves its
grading sheet together; the finding is the controlled features read from the saved sheet, admitted by
``RETURN_FORM``. The whole literature subtree below this episode is linked (its bindings and settings), as a run
links it. Nothing is faked."""
import asyncio
import importlib
import json
import types

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
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


HIT_CANDIDATES = [
    {'result_id': 'PMC100', 'provider_rank': 1, 'title': 'PopZ binds ParB',
     'description': 'Journal of Tests, 2024. Abstract of PopZ binds ParB.'},
    {'result_id': 'PMC300', 'provider_rank': 2, 'title': 'A third article',
     'description': 'Journal of Tests, 2024. Abstract of A third article.'}]


def test_the_first_decision_is_the_jev_assessment_of_every_hit_of_the_result_lists_against_the_search_goal(tmp_path):
    """Offline, without a model or Jev call: before this episode plans, its first decision is made by code:
    ``assess_search_results`` of every HIT of the result list (its PMCID, provider rank, title and description: the
    journal, year and abstract the provider returned) against the Search Goal (the runner's goal record of this episode
    with the results and subject the commission requests). The list holds five entries: one without a PMCID (nothing to
    fetch), one repeating a PMCID and one that is another publication's DOI are not items. Every hit is unconsumed and
    the one action offered is the assessment; the planner view exists only after it."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-decision')
    decision = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    task = importlib.import_module(PACKAGE + '.task')
    assert isinstance(decision, ToolCall) and decision.name == task.ASSESS
    assert decision.arguments['results'] == summary['search_result_candidates'] == HIT_CANDIDATES
    goal = decision.arguments['goal']
    assert goal == summary['jev_search_goal'] and goal['goal_id'] == run.view.goal.goal_id
    assert goal['requested_results']['commissioned_experiments'] == [{'label': 'Experiment A',
                                                                     'assay_type': 'activity_rate'}]
    assert goal['subject']['predicate'] == 'catalyzes' and goal['subject']['partner'] == 'Hydrolysis'
    assert summary['input_list'] == ['PMC100', 'PMC300'] and summary['search_assessment_ref'] is None
    assert summary['named_source_refs'] == [] and summary['pending_page'] is None and summary['hit_fetches'] == []
    assert summary['search_planner_context'] is None and summary['prior_page_outcomes'] == []
    assert EPISODE.offered_actions(summary, None) == [task.ASSESS]
    assert summary['assay_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    assert list((tmp_path / 'model_calls').glob('call-*')) == []
    # After the assessment the planner is asked with the owner's grading instructions and the reasoning commit.
    assert ASSAY_GRADING_TASK in task.instructions(knowledge=None, leads=False, populations=())
    assert 'reason' in {entry['name'] for entry in task.catalog(task.offered(SETTINGS), summary['reasoning_schema'], False,
                                                              SETTINGS)}
    world['store'].close()



def test_an_article_examined_by_a_page_is_not_a_search_result_any_more_but_one_only_held_is(tmp_path):
    """An item leaves the list when its work is done: the article a page of an earlier run examined (named by the
    assignment's ``examined_article_refs``) is not offered."""
    world = held_world(tmp_path, held_articles=['PMC100'], examined_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-upper-examined')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['search_result_candidates'] == HIT_CANDIDATES[1:] and summary['input_list'] == ['PMC300']
    world['store'].close()


def test_an_article_only_held_stays_a_search_result(tmp_path):
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-upper-held')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['search_result_candidates'] == HIT_CANDIDATES and summary['input_list'] == ['PMC100', 'PMC300']
    world['store'].close()


def test_a_held_article_is_opened_without_a_new_fetch(tmp_path):
    """Picking a hit whose article is held completes on the held source (no provider call, no second record), and the
    page is then commissioned on it as for a fresh fetch."""
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    task = importlib.import_module(PACKAGE + '.task')
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-upper-open-held')
    asyncio.run(run.next_decision())
    before = sorted(run.view.records.refs())
    ctx = types.SimpleNamespace(store=run.view.records, operation_key='open-held')
    arguments = {'arguments': {'hit': 'PMC100', 'objective': 'evidence_in_passages'}}
    outcome = asyncio.run(task.fetch_search_hit(arguments, ctx))
    assert outcome['status'] == 'completed' and outcome['result'] == {'source_ref': world['articles'][0]}
    assert sorted(run.view.records.refs()) == before
    page = summary_module.pending_page({'kind': 'tool', 'tool': task.FETCH, 'outcome': outcome,
                                        'arguments': arguments}, run.view.records)
    assert page['page']['source_ref'] == world['articles'][0] and page['hit'] == 'PMC100'
    world['store'].close()


def test_a_fetched_hit_is_consumed_whether_it_completed_or_failed_and_only_a_completed_fetch_gets_its_page(tmp_path):
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    task = importlib.import_module(PACKAGE + '.task')
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-upper-fetch')
    asyncio.run(run.next_decision())
    records = run.view.records
    article = world['articles'][0]

    def fetch(hit, outcome):
        return {'kind': 'tool', 'tool': task.FETCH, 'outcome': outcome,
                'arguments': {'arguments': {'hit': hit, 'objective': 'evidence_in_passages'}}}
    completed = fetch('PMC100', {'status': 'completed', 'feedback': None, 'result': {'source_ref': article}})
    failed = fetch('PMC300', {'status': 'failed', 'feedback': {'code': 'provider_http_500'}})
    page = {'source_ref': article, 'representation': 'text', 'artifact_ref': records.get(article)['text_ref'],
            'prior_delivery_refs': []}
    # the page is commissioned by code on the article that was fetched, with the objective the model chose
    assert summary_module.pending_page(completed, records) == {'hit': 'PMC100', 'objective': 'evidence_in_passages',
                                                               'page': page}
    # a failed fetch is never opened: no page, and the hit is reported with the provider status
    assert summary_module.pending_page(failed, records) is None and summary_module.pending_page(None, records) is None
    assert summary_module.hit_fetches([completed, failed]) == [
        {'hit': 'PMC100', 'status': 'completed', 'provider_status': None},
        {'hit': 'PMC300', 'status': 'failed', 'provider_status': 'provider_http_500'}]
    assert summary_module.consumed_results([completed, failed], False) == ['PMC100', 'PMC300']
    child = {'kind': 'child', 'slot': 'page', 'arguments': {'hit': 'PMC100', 'page': page}}
    assert summary_module.pending_page(child, records) is None
    world['store'].close()


def test_under_a_task_that_names_its_source_the_page_candidate_is_that_source_and_no_hit_is_offered(tmp_path):
    """The page refuses a source other than the one it is assigned (``literature_task_outside_assigned_source``), so a
    task naming a source offers the page on that source only: no hit, no Jev measurement, no fetch."""
    world = held_world(tmp_path, 'named_assessment')
    run = linked_run(tmp_path, world, 'a105-upper-named')
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    task = importlib.import_module(PACKAGE + '.task')
    assert isinstance(request, ModelRequest)
    assert summary['named_source_refs'] == summary['input_list'] == [world['source']]
    assert summary['search_result_candidates'] == [] and summary['search_assessment_ref'] is None
    assert request.context['page_candidates'] is None and request.context['input_list'] == [world['source']]
    assert [entry['slot'] for entry in request.context['child_options']] == ['page']
    assert task.FETCH not in {entry['name'] for entry in request.context['tools']}
    offered = EPISODE.offered_actions(summary, types.SimpleNamespace(settings=SETTINGS))
    assert 'page' in offered and task.FETCH not in offered
    world['store'].close()
