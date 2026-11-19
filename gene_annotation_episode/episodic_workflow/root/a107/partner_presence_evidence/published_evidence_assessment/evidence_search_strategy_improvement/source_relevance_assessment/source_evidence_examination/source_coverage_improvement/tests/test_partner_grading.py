"""The A107 literature partner grading of this episode, run through the real runner on a real Store.

The run is linked with the public API (``link``) and stepped with ``EpisodeRun.next_decision`` (the Episode entered
as ``run()`` enters it: its yield controller built from ``credit`` of the initial summary, then ``decide``) and
``EpisodeRun.run_unit`` (a real journaled tool unit with custody receipts, ``credit`` and a controller step). The model
is not asked here. Nothing is faked: the populate tool reads real held records (a paper, a literal witness source, an
interpretation source and a retained partner selection dataset)."""
import asyncio
import importlib
import json

from episode_runtime import ModelRequest, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_partner_prompt import (
    PARTNER_LEAD, PARTNER_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import (
    PARTNER_CELLS_MEANING, POPULATE_DESCRIPTION, SOURCE_POPULATE_DESCRIPTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    EVIDENCE_TYPE)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import (
    CELLS, COMPONENTS, PROVIDER, LiteraturePartnerRepository)

from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.scoring_sheet import (
    PATHS, scoring_sheet, strongest_sheet)

from .partner_world import held_world, linked

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
TASK = importlib.import_module(PACKAGE + '.task')
SUMMARY = importlib.import_module(PACKAGE + '.messages.internal_summary')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}


def stepped(tmp_path, run_id, **world):
    store, entry, selection, rows = held_world(tmp_path, **world)
    run, journal, _ = linked([EPISODE()], PATH, entry, tmp_path, store, run_id, {PATH: SETTINGS})
    return store, run, journal, entry, selection, rows


def test_the_next_decision_offers_the_partner_graders_with_the_grader_instructions(tmp_path):
    store, run, journal, entry, _, _ = stepped(tmp_path, 'a107-leaf-first')
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = SUMMARY.internal_summary(view)
    assert summary['partner_sheets'] == [] and summary['partner_requested'] is True
    assert summary['partner_agreement'] == {'matched_sheet_count': 0, 'matched_loss_sheet_count': 0,
                                            'distinct_experiment_count': 0}
    assert EPISODE.credit(summary, view.records) == 0
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {tool['name']: tool for tool in request.context['tools']}
    assert set(tools) == {'source_read', 'source_locate', 'literature_partner_populate',
                          'literature_partner_source_populate'}
    assert tools['literature_partner_populate']['description'] == POPULATE_DESCRIPTION
    assert tools['literature_partner_source_populate']['description'] == SOURCE_POPULATE_DESCRIPTION
    assert 'quote' not in json.dumps(tools['literature_partner_populate']['input_schema']['properties']['literals'])
    for text in (PARTNER_LEAD, PARTNER_TASK, PARTNER_CELLS_MEANING):
        assert text in request.instructions
    assert 'report' not in tools and 'report_update' not in request.instructions
    assert request.context['partner_sheets'] == []
    # Without requested components the lead is not opened; the grader instructions stay.
    assert PARTNER_LEAD not in TASK.instructions(False) and PARTNER_TASK in TASK.instructions(False)
    store.close()


