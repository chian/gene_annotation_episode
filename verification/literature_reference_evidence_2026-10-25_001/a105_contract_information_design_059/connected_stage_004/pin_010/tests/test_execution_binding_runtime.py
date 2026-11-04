"""Configured entrypoint publication before provider entry, without live work.

These checks use the real application binding and reconstruction factory. The
owned connection is interrupted at __aenter__; no model or native job runs.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from method_loop.durable import DurableExecutionError, content_digest
from gene_annotation_episode import application_execution_binding as application
from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.default_scientific_binding import VERSION as DEFAULT_VERSION
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_runtime import ScriptedProvider


MARKER = {'version': 'durable_episode_application_v1',
          'binding_file': 'episode-execution-binding.json'}


class ProviderEntryReached(Exception):
    """Fixture interruption before ModelConnection can start transport."""


class RootBuildReached(Exception):
    """Fixture interruption before a legacy root is created."""


def saved_run(store):
    rows = store.db.execute('SELECT * FROM runtime_runs').fetchall()
    assert len(rows) == 1
    return dict(rows[0]), json.loads(rows[0]['settings'])


def assert_no_work(store, run_id):
    for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations',
                  'runtime_model_calls'):
        assert store.db.execute(f'SELECT COUNT(*) FROM {table} WHERE run_id=?',
                                (run_id,)).fetchone()[0] == 0
    for table in ('tool_operations', 'reasoning_commits'):
        assert store.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def assert_no_execution_binding(store, directory):
    assert not (directory/application.BINDING_FILE).exists()
    assert store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                            "AND name='runtime_execution_bindings'").fetchone() is None


def unsupported_controller(path, initial_credit):
    pytest.fail('entrypoint reconstruction must not execute the custom controller')


def test_owned_configured_entrypoint_commits_exact_binding_before_provider_entry(tmp_path, monkeypatch):
    directory = tmp_path/'run'
    configuration = {'public': {'transport_timeout_seconds': 73, 'ncbi_email': None},
        'local_tools': {'cmsearch_cpu': 2}, 'caller_metadata': {'selection': ['actual']}}
    original_configuration = deepcopy(configuration)
    entered = []
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        tools = build_tools(store, configuration)
        configuration['caller_metadata']['selection'].append('later')

        async def before_transport(connection):
            entered.append(connection)
            # A separate connection observes committed authority, not merely
            # uncommitted state on run_workflow's Store connection.
            with Store(store.path) as reopened:
                row, settings = saved_run(reopened)
                assert_no_work(reopened, row['run_id'])
                saved = reopened.db.execute('SELECT * FROM runtime_execution_bindings '
                    'WHERE run_id=?', (row['run_id'],)).fetchone()
                assert settings['episode_execution'] == MARKER
                assert settings['tool_configuration'] == original_configuration
                assert settings['binding_definitions']['credit']['default_entrypoint'] == DEFAULT_VERSION
                assert settings['episode_bindings']
                assert settings['initial_tool_resources'] == tools.resource_binding()
                manifest = json.loads((directory/'run.json').read_text())
                assert manifest == {'run_id': row['run_id'], **settings}
                binding = json.loads((directory/application.BINDING_FILE).read_text())
                assert json.loads(saved['runtime_binding']) == binding
                assert saved['settings_sha256'] == binding['settings_sha256'] == content_digest(settings)
                assert 'runtime_binding' not in settings
                assert binding['arguments'] == {'version': reconstruction.VERSION,
                    'workspace': str(store.path), 'run_directory': str(directory),
                    'kind': 'standard_default', 'tool_configuration': original_configuration,
                    'caller_binding_pins': {}}
                assert binding == reconstruction.make_runtime_binding(reopened, directory,
                    kind='standard_default', tool_configuration=original_configuration)
                assert row['state'] == 'created' and row['summary'] is None
            assert connection.config == settings['models']
            assert connection.directory.parent == directory/'providers'
            assert connection.workers == {} and connection.sessions == {}
            assert connection.session_index == 0
            raise ProviderEntryReached

        monkeypatch.setattr(ModelConnection, '__aenter__', before_transport)
        with pytest.raises(ProviderEntryReached):
            asyncio.run(run_workflow(store, tools, run_dir=directory))
        assert len(entered) == 1
        row, _ = saved_run(store)
        assert_no_work(store, row['run_id'])


def test_owned_configured_entrypoint_rejects_custom_controller_before_provider_entry(tmp_path, monkeypatch):
    directory = tmp_path/'run'
    entered = []

    async def forbidden_provider_entry(connection):
        entered.append(connection)
        pytest.fail('unavailable reconstruction must fail before provider entry')

    monkeypatch.setattr(ModelConnection, '__aenter__', forbidden_provider_entry)
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        with pytest.raises(DurableExecutionError) as error:
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                controller_factory=unsupported_controller))
        row, settings = saved_run(store)
        assert error.value.failure == {'code': 'unavailable_binding',
            'affected_refs': [settings['bindings']['controller']],
            'diagnostic_ref': None, 'partial_record_refs': []}
        assert settings['controller'] is None
        assert settings['bindings']['controller'] == __name__+'.unsupported_controller'
        assert settings['binding_definitions']['credit']['default_entrypoint'] == DEFAULT_VERSION
        assert entered == []
        assert_no_work(store, row['run_id'])
        assert not (directory/application.BINDING_FILE).exists()


def test_owned_configured_resume_keeps_markerless_legacy_run_unchanged(tmp_path, monkeypatch):
    directory = tmp_path/'run'
    configuration = {'public': {'transport_timeout_seconds': 73},
                     'local_tools': {'cmsearch_cpu': 2}}
    scripted = ScriptedProvider([])
    built = []
    entered = []
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        tools = build_tools(store, configuration)

        def before_root(workflow, name, key, *args, **kwargs):
            built.append((name, key))
            assert workflow.execution_binding is None
            raise RootBuildReached

        with monkeypatch.context() as setup_patch:
            setup_patch.setattr(Workflow, 'build', before_root)
            with pytest.raises(RootBuildReached):
                asyncio.run(run_workflow(store, tools, provider=scripted, run_dir=directory))
        assert built == [('annotation', 'root')]
        assert scripted.contexts == []
        original_row, original_settings = saved_run(store)
        original_manifest = (directory/'run.json').read_bytes()
        assert 'episode_execution' not in original_settings
        assert_no_execution_binding(store, directory)
        assert_no_work(store, original_row['run_id'])

        async def before_transport(connection):
            entered.append(connection)
            with Store(store.path) as reopened:
                row, settings = saved_run(reopened)
                assert row == original_row and settings == original_settings
                assert 'episode_execution' not in settings
                assert_no_execution_binding(reopened, directory)
                assert_no_work(reopened, row['run_id'])
            assert (directory/'run.json').read_bytes() == original_manifest
            assert connection.config == original_settings['models']
            assert connection.workers == {} and connection.session_index == 0
            raise ProviderEntryReached

        monkeypatch.setattr(ModelConnection, '__aenter__', before_transport)
        with pytest.raises(ProviderEntryReached):
            asyncio.run(run_workflow(store, tools, run_dir=directory, resume=True))
        assert len(entered) == 1
        assert saved_run(store) == (original_row, original_settings)
        assert_no_execution_binding(store, directory)
        assert_no_work(store, original_row['run_id'])
