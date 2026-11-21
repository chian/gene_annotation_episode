"""The A105 grading of the head through the real runner on a real Store, without a model: a ``reason`` unit commits
the interpretation and saves its grading sheet together (``literature_reasoning.reason``); the head's credit is its
finding progress over the assessments it holds (the library's projection, run on ``records``); the finding is the
controlled features read from the saved sheet, admitted by ``RETURN_FORM``. The whole subtree is linked."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .grading_world import SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExperimentalActivityEvidence
PATH = EPISODE.binding_path
BELOW = {'': 'ExperimentalActivityEvidence', '.literature': 'PublishedEvidenceAssessment',
         '.literature.strategy': 'EvidenceSearchStrategyImprovement',
         '.literature.strategy.web_search': 'SourceRelevanceAssessment'}
SEE = '.literature.strategy.web_search.page'
BELOW.update({SEE: 'SourceEvidenceExamination', SEE + '.table': 'TableEvidenceExtraction',
              SEE + '.report': 'SourceCoverageImprovement',
              SEE + '.chunk': 'PassageEvidenceExtraction'})
CLASSES = [getattr(importlib.import_module(PACKAGE + name + '.episode'), cls) for name, cls in BELOW.items()]


def test_the_reason_unit_saves_the_sheet_the_credit_counts_the_finding_and_the_return_is_its_features(tmp_path):
    world = held_world(tmp_path)
    settings = {**SETTINGS, 'library_directory': str(tmp_path / 'library')}
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                     'continuation': {cls.binding_path: settings for cls in CLASSES}, 'services': {}}
    run = link(BindingRegistry([cls() for cls in CLASSES]), PATH, world['input'], run_id='a105-head-reason',
               journal=RunJournal(tmp_path / 'journal.sqlite3'), collaborators=collaborators)
    selection = world['input']['assignment']['selection']
    unit = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': reasoning_selection(world), 'scope': world['scope'], 'selection': selection,
        'proposed_annotation_ref': world['proposed']})))
    assert unit['outcome']['status'] == 'completed', json.dumps(unit['outcome'])[:2000]
    sheet_ref = unit['outcome']['evidence_processing']['gradings'][0]['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    assert [features['sheet_refs'] for features in summary['assay_sheets']] == [[sheet_ref]]
    assert summary['progress']['retained_finding_count'] == 1
    assert EPISODE.credit(summary, run.view.records) == 1.0
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0},
                                     ('committed_record_refs',))
    assert EPISODE.return_form.select(('committed_record_refs',)).admit(result, 'return') == result
    assert sheet_ref in result['committed_record_refs'] and result['finding']['assay_count'] == 1
    world['store'].close()
