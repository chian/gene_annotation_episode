"""Real private Launch registry/selection/build boundaries, with controlled ports.

The selected path and original own-axis selected/build methods are executed.
Assignment admission, scope storage, journal persistence and receipt transport
are controlled engineering ports; child construction is stopped after observing
the actual immutable request. No native/provider or scientific work is claimed.
"""
from __future__ import annotations
import ast
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103'
ORIGINAL_SHA = '0bec5b330670ae9b47f48180654ddb5e5f5e2bde041302b7d653181b048e489f'
PARENTS = ('execution_job_submission', 'hpc_work_planning/execution_job_submission',
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
    'scientific_process/execution_job_submission',
    'scientific_process/hpc_work_planning/execution_job_submission',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission')
CHILDREN = (('launch_api', 'api_job_execution'), ('launch_local', 'local_job_execution'),
    ('launch_hpc', 'hpc_job_execution'))
EDGES = tuple((parent, role, parent + '/' + child) for parent in PARENTS for role, child in CHILDREN)
ROLE = {'scientific_process': 'scientific_process', 'hpc_work_planning': 'hpc',
    'hpc_allocation_execution': 'hpc_execution', 'execution_job_submission': 'launch'}


def own(name):
    return import_module(PACKAGE + '.' + name)


class EnvelopeCaptured(Exception):
    """Observation stop before child initialization or credit projection."""


def original_methods(runtime):
    path = Path(__file__).parent / 'fixtures/source_request_assembly/runtime_original.py.txt'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA
    tree = ast.parse(raw)
    owner, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Workflow']
    methods = [deepcopy(node) for node in owner.body if isinstance(node, ast.FunctionDef)
        and node.name in {'selected', 'build'}]
    assert {node.name for node in methods} == {'selected', 'build'}
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])),
        str(path), 'exec'), namespace)
    return SimpleNamespace(**{node.name: namespace[node.name] for node in methods})


def setup(parent_home, role, child_home, failure=None):
    runtime = own('runtime')
    homes = set(PARENTS) | {child for _, _, child in EDGES}
    homes.update('/'.join(parent.split('/')[:index])
        for parent in PARENTS for index in range(1, len(parent.split('/'))))
    bindings = {}
    for home in sorted(homes):
        cls_name = ('ScientificProcessEpisode' if home == 'scientific_process' else
            'HPCEpisode' if home.endswith(('hpc_work_planning', 'hpc_allocation_execution')) else 'ExecutionEpisode')
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
    resources = {'api': {'kind': 'api'}, 'local': {'kind': 'local'}, 'hpc': {'kind': 'pbs_ssh'}}
    parent_assignment = {'version': 'execution_launch_assignment_v1',
        'requests': {name: {'resource_id': name} for name in resources},
        'constraints': {}, 'immutable_input_versions': []}
    parent_binding.resources = resources
    # Actual A103 report-source adapter configuration: no optional native or API sources.
    parent_binding.api_execution = None
    for attribute in ('native_blast_standard_database_results', 'native_blast_database_results',
        'native_hmmer_preparation_results', 'native_blast_results'):
        setattr(parent_binding, attribute, None)
    # Control assignment validation only. The original allowed_children and
    # _permitted methods still choose from the actual parent assignment/resources.
    def admitted_launch(value, **kwargs):
        assert value == parent_assignment and not kwargs
        return value
    parent_binding._launch = admitted_launch
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
    handoffs = deepcopy(parent_binding.fact_sources('launch')['execution_handoff_refs']['report_schema'])
    assert handoffs['items'] == {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'execution_handoff'}
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


def invoke(value, *, original=False, direct=False):
    runtime = value.runtime
    original_episode, original_record = runtime.Episode, runtime.Record
    def identity(context, grain, key, *, parent_path=()):
        value.events.append(('identity', grain.name, key, tuple(parent_path)))
        return original_episode.identity(context, grain, key, parent_path=parent_path)
    def record(message):
        value.events.append(('record', deepcopy(message)))
        return original_record(message)
    with patch.object(runtime, 'Episode', SimpleNamespace(identity=identity)), patch.object(runtime, 'Record', record):
        methods = original_methods(runtime) if original else runtime.Workflow
        value.workflow.build = methods.build.__get__(value.workflow)
        try:
            if direct:
                contract = runtime.TypedReportContract(value.selection['purpose'], value.schema, lambda *_: False)
                value.workflow.build(value.role, 'child_7', value.selection['goal'], value.scope,
                    parent=value.source.request.goal, parent_path=value.source.path, contract=contract,
                    initial={}, job_assignment={'original': 'job'},
                    episode_assignment=value.assignment, scientific_process={'original': 'optional scientific operand'})
            else:
                methods.selected(value.workflow, value.source, value.selection, 7)
        except EnvelopeCaptured:
            return {'status': 'captured'}
        except Exception as error:
            value.caught_error = error
            return {'status': 'raised', 'type': type(error), 'message': str(error),
                'code': getattr(error, 'code', None), 'field': getattr(error, 'field', None)}
        raise AssertionError('request boundary failed to reach the observation stop')
