"""Actual default Root supplier construction, independently of caller ports.

No tool is executed. A constructor failure remains an ordinary failed test with
its actual source location; no substitute registry/client/configuration masks it.
"""
from gene_annotation_episode.state import Store
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.root.tool_configuration import build_tools
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.tests.public_caller_checks import create_workspace


def test_actual_default_root_registry_constructs_without_dispatch(tmp_path, monkeypatch):
    workspace = tmp_path / 'store'
    create_workspace(workspace)
    run = tmp_path / 'caller-run'
    run.mkdir()
    # This real documented configuration path keeps the capacity database in
    # the test's own temporary directory. No capacity reservation is requested.
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'resources'))
    configuration = {'public': {'ncbi_email': None},
        'local_jobs': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}
    with Store(workspace) as store:
        tools = build_tools(store, configuration, run_directory=run)
        assert type(tools) is ToolRegistry
        assert type(tools.clients) is PublicClients and tools.store is store
        assert tools.clients.work_dir == run / 'public-client-work'
        assert tools.reconstruction_configuration == configuration
        assert tools.native_statistics is None
        assert tools.remote_searches.store is store and tools.remote_searches.clients is tools.clients
        assert store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
        assert not (run / 'run.json').exists()
