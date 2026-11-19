"""The graded local phmmer return of the A101 result acquisition, run through the real runner on a real Store.

The run is linked with the public API and stepped with ``EpisodeRun.next_decision`` and ``run_unit``: the
grading tool runs as a real tool unit on the held fetched native output (``fixtures/phmmer``): the native rows are
written to the declared work table, each printed alignment is joined to exactly one table row and graded into the
HMMER search sheet, and the graded alignments are published with their observations. The model is not asked here;
the run with the real model is ``test_phmmer_grading_model_run.py``."""
import asyncio
import json

from episode_runtime import ModelRequest
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_grading_values import (
    NATIVE_ROWS, grading_identity)

from .. import task as task_file
from ..episode import ExecutionResultAcquisition
from ..messages.final_to_parent import FINDING_FORM, RETURN_FORM
from .phmmer_world import FIXTURES, grade_call, held_world, linked
from .test_blast_grading import AxisSheet


def test_the_next_decision_offers_the_phmmer_grader_with_its_instructions(tmp_path):
    world = held_world(tmp_path)
    _, _, run = linked(tmp_path, world, 'a101-phmmer-first')
    request = asyncio.run(run.next_decision())
    summary = ExecutionResultAcquisition()._summary(run.view)
    assert summary['family'] == 'phmmer_graded' and summary['query_ref'] == world['subject']
    assert summary['fetch_offered'] is False and summary['profile_sheets'] == []
    lines = {row['result_ref']: row['first_line'] for row in summary['fetched_results']}
    assert lines[world['files']['native_text_ref']].startswith('# phmmer ::')
    assert ExecutionResultAcquisition.credit(summary, run.view.records) == 0.0
    assert isinstance(request, ModelRequest)
    assert request.output_schema['properties']['tool']['enum'] == ['phmmer_grade']
    assert task_file.PHMMER_GRADER_INSTRUCTIONS in request.instructions
    assert 'joining its printed alignment to exactly one table row' in request.instructions
    world['store'].close()


def test_the_grading_unit_saves_the_sheets_the_observations_and_the_profile_row(tmp_path):
    world = held_world(tmp_path)
    _, journal, run = linked(tmp_path, world, 'a101-phmmer-grade')
    outcome = asyncio.run(run.run_unit(grade_call(world)))['outcome']
    assert outcome['status'] == 'completed', outcome
    result = outcome['result']
    records = run.view.records
    assert len(result['grading_artifact_refs']) == 2 and len(result['observations']) == 2
    for row in result['observations']:
        entry, = source_tool_grading_entries(records, row['source_ref'])
        assert entry['grading']['sheet']['schema'] == 'hmmer_search_sheet_v1'
        assert entry['grading']['scores']['domains'][0]['paired_positions'] == 20
        assert records.get(row['observation_ref'])['kind'] == 'alignment'
    # The native rows of the capture are rows of the declared work table, held by this Episode.
    rows = records.table(NATIVE_ROWS).select()
    assert rows and {row['role'] for row in rows} == {'stdout', 'tblout', 'domtblout'}
    assert [(row['source_ref'], row['query_ref'], row['profile'])
            for row in records.table(SEARCHES).select({'source_ref': result['snapshot_ref']})] == [
        (result['snapshot_ref'], world['subject'], 'hmmer')]
    # The axis sheet over the held records: the HMMER channel is in the profile and the alignments supply it.
    known = [ref for ref in records.refs() if not ref.startswith('row_')]
    details = AxisSheet().read_details(records, {'subject_refs': [world['subject']]}, known_record_refs=known,
                                       details_limit=ALL, details_offset=0)
    target, = axis_features(details)
    assert target['algorithm_count'] == 1 and target['hmmer_component'] > 0 and target['comparison_count'] == 2
    assert details['credit'] > 0

    closed = asyncio.run(run.run())
    assert closed['record'].ended_by == 'yield_stop' and closed['record'].units_consumed == 1
    returned = closed['result'].as_record()
    assert returned['credit'] == 1.0
    finding = returned['finding']
    assert FINDING_FORM.admit(finding, 'finding') == finding
    assert finding['target_family'] == 'phmmer_graded' and finding['execution_completed'] is True
    assert [row['domain_count'] for row in finding['profile_sheets']] == [1, 1]
    first = finding['profile_sheets'][0]
    assert first['evidence_type'] == 'protein_profile_match' and first['program'] == 'phmmer'
    assert first['routed_to_axis_credit'] is True and first['model_coverage'] == 1.0
    assert first['min_independent_evalue'] == 4.3e-24 and 'gathering_cutoff_passed' not in first
    selected = RETURN_FORM.select(['execution_phmmer_graded_refs'])
    assert selected.admit(returned, 'return') == returned
    assert set(result['grading_artifact_refs']) <= set(returned['execution_phmmer_graded_refs'])
    assert journal.run_state('a101-phmmer-grade')[1]['ended_by'] == 'yield_stop'
    json.dumps(returned, allow_nan=False)
    world['store'].close()


