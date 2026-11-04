"""Timing survives publication/recovery without inventing work or observations."""
import asyncio
import json

import pytest

from gene_annotation_episode import execution_timing as timing
from gene_annotation_episode.runtime import Journal
from gene_annotation_episode.state import Store


@pytest.fixture
def clock(monkeypatch):
    state = {'ns': 10_000_000_000, 'identity': {'pid': 123, 'start_ticks': '77', 'boot_id': 'a'}}
    monkeypatch.setattr(timing.time, 'monotonic_ns', lambda: state['ns'])
    monkeypatch.setattr(timing, '_process_identity', lambda pid=None: state['identity'])
    return state


def selected(journal, index):
    journal.save('runtime_actions', {'episode_id': 'episode', 'decision_index': index,
        'action': json.dumps({'kind': 'tool', 'index': index}), 'result': None, 'credit': None})


def test_outcome_publication_preserves_actual_time_without_creating_observations(tmp_path, clock):
    with Store(tmp_path) as store:
        journal = Journal(store, 'run')
        selected(journal, 0)
        with journal.measure('runtime_actions', 'episode', 0):
            clock['ns'] += 2_500_000_000
            live = journal.elapsed_view('episode')['selected_work']
            assert live['latest']['timing']['live_interval_elapsed_seconds'] == 2.5
            assert live['unmeasured_ended_intervals'] == 0
        # A returned operational failure still used time; it earns no fabricated
        # credit or completed-action observation just because its timer returned.
        journal.save('runtime_actions', {'episode_id': 'episode', 'decision_index': 0,
            'action': json.dumps({'kind': 'tool', 'index': 0}),
            'result': json.dumps({'status': 'failed'}), 'credit': None})
        view = journal.elapsed_view('episode')['selected_work']
        assert view['measured_elapsed_seconds'] == 2.5
        assert view['latest']['timing']['state'] == 'returned'
        assert journal.row('runtime_actions', 'episode', 0)['credit'] is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('exception', [ValueError('bad input'), KeyboardInterrupt(), asyncio.CancelledError()])
def test_raised_and_interrupted_work_retains_measured_duration(tmp_path, clock, exception):
    with Store(tmp_path) as store:
        journal = Journal(store, 'run')
        selected(journal, 0)
        with pytest.raises(type(exception)):
            with journal.measure('runtime_actions', 'episode', 0):
                clock['ns'] += 1_000_000_000
                raise exception
        view = journal.elapsed_view('episode')['selected_work']
        assert view['measured_elapsed_seconds'] == 1
        expected = 'raised' if isinstance(exception, ValueError) else 'interrupted'
        assert view['latest']['timing']['state'] == expected
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def unfinished(journal, index, clock):
    selected(journal, index)
    record = {'version': timing.VERSION, 'measured_elapsed_seconds': 3,
        'unmeasured_ended_intervals': 0, 'intervals': [
            {'state': 'returned', 'elapsed_seconds': 3},
            {'state': 'running', 'owner': dict(clock['identity']),
             'started_monotonic_ns': clock['ns'], 'started_at': 'old',
             'ended_at': None, 'elapsed_seconds': None, 'exception_type': None}]}
    journal.save('runtime_actions', {'episode_id': 'episode', 'decision_index': index,
        'action': json.dumps({'kind': 'tool', 'index': index}), 'timing': json.dumps(record)})


def test_dead_interval_is_unknown_in_both_latest_and_aggregate_read_without_writes(tmp_path, clock):
    with Store(tmp_path) as store:
        journal = Journal(store, 'run')
        unfinished(journal, 0, clock)
        before = journal.row('runtime_actions', 'episode', 0)
        clock['ns'] += 1_000_000_000_000
        # Same PID with a new start time is a different process incarnation.
        clock['identity'] = {**clock['identity'], 'start_ticks': '88'}
        view = journal.elapsed_view('episode')['selected_work']
        assert view['measured_elapsed_seconds'] == 3
        assert view['unmeasured_ended_intervals'] == 1
        assert view['latest']['timing']['unmeasured_ended_intervals'] == 1
        assert view['latest']['timing']['state'] == 'end_unobserved'
        assert view['latest']['timing']['live_interval_elapsed_seconds'] is None
        assert journal.row('runtime_actions', 'episode', 0) == before


def test_older_dead_interval_is_not_hidden_by_newer_completed_action(tmp_path, clock):
    with Store(tmp_path) as store:
        journal = Journal(store, 'run')
        unfinished(journal, 0, clock)
        clock['identity'] = {**clock['identity'], 'boot_id': 'new-boot'}
        selected(journal, 1)
        with journal.measure('runtime_actions', 'episode', 1):
            clock['ns'] += 4_000_000_000
        view = journal.elapsed_view('episode')['selected_work']
        assert view['measured_elapsed_seconds'] == 7
        assert view['unmeasured_ended_intervals'] == 1
        assert view['latest']['timing']['state'] == 'returned'


def test_resuming_lost_dispatch_excludes_offline_gap_and_keeps_prior_elapsed(tmp_path, clock):
    with Store(tmp_path) as store:
        journal = Journal(store, 'run')
        unfinished(journal, 0, clock)
        clock['ns'] += 1_000_000_000_000
        clock['identity'] = {**clock['identity'], 'start_ticks': '88'}
        with journal.measure('runtime_actions', 'episode', 0):
            clock['ns'] += 2_000_000_000
        view = journal.elapsed_view('episode')['selected_work']
        assert view['measured_elapsed_seconds'] == 5
        assert view['unmeasured_ended_intervals'] == 1
        assert view['latest']['timing']['interval_count'] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
