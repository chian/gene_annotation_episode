"""The A106 grading of this episode, run through the real runner's public API on a real Store.

The run is linked with ``link`` and stepped with ``EpisodeRun.next_decision()`` (the Episode entered as ``run()``
enters it, its yield controller built from ``credit`` of the initial summary, its first ``decide``; no model call)
and ``EpisodeRun.run_unit(ToolCall(...))`` (a real journaled tool unit with custody receipts, ``credit`` and a
controller step). The population tools run on real held records (``a106_world``): the intervention grading sheet
G1 and the A106 final subscore G2 are saved, the controlled features are read by code from the saved sheets and the
return is admitted by ``RETURN_FORM``. Nothing is faked; no model is asked."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import ModelRequest, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_intervention_grading import (
    CRITERION_QUESTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    TASK as A106_SUBSCORE_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    G1_FEATURES, G2_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage import (
    OPERATION_DESCRIPTION, PROVIDER as G1_PROVIDER)

from .a106_world import SETTINGS, envelope, finalize_arguments, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path


def start(tmp_path, run_id):
    store, entry, grading, names = held_world(tmp_path)
    linked, journal, _ = linked_run(tmp_path, [EPISODE()], PATH, entry, store, run_id, {PATH: SETTINGS})
    return store, linked, grading, names


def test_the_next_decision_offers_the_graders_with_the_owners_instructions(tmp_path):
    store, linked, _, _ = start(tmp_path, 'a106-first-decision')
    request = asyncio.run(linked.next_decision())
    view = linked.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = EPISODE.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0
    assert summary['a106_findings'] == {'intervention_assessments': [], 'a106_subscores': []}
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert {'open_population', 'literature_a106_score_judgment', 'reason'} <= set(tools)
    populations = tools['open_population']['input_schema']['properties']['population']['enum']
    assert {'literature_intervention_grading_populate', 'literature_a106_finalize',
            'literature_perturbation_populate'} <= set(populations)
    assert OPERATION_DESCRIPTION in tools['open_population']['description']
    assert 'report' not in tools
    assert OPERATION_DESCRIPTION in request.instructions and A106_SUBSCORE_TASK in request.instructions
    assert all(question in request.instructions for question in CRITERION_QUESTIONS.values())
    assert 'literature.intervention_grading.populate accepts source_table_number' in request.instructions
    assert request.context['a106_findings'] == summary['a106_findings']
    size = len(request.instructions) + len(json.dumps(request.context)) + len(json.dumps(request.output_schema))
    assert size < 1048576

    # Opening the intervention grader: the next decision offers it with its full input schema.
    opened = asyncio.run(linked.run_unit(ToolCall('open_population', {
        'arguments': {'population': 'literature_intervention_grading_populate'}})))
    assert opened['outcome']['opened_population'] == 'literature_intervention_grading_populate'
    request = asyncio.run(linked.next_decision())
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert tools['literature_intervention_grading_populate']['input_schema']['properties']['quantities']
    assert '"literature_intervention_grading_populate"' in json.dumps(request.output_schema)
    size = len(request.instructions) + len(json.dumps(request.context)) + len(json.dumps(request.output_schema))
    assert size < 1048576
    store.close()


def test_the_graders_save_their_sheets_and_the_return_is_their_controlled_features(tmp_path):
    store, linked, grading, names = start(tmp_path, 'a106-grading-units')
    graded = asyncio.run(linked.run_unit(ToolCall('literature_intervention_grading_populate',
                                                  envelope(names, grading))))
    outcome = graded['outcome']
    assert outcome['status'] == 'completed', outcome
    sheet_ref = outcome['result']['sheet_ref']
    reader = linked.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == G1_PROVIDER

    # The same assessment again without naming its predecessor is refused by the revision rule; it enters the
    # iterator as an invalid outcome.
    again = asyncio.run(linked.run_unit(ToolCall('literature_intervention_grading_populate',
                                                 envelope(names, grading))))
    assert again['outcome']['status'] == 'invalid'
    assert again['outcome']['feedback']['code'] == 'intervention_latest_revision_required'

    final = asyncio.run(linked.run_unit(ToolCall('literature_a106_finalize',
                                                 envelope(names, finalize_arguments(names, sheet_ref)))))
    assert final['outcome']['status'] == 'completed', final['outcome']
    subscore_ref = final['outcome']['result']['sheet_ref']

    summary = EPISODE.internal_summary(linked.view)
    g1, = summary['a106_findings']['intervention_assessments']
    g2, = summary['a106_findings']['a106_subscores']
    assert g1['sheet_ref'] == [sheet_ref] and g2['sheet_ref'] == [subscore_ref]
    assert g1['log_evidence_ratio'] == pytest.approx(7.5) and g1['log_evidence_ratio_status'] == 'conditional'
    assert g1['measured_effect'] == pytest.approx(0.8) and g1['effect_variance'] == pytest.approx(0.04)
    assert g1['effect_over_noise'] == pytest.approx(4.0)
    assert g1['quantity_kind'] == 'endpoint_ratio' and g1['uses_synthetic_operand'] is True
    assert g1['criterion_prediction_independence'] == 'supported' and g1['is_revision'] is False
    assert g1['design_fields_witnessed_count'] == 0 and g1['experiment_ref'] == [names['experiment']]
    assert set(g1) <= set(G1_FEATURES) and set(g2) <= set(G2_FEATURES)
    assert g2['log_evidence_ratio'] == pytest.approx(7.5) and g2['status'] == 'complete'
    assert (g2['experiment_count'], g2['scored_experiment_count'], g2['supporting_experiment_count']) == (1, 1, 1)
    assert g2['dependence_status'] == 'unknown' and g2['is_revision'] is False

    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 0.0}
    selection = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, completion, selection)
    admitted = EPISODE.return_form.select(selection).admit(result, 'return')
    assert admitted == result
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 0, 'lead_source_refs': []}
    refs = set(EPISODE.return_form.select(selection).record_refs(admitted))
    assert {sheet_ref, subscore_ref, names['experiment'], names['assertion'], names['comparison']} <= refs
    texts = [spec for form in (EPISODE.return_form,) for spec in form.fields.values() if spec.type == 'text']
    assert texts == []
    json.dumps(result, allow_nan=False)
    store.close()
