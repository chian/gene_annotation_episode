"""Engineering reconstruction-port controls, not scientific reopening evidence.

Real entry functions, commission validation, saved settings equality, SQLite
reads and context cleanup are exercised. Lightweight Store/assignment/resolver
ports are controlled. An explicit check-port exception ends the open path before
any provider, native worker or episode is constructed.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a101 import independent_execution as subject
from gene_annotation_episode.episodic_workflow.root.a101.method_loop import EpisodeGoal
from gene_annotation_episode.episodic_workflow.root.a101.method_loop.communication import ReportContract
from gene_annotation_episode.episodic_workflow.root.a101.method_loop.identities import EpisodeRef


class BoundaryReached(Exception):
    """Explicit controlled end of this reconstruction-port test."""


@pytest.fixture
def reconstruction(tmp_path, monkeypatch):
    workspace = tmp_path / 'engineering-state'
    directory = tmp_path / 'engineering-run'
    workspace.mkdir()
    directory.mkdir()
    run_id = 'engineering-standard-options'
    problem = {'engineering_fixture': 'saved-settings-only'}
    settings = {'directory': str(directory), 'problem': problem,
                'tool_configuration': {'engineering_fixture': True}}
    with sqlite3.connect(workspace / 'state.sqlite3') as database:
        database.execute('CREATE TABLE runtime_runs(run_id TEXT PRIMARY KEY, settings TEXT)')
        database.execute('INSERT INTO runtime_runs VALUES (?,?)', (run_id, json.dumps(settings)))
    (directory / 'run.json').write_text(json.dumps({'run_id': run_id, **settings}))
    events = []
    stores = []

    class SavedSettingsStore:
        def __init__(self, path):
            assert Path(path) == workspace
            self.path = Path(path)
            self.db = sqlite3.connect(self.path / 'state.sqlite3')
            self.closed = False
            stores.append(self)
        def problem(self):
            return deepcopy(problem)
        def __enter__(self):
            events.append('store-enter')
            return self
        def __exit__(self, kind, error, traceback):
            events.append('store-exit')
            self.db.close()
            self.closed = True

    monkeypatch.setattr(subject, 'Store', SavedSettingsStore)
    options = {'project_credit': object(), 'binding_definitions': {'engineering_fixture': True}}
    def resolve(store, supplied_directory, supplied_settings):
        assert store is stores[-1] and not store.closed
        assert supplied_directory == directory and supplied_settings == settings
        events.append('resolve')
        return options
    monkeypatch.setattr(subject, '_standard_bindings', resolve)
    parent = EpisodeGoal.root(objective='Inspect a reconstruction connection', result_contract={})
    schema = {'type': 'object', 'properties': {'connected': {'type': 'boolean'}},
              'required': ['connected'], 'additionalProperties': False}
    child = EpisodeGoal.child(parent, objective='Check saved reconstruction operands', result_contract=schema)
    contract = ReportContract('Report the engineering connection state', {'schema': schema},
                              {'connected': 'Whether the selected reconstruction connection was reached'})
    parent_path = [['sequence_homology_evidence', 'parent']]
    child_path = parent_path + [['sequence_homology_evidence', 'child_0']]
    binding = {'factory_module': subject.FACTORY_MODULE, 'factory_name': subject.FACTORY_NAME,
               'arguments': {'version': subject.VERSION, 'workspace': str(workspace),
                             'run_directory': str(directory), 'kind': 'standard_default',
                             'tool_configuration': settings['tool_configuration'], 'caller_binding_pins': {}},
               'settings_sha256': subject.content_digest(settings)}
    spec = {'version': 'episode_commission_v1', 'handle': 'engineering-child',
            'operation_key': 'engineering-operation', 'run_id': run_id,
            'parent': {'episode_id': EpisodeRef(run_id, parent_path).episode_id,
                       'goal_id': parent.goal_id, 'path': parent_path},
            'child': {'episode_id': EpisodeRef(run_id, child_path).episode_id,
                      'role': 'sequence_homology_evidence', 'key': 'child_0', 'path': child_path,
                      'request': {'goal': child.as_record(), 'message': {}, 'report_contract': contract.as_record()},
                      'scope': {'engineering_fixture': True}},
            'input_versions': [], 'runtime_binding': binding, 'constraints': {},
            'resource_selection': None, 'expectation_snapshot_refs': []}
    assert subject.validate_commission(spec) == spec
    def assignment(store, supplied):
        assert store is stores[-1] and supplied == spec
        events.append('assignment')
        return parent, supplied['child']['scope']
    monkeypatch.setattr(subject, '_check_assignment', assignment)
    return SimpleNamespace(workspace=workspace, directory=directory, settings=settings,
                           options=options, spec=spec, events=events, stores=stores)


def check_port(case, error=None):
    def check(options, settings):
        assert options is case.options and settings == case.settings
        case.events.append('check')
        if error is not None:
            raise error
    return check


async def enter_only(spec):
    async with subject.open_commission(spec):
        raise AssertionError('controlled binding-check boundary must end this test before providers')


def test_make_runtime_binding_resolves_original_options_once(reconstruction, monkeypatch):
    case = reconstruction
    monkeypatch.setattr(subject, '_check_bindings', check_port(case))
    before = deepcopy(case.settings)
    binding = subject.make_runtime_binding(case.workspace, case.directory)
    assert binding == case.spec['runtime_binding']
    assert case.events == ['store-enter', 'resolve', 'check', 'store-exit']
    assert case.settings == before and all(store.closed for store in case.stores)


def test_open_commission_resolves_before_binding_check(reconstruction, monkeypatch):
    case = reconstruction
    failure = BoundaryReached('original binding comparison reached')
    monkeypatch.setattr(subject, '_check_bindings', check_port(case, failure))
    with pytest.raises(BoundaryReached) as caught:
        asyncio.run(enter_only(case.spec))
    assert caught.value is failure
    assert case.events == ['store-enter', 'assignment', 'resolve', 'check', 'store-exit']
    assert all(store.closed for store in case.stores)


def test_open_commission_preserves_resolver_failure_and_cleanup(reconstruction, monkeypatch):
    case = reconstruction
    failure = BoundaryReached('controlled resolver failure')
    def reject(store, directory, settings):
        assert store is case.stores[-1] and directory == case.directory and settings == case.settings
        case.events.append('resolve-rejected')
        raise failure
    monkeypatch.setattr(subject, '_standard_bindings', reject)
    monkeypatch.setattr(subject, '_check_bindings', check_port(case))
    with pytest.raises(BoundaryReached) as caught:
        asyncio.run(enter_only(case.spec))
    assert caught.value is failure
    assert case.events == ['store-enter', 'assignment', 'resolve-rejected', 'store-exit']
    assert all(store.closed for store in case.stores)


def test_open_commission_retains_binding_rejection(reconstruction, monkeypatch):
    case = reconstruction
    failure = subject._failure('identity_conflict', 'controlled-saved-binding')
    monkeypatch.setattr(subject, '_check_bindings', check_port(case, failure))
    with pytest.raises(subject.DurableExecutionError) as caught:
        asyncio.run(enter_only(case.spec))
    assert caught.value is failure
    assert case.events == ['store-enter', 'assignment', 'resolve', 'check', 'store-exit']
    assert all(store.closed for store in case.stores)


def test_open_commission_rejects_changed_settings_before_resolution(reconstruction, monkeypatch):
    case = reconstruction
    spec = deepcopy(case.spec)
    spec['runtime_binding']['settings_sha256'] = 'b' * 64
    monkeypatch.setattr(subject, '_check_bindings', check_port(case))
    with pytest.raises(subject.DurableExecutionError) as caught:
        asyncio.run(enter_only(spec))
    assert caught.value.failure['code'] == 'identity_conflict'
    assert case.events == ['store-enter', 'store-exit']
    assert all(store.closed for store in case.stores)


def test_make_runtime_binding_propagates_resolver_failure(reconstruction, monkeypatch):
    case = reconstruction
    failure = BoundaryReached('controlled resolver failure')
    def reject(store, directory, settings):
        assert store is case.stores[-1] and directory == case.directory and settings == case.settings
        case.events.append('resolve-rejected')
        raise failure
    monkeypatch.setattr(subject, '_standard_bindings', reject)
    monkeypatch.setattr(subject, '_check_bindings', check_port(case))
    with pytest.raises(BoundaryReached) as caught:
        subject.make_runtime_binding(case.workspace, case.directory)
    assert caught.value is failure
    assert case.events == ['store-enter', 'resolve-rejected', 'store-exit']
    assert all(store.closed for store in case.stores)
