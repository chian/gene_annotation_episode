"""The A105 grading of this episode through the real runner on a real Store, without a model: the first decision
offers ``reason`` with the owner's grading instructions; a ``reason`` unit commits the interpretation and saves its
grading sheet together; the finding is the controlled features read from the saved sheet, admitted by
``RETURN_FORM``. The whole literature subtree below this episode is linked (its bindings and settings), as a run
links it. Nothing is faked."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)

from .grading_world import SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = getattr(importlib.import_module(PACKAGE + '.episode'), 'EvidenceSearchStrategyImprovement')
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


def test_the_first_decision_offers_reason_with_the_owners_grading_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-decision')
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and ASSAY_GRADING_TASK in request.instructions
    tools = {entry['name'] for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    summary = EPISODE()._summary(run.view)
    assert summary['assay_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    assert summary['input_list'] == [world['search']]
    world['store'].close()


def test_a_search_result_is_a_retained_search_response_never_an_article_the_episode_fetched(tmp_path):
    """The web search child works on the hits of the result lists it is handed; an article this episode fetched is not a
    list, so it is not offered as a search result (it was, and the child then took a whole article for a result)."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-results')
    asyncio.run(run.next_decision())
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    parent = {'strategy': {'prior_search_refs': [world['search']]}}
    outcomes = [{'kind': 'tool', 'tool': 'public_literature_read', 'outcome': {'record_refs': [world['source']]}},
                {'kind': 'tool', 'tool': 'public_literature_search', 'outcome': {'record_refs': [world['search']]}}]
    assert summary_module.search_results(parent, outcomes, run.view.records) == [world['search']]
    world['store'].close()


def test_the_commission_to_the_web_search_selects_the_articles_its_pages_examined():
    to_child = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    task = {'version': 'literature_local_task_v1', 'kind': 'a105_experiments', 'evidence_axis': 'A105',
            'credit_unit': 1.0, 'experiments': []}
    summary = {'task': task, 'task_key': 'A105:experiments', 'strategy': {'question_context_refs': []},
               'proposed_annotation_ref': 'hyp_1', 'requested': {}, 'sheet_state_refs': [], 'scope': {},
               'held_record_refs': [], 'all_examined_article_refs': ['src_9', 'src_8']}
    message = to_child.msg_to_child('web_search', {'objective': 'x', 'search': {'search_result_refs': ['src_1']}},
                                    summary)
    assert 'examined_article_refs' in message.selection and 'sheet_state_refs' in message.selection
    # every article examined so far (the ones this episode was given and its children's) goes to each web-search commission
    assert message.assignment['examined_article_refs'] == ['src_9', 'src_8']


def test_the_articles_examined_are_the_ones_given_and_the_ones_the_web_search_children_returned(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-examined')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['examined_article_refs'] == [] and summary['all_examined_article_refs'] == []
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    given = {**run.view.parent_input, 'examined_article_refs': ['src_given']}
    child = {'kind': 'child', 'slot': 'web_search', 'arguments': {'search': {'search_result_refs': ['src_1']}},
             'report': {'examined_article_refs': ['src_a', 'src_b']}}
    again = {**child, 'report': {'examined_article_refs': ['src_b', 'src_c']}}
    assert summary_module.examined_article_refs(given, [child, again]) == (['src_a', 'src_b', 'src_c'],
                                                                           ['src_given', 'src_a', 'src_b', 'src_c'])
    world['store'].close()


def test_the_return_declares_the_articles_its_pages_examined_and_returns_them_when_selected():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'scores': [], 'features': [], 'examined_article_refs': ['src_1'], 'sheet_state_refs': []}
    result = final.final_to_parent(summary, {'credit': 1.0}, ['examined_article_refs'])
    assert result['examined_article_refs'] == ['src_1']
    assert EPISODE.return_form.admit(result, 'test')['examined_article_refs'] == ['src_1']
    assert 'examined_article_refs' not in final.final_to_parent(summary, {'credit': 1.0}, [])