def test_a_repeated_capture_is_the_same_grading(tmp_path):
    world = held_world(tmp_path)
    _, _, run = linked(tmp_path, world, 'a101-phmmer-again')
    first = asyncio.run(run.run_unit(grade_call(world)))['outcome']
    grading = json.loads(run.view.records.get_artifact(first['result']['grading_artifact_refs'][0]))['grading']
    identity = grading_identity(grading)
    assert identity == grading_identity(json.loads(json.dumps(grading)))
    changed = json.loads(json.dumps(grading))
    changed['scores']['domains'][0]['native_domain_score_bits'] += 1
    assert grading_identity(changed) != identity
    failed = {'sheet': None, 'scores': None, 'failure': {'code': 'phmmer_grading_alignment_association_missing'}}
    assert grading_identity(failed) == grading_identity({**failed, 'failure': {**failed['failure'], 'x': 1}})
    world['store'].close()


def test_a_missing_or_ambiguous_table_join_is_recorded_never_guessed(tmp_path):
    """Without the per-domain table the printed domain has no table row: the grading still joins the printed
    alignment to its one stdout row and records the missing table association on the domain."""
    world = held_world(tmp_path)
    _, _, run = linked(tmp_path, world, 'a101-phmmer-missing')
    call = grade_call(world, without=('domain_table_ref',))
    outcome = asyncio.run(run.run_unit(call))['outcome']
    assert outcome['status'] in ('completed', 'partial'), outcome
    grading = json.loads(run.view.records.get_artifact(outcome['result']['grading_artifact_refs'][0]))['grading']
    codes = {issue['code'] for issue in grading['sheet']['domains'][0]['issues']}
    assert 'hmmer_native_table_unavailable' in codes
    world['store'].close()


def test_an_ambiguous_table_join_is_recorded_never_guessed(tmp_path):
    """A per-domain table that lists the printed domain twice gives two candidates: uniqueness is the only
    permission to join, so the domain keeps its printed row and records the ambiguity."""
    world = held_world(tmp_path)
    table = (FIXTURES / 'phmmer.domtblout').read_text().splitlines(keepends=True)
    duplicated = ''.join([*table[:4], table[3], *table[4:]])
    ref = world['store'].artifact(duplicated.encode(), 'text/plain')
    assignment = world['input']['assignment']
    assignment['record_refs'].append(ref)
    assignment['initial_result_refs'].append(ref)
    world['files']['domain_table_ref'] = ref
    _, _, run = linked(tmp_path, world, 'a101-phmmer-ambiguous')
    outcome = asyncio.run(run.run_unit(grade_call(world)))['outcome']
    assert outcome['status'] in ('completed', 'partial'), outcome
    gradings = [json.loads(run.view.records.get_artifact(ref))['grading']
                for ref in outcome['result']['grading_artifact_refs']]
    codes = {issue['code'] for grading in gradings for issue in grading['sheet']['domains'][0]['issues']}
    assert 'hmmer_table_stdout_association_ambiguous' in codes
    world['store'].close()
