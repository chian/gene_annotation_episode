"""Parent-requested recorded status, distinct from closure validation/sampling."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.native_lifecycle import cancel
from test_homology_episode_runtime import prepared, Provider, action, commission, run


@pytest.mark.parametrize('selected_check', [False, True])
def test_parent_receives_exact_selected_status_or_null_without_extra_poll_or_observation(
        tmp_path, monkeypatch, selected_check):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True)
    original = jobs.check_handoff
    checked = []
    def check(handoff):
        value = original(handoff)
        checked.append(deepcopy(value))
        return value
    monkeypatch.setattr(jobs, 'check_handoff', check)
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    schema = json.loads(selected['selection']['schema_json'])
    schema['properties']['checked_execution'] = binding.fact_sources('job_launch')['job_checked_status']['report_schema']
    schema['properties']['sample'] = binding.fact_sources('job_launch')['job_sample']['report_schema']
    schema['required'].extend(['checked_execution', 'sample'])
    selected['selection']['schema_json'] = json.dumps(schema)
    actions = [action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit')]
    if selected_check:
        actions.append(action('homology.check_handoff'))
    try:
        summary = run(store, tools, Provider([selected, *actions]), binding, tmp_path/'run',
            counts={'annotation': 1, 'job_launch': len(actions)})
        assert summary['completed_actions'] == 1
        form = json.loads(store.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])
        assert form['job_handoff_state'] == 'usable'
        assert form['sample'] is None  # No selected monitoring sample is invented.
        assert len(checked) == (2 if selected_check else 1)
        if selected_check:
            expected = {'checked_at_unix_seconds': checked[0]['checked_at_unix_seconds'],
                **checked[0]['sample']}
            assert form['checked_execution'] == expected
            assert form['checked_execution']['state'] == 'running'
            assert checked[-1]['checked_at_unix_seconds'] >= expected['checked_at_unix_seconds']
        else:
            assert form['checked_execution'] is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == len(actions)+1
        saved = store.db.execute('SELECT facts FROM runtime_forms').fetchone()[0]
        polls = len(checked)
        assert run(store, tools, Provider([]), binding, resume=True,
            counts={'annotation': 1, 'job_launch': len(actions)}) == summary
        assert len(checked) == polls
        assert store.db.execute('SELECT facts FROM runtime_forms').fetchone()[0] == saved
        assert store.count('assessment') == store.count('annotation') == 0
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
