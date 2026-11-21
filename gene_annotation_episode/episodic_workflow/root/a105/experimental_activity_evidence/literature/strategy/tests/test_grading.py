"""The decision of this episode through the real runner on a real Store, without a model: the first decision offers the
writing of a query and nothing else (no search child until a query is written, no read, search or fetch tool, no
reasoning commit); a written query is a record of this episode handed out by its reference, one query at a time. The
whole literature subtree below this episode is linked (its bindings and settings), as a run links it. Nothing is
faked."""
import asyncio
import importlib
import json
import types

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .grading_world import SETTINGS, held_world
from ..web_search.page.tests.grading_world import job_world_services

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
                     'continuation': {cls.binding_path: SETTINGS for cls in BELOW}, 'services': job_world_services(directory)}
    return link(BindingRegistry([cls() for cls in BELOW]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_first_decision_offers_only_the_writing_of_a_query(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-strategy-decision')
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    # no tool runs a provider search, fetches or reads, and no reasoning commit is offered
    assert {entry['name'] for entry in request.context['tools']} == {'write_search'}
    assert 'evidence_processing' not in request.instructions
    summary = EPISODE()._summary(run.view)
    assert EPISODE.credit(summary, run.view.records) == 0
    # nothing is written yet: no search child is offered until a query is written
    assert summary['input_list'] == [] and request.context['child_options'] == []
    assert EPISODE.offered_actions(summary, types.SimpleNamespace(settings=SETTINGS)) == ['write_search']
    world['store'].close()


def test_a_written_query_is_a_record_of_this_episode_and_is_handed_out_by_its_reference_one_at_a_time(tmp_path):
    """The model writes a query with ``write_search``: the unit keeps it as a source record of this episode whose
    ``request_ref`` artifact holds the request (written through the scoped store, held as produced). Its reference is
    the input list until a search child is handed it; the commission passes the reference, never the query. A query
    handed out is done and is not offered again."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-strategy-write')
    asyncio.run(run.next_decision())
    task = importlib.import_module(PACKAGE + '.task')
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    arguments = {'arguments': {'query': 'PopZ ParB binding assay', 'size': 25}, 'scope': world['scope']}
    unit = asyncio.run(run.run_unit(ToolCall(task.WRITE_SEARCH, arguments)))
    written = unit['outcome']['result']['search_ref']
    records = run.view.records
    source = records.get(written)
    assert source['record_type'] == 'source' and source['provider'] == 'europepmc_search_request'
    assert json.loads(records.get_artifact(source['request_ref'])) == {'query': 'PopZ ParB binding assay', 'size': 25}
    assert records.receipt(written)['how'] == 'produced'
    assert summary_module.written_searches(run.view.outcomes) == [written]
    summary = EPISODE()._summary(run.view)
    assert summary['input_list'] == [written]
    assert EPISODE.offered_actions(summary, types.SimpleNamespace(settings=SETTINGS)) == ['write_search', 'web_search']
    schema = task.selection_schema(summary)
    child = schema['properties']['selection']['anyOf'][-1]['properties']['arguments']
    assert child['properties']['search_query_ref'] == {'enum': [written]}
    handed = {'kind': 'child', 'slot': 'web_search', 'arguments': {'objective': 'o', 'search_query_ref': written}}
    assert summary_module.consumed_results([handed]) == [written]
    world['store'].close()
