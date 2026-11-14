"""Real Root private construction and bounded runtime boundary controls.

No provider, job, transport or scheduler is dispatched. Assignment preparation
is an explicit controlled port in request comparisons; actual schema admission,
runtime forwarding, journal transactions and report admission remain active.
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
from gene_annotation_episode.episodic_workflow.root.task_values import Record

ROOT = 'gene_annotation_episode.episodic_workflow.root'
PARENTS = (
    'annotation', 'legacy_annotation', 'scientific_process',
    'hpc_coordination', 'hpc_coordination/hpc_allocation_execution',
    'legacy_annotation/hpc_coordination',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution',
    'scientific_process/hpc_coordination',
    'scientific_process/hpc_coordination/hpc_allocation_execution',
)
HOSTS = PARENTS[:3]
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
HPC_ROLES = ('hpc', 'hpc_prediction', 'hpc_execution')


def forbidden(*args, **kwargs):
    raise AssertionError('external execution is outside this boundary fixture')


def parent_path(parent):
    parts = parent.split('/')
    host = 'annotation'
    if parts[0] in ('legacy_annotation', 'scientific_process'):
        host = 'improvement' if parts.pop(0) == 'legacy_annotation' else 'scientific_process'
    elif parts[0] == 'annotation':
        parts.pop(0)
    roles = [host]
    for part in parts:
        roles.append({'hpc_coordination': 'hpc',
                      'hpc_allocation_execution': 'hpc_execution'}[part])
    return tuple((role, 'original_' + str(index)) for index, role in enumerate(roles))


def binding_path(parent, role):
    path = parent_path(parent)
    if role in ('launch_api', 'launch_local', 'launch_hpc'):
        path += (('launch', 'original_parent_launch'),)
    elif role in ('hpc_prediction', 'hpc_execution'):
        path += (('hpc', 'original_parent_hpc'),)
    return path + ((role, 'original_child'),)


@contextmanager
def families(directory):
    from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
    from gene_annotation_episode.episodic_workflow.root.execution_binding_catalogue import execution_bindings
    from gene_annotation_episode.episodic_workflow.root.resource_binding_catalogue import resource_bindings
    from gene_annotation_episode.episodic_workflow.root.hpc_service_composition import hpc_bindings
    store = Store(directory / 'store')
    try:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'root-private-boundaries')
        workspace = directory / 'workspace'
        workspace.mkdir()
        local = {'kind': 'local', 'workspace': str(workspace),
                 'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}
        hpc = {'kind': 'pbs_ssh', 'workspace': str(workspace),
               'ssh_argv': ['never-dispatch-this-test-transport'],
               'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
               'scheduler': {'kind': 'pbs', 'required_resources': []}}
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden)
        bound_ports = {}
        tools = SimpleNamespace(ordinary_flux_balance_backend=None,
            bind_molecular_sequence_results=lambda value: bound_ports.__setitem__('molecular_results', value),
            bind_execution_owner=lambda value: bound_ports.__setitem__('execution_owner', value))
        execution_owner = ExecutionEpisodes(services, store=store, directory=directory / 'run',
            run_id=journal.run_id, resources={'here': local, 'remote': hpc}, initial_information={},
            tool_registry=tools, handoff_unit=3, acquired_record_unit=2,
            log_window_bytes=4, log_roles=['stdout', 'stderr'])
        resource_owner = ResourceEpisodes(services, resource_adapters=())
        assert bound_ports['execution_owner'] is execution_owner
        assert bound_ports['molecular_results'] is execution_owner.molecular_sequence_results
        execution = execution_bindings(execution_owner, parents=PARENTS)
        resource = resource_bindings(resource_owner, parents=PARENTS)
        hpc_bindings_actual = hpc_bindings(services, store=store, run_id=journal.run_id,
            directory=directory / 'hpc', resources={'aurora': hpc}, commissions={}, parents=HOSTS)
        yield SimpleNamespace(store=store, journal=journal, directory=directory,
            scope={'subject_refs': [subject]}, services=services, tools=tools,
            execution_owner=execution_owner, resource_owner=resource_owner,
            execution=execution, resource=resource, hpc=hpc_bindings_actual, workspace=workspace)
    finally:
        store.close()


def selected_binding(host, family, parent, role):
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_path
    return binding_for_path(getattr(host, family), binding_path(parent, role))


def native_state_context(host, parent, role):
    """Original practical record operands; no command is acquired or executed."""
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    kind = 'local' if role == 'launch_local' else 'hpc'
    resource = 'here' if kind == 'local' else 'remote'
    workspace = str(host.workspace)
    assignment = {
        'version': 'practical_assignment_v1', 'assignment_id': 'original-state-' + kind,
        'resource_id': resource, 'resource_kind': kind, 'workspace': workspace,
        'endpoint': 'completed_job_outputs',
        'requested_job': {'argv': ['/opt/bio/python', 'analysis.py'], 'environment': {}},
        'progress_requirements': [
            {'key': 'environment', 'credit': 2, 'predicate': {'kind': 'path_exists',
                'path': workspace + '/env', 'object_type': 'directory'}},
            {'key': 'requested-result', 'credit': 5, 'predicate': {'kind': 'requested_job_outputs',
                'output_paths': [workspace + '/results.json']}}],
        'completion_keys': ['requested-result'],
        'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {},
    }
    path = binding_path(parent, role)
    episode_id = 'private-state-' + parent.replace('/', '-') + '-' + role
    context = BindingContext(host.journal.run_id, episode_id, role, path, host.scope, assignment,
        {'message': {'scope': host.scope, 'episode_assignment': assignment}})
    return context, resource


@contextmanager
def isolated_rows(host):
    """Retain the actual Store transaction implementation and roll back test rows."""
    class RestoreRows(Exception):
        pass
    try:
        with host.store.transaction():
            yield
            raise RestoreRows()
    except RestoreRows:
        pass


def source_for(host, path, label):
    goal = EpisodeGoal.root(objective='Preserve original operational request boundaries',
                            result_contract={'type': 'object'})
    return SimpleNamespace(path=path, episode_id=label, scope=host.scope,
        request=EpisodeRequest(goal, Record({'scope': host.scope})),
        _delivery_resolution_ref=None)


def request_fixture(host, family, parent, role, *, failure=None, original=False,
                    resource_hpc_negative=False):
    """Use actual private objects/registry, with assignment and child build ports.

    The constructor cutoff follows the real saved action and TypedReportContract
    construction. It avoids pretending a synthetic child is a commissioned job.
    """
    from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_path
    from gene_annotation_episode.episodic_workflow.root import action_execution
    from operational_original_runtime import OriginalActionExecution
    bindings = getattr(host, family)
    registry = EpisodeBindingRegistry(bindings)
    child_path = binding_path(parent, role)
    path = child_path[:-1]
    # The real registry walks every actual ancestor, not only this family.
    # Reuse the existing constructed HPC objects for their exact parent path.
    for end in range(1, len(path) + 1):
        if path[end - 1][0] in HPC_ROLES:
            ancestor = binding_for_path(host.hpc, path[:end])
            assert ancestor is not None
            if not any(ancestor is value for value in registry._bindings):
                registry.register(ancestor)
    # This actual lineage needs the real Scientific binding in the registry.
    # The explicit empty catalogue ports are constructor inputs only; no
    # Scientific decision, resolution, provider or native operation is run.
    if any(part[0] == 'scientific_process' for part in path):
        from gene_annotation_episode.episodic_workflow.root.scientific_process.episode import ScientificProcessEpisodes
        library = SimpleNamespace(as_record=lambda: {'entries': []},
                                  headers=lambda: (), resolve=forbidden)
        tool_library = SimpleNamespace(as_record=lambda: {'tools': []},
                                       resolve=forbidden)
        scientific_parent = ScientificProcessEpisodes(host.services,
            library=library, tool_library=tool_library,
            child_roles=('scientific_process', *ROLES, *HPC_ROLES))
        registry.register(scientific_parent)
        assert registry.for_role('scientific_process') is scientific_parent
    child_binding = binding_for_path(bindings, child_path)
    parent_binding = binding_for_path(bindings, path)
    source = source_for(host, path, 'request-' + family + '-' + role)
    events, assemblies, built = [], [], []
    injected = RuntimeError('controlled-' + str(failure))
    cutoff = RuntimeError('controlled-build-cutoff')
    prepared = {'identity': 'original prepared assignment'}
    schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}
    # Required facts use the real child's declared source schemas, so the original
    # required-return guard remains meaningful rather than being bypassed.
    context = SimpleNamespace(role=path[-1][0], path=path, run_id=host.journal.run_id,
                              episode_id=source.episode_id, scope=host.scope, assignment={})
    required = getattr(child_binding, 'required_return_sources', lambda *a: ())(context, role)
    sources = child_binding.fact_sources(role)
    required = tuple(required)
    if resource_hpc_negative:
        # Preserve the inherited runtime rejection using actual structured
        # Resource facts, never a fabricated Execution receipt-reference alias.
        assert (family, parent, role) == (
            'resource', 'hpc_coordination/hpc_allocation_execution', 'launch_hpc')
        assert failure is None and required == ()
        assert 'execution_handoff_refs' not in sources
        assert sources['execution_handoffs']['report_schema']['x-source'] == 'execution_handoffs'
        requested_sources = ('execution_handoffs',)
    else:
        if (role == 'launch' and path[-1][0] in ('hpc', 'hpc_execution')
                or role == 'launch_hpc' and any(part[0] == 'hpc' for part in path)):
            required = tuple(dict.fromkeys(required + ('execution_handoff_refs',)))
        requested_sources = required
    for number, name in enumerate(requested_sources):
        schema['properties']['fact_' + str(number)] = deepcopy(sources[name].get('report_schema', sources[name]))
        schema['properties']['fact_' + str(number)]['x-source'] = name
    if not schema['properties']:
        # A parent must request actual return information even when the child
        # has no mandatory source. Keep required unchanged and select one of
        # this actual child's existing facts, with its original schema/custody.
        requested_source = {'execution': 'execution_handoff_refs',
                            'resource': 'execution_handoff',
                            'hpc': 'hpc_model_ref'}[family]
        requested_schema = deepcopy(sources[requested_source]['report_schema'])
        assert requested_schema['x-source'] == requested_source
        schema['properties']['fact_0'] = requested_schema
    schema['required'] = list(schema['properties'])
    def expand(*args, **kwargs):
        events.append('expanded_form')
        return deepcopy(schema), None
    def materialize(value):
        events.append(('materialize', value))
        if failure == 'materialize':
            raise injected
    def prepare(actual_parent, actual_role, assignment, scope, key):
        events.append(('prepare', actual_role, deepcopy(assignment), deepcopy(scope), key))
        assert actual_parent is context
        if failure == 'prepare':
            raise injected
        return prepared
    def build(actual_role, identity, objective, scope, **kwargs):
        events.append('build')
        assert kwargs['episode_assignment'] is prepared
        built.append({'role': actual_role, 'identity': identity, 'objective': objective,
                      'scope': deepcopy(scope), 'parent_path': kwargs['parent_path'],
                      'initial': kwargs['initial'], 'job_assignment': kwargs['job_assignment'],
                      'scientific_process': kwargs['scientific_process'],
                      'contract': kwargs['contract'].as_record()})
        raise cutoff
    workflow = SimpleNamespace(store=host.store, journal=host.journal, run_id=host.journal.run_id,
        episode_bindings=registry, annotation_child_roles=ROLES + HPC_ROLES,
        execution_binding=None, inprocess_replay=None, root_action_boundary=None,
        services=host.services, receipts=None, job_episodes=SimpleNamespace(assign=forbidden),
        validate_child_choice=lambda *a, **k: events.append('validate_child_choice'),
        permits_common_action=lambda *a: True, _closed_child_commission=lambda *a: None,
        binding_selection_for_child=lambda *a: None, expanded_contract_form=expand,
        child_initial_report_input=lambda *a: '{"unknown":1}' if failure == 'initial' else '{}',
        binding_context=lambda *a: context,
        specialist=lambda *a: parent_binding, available_child_roles=lambda *a: (role,),
        launch_instructions=SimpleNamespace(materialize=materialize), build=build,
        scientific_binding=lambda *a: SimpleNamespace(validate_execution_context=lambda *a: events.append('scientific_context')))
    selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(host.scope),
                 'goal': 'Original operational goal', 'purpose': 'Original typed return',
                 'assignment': {'launch_instructions': None}}
    private_selector = getattr(parent_binding, 'child_message_exchange', None)
    patches = [patch.object(child_binding, 'prepare_assignment', prepare)]
    if private_selector is not None:
        def observed_selector(selected_role, **kwargs):
            selected = private_selector(selected_role, **kwargs)
            if selected is None:
                return None
            request, response = selected
            def observed_request(*args, **kw):
                assemblies.append(request.__module__)
                return request(*args, **kw)
            return observed_request, response
        patches.append(patch.object(parent_binding, 'child_message_exchange', observed_selector))
    # Host routes have no parent EpisodeBinding; observe the exact substantive
    # owner selected by the real central dispatch without supplying a callable.
    from gene_annotation_episode.episodic_workflow.root.operational_child_message_owners import exchange_for_child
    direct_exchange = exchange_for_child(workflow, source, role)
    if parent_binding is None and direct_exchange is not None:
        request = direct_exchange[0]
        module = import_module(request.__module__)
        def observed_request(*args, **kw):
            assemblies.append(request.__module__)
            return request(*args, **kw)
        patches.append(patch.object(module, 'prepare_request', observed_request))
    from contextlib import ExitStack
    with ExitStack() as stack:
        for item in patches:
            stack.enter_context(item)
        try:
            call = OriginalActionExecution.selected if original else action_execution.ActionExecution.selected
            call(workflow, source, deepcopy(selection), 7)
        except BaseException as error:
            caught = error
        else:
            raise AssertionError('the real child-build cutoff was not reached')
    return SimpleNamespace(events=events, assemblies=assemblies, built=built,
        error=caught, injected=injected, cutoff=cutoff, required=required,
        schema=deepcopy(schema),
        row=host.journal.row('runtime_actions', source.episode_id, 7))


def admission_observation(host, incoming, case):
    from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract, EPISODE_BRANCH_LIFECYCLE
    from gene_annotation_episode.episodic_workflow.root.report_redelivery import ReportRedelivery
    from gene_annotation_episode.episodic_workflow.root.task_values import _digest
    from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
    source = source_for(host, (('annotation', 'original'),), 'admission-parent')
    child = SimpleNamespace(source=SimpleNamespace(episode_id='admission-child'))
    schema = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'const': 'unresolved'}},
              'required': ['qualification'], 'additionalProperties': False}
    admitted_schema = TypedReportContract('Preserve a typed unresolved return', schema, lambda *a: True)
    request = source.request
    result = Record({'form': {'qualification': 'unresolved'}})
    events = []
    receive_error = RuntimeError('controlled-receive-error')
    def receive(source, form, actual_schema, index, **kwargs):
        events.append((deepcopy(form), deepcopy(actual_schema), index, kwargs))
        if case == 'receive-error':
            raise receive_error
        return ['original-received-reference']
    workflow = SimpleNamespace(store=host.store, journal=host.journal, run_id=host.journal.run_id,
        episode_branch_lifecycle=EPISODE_BRANCH_LIFECYCLE, receive_form=receive,
        delivery_feedback=ReportRedelivery.delivery_feedback)
    workflow.save_attempt = ReportRedelivery.save_attempt.__get__(workflow)
    index = 11
    host.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
        'action': '{}', 'result': None, 'credit': None})
    delivery = 'delivery_' + _digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    if case == 'invalid':
        result = Record({'form': {'qualification': 'invented-support'}})
    if case in ('saved', 'saved-failure', 'redelivery'):
        # Use the real save_attempt protocol, not a hand-written completed receipt.
        saved_index = 13 if case == 'redelivery' else index
        if case == 'saved-failure':
            workflow.save_attempt(source.episode_id, saved_index, delivery, child.source.episode_id,
                admitted_schema, failure={'kind': 'report_delivery_failure', 'reason': 'original-failure'})
        else:
            admitted = admitted_schema.admit(result.as_record()['form'],
                audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
            workflow.save_attempt(source.episode_id, saved_index, delivery, child.source.episode_id,
                admitted_schema, form=admitted)
            result = SimpleNamespace(as_record=forbidden)
    try:
        output = incoming(workflow, source, child, index, schema, admitted_schema, result, request)
        error = None
    except (ReportDeliveryError, RuntimeError) as caught:
        output = None
        error = caught
    rows = [dict(row) for row in host.store.db.execute(
        'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
        (workflow.run_id, source.episode_id))]
    return SimpleNamespace(output=output, error=error, events=events, rows=rows, receive_error=receive_error)
