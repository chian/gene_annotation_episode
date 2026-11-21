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


def test_the_first_decision_offers_reason_with_the_owners_grading_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-decision')
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and ASSAY_GRADING_TASK in request.instructions
    tools = {entry['name'] for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    summary = EPISODE()._summary(run.view)
    assert summary['assay_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    world['store'].close()


def test_the_reason_unit_saves_the_sheet_and_the_finding_is_its_features(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-upper-reason')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    unit = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': reasoning_selection(world), 'scope': world['scope'],
        'assignment': summary['literature_assignment'], 'requested': summary['requested'],
        'proposed_annotation_ref': world['proposed']})))
    assert unit['outcome']['status'] == 'completed', json.dumps(unit['outcome'])[:2000]
    sheet_ref = unit['outcome']['evidence_processing']['gradings'][0]['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    assert features['sheet_refs'] == [sheet_ref] and features['effect_value'] == 12.5
    assert EPISODE.credit(summary, run.view.records) == 1.0
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    world['store'].close()
