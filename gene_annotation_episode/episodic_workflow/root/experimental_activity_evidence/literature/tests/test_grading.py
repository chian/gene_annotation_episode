"""The decision of this episode through the real runner on a real Store, without a model: the first decision offers the
reading of held records and the strategy child (its objective alone); no tool runs a provider search or obtains or reads
a paper, and no reasoning commit is offered. The whole literature subtree below this episode is linked (its bindings and
settings), as a run links it. Nothing is faked."""
import asyncio
import importlib
import types

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .grading_world import SETTINGS, held_world
from ..strategy.web_search.page.tests.grading_world import job_world_services

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = getattr(importlib.import_module(PACKAGE + '.episode'), 'PublishedEvidenceAssessment')
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


def test_the_first_decision_offers_the_reading_of_held_records_and_the_strategy_child_with_its_objective_only(tmp_path):
    """This episode holds the question context and the claim; it reads records it holds and hands its strategy child its
    objective alone (the strategy writes its own searches). No search, paper, population or reasoning tool is offered."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-offered')
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    assert {entry['name'] for entry in request.context['tools']} == {'state_query'}
    assert 'reason' not in request.instructions.split() and 'evidence_processing' not in request.instructions
    options = request.context['child_options']
    assert [option['slot'] for option in options] == ['strategy']
    assert list(options[0]['arguments']['properties']) == ['objective']
    summary = EPISODE()._summary(run.view)
    assert 'input_list' not in summary and EPISODE.credit(summary, run.view.records) == 0
    assert {world['proposed'], world['reaction'], world['context']} <= set(summary['held_record_refs'])
    assert summary['literature_assignment']['literature_task']['kind'] == 'verified_source_leads'
    world['store'].close()


def test_the_strategy_commission_the_model_writes_is_built_by_this_episode_and_admitted_by_the_strategy(tmp_path):
    """Hand-off literature -> strategy: the model's answer (the strategy slot with its objective alone, as the model
    writes it) goes through ``action`` and ``msg_to_child``; the strategy's own forms admit the assignment and the selection,
    its ``read_from_parent`` reads it, and every record it passes is one this episode holds. The strategy's return, built by
    its own ``final_to_parent`` for the selection asked, is admitted by its form and read by this episode's
    ``read_from_child``, ``internal_summary``, ``credit`` and ``final_to_parent``."""
    from ..strategy.episode import EvidenceSearchStrategyImprovement as Strategy
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-literature-strategy')
    asyncio.run(run.next_decision())
    records = run.view.records
    summary = EPISODE()._summary(run.view)
    answer = {'selection': {'kind': 'child', 'slot': 'strategy',
                            'arguments': {'objective': 'Find experiments that establish binding of the two proteins.'}}}
    call = EPISODE.action(answer, summary, records, None)
    message = EPISODE.msg_to_child(call.slot, call.arguments, summary)
    form = Strategy.return_form.select(message.selection)
    admitted = Strategy.assignment_form.admit(message.assignment, 'test')
    parent_input = Strategy.read_from_parent(dict(admitted), message.message)
    assert parent_input['proposed_annotation_ref'] == world['proposed'] and parent_input['scope'] == world['scope']
    assert parent_input['task_key'] == 'A105:verified_source_leads'
    assert set(form.fields) >= {'credit', 'finding', 'sheet_state_refs', 'examined_article_refs',
                                'literature_source_lead_dispositions'}
    passed = Strategy.assignment_form.record_refs(admitted)
    assert passed and all(records.holds(ref) for ref in passed)
    # the return: what the strategy builds for the selection asked is what this episode reads and passes up
    returned = Strategy.final_to_parent({'scores': [], 'features': [], 'sheet_state_refs': [],
                                         'examined_article_refs': [], 'lead_source_refs': []},
                                        {'credit': 0.0}, message.selection)
    result = form.admit(returned, 'test')
    report = EPISODE.read_from_child(call.slot, result, summary, records)
    outcome = {'kind': 'child', 'slot': call.slot, 'arguments': dict(call.arguments),
               'message': {'objective': message.objective, 'message': dict(message.message),
                           'assignment': dict(message.assignment), 'selection': list(message.selection)},
               'completion': {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0},
               'result': result, 'report': report}
    view = types.SimpleNamespace(parent_input=run.view.parent_input, records=records, goal=run.view.goal,
                                 units_consumed=1, controller_state=None, outcomes=[outcome])
    after = EPISODE()._summary(view)
    assert after['examined_article_refs'] == [] and after['sheet_state_refs'] == []
    assert EPISODE.credit(after, records) == 0
    sent = EPISODE.final_to_parent(after, {'credit': 0.0}, ('sheet_state_refs', 'literature_source_lead_dispositions'))
    assert EPISODE.return_form.select(('sheet_state_refs', 'literature_source_lead_dispositions')).admit(
        sent, 'test') == sent
    world['store'].close()
