"""The decisions of this episode through the real runner on a real Store, without a model or a provider: the first
decision is the provider search of the one query the strategy handed over, run from its record through custody; the
second is Jev's measurement of every hit; the model then picks ONE unprocessed hit and code obtains its paper and
commissions the page. The whole literature subtree below this episode is linked (its bindings and settings), as a run
links it. Nothing is faked."""
import asyncio
import importlib
import types

import pytest

from episode_runtime import BindingRegistry, CustodyError, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .grading_world import HIT_CANDIDATES, SETTINGS, held_world
from ..page.tests.grading_world import job_world_services

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
                     'continuation': {cls.binding_path: SETTINGS for cls in BELOW}, 'services': job_world_services(directory)}
    return link(BindingRegistry([cls() for cls in BELOW]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def after_search(run, world):
    """The view of the run once the query of the assignment has been run. The provider call is no part of an offline
    test: the outcome is the one the ``run_search`` unit records, over the retained response the world holds."""
    outcome = {'kind': 'tool', 'tool': 'run_search', 'arguments': {'search_query_ref': world['request']},
               'outcome': {'status': 'completed', 'record_refs': [world['search']]}}
    view = run.view
    return types.SimpleNamespace(parent_input=view.parent_input, records=view.records, goal=view.goal,
                                 units_consumed=view.units_consumed, controller_state=view.controller_state,
                                 outcomes=[*view.outcomes, outcome])


def test_the_first_decision_is_the_search_of_the_query_handed_over_run_from_its_record_through_custody(tmp_path,
                                                                                                     monkeypatch):
    """The commission names ONE query of the strategy (a record holding the request), not a result list. The first
    decision is made by code: ``run_search`` of that query; the unit reads the request from the record through custody
    and runs the operation of ``public.literature.search`` with exactly the arguments the strategy wrote. Until it ran,
    no hit is known and the one action offered is the search."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-search-first')
    decision = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    task = importlib.import_module(PACKAGE + '.task')
    assert isinstance(decision, ToolCall) and decision.name == task.RUN_SEARCH
    assert decision.arguments['search_query_ref'] == world['request']
    assert summary['pending_search'] == world['request'] and summary['search_result_candidates'] == []
    assert EPISODE.offered_actions(summary, None) == [task.RUN_SEARCH]
    called = {}

    async def run_operation(name, arguments, scope, ctx):
        called.update(name=name, arguments=arguments)
        return {'status': 'completed'}
    monkeypatch.setattr(task, 'run_operation', run_operation)
    asyncio.run(task.run_search(decision.arguments, types.SimpleNamespace(store=run.view.records)))
    assert called == {'name': 'public.literature.search',
                      'arguments': {'query': 'PopZ ParB binding assay', 'size': 25}}
    world['store'].close()


def test_the_units_run_in_the_order_the_code_decides_and_the_page_commission_is_admitted_by_the_page(tmp_path, monkeypatch):
    """Hand-off web_search -> page, through the real runner and the units in the order code decides them: ``run_search``
    (the query read from the strategy's record through custody), Jev's ``assess_search_results`` (the one measurement
    of every hit), the model's pick of a hit (its answer, as the model writes it), ``fetch_search_hit`` (a held article), and
    then the page commissioned by code. Only the provider search and Jev's call are stood in for (their results are the
    world's retained response and a measurement of the hits); every summary field each unit reads exists when it runs. The
    page's own forms admit the commission, its ``read_from_parent`` reads it, every record it passes is held here, and the
    return the page builds for the selection asked is read by this episode."""
    from ..page.episode import SourceEvidenceExamination as Page
    task = importlib.import_module(PACKAGE + '.task')
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-search-page')

    async def run_operation(name, arguments, scope, ctx):
        assert (name, arguments) == ('public.literature.search', {'query': 'PopZ ParB binding assay', 'size': 25})
        return {'status': 'completed', 'record_refs': [world['search']], 'changed_record_refs': [], 'result': None,
                'feedback': None}

    async def assess_results(jev, *, goal, results):
        return {'version': 'model_planned_from_jev_evidence', 'assessments': [
            {**item, 'relevance_probability': 0.5, 'window_probabilities': [0.5], 'text_source': 'description',
             'text_tokens': 10, 'attempts': 1} for item in results]}
    monkeypatch.setattr(task, 'run_operation', run_operation)
    monkeypatch.setattr(task, 'assess_results', assess_results)
    monkeypatch.setattr(task, 'JevDecisionClient', types.SimpleNamespace(from_repository_env=lambda: None))
    searched = asyncio.run(run.next_decision())
    assert isinstance(searched, ToolCall) and searched.name == task.RUN_SEARCH
    assert asyncio.run(run.run_unit(searched))['outcome']['status'] == 'completed'
    assessed = asyncio.run(run.next_decision())
    assert isinstance(assessed, ToolCall) and assessed.name == task.ASSESS
    assert asyncio.run(run.run_unit(assessed))['outcome']['status'] == 'completed'
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['input_list'] == ['PMC100', 'PMC300']
    assert [item['option_id'] for item in request.context['page_candidates']['unprocessed_page_candidates']] == [
        'PMC100', 'PMC300']
    pick = EPISODE.action({'selection': {'kind': 'tool', 'tool': task.FETCH, 'arguments': {'hit': 'PMC100'}}},
                          summary, run.view.records, None)
    fetched = asyncio.run(run.run_unit(pick))
    assert fetched['outcome']['status'] == 'completed' and fetched['outcome']['result'] == {
        'source_ref': world['articles'][0]}
    call = asyncio.run(run.next_decision())
    records = run.view.records
    summary = EPISODE()._summary(run.view)
    assert call.slot == 'page' and call.arguments == summary['pending_page']
    message = EPISODE.msg_to_child(call.slot, call.arguments, summary)
    form = Page.return_form.select(message.selection)
    admitted = Page.assignment_form.admit(message.assignment, 'test')
    parent_input = Page.read_from_parent(dict(admitted), message.message)
    assert parent_input['page']['source_ref'] == world['articles'][0] and parent_input['scope'] == world['scope']
    assert parent_input['objective']['value'] == 'evidence_location_unknown'
    assert set(form.fields) >= {'credit', 'finding', 'sheet_state_refs', 'literature_source_lead_dispositions'}
    passed = Page.assignment_form.record_refs(admitted)
    assert world['articles'][0] in passed and all(records.holds(ref) for ref in passed)
    returned = Page.final_to_parent({'sheet_update': None, 'sheet_state_refs': [], 'lead_source_refs': []},
                                    {'credit': 0.0}, message.selection)
    result = form.admit(returned, 'test')
    report = EPISODE.read_from_child(call.slot, result, summary, records)
    outcome = {'kind': 'child', 'slot': call.slot, 'arguments': dict(call.arguments),
               'message': {'objective': message.objective, 'message': dict(message.message),
                           'assignment': dict(message.assignment), 'selection': list(message.selection)},
               'completion': {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 0.0},
               'result': result, 'report': report}
    view = types.SimpleNamespace(parent_input=run.view.parent_input, records=records, goal=run.view.goal,
                                 units_consumed=5, controller_state=None, outcomes=[*run.view.outcomes, outcome])
    after = EPISODE()._summary(view)
    assert after['examined_article_refs'] == [world['articles'][0]] and after['input_list'] == ['PMC300']
    assert after['prior_page_outcomes'][0]['result_id'] == 'PMC100' and after['pending_page'] is None
    assert EPISODE.credit(after, records) == 0
    sent = EPISODE.final_to_parent(after, {'credit': 0.0}, ('sheet_state_refs', 'examined_article_refs',
                                                           'literature_source_lead_dispositions'))
    assert EPISODE.return_form.select(('sheet_state_refs', 'examined_article_refs',
                                       'literature_source_lead_dispositions')).admit(sent, 'test') == sent
    world['store'].close()


def test_a_protein_target_is_looked_up_right_after_the_search_and_its_sequence_artifact_must_be_named_in_the_commission(
        tmp_path, monkeypatch):
    """The listing unit (``list_record_publications``) comes right after ``run_search`` and before Jev's measurement, for the
    protein subjects of the claim that carry a sequence. It reads the subject's sequence artifact through custody, and
    holding the input record does not hold its artifact: the commission (the entry assignment's ``evidence_refs``) must name
    the sequence artifact of every input, or the unit fails with the custody error."""
    task = importlib.import_module(PACKAGE + '.task')

    async def run_operation(name, arguments, scope, ctx):
        return {'status': 'completed', 'record_refs': [world['search']], 'changed_record_refs': [], 'result': None,
                'feedback': None}
    monkeypatch.setattr(task, 'run_operation', run_operation)
    for hold in (False, True):
        directory = tmp_path / str(hold)
        directory.mkdir()
        world = held_world(directory, protein='MKVLAAGIVGLLLAQPSMAEEHHHHHH', hold_sequence=hold)
        run = linked_run(directory, world, 'a105-search-listing-' + str(hold))
        searched = asyncio.run(run.next_decision())
        assert searched.name == task.RUN_SEARCH
        asyncio.run(run.run_unit(searched))
        listed = asyncio.run(run.next_decision())
        assert isinstance(listed, ToolCall) and listed.name == task.LIST
        assert listed.arguments == {'subject_refs': [world['target']], 'scope': world['scope']}
        if hold:
            with pytest.raises(ValueError, match='sequence_identity_lookup_not_held'):
                asyncio.run(run.run_unit(listed))
        else:
            with pytest.raises(CustodyError):
                asyncio.run(run.run_unit(listed))
        world['store'].close()


def test_a_search_that_ran_is_not_run_again(tmp_path):
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-search-ran')
    asyncio.run(run.next_decision())
    done = after_search(run, world)
    parent = run.view.parent_input
    assert summary_module.next_search(parent, run.view.outcomes) == world['request']
    assert summary_module.next_search(parent, done.outcomes) is None
    assert summary_module.result_response(done.outcomes) == [world['search']]
    world['store'].close()


def test_the_decision_after_the_search_is_the_jev_assessment_of_every_hit_against_the_search_goal(tmp_path):
    """Offline, without a model or Jev call: once its search ran, before the model picks, the decision is made by code:
    ``assess_search_results`` of every HIT of the result list (its PMCID, provider rank, title and description) against
    the Search Goal (the runner's goal record of this episode with the commissioned task and the subject of the claim).
    The list holds five entries: one without a PMCID (nothing to fetch), one repeating a PMCID and one that is another
    publication's DOI are not items. Every hit is unprocessed and the one action offered is the assessment."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-search-assess')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(after_search(run, world))
    task = importlib.import_module(PACKAGE + '.task')
    decision = task.decide(summary, None, None)
    assert isinstance(decision, ToolCall) and decision.name == task.ASSESS
    assert decision.arguments['results'] == summary['search_result_candidates'] == HIT_CANDIDATES
    goal = decision.arguments['goal']
    assert goal == summary['jev_search_goal'] and goal['goal_id'] == run.view.goal.goal_id
    assert goal['requested_results'] == {'task_key': 'A105:verified_source_leads', 'task_kind': 'verified_source_leads'}
    assert goal['subject']['predicate'] == 'catalyzes' and goal['subject']['partner'] == 'Hydrolysis'
    assert summary['input_list'] == ['PMC100', 'PMC300'] and summary['search_assessment_ref'] is None
    assert summary['pending_page'] is None and summary['hit_fetches'] == []
    assert summary['search_planner_context'] is None and summary['prior_page_outcomes'] == []
    assert EPISODE.offered_actions(summary, None) == [task.ASSESS]
    assert EPISODE.credit(summary, run.view.records) == 0
    assert list((tmp_path / 'model_calls').glob('call-*')) == []
    world['store'].close()


def test_an_article_examined_by_a_page_is_not_a_search_result_any_more_but_one_only_held_is(tmp_path):
    """A hit leaves the list when its work is done: the article a page of an earlier run examined (named by the
    assignment's ``examined_article_refs``) is not offered; one that is only held stays."""
    world = held_world(tmp_path, held_articles=['PMC100'], examined_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-search-examined')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(after_search(run, world))
    assert summary['search_result_candidates'] == HIT_CANDIDATES[1:] and summary['input_list'] == ['PMC300']
    world['store'].close()
    (tmp_path / 'held').mkdir()
    held = held_world(tmp_path / 'held', held_articles=['PMC100'])
    run = linked_run(tmp_path / 'held', held, 'a105-search-held')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(after_search(run, held))
    assert summary['search_result_candidates'] == HIT_CANDIDATES and summary['input_list'] == ['PMC100', 'PMC300']
    held['store'].close()


def test_a_held_article_is_opened_without_a_new_fetch_and_the_page_is_commissioned_by_code_on_it(tmp_path):
    """Picking a hit whose article is held completes on the held source (no provider call, no second record), and the
    page is then commissioned on it as for a fresh fetch, with no model call."""
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    task = importlib.import_module(PACKAGE + '.task')
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-search-open-held')
    asyncio.run(run.next_decision())
    before = sorted(run.view.records.refs())
    ctx = types.SimpleNamespace(store=run.view.records, operation_key='open-held')
    arguments = {'arguments': {'hit': 'PMC100'}, 'scope': world['scope']}
    outcome = asyncio.run(task.fetch_search_hit(arguments, ctx))
    assert outcome['status'] == 'completed' and outcome['result'] == {'source_ref': world['articles'][0]}
    assert sorted(run.view.records.refs()) == before
    last = {'kind': 'tool', 'tool': task.FETCH, 'outcome': outcome, 'arguments': arguments}
    pending = summary_module.pending_page(last, run.view.records)
    assert pending['page']['source_ref'] == world['articles'][0] and pending['hit'] == 'PMC100'
    assert set(pending) == {'hit', 'page'}
    world['store'].close()


def test_a_picked_hit_is_done_whether_its_fetch_completed_or_failed_and_only_a_completed_fetch_gets_its_page(tmp_path):
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    task = importlib.import_module(PACKAGE + '.task')
    world = held_world(tmp_path, held_articles=['PMC100'])
    run = linked_run(tmp_path, world, 'a105-search-fetch')
    asyncio.run(run.next_decision())
    records = run.view.records
    article = world['articles'][0]

    def fetch(hit, outcome):
        return {'kind': 'tool', 'tool': task.FETCH, 'outcome': outcome, 'arguments': {'arguments': {'hit': hit}}}
    completed = fetch('PMC100', {'status': 'completed', 'feedback': None, 'result': {'source_ref': article}})
    failed = fetch('PMC300', {'status': 'failed', 'feedback': {'code': 'provider_http_500'}})
    page = {'source_ref': article, 'representation': 'text', 'artifact_ref': records.get(article)['text_ref'],
            'prior_delivery_refs': []}
    # the page is commissioned by code on the paper that was fetched
    assert summary_module.pending_page(completed, records) == {'hit': 'PMC100', 'page': page}
    # a failed fetch is never opened: no page, and the hit is reported with the provider status
    assert summary_module.pending_page(failed, records) is None and summary_module.pending_page(None, records) is None
    assert summary_module.hit_fetches([completed, failed]) == [
        {'hit': 'PMC100', 'status': 'completed', 'provider_status': None},
        {'hit': 'PMC300', 'status': 'failed', 'provider_status': 'provider_http_500'}]
    assert summary_module.consumed_results([completed, failed]) == ['PMC100', 'PMC300']
    child = {'kind': 'child', 'slot': 'page', 'arguments': {'hit': 'PMC100', 'page': page}}
    assert summary_module.pending_page(child, records) is None
    world['store'].close()
