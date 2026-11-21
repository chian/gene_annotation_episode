"""Closeness of the paper's protein to the target by pairwise BLAST: the gradual curve over hand-made graded results (offline), and
one real run of A105's own pairwise BLAST through the real function (``-m model_run``: it runs the local BLAST program, no model is
asked)."""
import asyncio
import json
import math
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_subject_closeness import (
    IDENTITY_MIDPOINT, closeness_of_features, identity_term)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pairwise_grading import (
    graded_report, grading_features)

from .closeness_probe.episode import ClosenessProbe


def graded(identity, query_coverage=1.0, target_coverage=1.0):
    """The controlled features of a graded pairwise result (``blast_pairwise_features.grading_features``) that closeness reads."""
    features = {'sheet_refs': ['comparison_1'], 'query_paired_coverage': query_coverage, 'reference_paired_coverage': target_coverage}
    if identity is not None:
        features['paired_identity'] = identity
    return features


def test_the_identical_full_length_sequence_is_exactly_one():
    assert closeness_of_features(graded(1.0)) == {'closeness': 1.0, 'identity': 1.0, 'query_coverage': 1.0,
                                                  'target_coverage': 1.0, 'comparison_ref': 'comparison_1'}


def test_closeness_falls_smoothly_with_the_identity_over_the_aligned_region():
    identities = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
    values = [closeness_of_features(graded(identity))['closeness'] for identity in identities]
    assert values == sorted(values, reverse=True) and len(set(values)) == len(values)
    assert values[-1] == 0.0 and values[0] == 1.0
    assert identity_term(IDENTITY_MIDPOINT) == pytest.approx(0.486, abs=0.001)      # about one half at the identity where function is no longer reliably kept
    # no step anywhere: the largest drop between neighbouring identities of a 0.01 grid is small
    grid = [identity_term(index / 100) for index in range(101)]
    assert max(abs(later - earlier) for earlier, later in zip(grid, grid[1:])) < 0.03
    # about 0.13 at 20% identity (twilight zone), about 0.84 at 60% (close homologues), about 0.99 at 90%
    assert (identity_term(0.2), identity_term(0.6), identity_term(0.9)) == pytest.approx((0.130, 0.841, 0.991), abs=0.002)


def test_closeness_falls_smoothly_with_how_much_of_each_sequence_the_alignment_covers():
    full = closeness_of_features(graded(1.0))['closeness']
    halves = [closeness_of_features(graded(1.0, query_coverage=coverage))['closeness'] for coverage in (1.0, 0.75, 0.5, 0.25, 0.0)]
    assert halves == sorted(halves, reverse=True) and halves[0] == full and halves[-1] == 0.0
    both = closeness_of_features(graded(1.0, 0.5, 0.5))['closeness']
    assert both == pytest.approx(0.25) and closeness_of_features(graded(1.0, 0.5, 1.0))['closeness'] == pytest.approx(0.5)
    assert closeness_of_features(graded(0.6, 0.8, 0.9))['closeness'] == pytest.approx(identity_term(0.6) * 0.8 * 0.9)


def test_closeness_is_zero_only_when_nothing_aligns():
    nothing = closeness_of_features(graded(None, 0.0, 0.0))
    assert nothing['closeness'] == 0.0 and nothing['identity'] == 0.0
    assert closeness_of_features(graded(0.05, 0.1, 0.1))['closeness'] > 0.0


NO_HIT_REPORT = json.dumps({'BlastOutput2': [{'report': {
    'program': 'blastp', 'version': 'BLASTP 2.17.0+', 'search_target': {'subjects': [{'id': 'subject_sequence', 'len': 30}]},
    'params': {'expect': 10.0},
    'results': {'bl2seq': [{'query_id': 'query_sequence', 'query_len': 20, 'hits': [],
                            'stat': {'db_num': 0, 'db_len': 0, 'hsp_len': 0, 'eff_space': 0, 'kappa': 0.041,
                                     'lambda': 0.267, 'entropy': 0.14}, 'message': 'No hits found'}]}}}]}).encode()


def test_a_report_with_no_alignment_is_the_graded_no_alignment_result_and_closeness_zero():
    """BLAST reporting no alignment is a normal outcome of A105's own grading: closeness 0.0, no error."""
    grading = graded_report(NO_HIT_REPORT, 'blastp', 'A' * 20, 'C' * 30)
    assert grading['sheet']['status'] == 'no_reported_alignment' and grading['sheet']['reference'] is None
    features = grading_features(grading, 'grading_1')
    assert features['hsp_count'] == 0 and 'paired_identity' not in features and 'reference_length' not in features
    assert closeness_of_features(features) == {'closeness': 0.0, 'identity': 0.0, 'query_coverage': 0.0,
                                               'target_coverage': 0.0, 'comparison_ref': 'grading_1'}


