"""Genuine Store/Journal intent and immutable publication; no factory execution."""
from datetime import datetime, timezone
import json

import pytest

from gene_annotation_episode.episodic_workflow.root import application_execution_binding as binding
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import (
    DurableExecutionError, canonical, content_digest)
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tests.model_transport_support import requested_descriptor

RUN = 'controlled-publication-identity'


def initialize(directory):
    workspace, run = directory / 'store', directory / 'run'
    run.mkdir()
    with Store(workspace) as store:
        store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        journal = Journal(store, RUN)
        settings = {'directory': str(run.resolve()), 'problem': store.problem(),
                    'purpose': 'execution publication fixture; no scientific work'}
        stamp = datetime.now(timezone.utc).isoformat()
        with store.transaction():
            journal.save('runtime_runs', {'settings': canonical(settings), 'state': 'active',
                'summary': None, 'started_at': stamp, 'updated_at': stamp})
    return workspace, run, settings


def saved_settings(store):
    return json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (RUN,)).fetchone()[0])


def saved_binding(store):
    row = store.db.execute('SELECT * FROM runtime_execution_bindings WHERE run_id=?', (RUN,)).fetchone()
    return dict(row)


def assert_no_work(store):
    for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_episodes'):
        assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


def test_no_execution_request_preserves_early_return_and_original_settings(tmp_path):
    workspace, run, settings = initialize(tmp_path)
    with Store(workspace) as store:
        result = binding.bind_episode_execution(store, run, settings=settings)
        assert type(result) is binding.ExecutionBindingResult
        assert result.settings == settings and result.runtime_binding is None
        assert saved_settings(store) == settings
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='runtime_execution_bindings'").fetchone() is None
        assert_no_work(store)
    assert not (run / 'run.json').exists() and not (run / binding.BINDING_FILE).exists()


def test_explicit_binding_publication_is_exact_and_reopens_without_execution(tmp_path):
    workspace, run, settings = initialize(tmp_path)
    descriptor = requested_descriptor(settings)
    with Store(workspace) as store:
        first = binding.bind_episode_execution(store, run, settings=settings, requested_binding=descriptor)
        assert first.runtime_binding == descriptor
        assert first.settings['episode_execution'] == {'version': binding.VERSION, 'binding_file': binding.BINDING_FILE}
        state = saved_binding(store)
        assert json.loads(state['selection']) == {'mode': 'requested', 'runtime_binding': descriptor}
        assert json.loads(state['runtime_binding']) == descriptor
        assert state['settings_sha256'] == content_digest(first.settings)
        assert_no_work(store)
    before = {name: (run / name).read_bytes() for name in ('run.json', binding.BINDING_FILE)}
    assert before[binding.BINDING_FILE] == (canonical(descriptor) + '\n').encode()
    assert json.loads(before['run.json']) == {'run_id': RUN, **first.settings}
    with Store(workspace) as store:
        repeated = binding.bind_episode_execution(store, run, settings=saved_settings(store),
                                                   requested_binding=descriptor, resume=True)
        assert repeated == first and saved_binding(store) == state
        assert_no_work(store)
    assert {name: (run / name).read_bytes() for name in before} == before


@pytest.mark.parametrize('changed', ['binding', 'settings', 'tool_configuration'])
def test_reopened_identity_conflicts_preserve_saved_binding(tmp_path, changed):
    workspace, run, settings = initialize(tmp_path)
    descriptor = requested_descriptor(settings)
    with Store(workspace) as store:
        binding.bind_episode_execution(store, run, settings=settings, requested_binding=descriptor,
                                       tool_configuration={'purpose': 'controlled fixture'})
        original_state = saved_binding(store)
        original_settings = saved_settings(store)
    before = {name: (run / name).read_bytes() for name in ('run.json', binding.BINDING_FILE)}
    supplied, requested, config = dict(original_settings), descriptor, None
    if changed == 'binding':
        requested = {**descriptor, 'arguments': {'purpose': 'different declared request'}}
    elif changed == 'settings':
        supplied['purpose'] = 'changed without authority'
    else:
        config = {'purpose': 'different configuration'}
    with Store(workspace) as store:
        with pytest.raises(DurableExecutionError) as caught:
            binding.bind_episode_execution(store, run, settings=supplied,
                requested_binding=requested, tool_configuration=config, resume=True)
        assert type(caught.value) is DurableExecutionError
        assert caught.value.failure['code'] == 'identity_conflict'
        assert saved_binding(store) == original_state and saved_settings(store) == original_settings
        assert_no_work(store)
    assert {name: (run / name).read_bytes() for name in before} == before


@pytest.mark.parametrize('failure_point', ['run.json', binding.BINDING_FILE], ids=['after-intent-commit', 'after-binding-commit'])
def test_original_publication_recovers_after_declared_io_failure(tmp_path, monkeypatch, failure_point):
    workspace, run, settings = initialize(tmp_path)
    descriptor = requested_descriptor(settings)
    publish = binding._publish
    calls = []
    def fail_selected(path, value, *, immutable=False):
        calls.append((path.name, immutable))
        if path.name == failure_point:
            raise OSError('controlled publication interruption')
        return publish(path, value, immutable=immutable)
    monkeypatch.setattr(binding, '_publish', fail_selected)
    with Store(workspace) as store:
        with pytest.raises(DurableExecutionError) as caught:
            binding.bind_episode_execution(store, run, settings=settings, requested_binding=descriptor)
        assert caught.value.failure['code'] == 'storage_failure'
        assert isinstance(caught.value.__cause__, OSError)
        committed_settings = saved_settings(store)
        committed = saved_binding(store)
        assert committed_settings['episode_execution'] == {'version': binding.VERSION, 'binding_file': binding.BINDING_FILE}
        assert json.loads(committed['selection']) == {'mode': 'requested', 'runtime_binding': descriptor}
        assert (committed['runtime_binding'] is None) is (failure_point == 'run.json')
        assert_no_work(store)
    assert calls[-1][0] == failure_point
    assert not (run / binding.BINDING_FILE).exists()
    assert (run / 'run.json').exists() is (failure_point != 'run.json')
    monkeypatch.setattr(binding, '_publish', publish)
    with Store(workspace) as store:
        recovered = binding.bind_episode_execution(store, run, settings=saved_settings(store),
                                                     requested_binding=descriptor, resume=True)
        assert recovered.settings == committed_settings and recovered.runtime_binding == descriptor
        assert json.loads(saved_binding(store)['runtime_binding']) == descriptor
        assert_no_work(store)
    assert json.loads((run / 'run.json').read_text()) == {'run_id': RUN, **committed_settings}
    assert (run / binding.BINDING_FILE).read_text() == canonical(descriptor) + '\n'
    assert not list(run.glob('.episode-execution-binding.json-*'))
    assert not list(run.glob('.run.json-*'))


def test_existing_divergent_descriptor_is_not_overwritten(tmp_path):
    workspace, run, settings = initialize(tmp_path)
    descriptor = requested_descriptor(settings)
    target = run / binding.BINDING_FILE
    original = (canonical({**descriptor, 'arguments': {'purpose': 'preexisting conflicting file'}}) + '\n').encode()
    target.write_bytes(original)
    with Store(workspace) as store:
        with pytest.raises(DurableExecutionError) as caught:
            binding.bind_episode_execution(store, run, settings=settings, requested_binding=descriptor)
        assert caught.value.failure['code'] == 'identity_conflict'
        assert saved_settings(store) == settings
        assert_no_work(store)
    assert target.read_bytes() == original and not (run / 'run.json').exists()
