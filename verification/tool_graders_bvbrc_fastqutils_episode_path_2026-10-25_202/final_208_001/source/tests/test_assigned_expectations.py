"""Actual registry metadata selects statistical classes; no native/model work."""
from copy import deepcopy
import json

from gene_annotation_episode.execution_recording import HomologyStatistics
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.run_statistics import RunHistory
from test_homology_jobs import prepare, QUERY


def test_actual_assigned_query_and_cpu_choose_class_without_global_identity_leak(tmp_path):
    history_path = tmp_path/'global.sqlite'
    history = RunHistory(history_path); history.close()
    jobs = prepare(tmp_path)
    stats = HomologyStatistics(history_path, 'fixture-host', 1, 253)
    binding = ExecutionExpectations.for_homology(jobs, stats, roles=['job_launch', 'job_monitor'])
    full = jobs.order(query_ref='fixture_full_query', query_fasta=QUERY, cpu=1, operation_key='full')
    fragment = jobs.order(query_ref='fixture_fragment_query', query_fasta='>fragment\n'+'M'*21+'\n', cpu=1, operation_key='fragment')
    try:
        assignment = {'job_ref': fragment, 'query_ref': 'fixture_fragment_query', 'cpu': 1}
        before = binding.capture('job_launch', assignment=assignment)
        assert before['status'] == 'available'
        assert before['execution_classes'][0]['query_residues'] == 21
        assert before['execution_classes'][0]['cpu_threads'] == 1
        assert before['assigned_execution_class_ref'] == before['snapshots'][0]['data']['class_ref']
        jobs.configure(fragment, 1)
        after = binding.capture('job_launch', assignment=assignment)
        assert after['execution_classes'][0]['cpu_threads'] == 1
        assert before == after
        assert stats.execution_class_for_query(jobs, query_fasta='>fragment\n'+'M'*21+'\n', cpu=1).ref == before['assigned_execution_class_ref']
        full_context = binding.capture('job_launch', assignment={'job_ref': full, 'query_ref': 'fixture_full_query', 'cpu': 1})
        assert full_context['execution_classes'][0]['query_residues'] == 253
        assert full_context['snapshots'][0]['ref'] != after['snapshots'][0]['ref']
        classes = json.dumps(before['execution_classes']+after['execution_classes'])
        assert 'fixture_full_query' not in classes and 'fixture_fragment_query' not in classes
        assert fragment not in classes and full not in classes
        frozen = binding.as_record()
        mutable = binding.homology
        mutable['registry_directory'] = str(tmp_path/'wrong')
        assert binding.as_record() == frozen
        restored = ExecutionExpectations.from_record(frozen)
        assert restored.capture('job_launch', assignment=assignment) == after
        assert restored.capture('job_launch')['status'] == 'unavailable'
        assert restored.capture('job_launch', assignment={'job_ref': full, 'query_ref': 'fixture_fragment_query', 'cpu': 1})['status'] == 'unavailable'
        assert restored.capture('job_launch', assignment={**assignment, 'cpu': 2})['status'] == 'unavailable'
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()
