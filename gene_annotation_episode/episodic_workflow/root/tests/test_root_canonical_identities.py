"""Canonical root identities and immutable saved receiving contexts.

These are local persistence/type-boundary tests, not scientific scoring checks.
"""
from contextlib import closing
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root import episode_return_records
from gene_annotation_episode.episodic_workflow.root import scientific_process_records
from gene_annotation_episode.episodic_workflow.root.method_loop import identities
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext


def test_receipt_reader_uses_iterator_identity_class():
    assert episode_return_records.EpisodeRef is identities.EpisodeRef
    ref = episode_return_records.EpisodeRef('identity-run', (('annotation', 'root'),))
    assert identities.EpisodeRef.from_record(ref.as_record()) == ref
    assert type(ref) is identities.EpisodeRef


def test_process_records_use_canonical_structural_path_normalizer():
    assert scientific_process_records.normalize_structural_path is identities.normalize_structural_path


def test_saved_context_restores_exact_type_and_detaches_nested_assignments():
    path = (('annotation', 'root'),)
    ref = identities.EpisodeRef('identity-run', path)
    request = {'message': {'scope': {'subject': 'same-subject'},
                           'episode_assignment': {'nested': {'values': [1, 2]}}}}
    original_request = json.loads(json.dumps(request))
    with closing(sqlite3.connect(':memory:')) as db:
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE runtime_episodes '
                   '(run_id TEXT, episode_id TEXT, path TEXT, request TEXT)')
        db.execute('INSERT INTO runtime_episodes VALUES (?,?,?,?)',
                   (ref.run_id, ref.episode_id, json.dumps(path), json.dumps(request)))
        reader = episode_return_records.EpisodeReturnRecords(
            SimpleNamespace(db=db), ref.run_id, failure_prefix='identity_test_')
        context = reader.context(ref.episode_id)
        assert type(context) is BindingContext
        assert context.episode_id == ref.episode_id
        assert context.path == path
        assert context.as_record()['request'] == original_request
        request['message']['episode_assignment']['nested']['values'].append(3)
        assert context.assignment['nested']['values'] == (1, 2)
        with pytest.raises(TypeError):
            context.assignment['nested']['values'][0] = 9
        with pytest.raises(TypeError):
            context.request['message']['scope']['subject'] = 'changed'
        detached = context.as_record()
        detached['assignment']['nested']['values'].append(8)
        detached['request']['message']['scope']['subject'] = 'changed'
        assert context.assignment['nested']['values'] == (1, 2)
        assert context.as_record()['request'] == original_request
        restored = reader.context(ref.episode_id)
        assert type(restored) is type(context)
        assert restored == context
        assert reader.authenticate(restored) is restored
        db.execute('UPDATE runtime_episodes SET request=?',
                   (json.dumps({'message': {'scope': {'subject': 'changed'},
                                           'episode_assignment': {}}}),))
        with pytest.raises(ValueError, match='identity_test_original_context_conflict'):
            reader.authenticate(context)
