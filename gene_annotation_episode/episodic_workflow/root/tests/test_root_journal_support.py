"""Actual Store-backed Journal persistence; no controller or task execution."""
import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal, WorkflowError


def test_journal_updates_exact_run_record_and_reopens_store(tmp_path):
    directory = tmp_path / 'journal-store'
    with Store(directory) as store:
        first, other = Journal(store, 'first'), Journal(store, 'other')
        first.save('runtime_forms', {'episode_id': 'episode', 'facts': '{}', 'form': '{"value":1}'})
        other.save('runtime_forms', {'episode_id': 'episode', 'facts': '{}', 'form': '{"value":9}'})
        first.save('runtime_forms', {'episode_id': 'episode', 'facts': '{}', 'form': '{"value":2}'})
        assert json.loads(first.row('runtime_forms', 'episode')['form']) == {'value': 2}
        assert json.loads(other.row('runtime_forms', 'episode')['form']) == {'value': 9}
    with Store(directory) as reopened:
        assert json.loads(Journal(reopened, 'first').row('runtime_forms', 'episode')['form']) == {'value': 2}


def test_journal_writes_share_authoritative_store_rollback(tmp_path):
    with Store(tmp_path / 'journal-store') as store:
        journal = Journal(store, 'run')
        with pytest.raises(WorkflowError, match='controlled interruption'):
            with store.transaction():
                journal.save('runtime_forms', {'episode_id': 'episode', 'facts': '{}', 'form': '{}'})
                raise WorkflowError('controlled interruption')
        assert journal.row('runtime_forms', 'episode') is None
        assert not store.db.in_transaction
