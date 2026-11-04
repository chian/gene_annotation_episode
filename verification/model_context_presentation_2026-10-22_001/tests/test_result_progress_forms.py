"""Actual tiny native results through shared episodes and requested forms.

Decisions, scores and stopping counts are engineering fixtures. No configured
model, new full-corpus search or scientific interpretation is claimed.
"""
import json
import sqlite3

import pytest

from gene_annotation_episode import homology_episodes as episode_module
from gene_annotation_episode.homology_results import recorded_coverage
from gene_annotation_episode.native_lifecycle import cancel
from test_homology_episode_runtime import Provider, action, commission, prepared, run
from test_homology_jobs import wait_terminal


@pytest.mark.parametrize('coverage_storage_failure', [False, True])
def test_result_coverage_form_preserves_actual_acquisition_and_independent_results(
        tmp_path, monkeypatch, coverage_storage_failure):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    handoffs, snapshots, returned = [], [], []
    real_status = jobs.status
    real_coverage = episode_module.recorded_coverage

    def results(context):
        handoff = context['child_reports'][-1]['job_handoff']
        handoffs.append(handoff)
        wait_terminal(jobs, handoff['job_ref'])
        selected = commission(binding, 'job_results', scope, handoff=handoff)
        schema = json.loads(selected['selection']['schema_json'])
        schema['properties']['coverage'] = binding.fact_sources('job_results')[
            'job_result_progress']['report_schema']
        schema['properties']['coverage_failure'] = binding.fact_sources('job_results')[
            'job_result_progress_failure']['report_schema']
        schema['required'] = list(schema['properties'])
        selected['selection']['schema_json'] = json.dumps(schema)
        return selected

    def read_coverage(context):
        result = context['last_local_outcome']['result']
        snapshots.append(result['snapshot_ref'])
        assert result['offset'] == 0 and result['next_offset'] == 1
        assert result['total'] == 2
        assert len(result['publication_rows']) == 1
        assert result['publication_rows'][0]['ordinal'] == 1
        assert result['publication_rows'][0]['record_type'] == 'reference'
        # The selected coverage read must not poll the job. Restore this before
        # later extraction and the explicitly required closure handoff check.
        def forbidden_poll(*args, **kwargs):
            raise AssertionError('A coverage read polled native execution')
        monkeypatch.setattr(jobs, 'status', forbidden_poll)
        return action('homology.coverage', {'snapshot_ref': snapshots[-1]})

    def last_page(context):
        progress = context['last_local_outcome']['result']
        assert progress['snapshot_ref'] == snapshots[-1]
        assert progress['parsed_row_count'] == 2
        assert progress['acquired_row_count'] == 1
        assert progress['acquired_ordinal_intervals'] == [[1, 2]]
        assert progress['all_parsed_rows_acquired'] is False
        monkeypatch.setattr(jobs, 'status', real_status)
        if coverage_storage_failure:
            def unavailable(*args, **kwargs):
                raise sqlite3.OperationalError('SYNTHETIC coverage-read storage failure')
            # Only the optional closure fact read fails. Real native extraction
            # still uses its own factual implementation and publishes the row.
            monkeypatch.setattr(episode_module, 'recorded_coverage', unavailable)
        return action('homology.extract', {'limit': 1, 'offset': 1, 'snapshot_ref': snapshots[-1]})

    def use_returned(context):
        report = context['child_reports'][-1]
        returned.append(report)
        assert len(report['comparisons']) == 1
        actual = recorded_coverage(store, snapshots[-1], query_ref=query, scope=scope,
            execution_context={'job_ref': handoffs[-1]['job_ref'], 'registry_ref': jobs.config['registry_ref']})
        assert actual['parsed_row_count'] == actual['acquired_row_count'] == 2
        assert actual['acquired_ordinal_intervals'] == [[1, 3]]
        assert actual['all_parsed_rows_acquired'] is True
        assert actual['native_result_complete'] is True
        if coverage_storage_failure:
            assert report['coverage'] is None
            assert report['coverage_failure'] == 'storage_failure'
        else:
            assert report['coverage_failure'] is None
            assert report['coverage']['snapshot_ref'] == snapshots[-1]
            assert report['coverage']['parsed_row_count'] == report['coverage']['acquired_row_count'] == 2
            assert report['coverage']['acquired_ordinal_intervals'] == [[1, 3]]
            assert report['coverage']['parser_finished'] is True
            assert report['coverage']['native_result_complete'] is True
            assert report['coverage']['parse_execution_failed'] is False
            assert 'parse_execution_failure' not in report['coverage']
        monkeypatch.setattr(episode_module, 'recorded_coverage', real_coverage)
        assert store.get(report['comparisons'][0])['record_type'] == 'observation'
        return action('fixture.inspect_returned', {'observation_ref': report['comparisons'][0]})

    provider = Provider([
        commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), action('homology.check_handoff'), results,
        action('homology.extract', {'limit': 1}), read_coverage, last_page, use_returned,
    ])
    try:
        summary = run(store, tools, provider, binding, tmp_path/'run',
            counts={'annotation': 3, 'job_launch': 5, 'job_results': 3})
        assert summary['completed_actions'] == 3 and summary['credit'] == 0
        assert len(tools.seen) == 1
        assert store.count('assessment') == store.count('annotation') == 0
        child_id = store.db.execute("SELECT episode_id FROM runtime_episodes "
            "WHERE json_extract(path,'$[#-1][0]')='job_results'").fetchone()[0]
        saved = store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?', (child_id,)).fetchone()[0]
        assert json.loads(saved) == returned[0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                                (child_id,)).fetchone()[0] == 3
        for role in ('job_launch', 'job_monitor'):
            assert 'job_result_progress' not in binding.fact_sources(role)
    finally:
        monkeypatch.setattr(jobs, 'status', real_status)
        monkeypatch.setattr(episode_module, 'recorded_coverage', real_coverage)
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
