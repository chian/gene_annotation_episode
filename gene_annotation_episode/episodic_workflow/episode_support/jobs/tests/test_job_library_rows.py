"""The job library functions that keep rows of an Episode's work, run through the real runner on the scoped store.

Every test links the ``library_probe`` test episode with a real ``Store``, ``RunJournal`` and model provider. Its
tools call the library function under test on ``ctx.store``; its ``internal_summary`` reads the same rows back
through the read-only reader. The remote search is refused by the real ``PublicClients`` before any request is
sent (no contact address is configured), so no network is used."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from .library_probe.episode import LibraryProbe

SETTINGS = {'library_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
TIMING_AXES = ('evolutionary_history_evidence', 'partner_presence_evidence', 'perturbation_evidence',
               'sequence_homology_evidence', 'structural_homology_evidence')
MEASUREMENT_ONLY_AXES = ('biochemical_feasibility_evidence', 'gene_context_evidence', 'sample_context_evidence')
PROGRESS_AXES = ('biochemical_feasibility_evidence', 'evolutionary_history_evidence', 'gene_context_evidence',
                 'partner_presence_evidence', 'sequence_homology_evidence', 'structural_homology_evidence')
SEARCH_AXES = ('evolutionary_history_evidence', 'gene_context_evidence', 'partner_presence_evidence',
               'sequence_homology_evidence', 'structural_homology_evidence')


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    target, = store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ', molecule='protein')['subject_refs']
    yield {'store': store, 'target': target, 'tmp': tmp_path, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
    store.close()


def run(world, run_id, plan):
    entry = {'assignment': {'record_refs': [world['target']]}, 'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([LibraryProbe()]), 'library_probe', entry, run_id=run_id, journal=world['journal'],
                  collaborators={'store': world['store'], 'model_provider': world['provider'],
                                 'continuation': SETTINGS, 'services': {}})
    return asyncio.run(linked.run())['result'].as_record()


def outcomes(world, run_id):
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, (('library_probe', run_id),))]


def step(tool, **arguments):
    return {'tool': tool, 'arguments': arguments}


@pytest.mark.parametrize('axis', TIMING_AXES)
def test_a_native_measurement_is_a_work_table_row_and_its_credit_is_read_from_the_rows_it_holds(world, axis):
    scope = {'subject_refs': [world['target']]}
    result = run(world, 'timing', [step('native_timing', axis=axis, scope=scope)])
    done, = outcomes(world, 'timing')
    refs, details = done['refs'], done['details']
    # Four measurements, three physical attempts, two of them with a complete duration: credit 2 units each.
    assert len(set(refs)) == 4 and all(ref.startswith('row_') for ref in refs)
    assert details['measured_attempt_count'] == 2 and details['credit'] == 4.0 == details['monitoring_information_credit']
    assert [row['receipt_ref'] for row in details['native_execution_measurements']] == refs[:2]
    assert {row['operation'] for row in details['native_execution_measurements']} == {'align_pair'}
    assert [row['elapsed_seconds'] for row in details['native_execution_measurements']] == [2.5, 3.5]
    # The summary read the same rows through the read-only reader, and the rows are the Episode's products.
    assert result['record_refs'][-4:] == refs[-4:] or set(refs) <= set(result['record_refs'])


@pytest.mark.parametrize('axis', PROGRESS_AXES)
def test_progress_observations_are_rows_of_the_episode_and_an_unchanged_observation_is_the_same_row(world, axis):
    scope = [world['target']]
    result = run(world, 'progress', [
        step('publish_practical_job', axis=axis, subject_refs=scope, states=['running', 'completed']),
        step('progress_observe', axis=axis, expose=[])])
    published, done = outcomes(world, 'progress')
    assert len(published['source_refs']) == 2
    assert done['second_is_first'] and done['exposure_again_is_same'] and done['read_back']
    assert done['resolves'] == [True, True, True, False]
    assert done['first']['execution_status']['native']['state'] == 'completed'
    assert done['first']['result_available'] is True and done['description'] == 'practical_job'
    assert done['first']['committed_record_refs'] == published['source_refs']
    assert done['first']['progress_ref'].startswith('progress_')
    assert done['exposure']['publication_ref'].startswith('progress_publication_')
    # The reader found the observation among the rows the Episode holds.
    assert result['finding'] == {'plan_steps': 2, 'steps_done': 2}


@pytest.mark.parametrize('axis', SEARCH_AXES)
def test_a_refused_remote_search_leaves_a_job_row_and_a_failure_row_that_is_withdrawn_when_cleared(
        world, axis, tmp_path):
    run(world, 'search', [step('remote_search', axis=axis, subject_ref=world['target'], directory=str(tmp_path / 'blast'))])
    done, = outcomes(world, 'search')
    assert done['search']['code'] == 'ncbi_contact_not_configured' and done['search']['outcome'] == 'not_sent'
    assert done['state'] == 'not_submitted' and done['cause'] == 'ncbi_contact_not_configured'
    assert done['job_rows'] == 1 and done['failure_rows_live'] == 1
    assert done['listed'] == [] and done['listed_all'] == [done['search']['job_ref']]
    assert done['cleared_cause'] is None and done['withdrawn'] == [True] and done['failure_revisions'] == [2]
    assert done['artifacts_held'] is True and done['again'] is True


@pytest.mark.parametrize('axis', MEASUREMENT_ONLY_AXES)
def test_an_axis_without_monitoring_credit_still_reads_its_measurements_back_from_the_rows(world, axis):
    scope = {'subject_refs': [world['target']]}
    run(world, 'measured', [step('native_timing', axis=axis, scope=scope)])
    done, = outcomes(world, 'measured')
    assert len(set(done['refs'])) == 4 and all(ref.startswith('row_') for ref in done['refs'])
    assert [row['statistic']['elapsed_seconds'] for row in done['details']['measurements']] == [2.5, 3.5, 4.5, None]
    assert set(done['details']) == {'measurements'}


@pytest.mark.parametrize('axis', ('structural_homology_evidence', 'evolutionary_history_evidence',
                                  'partner_presence_evidence'))
def test_an_hpc_request_source_is_found_only_once_its_row_is_written(world, axis):
    run(world, 'registry', [step('hpc_registry', axis=axis, subject_refs=[world['target']])])
    done, = outcomes(world, 'registry')
    assert done['refused'].endswith('grant_required')
    assert done['registered'] is True and done['other_provider'] is None
    assert done['rows'] == [done['request_ref']]


def test_a_component_request_is_published_and_read_back_from_its_row(world):
    run(world, 'component', [step('component_request', subject_refs=[world['target']])])
    done, = outcomes(world, 'component')
    assert done['read'] is True and done['other_provider'] is None and done['rows'] == [done['reference']]
    assert [row['status'] for row in done['findings']] == ['native_work_requested']
