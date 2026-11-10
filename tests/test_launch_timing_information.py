"""Timing discovered during launch remains monitoring information.

Actual tiny native job, explicit fixture decisions/continuation and units. No
biological claim, configured-model verification or new stopping rule is implied.
"""
import json

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.runtime import Journal
from test_resource_monitoring_separation import sample
from test_runtime import obj, setup


def journal_check(store, checked, index, *, episode='launch'):
    Journal(store, 'run_fixture').save('runtime_actions', {'episode_id': episode,
        'decision_index': index, 'action': json.dumps({'kind': 'tool', 'tool': 'homology.check_handoff'}),
        'result': json.dumps({'status': 'completed', 'result': {
            'checked_at_unix_seconds': checked['checked_at_unix_seconds'],
            'sample': {key: value for key, value in checked.items() if key != 'checked_at_unix_seconds'}}}),
        'credit': None})


def test_selected_checks_earn_information_once_without_fabricating_samples_or_role_ownership(tmp_path):
    store, _ = setup(tmp_path)
    projector = MonitoringInformationCredit(information_unit=7, include_handoff_checks=True)
    pending = sample(0, None, state='returned')
    pending.update(outcome='succeeded', native_returncode=0, duration_measure='systemd_service_wall_seconds')
    for key in ('sample_ref', 'sampled_at_unix_seconds'):
        pending.pop(key)
    pending['checked_at_unix_seconds'] = 100
    completed = {**pending, 'checked_at_unix_seconds': 101, 'elapsed_seconds': 5}
    assignment = {'job_ref': pending['job_ref'], 'prior_checked_statuses': [pending]}
    journal_check(store, completed, 0)
    journal_check(store, {**completed, 'checked_at_unix_seconds': 102}, 1)
    for role in ('job_launch', 'job_monitor', 'job_results'):
        assert projector(store, role=role, assignment=assignment,
            episode_id='launch', run_id='run_fixture') == 7
    findings = projector.findings(store, assignment=assignment, episode_id='launch', run_id='run_fixture')
    finding, = findings
    assert finding['new_completed_timing'] is True
    assert finding['new_state'] is finding['new_outcome'] is False
    assert finding['sample']['observation_kind'] == 'handoff_check'
    assert finding['sample']['checked_at_unix_seconds'] == 101
    assert finding['sample']['sample_ref'] is finding['sample']['sampled_at_unix_seconds'] is None
    assert finding['new_output_states'] == finding['new_timing_overruns'] == []
    validate_form({'information': findings},
        obj({'information': projector.information_report_source()['report_schema']}), lambda *_: True)
    # A later child inherits the actually received result and cannot rediscover
    # it simply because it has another episode identity or role.
    journal_check(store, {**completed, 'checked_at_unix_seconds': 103}, 0, episode='later')
    assert projector(store, role='job_results', assignment={**assignment,
        'prior_checked_statuses': [completed]}, episode_id='later', run_id='run_fixture') == 0
    assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='samples'").fetchone()[0] == 0
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    store.db.close()