# ----- the real run: A105's own pairwise BLAST on the local resource, through the real function and the real runner -----

INPUTS = 'runs/a105_head_real_20261121_01/inputs'
REPOSITORY = next(parent for parent in Path(__file__).parents if (parent / 'resources' / 'software').is_dir())
BLAST_DIRECTORY = str(REPOSITORY / 'resources' / 'software' / 'ncbi-blast-2.17.0+' / 'bin')
LOCAL_RESOURCE = 'local'


def job_world_services(directory):
    """The job services of the test run: one local resource under the test's own directory."""
    return job_services({
        'local': {LOCAL_RESOURCE: {'workspace': str(directory / 'jobs'), 'cpu_threads': 1,
                                   'policy': {'memory_bytes': 1024 ** 3, 'scratch_bytes': 64 * 1024 ** 2}}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'not_used_launch'),
        'tool_knowledge_directory': str(directory / 'not_used_knowledge')})


SETTINGS = {'closeness_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05},
                                'blast_executable_directory': BLAST_DIRECTORY, 'blast_resource_id': LOCAL_RESOURCE}}
PATH = (('closeness_probe', 'closeness'),)


def fasta_sequence(name):
    return ''.join((REPOSITORY / INPUTS / name).read_text().splitlines()[1:])


def measure(tmp_path, subjects):
    """The closeness of each subject sequence (a subject record of its own) to PopZ, the target, by the real function."""
    store = Store(tmp_path / 'store')
    try:
        popz = fasta_sequence('popz.fasta')
        store.create_problem(raw_sequence=popz, molecule='protein')
        target = store.problem()['subject_refs'][0]
        source = store.put('source', {'provider': 'closeness_test', 'accession': None, 'uri': None, 'artifact_ref': store.artifact(popz, 'text/plain'),
                                      'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                           origin='caller')['id']

        def reference(label, sequence):
            return store.put('reference', {'reference_type': 'protein', 'source_ref': source, 'accession': label, 'label': label,
                                           'sequence_ref': store.artifact(sequence, 'text/plain'), 'molecule': 'protein',
                                           'length': len(sequence), 'term_refs': [], 'context_refs': []}, origin='caller')['id']
        references = [reference('subject_' + str(index), sequence) for index, sequence in enumerate(subjects)]
        plan = [{'subject_record_ref': ref, 'target_record_ref': target} for ref in references]
        held = [target, *references]      # the records and the sequences they hold (an artifact is held as its own reference)
        held = list(dict.fromkeys(held + [store.get(ref)['sequence_ref'] for ref in held]))
        entry = {'assignment': {'input_refs': held},'message': {'plan': plan}, 'selection': []}
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                         'continuation': SETTINGS, 'services': job_world_services(tmp_path)}
        run = link(BindingRegistry([ClosenessProbe()]), 'closeness_probe', entry, run_id='closeness', journal=journal,
                   collaborators=collaborators)
        asyncio.run(run.run())
        units = journal.units('closeness', PATH)
        results = [unit[2]['outcome'] for unit in units if unit[2].get('tool') == 'compare']
        print('CLOSENESS', results)
        return results
    finally:
        store.close()


@pytest.mark.model_run
def test_real_blast_of_popz_against_itself_and_against_its_first_half(tmp_path):
    popz = fasta_sequence('popz.fasta')
    itself, half = measure(tmp_path, [popz, popz[:len(popz) // 2]])
    assert itself['closeness'] == 1.0 and itself['identity'] == 1.0
    assert itself['query_coverage'] == 1.0 and itself['target_coverage'] == 1.0
    assert half['identity'] == 1.0 and half['query_coverage'] == 1.0
    assert half['target_coverage'] == pytest.approx(len(popz[:len(popz) // 2]) / len(popz))
    assert half['closeness'] == pytest.approx(half['target_coverage']) and itself['comparison_ref'] != half['comparison_ref']


@pytest.mark.model_run
def test_real_blast_of_parb_against_popz_where_nothing_aligns(tmp_path):
    """Nothing aligns: closeness 0.0 (A105's pairwise_blast_comparison returns the graded no-alignment result)."""
    (against,) = measure(tmp_path, [fasta_sequence('parb.fasta')])
    assert against['closeness'] == 0.0 and math.isfinite(against['identity'])
