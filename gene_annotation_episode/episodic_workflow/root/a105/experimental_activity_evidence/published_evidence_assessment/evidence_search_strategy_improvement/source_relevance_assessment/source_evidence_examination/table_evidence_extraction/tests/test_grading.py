"""The A105 grading of this episode through the real runner on a real Store, without a model.

The run is linked with the public API (``link``) and stepped with ``EpisodeRun.next_decision`` (the Episode is
entered as ``run()`` enters it; ``decide`` is called; the model is not asked) and ``EpisodeRun.run_unit`` (one
journaled tool unit with its controller step). The ``reason`` unit commits the interpretation and saves the assay
grading sheet together on held records; the finding is read by code from the saved sheet and admitted by the
episode's ``RETURN_FORM``. Nothing is faked."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_selection_prompt import (
    A105_ASSAY_SELECTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    FEATURES, OPTIONAL)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    CELLS, PROVIDER, LiteratureAssayGradingRepository)

from .grading_world import MODEL_SETTINGS, SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path


def linked_run(directory, world, run_id='a105-table-grading', settings=SETTINGS):
    collaborators = {'store': world['store'],
                     'model_provider': world.setdefault('provider', ModelProvider(load_config(), directory / 'model_calls',
                                                                                    directory)),
                     'continuation': {PATH: settings}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_next_decision_offers_reason_with_the_owners_grading_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    request = asyncio.run(run.next_decision())
    view = run.view
    summary = EPISODE()._summary(view)
    assert summary['assay_sheets'] == [] and summary['aggregation_sheets'] == []
    assert EPISODE.credit(summary, view.records) == 0
    assert view.controller_state is not None
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    assert A105_ASSAY_SELECTION_TASK in request.instructions and ASSAY_GRADING_TASK in request.instructions
    assert 'Select the grader by the experiment\'s protocol and question' in request.instructions
    assert 'evidence_processing' in json.dumps(tools['reason']['input_schema'])
    assert request.context['assay_sheets'] == []
    world['store'].close()


def test_the_reason_unit_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    arguments = {'arguments': reasoning_selection(world), 'scope': world['scope'],
                 'page_source_ref': world['source'], 'proposed_annotation_ref': world['proposed']}
    unit = asyncio.run(run.run_unit(ToolCall('reason', arguments)))
    outcome = unit['outcome']
    assert outcome['status'] in ('completed', 'partial'), json.dumps(outcome)[:3000]
    grading, = outcome['evidence_processing']['gradings']
    sheet_ref = grading['result']['sheet_ref']
    reader = run.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PROVIDER
    saved = LiteratureAssayGradingRepository(reader).read(sheet_ref)
    cells = saved['sheet']['cells']
    assert cells['measured_effect']['value'] == 12.5
    assert cells['source_log_evidence_ratio']['status'] == 'conditional'
    rows = {row['component'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert rows == set(LiteratureAssayGradingRepository.components)

    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    assert set(features) == set(FEATURES)
    assert features['sheet_refs'] == [sheet_ref] and features['experiment_refs'] == [world['assay']]
    assert features['evidence_type'] == 'activity_rate' and features['quantity_kind'] == 'rate'
    assert features['effect_value'] == 12.5 and features['effect_unit'] == 'U/mg'
    assert features['source_log_evidence_ratio'] == cells['source_log_evidence_ratio']['value']
    assert features['rate_regime_status'] == 'supported' and features['binding_regime_status'] == 'not_selected'
    assert features['prediction_model_kind'] == 'fixed_predictions_known_normal'
    # The experiment is graded and matched to the committed assessment: one answer, credit one.
    assert EPISODE.credit(summary, reader) == 1.0
    assert run.view.controller_state is not None

    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    result = EPISODE.final_to_parent(summary, completion, ())
    form = EPISODE.return_form.select(())
    admitted = form.admit(result, 'return')
    assert admitted == result and set(result) == {'credit', 'finding'}
    assert result['finding']['assay_count'] == 1 and result['finding']['assay_count_with_evidence_ratio'] == 1
    assert set(form.record_refs(admitted)) == {sheet_ref, world['assay'], world['proposed']}
    text_fields = [name for name, spec in FINAL.RETURN_FORM.fields['finding'].form.fields['assay_sheets'].items.fields.items()
                   if spec.type == 'text']
    assert text_fields and all(hasattr(FINAL.RETURN_FORM.fields['finding'].form.fields['assay_sheets'].items.fields[name],
                                       'options') for name in text_fields)
    selected = EPISODE.final_to_parent(summary, completion, (FINAL.SCREENING, FINAL.LEADS))
    assert EPISODE.return_form.select((FINAL.SCREENING, FINAL.LEADS)).admit(selected, 'return') == selected
    assert set(OPTIONAL) <= set(features)
    json.dumps(result, allow_nan=False)
    world['store'].close()


def test_an_interpretation_without_its_grading_is_refused_and_enters_the_iterator(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    selection = reasoning_selection(world)
    del selection['evidence_processing']
    unit = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': selection, 'scope': world['scope'], 'page_source_ref': world['source'],
        'proposed_annotation_ref': world['proposed']})))
    assert unit['outcome']['status'] == 'invalid'
    assert unit['outcome']['feedback']['code'] == 'applicable_evidence_requires_grading'
    assert EPISODE()._summary(run.view)['assay_sheets'] == []
    world['store'].close()


@pytest.mark.model_run
def test_the_model_grades_the_table_and_resume_replays_its_answers(tmp_path):
    """The real model reads the table and grades the assay through ``reason``; the run ends through the yield
    estimator, and a resume replays the recorded answers without a new model call."""
    from episode_runtime import resume
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, run_id='a105-table-model', settings=MODEL_SETTINGS)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    assert journal.run_state('a105-table-model')[1]['ended_by'] == 'yield_stop'
    episode_path = ((EPISODE().grain_name, 'a105-table-model'),)
    recorded = journal.model_calls('a105-table-model', episode_path)
    assert recorded and recorded[-1]['response']
    assert any(unit[2]['tool'] == 'reason' for unit in journal.units('a105-table-model', episode_path))
    units = journal.units('a105-table-model', episode_path)
    print('UNITS', [(unit[2]['tool'], unit[2]['outcome'].get('status') if isinstance(unit[2]['outcome'], dict)
                     else None) for unit in units])
    print('RESULT', json.dumps(result)[:4000])
    assert set(result) == {'credit', 'finding'}
    assert isinstance(result['credit'], float) and EPISODE.return_form.select(()).admit(result, 'return') == result
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    collaborators = {'store': world['store'],
                     'model_provider': world['provider'],
                     'continuation': {PATH: MODEL_SETTINGS}, 'services': {}}
    resumed = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id='a105-table-model', journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    world['store'].close()


def test_an_access_tool_reads_the_assigned_source_and_refuses_a_read_outside_it(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    envelope = {'scope': world['scope'], 'page_source_ref': world['source'],
                'proposed_annotation_ref': world['proposed']}
    read = asyncio.run(run.run_unit(ToolCall('source_read', {
        **envelope, 'arguments': {'source_ref': world['source'], 'representation': 'original', 'offset': 0,
                                  'limit': 40}})))['outcome']
    assert read['status'] == 'completed', read
    outside = asyncio.run(run.run_unit(ToolCall('source_read', {
        **envelope, 'arguments': {'source_ref': world['assay'], 'offset': 0, 'limit': 40}})))['outcome']
    assert outside['status'] == 'invalid'
    world['store'].close()
