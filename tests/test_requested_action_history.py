"""Requested own outcomes remain available without fresh work or new credit."""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_work_report import requested_action_history


@pytest.fixture
def journal():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action,result)')
    workflow = SimpleNamespace(store=SimpleNamespace(db=db), run_id='this-run')
    source = SimpleNamespace(episode_id='this-actor')

    def add(index, records, *, actor='this-actor', run='this-run', tool='episode.history'):
        db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)', (run, actor, index,
            json.dumps({'tool': tool}), json.dumps({'status': 'completed',
                'result': {'view': 'records', 'records': records}})))

    yield workflow, source, add
    db.close()


def record(index, text):
    return {'decision_index': index, 'kind': 'tool', 'tool': 'exec_command',
        'selection': {'arguments': {'cmd': 'original recorded command'}},
        'status': 'completed', 'outcome': {'result': {'stdout': text}},
        'controller_observation': {'step': {'marginal_credit': 0}}}


def test_successive_reads_keep_both_selected_outcomes(journal):
    workflow, source, add = journal
    first, second = record(36, 'runner contract'), record(37, 'resource contract')
    originals = deepcopy([first, second])
    add(38, [first])
    add(39, [second])
    retained = requested_action_history(workflow, source, before=40)
    assert [row['record']['decision_index'] for row in retained] == [36, 37]
    assert [row['record']['outcome'] for row in retained] == [row['outcome'] for row in originals]
    assert [row['last_requested_at_decision'] for row in retained] == [38, 39]
    assert [first, second] == originals
    assert workflow.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 2


def test_only_completed_own_requested_history_before_current_decision_is_retained(journal):
    workflow, source, add = journal
    add(1, [record(0, 'owned')])
    add(2, [record(1, 'other actor')], actor='other-actor')
    add(3, [record(2, 'other run')], run='other-run')
    add(4, [record(3, 'unrequested outcome')], tool='exec_command')
    add(5, [record(4, 'future read')])
    retained = requested_action_history(workflow, source, before=5)
    assert len(retained) == 1
    assert retained[0]['record']['outcome']['result']['stdout'] == 'owned'


def test_repeated_reads_replace_one_history_view_and_nested_reads_keep_leaves(journal):
    workflow, source, add = journal
    add(2, [record(0, 'earlier status')])
    nested = {'decision_index': 2, 'tool': 'episode.history', 'outcome': {
        'result': {'view': 'records', 'records': [record(0, 'latest received status')]}}}
    add(3, [nested, record(1, 'other requested result')])
    retained = requested_action_history(workflow, source, before=4)
    assert [row['record']['decision_index'] for row in retained] == [0, 1]
    assert retained[0]['record']['outcome']['result']['stdout'] == 'latest received status'
    assert all(row['last_requested_at_decision'] == 3 for row in retained)


def test_empty_first_decision_has_no_invented_memory(journal):
    workflow, source, add = journal
    assert requested_action_history(workflow, source, before=0) == []
