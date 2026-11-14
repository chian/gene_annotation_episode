"""Engineered completed receipt crosses the real Homology receiver and Store.

The registry order, journal and publisher are real. Completion files represent
explicit fixture data; no native service, provider or episode is executed.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.domain import canonical, validate_schema
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.state import Store
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root import execution_recording as recording
from gene_annotation_episode.episodic_workflow.root import native_measurement, native_timing_information as timing
from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
from gene_annotation_episode.episodic_workflow.root.library.homology_job_inputs import FileAsset
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import CHECKED_STATUS_SCHEMA
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.tests.public_caller_checks import (
    FIXTURES, create_workspace, forbidden, sha,
)


@pytest.mark.parametrize('mismatch', [False, True], ids=['authentic', 'changed-assignment'])
def test_recorded_homology_receipt_uses_canonical_measurement_and_original_assignment(tmp_path, mismatch):
    workspace = tmp_path / 'store'
    query_ref, _ = create_workspace(workspace, protein=True)
    policy = LocalJobPolicy(memory_bytes=128 * 1024 ** 2, scratch_bytes=8 * 1024 ** 2)
    jobs = HomologyJobs.create(tmp_path / 'jobs',
        executable=FileAsset(FIXTURES / 'inert_native', sha(FIXTURES / 'inert_native')),
        reference_database=FileAsset(FIXTURES / 'references.faa', sha(FIXTURES / 'references.faa')),
        policy=policy, max_cpu=1)
    history_path = tmp_path / 'history.sqlite3'
    history = RunHistory(history_path)
    history.close()
    statistics = recording.HomologyStatistics(history_path, 'controlled-public-host', 1, 3)
    binding = HomologyEpisodes(jobs, parser_policy=policy, credit_projector=forbidden,
        credit_binding={'kind': 'unexecuted-credit'}, monitoring_projector=forbidden,
        monitoring_binding={'kind': 'unexecuted-monitoring'}, statistics=statistics)
    try:
        job = jobs.order(query_ref=query_ref, query_fasta='>query\nMKT\n', cpu=1,
            operation_key='controlled-original-order')
        original_order = jobs._row(job)
        execution_class = statistics.execution_class(jobs, original_order)
        context = recording.NativeStatistics.capture(history_path, execution_class,
            recovery_directory=tmp_path / 'recovery')
        paths = {name: tmp_path / (name + '.json') for name in ('handle', 'status', 'result', 'statistics')}
        body = {'statistics': context.as_record(),
            'paths': {name: str(paths[name]) for name in ('status', 'result', 'statistics')},
            'unit': 'engineered-homology-receipt', 'boot_id': 'engineered-boot',
            'started_monotonic_ns': 1_000_000_000,
            'execution_memory_path': str(tmp_path / 'memory.sqlite3')}
        completion = {'SERVICE_RESULT': 'success', 'ended': {'boot_id': 'engineered-boot',
            'monotonic_ns': 3_500_000_000, 'at': '2026-11-13T00:00:00+00:00'}}
        for name, value in (('handle', body), ('status', completion), ('result', {
                'native_returncode': 0, 'execution_failure': None, 'resource_failure': None})):
            paths[name].write_text(canonical(value))
        exported = recording.publish_native_statistics(paths['handle'])
        assert exported['state'] == 'recorded' and exported['recovery_state'] == 'retained'
        measured = recording.NativeMeasurement.from_record(exported['measurement'])
        assert type(measured) is native_measurement.NativeMeasurement
        status = {'job_ref': job, 'registry_ref': jobs.config['registry_ref'],
            'state': 'returned', 'outcome': 'succeeded', 'elapsed_seconds': 2.5,
            'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': 0,
            'failure_code': None, 'resource': None,
            'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction',
            'outputs': [], 'checked_at_unix_seconds': 1700000000.0}
        schema = {**deepcopy(CHECKED_STATUS_SCHEMA), 'x-source': 'job_checked_status'}
        validate_schema(status, schema)
        scope = {'subject_refs': [query_ref]}
        assignment = {'job_ref': job, 'query_ref': query_ref, 'cpu': 2 if mismatch else 1}
        outcome = {'status': 'completed',
            'result': {'sample': {key: value for key, value in status.items() if key != 'checked_at_unix_seconds'},
                       'checked_at_unix_seconds': status['checked_at_unix_seconds']},
            'execution_statistics_export': [{**exported, 'job_ref': job}]}
        with Store(workspace) as store:
            journal = Journal(store, 'engineered-receipt-journal')
            with store.transaction():
                journal.save('runtime_episodes', {'episode_id': 'original-child',
                    'path': canonical([['annotation', 'root'], ['job_monitor', 'child']]),
                    'request': canonical({'message': {'scope': scope, 'job_assignment': assignment}}),
                    'initial_credit': 0.0, 'state': 'held'})
                journal.save('runtime_actions', {'episode_id': 'original-child', 'decision_index': 0,
                    'action': canonical({'tool': 'homology.check_handoff'}), 'result': canonical(outcome),
                    'credit': 0.0})
            before = tuple(store.db.execute('SELECT request FROM runtime_episodes').fetchone())
            result = binding.received_timing_records(store, status, schema, scope)
            if mismatch:
                assert result['native_execution_refs'] == []
                assert result['issues'] == [{'source': 'job_checked_status', 'field': [],
                    'job_ref': job, 'code': 'measurement_record_invalid'}]
                assert store.list('native_execution') == []
            else:
                assert result['issues'] == []
                reference, = result['native_execution_refs']
                restored = timing.read_measurement(store, reference)
                assert type(restored) is native_measurement.NativeMeasurement
                assert restored.as_record() == measured.as_record()
                assert binding.received_timing_records(store, status, schema, scope) == result
                assert len(store.list('native_execution')) == 1
                projected = timing.NativeTimingInformation(0.25).read_details(store, scope,
                    known_execution_refs=[reference, reference], initial_execution_refs=[],
                    details_limit=None, details_offset=0)
                assert projected['monitoring_information_credit'] == 0.25
                assert projected['measured_attempt_count'] == 1
                assert projected['native_execution_measurements'] == [
                    timing.measurement_fields(reference, measured, operation='phmmer_search')]
                assert projected['native_execution_measurements'][0]['elapsed_seconds'] == 2.5
            assert tuple(store.db.execute('SELECT request FROM runtime_episodes').fetchone()) == before
            assert jobs._row(job) == original_order
            assert not original_order['staged'] and not original_order['submission_requested']
    finally:
        jobs.close()
