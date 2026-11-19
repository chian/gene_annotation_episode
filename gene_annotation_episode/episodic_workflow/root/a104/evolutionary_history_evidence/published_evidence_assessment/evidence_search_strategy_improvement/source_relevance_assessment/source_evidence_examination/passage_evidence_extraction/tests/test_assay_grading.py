"""The A104 literature grading of this episode (row 16 of ``LOST_CONTENT_a104.md``) through the real runner on a real
Store, without a model.

The run is linked with the public API (``link``) and stepped with ``EpisodeRun.next_decision`` (the Episode is
entered as ``run()`` enters it, its yield controller built from ``credit`` of the initial summary; ``decide`` is
called; the model is not asked) and ``EpisodeRun.run_unit`` (one journaled tool unit with its controller step). The
``reason`` unit commits the interpretation and saves the A105 assay-grading sheet together on held records; the
finding is read by code from the saved sheet and admitted by the episode's ``RETURN_FORM``. Nothing is faked."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.evolutionary_history_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assay_grading_features import (
    FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import (
    CELLS, PROVIDER, LiteratureAssayGradingRepository)

from .grading_world import SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path


def linked_run(directory, world, run_id='a104-passage-grading', settings=SETTINGS):
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                     'continuation': {PATH: settings}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def envelope(world, arguments):
    return {'arguments': arguments, 'scope': world['scope'], 'page_source_ref': world['source'],
            'proposed_annotation_ref': world['proposed']}


def test_the_next_decision_offers_graded_reasoning_with_the_owners_grader_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    request = asyncio.run(run.next_decision())
    view = run.view
    summary = EPISODE()._summary(view)
    assert summary['assay_sheets'] == [] and summary['sheet_record_refs'] == []
    assert EPISODE.credit(summary, view.records) == 0
    assert view.controller_state is not None
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    assert ASSAY_GRADING_TASK in request.instructions
    assert 'it stays a record inside this episode' in request.instructions
    assert 'The iterator and parent consume that recorded scientific finding' not in request.instructions
    assert 'evidence_processing' in json.dumps(tools['reason']['input_schema'])
    assert request.context['assay_sheets'] == []
    world['store'].close()


def test_the_reason_unit_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    unit = asyncio.run(run.run_unit(ToolCall('reason', envelope(world, reasoning_selection(world)))))
    outcome = unit['outcome']
    assert outcome['status'] in ('completed', 'partial'), json.dumps(outcome)[:3000]
    grading, = outcome['evidence_processing']['gradings']
    sheet_ref = grading['result']['sheet_ref']
    reader = run.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PROVIDER
    saved = LiteratureAssayGradingRepository(reader).read(sheet_ref)
    assert saved['sheet']['cells']['measured_effect']['value'] == 12.5
    rows = {row['component'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert rows == set(LiteratureAssayGradingRepository.components)

    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    assert set(features) == set(FEATURES)
    assert features['sheet_refs'] == [sheet_ref] and features['experiment_refs'] == [world['assay']]
    assert features['evidence_type'] == 'activity_rate' and features['effect_value'] == 12.5
    assert sheet_ref in summary['sheet_record_refs'] and saved['direct_record_refs'][0] in summary['sheet_record_refs']
    # The graded assessment answers the commissioned source question: credit is one credit unit.
    assert EPISODE.credit(summary, reader) == 1.0

    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    result = EPISODE.final_to_parent(summary, completion, ())
    form = EPISODE.return_form.select(())
    admitted = form.admit(result, 'return')
    assert admitted == result and set(result) == {'credit', 'finding'}
    assert result['finding']['assay_count'] == 1 and result['finding']['assessment_count'] == 1
    assert {sheet_ref, world['assay'], world['proposed']} <= set(form.record_refs(admitted))
    graded, = result['finding']['assessments']
    assert graded['evidence_type'] == 'published_evolutionary_claim' and graded['finding_status'] == 'retained'
    assert graded['qualification_kind'] == 'different_source_subject' and graded['relation'] == 'strengthens'
    assert 'Experiment A' not in json.dumps(result)
    world['store'].close()


def test_an_interpretation_without_its_grading_is_refused_and_enters_the_iterator(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    selection = reasoning_selection(world)
    del selection['evidence_processing']
    unit = asyncio.run(run.run_unit(ToolCall('reason', envelope(world, selection))))
    assert unit['outcome']['status'] == 'invalid'
    assert unit['outcome']['feedback']['code'] == 'applicable_evidence_requires_grading'
    assert EPISODE()._summary(run.view)['assay_sheets'] == []
    world['store'].close()
