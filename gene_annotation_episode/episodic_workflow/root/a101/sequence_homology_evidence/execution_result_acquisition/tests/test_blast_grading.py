"""The graded BLAST return of the A101 result acquisition, run through the real runner on a real Store.

The run is linked with the public API and stepped with ``EpisodeRun.next_decision`` and ``run_unit``: the
Episode is entered as ``run()`` enters it (its completion controller is built from ``credit`` of the initial
summary), its own ``decide`` is shown, and the grading tool runs as a real tool unit (journaled attempt, custody
receipts, ``credit`` and the controller's step) on the held fetched result. The model is not asked here; the run
with the real model is ``test_blast_grading_model_run.py``."""
import asyncio
import json

from episode_runtime import ModelRequest, ToolCall
from yield_control import CompletionYieldController
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES, NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    EVIDENCE_TYPE, SHEET_FEATURES)

from .. import task as task_file
from ..episode import ExecutionResultAcquisition
from ..messages.final_to_parent import FINDING_FORM, RETURN_FORM
from .blast_world import held_world, linked, settings


def test_the_next_decision_offers_the_grader_with_its_instructions(tmp_path):
    world = held_world(tmp_path)
    _, _, run = linked(tmp_path, world, 'a101-blast-first')
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = ExecutionResultAcquisition()._summary(view)
    assert summary['family'] == 'blast_graded' and summary['graded_sheets'] == []
    assert summary['fetch_offered'] is False                        # the handoff row is not held here
    assert [row['result_ref'] for row in summary['fetched_results']] == [world['result_ref']]
    assert ExecutionResultAcquisition.credit(summary, view.records) == 0.0
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert request.output_schema['properties']['tool']['enum'] == ['blast_grade']
    assert world['result_ref'] in request.output_schema['properties']['arguments_json']['description']
    assert task_file.GRADER_INSTRUCTIONS in request.instructions
    assert 'Hitting a limit can censor evidence' in request.instructions
    assert request.context['graded_return_request']['return_type'] == 'blast_database_sheet_v1'
    world['store'].close()


def test_the_controller_is_the_completion_controller_of_the_credit_unit(tmp_path):
    world = held_world(tmp_path)
    _, _, run = linked(tmp_path, world, 'a101-blast-controller')
    asyncio.run(run.next_decision())
    built = ExecutionResultAcquisition.yield_controller(0.0, settings(tmp_path / 'again'), run.view.parent_input)
    assert isinstance(built, CompletionYieldController) and built.target == 1.0
    world['store'].close()


def test_the_grading_unit_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    world = held_world(tmp_path)
    _, journal, run = linked(tmp_path, world, 'a101-blast-grade')
    outcome = asyncio.run(run.run_unit(ToolCall('blast_grade', {
        'result_ref': world['result_ref'], 'request': world['input']['assignment']['selector']})))
    assert outcome['outcome']['status'] == 'completed', outcome['outcome']
    result = outcome['outcome']['result']
    source_ref, grading_ref = result['result_ref'], result['grading_artifact_ref']
    records = run.view.records
    assert records.receipt(source_ref)['how'] == 'produced' and records.receipt(grading_ref)['how'] == 'produced'
    entries = source_tool_grading_entries(records, source_ref)
    assert [entry['artifact_ref'] for entry in entries] == [grading_ref]
    sheet = entries[0]['grading']['sheet']
    assert sheet['schema'] == 'blast_database_sheet_v1' and sheet['coverage']['sequence_group_count'] == 3
    # The search entered the A101 tool profile from the identity of its producer.
    assert [(row['source_ref'], row['query_ref'], row['profile'])
            for row in records.table(SEARCHES).select({'source_ref': source_ref})] == [
        (source_ref, world['subject'], 'blast')]

    # A search with no published alignment still enters the axis sheet's profile: the BLAST channel is included
    # and its component is zero (convention 015 section 4), and the head's features read that from the sheet.
    known = [ref for ref in records.refs() if not ref.startswith('row_')]
    details = AxisSheet().read_details(records, {'subject_refs': [world['subject']]},
                                                         known_record_refs=known, details_limit=ALL,
                                                         details_offset=0)
    assert details['a101_sheet']['targets'][world['subject']]['profile'] == ['blast'] and details['credit'] == 0.0
    target, = axis_features(details)
    assert (target['algorithm_count'], target['blast_component'], target['comparison_count']) == (1, 0.0, 0)
    assert target['uncovered_region_count'] == 1 and 'hmmer_component' not in target

    # Completion: the controller stopped the Episode on this unit; the result was built and the run closed.
    closed = asyncio.run(run.run())
    assert closed['record'].ended_by == 'yield_stop' and closed['record'].units_consumed == 1
    returned = closed['result'].as_record()
    assert returned['credit'] == 1.0
    finding = returned['finding']
    assert FINDING_FORM.admit(finding, 'finding') == finding
    assert finding['execution_completed'] is True and finding['target_family'] == 'blast_graded'
    assert finding['acquisitions'] == 1 and finding['failure_count'] == 0
    graded, = finding['graded_sheets']
    assert graded['evidence_type'] == EVIDENCE_TYPE and graded['sheet_refs'] == [grading_ref]
    assert graded['routed_to_axis_credit'] is True and graded['total_group_count'] == 3
    assert graded['uncertainty_magnitude'] == 0.01 and graded['functions'] == []
    assert set(SHEET_FEATURES) - set(graded) <= {'search_limit_reached', 'unannotated_fraction'}
    search_ref = result['search_ref']
    assert returned['execution_blast_graded_refs'] == [source_ref, grading_ref, search_ref]
    selected = RETURN_FORM.select(['execution_blast_graded_refs'])
    assert selected.admit(returned, 'return') == returned
    assert set(selected.record_refs(returned)) == {source_ref, grading_ref, search_ref}
    assert journal.run_state('a101-blast-grade')[1]['ended_by'] == 'yield_stop'
    json.dumps(returned, allow_nan=False)
    world['store'].close()


def test_a_grading_of_another_database_is_an_invalid_outcome_that_enters_the_iterator(tmp_path):
    world = held_world(tmp_path, database='another_db')
    _, _, run = linked(tmp_path, world, 'a101-blast-conflict')
    outcome = asyncio.run(run.run_unit(ToolCall('blast_grade', {
        'result_ref': world['result_ref'], 'request': world['input']['assignment']['selector']})))
    assert outcome['outcome']['status'] == 'invalid'
    assert outcome['outcome']['feedback']['code'] == 'blast_grader_result_database_conflict'
    summary = ExecutionResultAcquisition()._summary(run.view)
    assert summary['graded_sheets'] == [] and summary['gradings'][0]['code'] == 'blast_grader_result_database_conflict'
    assert ExecutionResultAcquisition.credit(summary, run.view.records) == 0.0
    world['store'].close()


class AxisSheet(NativeCorrespondenceScoring):
    """The axis-sheet projector with the credit definition its ``read_details`` records as its policy (the heads
    each keep their own copy; this test names the projector's policy only)."""

    def as_record(self):
        return {'kind': 'a101_native_sequence_correspondence'}
