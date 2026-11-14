"""Focused actual report/action policy ownership and late-provider controls."""
import pytest
from .policy_checks import (actual_private_override, action_observation,
    original, paired, report_observation)


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


@pytest.mark.parametrize('role,scenario', [
    ('annotation', 'ordinary'), ('improvement', 'late-binding'),
    ('improvement', 'late-json-error'), ('scientific_process', 'registered'),
], ids=['annotation-private', 'improvement-late-binding', 'late-form-error', 'registered-scientific'])
def test_original_current_action_policy(tmp_path, role, scenario):
    value = paired(tmp_path, action_observation, role, scenario)
    if scenario == 'late-json-error':
        assert value['events'][-2:] == ['catalog', 'late_json']
        assert value['outcome'][-1] is True
    else:
        choices = value['outcome'][1]['properties']['selection']['anyOf']
        kinds = [item['properties']['kind']['const'] for item in choices]
        assert {'tool', 'reason', 'wait', 'redeliver_report'} <= set(kinds)
        assert ('child' in kinds) is (scenario == 'ordinary')
        if scenario == 'registered':
            children = [item for item in choices if item['properties']['kind']['const'] == 'episode_child']
            assert [item['properties']['role']['const'] for item in children] == ['scientific_process']
            assert ('filled_context', 'scientific_process') in value['events']


@pytest.mark.parametrize('role,scenario', [
    ('scientific_process', 'fresh'), ('scientific_process', 'saved'),
    ('scientific_process', 'received-conflict'), ('scientific_process', 'saved-read-error'),
    ('annotation', 'late-scientific'), ('improvement', 'late-scientific'),
], ids=['registered-fresh', 'registered-saved', 'received-conflict', 'saved-error-first',
        'annotation-late-scientific', 'improvement-late-scientific'])
def test_original_current_report_policy(tmp_path, role, scenario):
    value = paired(tmp_path, report_observation, role, scenario)
    if scenario == 'saved':
        assert value['events'] == ['saved_read', 'saved_refresh']
        assert 'interpretations' not in value['outcome'][1]
    elif scenario == 'saved-read-error':
        assert value['events'] == ['saved_read'] and value['outcome'][-1] is True
    elif scenario == 'received-conflict':
        assert value['outcome'][0:3] == ('raised', 'ValueError', 'received_report_fact_conflict')
    else:
        snapshots = [event[1] for event in value['events'] if isinstance(event, tuple) and event[0] == 'scientific_projection']
        assert len(snapshots) == 1
        assert snapshots[0]['parent_invocation_ref'] == 'supplied original parent invocation'
        assert snapshots[0]['controller_credit'] == 'supplied controller meaning'
        if scenario == 'late-scientific':
            assert value['events'].index('late_scientific_identity') < next(
                i for i, event in enumerate(value['events']) if isinstance(event, tuple) and event[0] == 'scientific_projection')


@pytest.mark.parametrize('kind', ['class', 'instance'])
def test_actual_private_task_preserves_schema_override(tmp_path, kind):
    actual_private_override(tmp_path, kind)
