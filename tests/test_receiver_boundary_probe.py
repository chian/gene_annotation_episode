"""Fault instrumentation checks, not configured-model occurrence evidence."""
import asyncio
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.runtime import Record
from test_homology_episode_runtime import Provider, action, commission, prepared, run


PROBE = Path(__file__).resolve().parents[1] / 'cases/gene_001/verification/receiver_boundary_probe.py'


def test_selected_receiver_fault_preserves_real_episode_repair_and_same_operation_replay(tmp_path):
    selected_receiver_fault = runpy.run_path(str(PROBE))['selected_receiver_fault']
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True)
    record_path = tmp_path / 'injected-receiver-fault.json'
    original_execute, original_receive = HomologyEpisodes._execute, HomologyJobs.receive

    def first_check(context):
        job_ref = jobs.db.execute('SELECT job_ref FROM orders').fetchone()[0]
        # An unselected/closure-style check must not consume the selected fault.
        assert jobs.check_handoff(jobs.handoff(job_ref))['sample']['state'] == 'running'
        assert not record_path.exists()
        return action('homology.check_handoff')

    def repair(context):
        assert context['feedback']['code'] == 'job_storage_failed'
        assert context['feedback']['operation'] == 'homology.check_handoff'
        assert context['working_state']['assignment']['job_ref'] == json.loads(record_path.read_text())['job_ref']
        return action('homology.check_handoff')

    provider = Provider([commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), first_check, repair])
    try:
        with selected_receiver_fault(record_path, jobs.directory):
            summary = run(store, tools, provider, binding, tmp_path / 'run',
                counts={'annotation': 1, 'job_launch': 5})
            assert summary['completed_actions'] == 1 and summary['credit'] == 0
            fault = json.loads(record_path.read_text())
            assert fault['not_a_natural_service_failure'] is True
            form = json.loads(store.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])
            assert form['job_handoff_state'] == 'usable'
            assert form['job_ref'] == fault['job_ref']
            assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
            assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 0
            assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
            failed = store.db.execute("SELECT count(*) FROM runtime_actions WHERE json_extract(result,'$.status')='failed'").fetchone()[0]
            assert failed == 1
            source = SimpleNamespace(path=(('job_launch', 'fixture'),), scope=scope,
                request=SimpleNamespace(message=Record({'job_assignment': {
                    'job_ref': fault['job_ref'], 'query_ref': query, 'cpu': 1}})),
                workflow=SimpleNamespace(store=store, run_id=fault['run_id']), episode_id=fault['episode_id'])
            before = record_path.read_bytes()
            # Interrupted replay of the SAME selected attempt retains failure;
            # only a new episode-selected attempt sees the recovered interface.
            replay = asyncio.run(binding.execute(source, 'homology.check_handoff', {},
                operation_key=fault['operation_key']))
            assert replay['status'] == 'failed' and replay['feedback']['code'] == 'job_storage_failed'
            later = asyncio.run(binding.execute(source, 'homology.check_handoff', {},
                operation_key='distinct-selected-attempt'))
            assert later['status'] == 'completed'
            assert record_path.read_bytes() == before
            assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        assert HomologyEpisodes._execute is original_execute and HomologyJobs.receive is original_receive
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
