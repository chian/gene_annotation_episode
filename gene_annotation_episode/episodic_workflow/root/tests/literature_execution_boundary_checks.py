"""Conditional Root Literature commissioning on actual configured bindings.

The real Store, Journal, parent classes, registry and API service constructors
remain active. Tool/client/catalog ports are supplied explicitly; no default
ToolRegistry, provider operation, remote job or biological outcome is claimed.
Request controls stop at the original assignment-preparation/build ports.
"""
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from operational_private_boundary_checks import forbidden, isolated_rows, source_for, HPC_ROLES

ROOT = 'gene_annotation_episode.episodic_workflow.root'
PARENTS = ('published_evidence_assessment',
           'legacy_annotation/published_evidence_assessment',
           'scientific_process/published_evidence_assessment')
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
APP_SERVICE = {'kind': 'api', 'service': 'bvbrc_appservice',
    'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': 'https://app.example.invalid/rpc',
                  'Workspace': 'https://workspace.example.invalid/rpc'},
    'scientific_adapters': []}


class EmptyCatalogPort:
    """Original catalog protocol with no adopted scientific options or tools."""
    def as_record(self):
        return {'boundary_fixture': 'no_scientific_options_or_tool_execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


def parent_path(parent):
    host = ('scientific_process' if parent.startswith('scientific_process/')
            else 'improvement' if parent.startswith('legacy_annotation/') else 'annotation')
    return ((host, 'original-parent'), ('literature', 'original-literature'))


def binding_path(parent, role):
    path = parent_path(parent)
    if role in ('launch_api', 'launch_local', 'launch_hpc'):
        path += (('launch', 'original-launch'),)
    return path + ((role, 'original-child'),)


@contextmanager
def families(directory, *, api=True):
    from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.episodic_workflow.root.execution_binding_catalogue import execution_bindings
    from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.scientific_process.episode import ScientificProcessEpisodes
    store = Store(directory / 'store')
    try:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'literature-execution-boundaries')
        workspace = directory / 'workspace'
        workspace.mkdir()
        resources = {
            'here': {'kind': 'local', 'workspace': str(workspace),
                     'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}},
            'remote': {'kind': 'pbs_ssh', 'workspace': str(workspace),
                       'ssh_argv': ['never-dispatch-this-test-transport'],
                       'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                       'scheduler': {'kind': 'pbs', 'required_resources': []}},
        }
        if api:
            resources['appservice'] = deepcopy(APP_SERVICE)
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden)
        ports = {}
        tools = SimpleNamespace(store=store, clients={}, ordinary_flux_balance_backend=None,
            bind_molecular_sequence_results=lambda value: ports.__setitem__('molecular_results', value),
            bind_execution_owner=lambda value: ports.__setitem__('execution_owner', value))
        owner = ExecutionEpisodes(services, store=store, directory=directory / 'run', run_id=journal.run_id,
            resources=resources, initial_information={}, tool_registry=tools,
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=4, log_roles=['stdout', 'stderr'])
        execution = execution_bindings(owner, parents=PARENTS)
        parents = {home: import_module(ROOT + '.' + home.replace('/', '.') + '.episode').LiteratureEpisode(
            services, rate_population=True, a106_intervention=True) for home in PARENTS}
        scientific = ScientificProcessEpisodes(services, library=EmptyCatalogPort(),
            tool_library=EmptyCatalogPort(), child_roles=('scientific_process', 'literature'))
        bindings = (scientific, *parents.values(), *execution)
        registry = EpisodeBindingRegistry(bindings)
        services.workflow = SimpleNamespace(store=store, journal=journal,
                                            episode_bindings=registry, run_id=journal.run_id)
        assert ports['execution_owner'] is owner
        assert ports['molecular_results'] is owner.molecular_sequence_results
        if api:
            from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
            assert type(owner.api_execution.services['appservice']) is BVBRCAppServiceService
        yield SimpleNamespace(store=store, journal=journal, directory=directory,
            scope={'subject_refs': [subject]}, services=services, tools=tools,
            execution_owner=owner, execution=execution, parents=parents,
            scientific=scientific, bindings=bindings, registry=registry, workspace=workspace)
    finally:
        store.close()


def literature_context(host, parent):
    path = parent_path(parent)
    return BindingContext(host.journal.run_id, EpisodeRef(host.journal.run_id, path).episode_id,
        'literature', path, host.scope, {}, {'message': {'scope': host.scope, 'episode_assignment': {}}})


def saved_axis_commission(host, option):
    """The exact saved ancestor request consumed by the original _enabled path."""
    path = parent_path(PARENTS[2])[:-1]
    goal = EpisodeGoal.root(objective='Preserve the original selected axis commission',
                           result_contract={'type': 'object'})
    request = EpisodeRequest(goal, Record({'scope': host.scope, 'episode_assignment': {
        'selection': {'evidence_axis': {'option_id': option}}}}))
    host.journal.save('runtime_episodes', {'episode_id': EpisodeRef(host.journal.run_id, path).episode_id,
        'path': json.dumps(path), 'request': json.dumps(request.as_record()),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})


def own_execution(host, parent, role):
    return host.registry.for_path(binding_path(parent, role))


def native_context(host, parent, role):
    # Reuse the authenticated original practical operands, replacing only the
    # structural path function so actual Literature ancestry is exercised.
    import operational_private_boundary_checks as original_controls
    with patch.object(original_controls, 'binding_path', binding_path):
        return original_controls.native_state_context(host, parent, role)


def incoming(host, parent, role):
    child = own_execution(host, parent, role)
    exchange = host.parents[parent].child_message_exchange(role, child_binding=child)
    assert exchange is not None
    return exchange[1]
