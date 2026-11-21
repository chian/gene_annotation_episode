"""The decision of this episode through the real runner on a real Store, without a model: the first decision offers the
reading of held records and the strategy child (its objective alone); no tool runs a provider search or obtains or reads
a paper, and no reasoning commit is offered. The whole literature subtree below this episode is linked (its bindings and
settings), as a run links it. Nothing is faked."""
import asyncio
import importlib

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