def test_the_source_tools_and_the_grader_run_on_held_records_and_the_return_is_controlled(tmp_path):
    store, run, journal, entry, selection, rows = stepped(tmp_path, 'a107-leaf-units')
    envelope = {'scope': entry['assignment']['scope'], 'page_source_ref': rows['paper']['id']}
    read = asyncio.run(run.run_unit(ToolCall('source_read', {**envelope, 'arguments': {
        'source_ref': rows['paper']['id'], 'representation': 'text', 'offset': 0, 'limit': 80}})))
    assert read['outcome']['status'] == 'completed'
    assert read['outcome']['result']['text'].startswith('Partner dependence of SubjX')
    located = asyncio.run(run.run_unit(ToolCall('source_locate', {**envelope, 'arguments': {
        'source_ref': rows['paper']['id'], 'representation': 'text', 'needle': '20 pmol/min/mg'}})))
    assert located['outcome']['status'] == 'completed', located['outcome']
    outside = asyncio.run(run.run_unit(ToolCall('source_read', {**envelope, 'arguments': {
        'source_ref': rows['ancestor']['id']}})))
    assert outside['outcome']['status'] == 'invalid'
    assert outside['outcome']['feedback']['code'] == 'literature_reading_outside_assigned_source'

    graded = asyncio.run(run.run_unit(ToolCall('literature_partner_populate', {**envelope, 'arguments': selection})))
    assert graded['outcome']['status'] == 'completed', graded['outcome']
    sheet_ref = graded['outcome']['result']['sheet_ref']
    reader = run.view.records
    assert reader.holds(sheet_ref) and reader.receipt(sheet_ref)['how'] == 'produced'
    assert reader.get(sheet_ref)['provider'] == PROVIDER and sheet_ref in graded['produced']
    saved = LiteraturePartnerRepository(reader).read(sheet_ref)
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert set(cells) == set(COMPONENTS)
    assert [cells[name]['value'] for name in COMPONENTS] == [100, 20, 90, 80, .8, 70, .875, .7]
    assert saved['extraction']['literals']['partner']['value'] == 'Partner'

    # A refused grading (an assessment naming an experiment literal of another role) is an invalid outcome.
    subject_ref = saved['experimental_bindings']['subject_ref']
    bad = {**selection, 'experiment_assessment': {
        'experiment_ref': subject_ref, 'experiment_type': 'partner_requirement', 'assessment_key': 'k',
        'scientific_question': 'q', 'conclusion': 'c', 'limitations': ['l'], 'revision_reason': None,
        'revises_sheet_ref': None}}
    refused = asyncio.run(run.run_unit(ToolCall('literature_partner_populate', {**envelope, 'arguments': bad})))
    assert refused['outcome']['status'] == 'invalid'

    view = run.view
    assert view.units_consumed == 5
    summary = SUMMARY.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 1.0
    assert summary['literature_selected_population_attempt']['status'] == 'invalid'
    [features] = summary['partner_sheets']
    assert features['evidence_type'] == EVIDENCE_TYPE and features['sheet_refs'] == [sheet_ref]
    assert features['partner_loss_fraction'] == .8 and features['partner_loss_fraction_status'] == 'populated'
    assert features['addback_fraction'] == .875 and features['restored_reference_fraction'] == .7
    assert features['reference_omitted_check'] == 'matched' and features['direction'] == 'support'
    assert features['observed_arm_count'] == 3 and features['conditions_complete_arm_count'] == 3
    assert features['reference_spread_kind'] == 'SD' and features['reference_spread_magnitude'] == 4
    assert features['omitted_spread_kind'] == 'unreported' and 'omitted_spread_magnitude' not in features
    assert features['target_correspondence'] == 'not_evaluated' and features['source_kind'] == 'synthetic_fixture'
    assert features['partner_refs'] == [saved['experimental_bindings']['partner_ref']]
    assert summary['partner_agreement'] == {'matched_sheet_count': 1, 'matched_loss_sheet_count': 1,
                                            'distinct_experiment_count': 1}

    # The A107 scoring sheet over the held sheet: separate named groups, no combined score, shared origins recorded.
    sheet = scoring_sheet(view.records, summary['partner_sheets'], [], [])
    assert sheet['paths'] == list(PATHS['A107']) and sheet['combined_scientific_score'] is None
    assert sheet['combination_status'] == 'separate_named_components; no_new_axis_reducer'
    assert sheet['numerical_results'] == [features] and sheet['dependencies']['shared_origins'] == []
    assert strongest_sheet(summary['partner_sheets']) == features

    completion = {'ended_by': 'yield_stop', 'units_consumed': 5, 'credit': 1.0}
    result = EPISODE.final_to_parent(summary, completion, ())
    admitted = EPISODE.return_form.select(()).admit(result, 'return')
    assert admitted == result and set(result) == {'credit', 'finding'}
    assert set(EPISODE.return_form.select(()).record_refs(admitted)) >= {sheet_ref}
    for name, spec in FINAL.SHEET_FORM.fields.items():
        assert spec.type != 'text' or hasattr(spec, 'options'), name
    json.dumps(result, allow_nan=False)
    store.close()
