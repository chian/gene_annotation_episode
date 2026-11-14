"""Actual selected Literature parents with original request ports/cutoff."""
from literature_execution_boundary_checks import *

def request_observation(host, parent, role, *, failure=None, original=False):
    """Use actual private objects/registry, with assignment and child build ports.

    The constructor cutoff follows the real saved action and TypedReportContract
    construction. It avoids pretending a synthetic child is a commissioned job.
    """
    from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_path
    from gene_annotation_episode.episodic_workflow.root import action_execution
    from operational_original_runtime import OriginalActionExecution
    bindings = host.bindings
    family = 'literature'
    registry = host.registry
    child_path = binding_path(parent, role)
    path = child_path[:-1]
    child_binding = registry.for_path(child_path)
    parent_binding = registry.for_path(path)
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
    if (role == 'launch' and path[-1][0] in ('hpc', 'hpc_execution')
            or role == 'launch_hpc' and any(part[0] == 'hpc' for part in path)):
        required = tuple(dict.fromkeys(required + ('execution_handoff_refs',)))
    for number, name in enumerate(required):
        schema['properties']['fact_' + str(number)] = deepcopy(sources[name].get('report_schema', sources[name]))
        schema['properties']['fact_' + str(number)]['x-source'] = name
    if not schema['properties']:
        # The original typed contract requires information even when the child
        # declares no mandatory source. Request an actual existing source.
        requested_source = ('execution_handoff_refs' if role == 'launch'
                            else 'execution_result_refs')
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
        specialist=lambda *a: parent_binding,
        available_child_roles=lambda *a: parent_binding.allowed_children(context, host.services.capabilities()),
        launch_instructions=SimpleNamespace(materialize=materialize), build=build,
        scientific_binding=forbidden)
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
        row=host.journal.row('runtime_actions', source.episode_id, 7))


