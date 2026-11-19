"""The A105 grading of this episode through the real runner on a real Store, without a model: the first decision
offers ``reason`` and the grader with the owner's instructions; the ``reason`` unit commits the interpretation and
saves its grading sheet together; the grader's population tool saves a sheet through the population route; the
finding is read by code from the saved sheets and admitted by ``RETURN_FORM``. Nothing is faked."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_a105_aggregation_prompt import (
    A105_AGGREGATION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    PROVIDER)

from .grading_world import SETTINGS, grading_arguments, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
PATH = EPISODE.binding_path


def linked_run(directory, world, run_id='a105-passage-grading'):
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def envelope(world, run):
    summary = EPISODE()._summary(run.view)
    return {'scope': world['scope'], 'page_source_ref': world['source'], 'proposed_annotation_ref': world['proposed'],
            'assignment': summary['literature_assignment'], 'requested': summary['requested']}


def test_the_next_decision_offers_reason_and_the_grader_with_the_owners_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['assay_sheets'] == [] and EPISODE.credit(summary, run.view.records) == 0
    assert isinstance(request, ModelRequest)
    tools = {entry['name'] for entry in request.context['tools']}
    assert {'reason', 'literature_assay_grading_populate', 'literature_a105_aggregate'} <= tools
    assert 'report' not in tools
    assert ASSAY_GRADING_TASK in request.instructions and A105_AGGREGATION_TASK in request.instructions
    world['store'].close()


def test_the_reason_unit_and_the_grader_tool_save_sheets_whose_features_are_returned(tmp_path):
    world = held_world(tmp_path, task_kind='verified_source_leads')   # accumulating: every unit runs
    run = linked_run(tmp_path, world)
    asyncio.run(run.next_decision())
    unit = asyncio.run(run.run_unit(ToolCall('reason', {**envelope(world, run),
                                                        'arguments': reasoning_selection(world)})))
    assert unit['outcome']['status'] == 'completed', json.dumps(unit['outcome'])[:2000]
    graded = unit['outcome']['evidence_processing']['gradings'][0]['result']['sheet_ref']
    arguments = grading_arguments(world, world['proposed'])
    arguments['interpretations']['rate_regime'] = {'status': 'unknown', 'support_refs': []}
    populated = asyncio.run(run.run_unit(ToolCall('literature_assay_grading_populate', {
        **envelope(world, run), 'arguments': arguments})))['outcome']
    assert populated['status'] == 'completed', json.dumps(populated)[:2000]
    revised = populated['result']['sheet_ref']
    assert run.view.records.get(revised)['provider'] == PROVIDER and revised != graded
    summary = EPISODE()._summary(run.view)
    # The same experiment, assertion, assay type, quantity and measured effect: the later sheet is the current one.
    assert [features['sheet_refs'] for features in summary['assay_sheets']] == [[revised]]
    assert summary['assay_sheets'][0]['rate_regime_status'] == 'unknown'
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 1.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    refused = asyncio.run(run.run_unit(ToolCall('literature_assay_grading_populate', {
        **envelope(world, run), 'arguments': {**arguments, 'source_ref': world['assay']}})))['outcome']
    assert refused['status'] == 'invalid'
    world['store'].close()


def test_the_aggregation_tool_combines_the_graded_experiment_with_the_owners_reducers(tmp_path):
    world = held_world(tmp_path, task_kind='verified_source_leads')
    run = linked_run(tmp_path, world, 'a105-passage-aggregate')
    asyncio.run(run.next_decision())
    graded = asyncio.run(run.run_unit(ToolCall('reason', {**envelope(world, run),
                                                          'arguments': reasoning_selection(world)})))['outcome']
    sheet_ref = graded['evidence_processing']['gradings'][0]['result']['sheet_ref']
    metrics = {'reliability': 'effect_precision', 'validity': 'recovery_deviation',
               'relevance': 'assertion_prediction_error', 'attribution': 'attributed_fraction',
               'overall': 'source_log_evidence_ratio'}
    arguments = {'assertion_ref': world['proposed'], 'comparison_ref': None, 'experiments': [
        {'experiment_ref': world['assay'],
         'metrics': {metric: {'sheet_ref': sheet_ref, 'component': component} for metric, component in metrics.items()}}]}
    aggregated = asyncio.run(run.run_unit(ToolCall('literature_a105_aggregate', {
        **envelope(world, run), 'arguments': arguments})))['outcome']
    assert aggregated['status'] == 'completed', json.dumps(aggregated)[:2000]
    summary = EPISODE()._summary(run.view)
    features, = summary['aggregation_sheets']
    assert features['sheet_refs'] == [aggregated['result']['sheet_ref']] and features['selected_assay_count'] == 1
    assert features['overall_status'] == 'complete' and features['overall_is_log_evidence_ratio'] is True
    assert features['overall_value'] == summary['assay_sheets'][0]['source_log_evidence_ratio']
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 0.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    world['store'].close()
