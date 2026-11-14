"""Actual A103 Resource parent selection and immutable request controls.

Uses the own-axis original selected/build oracle, authentic bound legacy lookup,
Resource capability policy and real handoff schema. Child admission is an explicit
controlled port; no native work or provider work is performed.
"""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from .launch_request_boundary_checks import EnvelopeCaptured, PACKAGE, invoke
from .resource_task_checks import ControlledAdapter, own

PARENTS = ('resource_work_submission', 'scientific_process/resource_work_submission')
CHILDREN = (('launch_api', 'api_resource_work_execution'),
    ('launch_local', 'local_resource_work_execution'), ('launch_hpc', 'hpc_resource_work_execution'))
EDGES = tuple((parent, role, parent + '/' + child) for parent in PARENTS for role, child in CHILDREN)
ROLE = {'scientific_process': 'scientific_process', 'resource_work_submission': 'launch'}


def setup(parent_home, role, child_home, failure=None):
    runtime = own('runtime')
    homes = set(PARENTS) | {child for _, _, child in EDGES}
    homes.update('/'.join(parent.split('/')[:index])
        for parent in PARENTS for index in range(1, len(parent.split('/'))))
    bindings = {}
    for home in sorted(homes):
        cls_name = ('ScientificProcessEpisode' if home == 'scientific_process' else
            'ResourceEpisode')
        bindings[home] = object.__new__(getattr(own(home.replace('/', '.') + '.episode'), cls_name))
    registry = object.__new__(own('episode_bindings').EpisodeBindingRegistry)
    registry._bindings = list(bindings.values())
    registry._by_path = dict(bindings)
    registry._by_role = {}
    for binding in bindings.values():
        for name in binding.roles:
            registry._by_role.setdefault(name, []).append(binding)
    parent_path = (('annotation', 'original-root'), *( (ROLE[part], 'original-' + str(index))
        for index, part in enumerate(parent_home.split('/')) ))
    parent_binding = bindings[parent_home]
    assert registry.for_path(parent_path) is parent_binding
    assert registry.for_child(parent_path, role) is bindings[child_home]
    events, selectors, assemblies, captures = [], [], [], []
    adapters = [ControlledAdapter(kind) for kind in ('api', 'local', 'hpc')]
    parent_binding.adapters = {adapter.resource_id: adapter for adapter in adapters}
    parent_binding.services = SimpleNamespace(capabilities=lambda: [])
    parent_assignment = {'version': 'resource_launch_assignment_v1', 'job_request': {'original': True},
        'immutable_input_versions': [], 'constraints': {}, 'resource_selection': None,
        'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    original_selector = getattr(parent_binding, 'child_request_assembler', None)
    def selector(selected_role):
        selectors.append(selected_role)
        chosen = None if original_selector is None else original_selector(selected_role)
        if chosen is None:
            return None
        def assemble(*args, **kwargs):
            assemblies.append(chosen.__module__)
            return chosen(*args, **kwargs)
        return assemble
    parent_binding.child_request_assembler = selector
    handoffs = deepcopy(parent_binding.fact_sources('launch')['execution_handoffs']['report_schema'])
    assert handoffs['x-source'] == 'execution_handoffs'
    assert handoffs['items'] == own('resource_records').HANDOFF_SCHEMA
    schema = {'type': 'object', 'properties': {'handoffs': handoffs},
        'required': ['handoffs'], 'additionalProperties': False}
    scope = {'subject_refs': ['subject:controlled-original']}
    assignment = {'version': 'controlled_admitted_assignment_v1',
        'resource_id': {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}[role],
        'launch_instructions': {'version': 'controlled_original_instructions'},
        'retained_reference': 'source:controlled-original'}
    def prepare(context, selected_role, value, selected_scope, operation_key):
        assert context.role == 'launch' and context.path == parent_path
        assert selected_role == role and value == assignment and selected_scope == scope
        events.append(('prepare_assignment', selected_role, operation_key, deepcopy(value)))
        return deepcopy(value)
    bindings[child_home].prepare_assignment = prepare
    def capture(workflow, path, request, child_scope):
        captures.append({'path': path, 'request': runtime._plain(request.as_record()), 'scope': deepcopy(child_scope)})
        events.append(('constructor', child_home))
        raise EnvelopeCaptured()
    bindings[child_home].decision_source_type = capture
    counts = {'materialize': 0}
    injected_error = ValueError('controlled_original_envelope_materialization_failure' if failure == 'materialize'
        else 'controlled_original_receipt_binding_failure')
    def materialize(value):
        counts['materialize'] += 1
        events.append(('materialize', deepcopy(value)))
        if failure == 'materialize' and counts['materialize'] == 2:
            raise injected_error
    def bind(child_id, parent_id):
        events.append(('bind', child_id, parent_id))
        if failure == 'bind':
            raise injected_error
        return {'version': 'controlled_original_inheritance', 'child': child_id, 'parent': parent_id}
    def validate_scope(value, *, parent_scope):
        assert value == parent_scope == scope
        events.append(('validate_scope', deepcopy(value)))
        return deepcopy(value)
    @contextmanager
    def transaction():
        events.append(('transaction_enter',))
        try:
            yield
        finally:
            events.append(('transaction_exit',))
    saved = {}
    def row(table, *keys):
        return saved.get((table, *keys))
    def save(table, value):
        assert table == 'runtime_actions'
        events.append(('save_action', deepcopy(value)))
        saved[(table, value['episode_id'], value['decision_index'])] = deepcopy(value)
    declaration = None if failure != 'typed_declaration' else {
        'submitted_schema_json': runtime._json(schema), 'version': 'invalid_original_declaration'}
    workflow = SimpleNamespace(episode_bindings=registry, run_id='original-launch-envelope',
        context=SimpleNamespace(require_run_id=lambda: 'original-launch-envelope'),
        grains={name: SimpleNamespace(name=name) for name in ('annotation', *registry.roles)},
        grain_names=('annotation', *registry.roles), inprocess_completion_order='original_controlled_order',
        scientific_process_binding=bindings['scientific_process'], execution_binding=None,
        inprocess_replay=None, native_timing_information=object(), annotation_child_roles=('scientific_process',),
        project_credit=SimpleNamespace(task_credit=False), services=SimpleNamespace(capabilities=lambda: {}),
        receipts=SimpleNamespace(bind=bind, known=lambda episode_id: ('source:controlled-original',)),
        launch_instructions=SimpleNamespace(materialize=materialize),
        store=SimpleNamespace(validate_scope=validate_scope, transaction=transaction),
        journal=SimpleNamespace(row=row, save=save),
        expanded_contract_form=lambda *args: (deepcopy(schema), deepcopy(declaration)))
    for name in ('specialist', 'binding_context', 'declared_child_roles', 'available_child_roles',
        'validate_child_choice', 'permits_common_action', '_closed_child_commission', 'child_initial_report_input',
        'legacy_parent_for_path'):
        setattr(workflow, name, getattr(runtime.Workflow, name).__get__(workflow))
    goal = runtime.EpisodeGoal.root(objective='Original parent launch objective', result_contract={'role': 'launch'})
    request = runtime.EpisodeRequest(goal, runtime.Record({'scope': scope,
        'episode_assignment': parent_assignment}), None)
    identity = runtime.Episode.identity(workflow.context, workflow.grains['launch'], parent_path[-1][1],
        parent_path=parent_path[:-1])
    source = SimpleNamespace(path=parent_path, scope=deepcopy(scope), episode_id=identity.episode_id,
        request=request, _delivery_resolution_ref=None)
    if failure == 'invalid_parent':
        source.request = SimpleNamespace(goal=object(), message=request.message, as_record=request.as_record)
    selection = {'kind': 'episode_child', 'role': role, 'goal': 'Original concrete child question',
        'scope': deepcopy(scope), 'purpose': 'Return original qualified handoff identities',
        'assignment': deepcopy(assignment), 'initial_report_json': runtime._json({})}
    return SimpleNamespace(runtime=runtime, workflow=workflow, source=source, selection=selection,
        schema=schema, events=events, selectors=selectors, assemblies=assemblies, captures=captures,
        role=role, parent_home=parent_home, child_home=child_home, scope=scope, assignment=assignment,
        failure=failure, injected_error=injected_error, caught_error=None)


