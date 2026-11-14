"""Exact-current implicit annotation preservation; no scientific/model/native run.

Workflow, Store, ToolRegistry, source constructors, child bindings, registry,
Journal, typed forms and saved identities are real. The selected-action tests
exercise invalid boundaries before child execution. External outcome providers
and report-progress delivery are explicit controlled ports. Original runtime
bodies come only from authenticated permanent own-axis predecessor fixtures.
"""
from __future__ import annotations

import ast
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import textwrap

import pytest

AXIS = __package__.split('.')[-2]
assert AXIS in ('a107', 'a110')
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
FIXTURES = Path(__file__).parent / 'fixtures' / 'organization_original'
ROUTES = (
    ('launch', 'execution_job_submission', 'ExecutionEpisode'),
    ('monitor', 'execution_progress_assessment', 'MonitorEpisode'),
    ('results', 'execution_result_acquisition', 'ExecutionEpisode'),
    ('hpc', 'hpc_work_planning', 'HPCEpisode'),
    ('scientific_process', 'scientific_process', 'ScientificProcessEpisode'),
    ('literature', 'published_evidence_assessment', 'LiteratureEpisode'),
)
ROLE_IDS = [row[0] for row in ROUTES]


def module(name):
    return importlib.import_module(PACKAGE + '.' + name.replace('/', '.'))


def original_tree():
    pins = json.loads((FIXTURES / 'implicit_parent_predecessors.json').read_text())
    data = (FIXTURES / 'implicit_parent_runtime.py.source').read_bytes()
    assert hashlib.sha256(data).hexdigest() == pins['runtime.py']['sha256']
    return ast.parse(data)


def original_member(owner, name):
    node, = [node for node in original_tree().body
             if isinstance(node, ast.ClassDef) and node.name == owner]
    method, = [node for node in node.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    return method


def original_function(runtime, owner, name):
    namespace = dict(vars(runtime))
    method = deepcopy(original_member(owner, name))
    method.decorator_list = []
    tree = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), str(FIXTURES / 'implicit_parent_runtime.py.source'), 'exec'), namespace)
    return namespace[name]


def original_source_class(runtime):
    tree = original_tree()
    node, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DecisionSource']
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(FIXTURES / 'implicit_parent_runtime.py.source'), 'exec'), namespace)
    return namespace['DecisionSource']


def dump(node):
    return ast.dump(node, include_attributes=False)


def import_normalized(node, package):
    class ResolveRelative(ast.NodeTransformer):
        def visit_ImportFrom(self, item):
            if item.level:
                parts = package.split(".")
                assert item.level <= len(parts)
                base = ".".join(parts[:len(parts) - item.level + 1])
                item.module = base + ("." + item.module if item.module else "")
                item.level = 0
            return item
    return ResolveRelative().visit(deepcopy(node))


def forbidden(*_args, **_kwargs):
    raise AssertionError('implicit_parent_control_crossed_execution_port')


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)


@contextmanager
def actual_workflow(directory, *, factories=(), workflow_class=None):
    runtime = module('runtime')
    directory.mkdir(parents=True, exist_ok=True)
    with module('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        tools = module('tools').ToolRegistry(store)
        workflow = (runtime.Workflow if workflow_class is None else workflow_class)(
            store, tools, object(), directory / 'workflow', 'implicit-parent-preservation',
            forbidden, lambda *_args, **_kwargs: 0.0,
            episode_binding_factories=factories, decision_protocol=None)
        yield workflow


def root(workflow, *, key='root'):
    return workflow.build('annotation', key, 'Preserve the assigned unknown', workflow.store.validate_scope())


def predecessor_source(workflow, source):
    return original_source_class(module("runtime"))(workflow, source.path, source.request, source.scope)


def failure(error):
    return {'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'diagnostic': getattr(error, 'diagnostic', None),
            'feedback': getattr(error, 'feedback', None)}


def constructed_entry(workflow, directory, route):
    role, home, class_name = route
    owner = getattr(module(home + '/episode'), class_name)
    if role in ('monitor', 'literature'):
        return owner(workflow.services)
    resources = json.loads((FIXTURES / 'implicit_parent_execution_resources.json').read_text())
    if role == 'hpc':
        return owner(workflow.services, store=workflow.store, run_id=workflow.run_id,
                     directory=workflow.directory, resources=resources, commissions={})
    if role in ('launch', 'results'):
        return owner(workflow.services, store=workflow.store, run_id=workflow.run_id,
                     directory=workflow.directory, resources=resources, initial_information={},
                     tool_registry=workflow.tools, handoff_unit=3., acquired_record_unit=2.,
                     log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    write_instruction_source(directory / 'instruction-source', AXIS)
    library = module('scientific_process_library').ScientificProcessLibrary.freeze(
        directory / 'scientific-process-library', source=directory / 'instruction-source')
    tools = module('scientific_tool_library').ScientificToolLibrary.freeze(
        directory / 'scientific-tool-library', catalog=[])
    return owner(workflow.services, library=library, tool_library=tools,
                 child_roles=('scientific_process',))


def install_entry(workflow, owner):
    # The parent/source were constructed before this test-local registry change.
    # No fake binding or source replaces the genuine selected entry owner.
    workflow.episode_bindings = module('episode_bindings').EpisodeBindingRegistry([owner])
    if owner.roles == ('scientific_process',):
        workflow.scientific_process_binding = owner
    return workflow.episode_bindings


def test_public_decision_source_effective_members_globals_and_c3():
    runtime = module('runtime')
    original = original_source_class(runtime)
    current = runtime.DecisionSource
    assert current.__name__ == current.__qualname__ == 'DecisionSource'
    assert current.__module__ == runtime.__name__ and current.__bases__ == (object,)
    for name, before in vars(original).items():
        if not inspect.isfunction(before):
            continue
        after = inspect.getattr_static(current, name)
        assert inspect.isfunction(after), name
        node, = ast.parse(textwrap.dedent(inspect.getsource(after))).body
        # Reverse only the explicit authentic runtime-attribute loads. Keep the
        # complete original method AST, actual provider identity and C3 checks.
        live_names = set()
        class OriginalRuntimeLoads(ast.NodeTransformer):
            def visit_Attribute(self, item):
                if isinstance(item.value, ast.Name) and item.value.id == '_original_runtime':
                    assert isinstance(item.ctx, ast.Load), (name, item.attr)
                    assert after.__globals__['_original_runtime'] is runtime
                    assert item.attr in before.__globals__, (name, item.attr)
                    assert getattr(runtime, item.attr) is before.__globals__[item.attr], (name, item.attr)
                    live_names.add(item.attr)
                    return ast.copy_location(ast.Name(id=item.attr, ctx=ast.Load()), item)
                return self.generic_visit(item)
        node = OriginalRuntimeLoads().visit(node)
        assert dump(import_normalized(node, after.__module__.rsplit(".", 1)[0])) == dump(
            import_normalized(original_member("DecisionSource", name), PACKAGE)), name
        # co_names recursively covers actual global resolution, including lambdas.
        def globals_used(code):
            import dis
            result = {instruction.argval for instruction in dis.get_instructions(code)
                      if instruction.opname in ('LOAD_GLOBAL', 'STORE_GLOBAL', 'DELETE_GLOBAL')}
            for value in code.co_consts:
                if inspect.iscode(value):
                    result.update(globals_used(value))
            return result
        used_globals = globals_used(before.__code__)
        assert live_names <= used_globals, (name, live_names - used_globals)
        for key in used_globals:
            if key in before.__globals__:
                if key in live_names:
                    assert after.__globals__['_original_runtime'] is runtime
                    assert getattr(runtime, key) is before.__globals__[key], (name, key)
                else:
                    assert after.__globals__[key] is before.__globals__[key], (name, key)
    class Left(current):
        marker = 'left'
    class Right(current):
        marker = 'right'
    class Diamond(Left, Right):
        pass
    assert Diamond.__mro__ == (Diamond, Left, Right, current, object)
    assert Diamond.marker == 'left'


def test_actual_annotation_construction_and_current_identity(tmp_path):
    runtime = module('runtime')
    with actual_workflow(tmp_path) as workflow:
        episode = root(workflow)
        source = episode.source
        assert type(source) is module('episode').AnnotationTask
        assert isinstance(source, runtime.DecisionSource)
        assert workflow.specialist(source) is None
        assert 'annotation' not in workflow.episode_bindings.roles
        expected = runtime.Episode.identity(workflow.context, workflow.grains['annotation'], 'root')
        assert source.episode_id == expected.episode_id
        before = original_source_class(runtime)(workflow, source.path, source.request, source.scope)
        assert vars(source) == vars(before)
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
        saved = workflow.journal.row('runtime_episodes', source.episode_id)
        assert json.loads(saved['request']) == runtime._plain(source.request.as_record())
        assert saved['state'] == 'active'


def test_saved_root_reconstruction_and_mismatch_are_unchanged(tmp_path):
    runtime = module('runtime')
    with actual_workflow(tmp_path) as workflow:
        first = root(workflow)
        original_row = dict(workflow.journal.row('runtime_episodes', first.source.episode_id))
        second = root(workflow)
        assert second.source.episode_id == first.source.episode_id
        assert dict(workflow.journal.row('runtime_episodes', first.source.episode_id)) == original_row
        for method in (original_function(runtime, 'Workflow', 'build'), runtime.Workflow.build):
            with pytest.raises(runtime.WorkflowError, match='reconstructed immutable assignment differs'):
                method(workflow, 'annotation', 'root', 'Changed immutable goal', first.source.scope)
        assert dict(workflow.journal.row('runtime_episodes', first.source.episode_id)) == original_row




@pytest.mark.parametrize('route', ROUTES, ids=ROLE_IDS)
def test_constructed_entry_registry_preserves_annotation_and_standalone_identity(tmp_path, route):
    with actual_workflow(tmp_path / 'workflow') as workflow:
        parent = root(workflow).source
        owner = constructed_entry(workflow, tmp_path / 'entry', route)
        registry = install_entry(workflow, owner)
        role, home, _ = route
        assert owner.binding_path == home and owner.commissioning_parent == 'legacy_annotation'
        assert registry.for_child(parent.path, role) is owner
        assert registry.for_path((*parent.path, (role, 'child_2'))) is owner
        assert registry.for_path(((role, 'standalone'),)) is owner
        before = original_function(module('runtime'), 'Workflow', 'declared_child_roles')
        assert workflow.declared_child_roles('annotation') == before(workflow, 'annotation')
        assert role in registry.entry_roles
        request = module('runtime').EpisodeRequest(
            module('runtime').EpisodeGoal.child(parent.request.goal,
                objective='Construct the genuine child source only', result_contract={}),
            module('runtime').Record({'scope': parent.scope, 'initial_report': {}, 'episode_assignment': {}}), None)
        workflow.grains[role] = module('runtime').Grain(role, 'Original selected work',
            'Original parent contract', workflow.controller)
        source = owner.decision_source_type(workflow, (*parent.path, (role, 'child_2')), request, parent.scope)
        assert type(source) is owner.decision_source_type
        assert source.episode_id == module('runtime').Episode.identity(
            workflow.context, workflow.grains[role], 'child_2', parent_path=parent.path).episode_id
        assert source.path == (*parent.path, (role, 'child_2'))


@pytest.mark.parametrize('route', ROUTES, ids=ROLE_IDS)
@pytest.mark.parametrize('boundary', ('scope', 'initial', 'assignment', 'entry_restriction'))
def test_selected_original_error_and_preparation_order(tmp_path, route, boundary):
    observations = []
    runtime = module('runtime')
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            source = root(workflow).source
            if use_original:
                source = predecessor_source(workflow, source)
            owner = constructed_entry(workflow, tmp_path / str(use_original) / 'entry', route)
            install_entry(workflow, owner)
            role = route[0]
            if role in ('launch', 'results'):
                # Actual registered execution owners require their original
                # configured readers even for a prospective child's form.
                # Keep this setup local to these selected-boundary cases.
                factory = module('execution_service_setup').ExecutionServiceFactory(
                    resources=runtime._plain(owner.resources),
                    initial_information=runtime._plain(owner.initial_information),
                    handoff_unit=owner.handoff_unit,
                    acquired_record_unit=owner.acquired_record_unit,
                    monitoring_information_unit=1.0,
                    log_window_bytes=owner.log_window_bytes,
                    log_roles=tuple(owner.log_roles),
                    require_private_execution_yield=owner.private_yield_binding,
                    results_yield_profiles=runtime._plain(owner.results_yield_profiles) or None,
                    task_yield_profiles=runtime._plain(owner.task_yield_profiles) or None)
                configuration = module('library.received_execution_information.received_configuration').ReceivedExecutionConfiguration.original_global_factory(factory)
                workflow.received_execution_configuration = configuration
                catalog = configuration.construct(store=workflow.store, run_id=workflow.run_id,
                    directory=owner.directory, tool_registry=workflow.tools, services=workflow.services)
                workflow.bind_received_execution_information(catalog,
                    module('annotation_received_execution_information').received_execution_information)
                if AXIS == 'a107':
                    # A107 has a separately authenticated API catalog. A110's
                    # actual execution catalog already owns its API readers.
                    configuration = module('library.received_api_information.received_api_authority').ReceivedAPIConfiguration.original_global_factory(factory)
                    workflow.received_api_configuration = configuration
                    catalog = configuration.construct(store=workflow.store, run_id=workflow.run_id,
                        directory=owner.directory, tool_registry=workflow.tools, services=workflow.services)
                    workflow.bind_received_api_information(catalog,
                        module('annotation_received_api_information').received_api_reports)
            workflow.annotation_child_roles = (role,) if boundary != 'entry_restriction' else ()
            events = []
            facts = owner.fact_sources(role)
            required = getattr(owner, 'required_return_sources', lambda *_: ())(workflow.binding_context(source), role)
            names = tuple(required) or (next(name for name, fact in facts.items() if 'report_schema' in fact),)
            schema = {'type': 'object', 'properties': {name: deepcopy(facts[name]['report_schema'])
                      for name in names}, 'required': list(names), 'additionalProperties': False}
            selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(source.scope),
                'goal': 'Inspect the original unknown', 'purpose': 'Preserve original typed failure',
                'assignment': {}, 'schema_json': json.dumps(schema), 'initial_report_json': '{}'}
            if boundary == 'scope':
                selection['scope'] = {'subject_refs': ['unavailable_subject_boundary']}
            elif boundary == 'initial':
                selection['initial_report_json'] = '{'
            original_expand = workflow.expanded_contract_form
            def expand(*args):
                events.append('expanded_contract_form')
                return original_expand(*args)
            workflow.expanded_contract_form = expand
            original_materialize = workflow.launch_instructions.materialize
            def materialize(value):
                events.append('materialize')
                return original_materialize(value)
            workflow.launch_instructions.materialize = materialize
            method_name = 'prepare_invocation' if role == 'scientific_process' else 'prepare_assignment'
            previous = getattr(owner, method_name)
            def prepare(*args, **kwargs):
                events.append(method_name)
                return previous(*args, **kwargs)
            setattr(owner, method_name, prepare)
            def no_child(*args, **kwargs):
                raise AssertionError('invalid_selection_reached_child_build')
            workflow.build = no_child
            method = original_function(runtime, 'Workflow', 'selected') if use_original else runtime.Workflow.selected
            try:
                method(workflow, source, selection, 7)
            except Exception as error:
                assert not isinstance(error, AssertionError)
                observations.append((failure(error), events, workflow.store.db.execute(
                    'SELECT count(*) FROM runtime_actions').fetchone()[0]))
            else:
                pytest.fail('invalid_selection_did_not_reject')
    assert observations[0] == observations[1]
    assert observations[0][2] == 0
    if boundary == 'assignment':
        assert observations[0][1][-2:] == ['materialize',
            'prepare_invocation' if route[0] == 'scientific_process' else 'prepare_assignment']
    if route[0] in ('launch', 'results'):
        if boundary == 'assignment':
            assert observations[0][0]['type'] == 'builtins.ValueError'
            assert observations[0][0]['message'] == 'invalid_execution_assignment'
        elif boundary == 'initial':
            assert observations[0][1] == ['expanded_contract_form']
            assert observations[0][0]['type'].endswith('.ModelOutputError')
            assert observations[0][0]['message'].startswith('LLM output was not valid JSON:')
        elif boundary == 'entry_restriction':
            assert observations[0][1] == []
            assert observations[0][0]['message'] == 'child_role_not_available_to_parent'
        else:
            assert boundary == 'scope' and observations[0][1] == []


@pytest.mark.parametrize('role', ROLE_IDS)
@pytest.mark.parametrize('redelivery', (False, True), ids=('fresh', 'redelivery'))
def test_actual_parent_return_receiver_preserves_progress_and_no_receipt_branch(tmp_path, role, redelivery):
    runtime = module('runtime')
    records = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            source = root(workflow).source
            if use_original:
                source = predecessor_source(workflow, source)
            events = []
            original_specialist = workflow.specialist
            def specialist(value):
                events.append(("specialist", value.episode_id))
                return original_specialist(value)
            workflow.specialist = specialist
            workflow.progress_provider = SimpleNamespace(receive_form=lambda *args:
                events.append(("progress", deepcopy(args))))
            schema = {'type': 'object', 'properties': {'unknown': {'type': 'boolean'}},
                      'required': ['unknown'], 'additionalProperties': False}
            method = original_function(runtime, 'Workflow', '_receive_form') if use_original else runtime.Workflow._receive_form
            result = method(workflow, source, {'unknown': True}, schema, 9,
                            redelivery=redelivery, child_role=role)
            records.append((result, events))
            assert result == [] and sum(event[0] == "progress" for event in events) == 1
            assert events[0] == ("specialist", source.episode_id)
    assert records[0] == records[1]


@pytest.mark.parametrize('status', ('completed', 'partial', 'invalid', 'failed', 'unavailable'))
@pytest.mark.parametrize('saved', (False, True), ids=('returned', 'saved'))
def test_returned_and_saved_outcomes_preserve_original_observation(tmp_path, status, saved):
    runtime = module('runtime')
    observations = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            episode = root(workflow)
            source = episode.source
            if use_original:
                source = original_source_class(runtime)(workflow, source.path, source.request, source.scope)
            events = []
            # Timing is an explicit unused measurement port in these returned-outcome controls.
            workflow.journal.measure = lambda *_args: nullcontext()
            selection = {'kind': 'tool', 'tool': 'controlled.returned_unit', 'arguments': {}}
            returned = {'status': status, 'record_refs': [], 'changed_record_refs': [],
                        'feedback': {'status': status, 'category': 'original_controlled_outcome'}}
            def execute(*args, **kwargs):
                events.append('execute')
                return deepcopy(returned)
            workflow.execute = execute
            workflow.receive_native_outcome = lambda *args: events.append('native_custody')
            workflow.receive_outcome = lambda *args: events.append('outcome_custody')
            async def score(_source, _index, value):
                events.append('score_port')
                return value
            workflow.automatic_score_updates = score
            workflow.pending_work = lambda _source: []
            workflow.controller_value = lambda _source, index, credit: {'index': index, 'credit': credit}
            if saved:
                workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                    'decision_index': 4, 'action': runtime._json(selection),
                    'result': runtime._json(returned), 'credit': None})
            try:
                value = asyncio.run(source.execute(selection, 4))
                result = {'returned': value}
            except runtime.ActionFailure as error:
                result = {'raised': failure(error)}
            row = dict(workflow.journal.row('runtime_actions', source.episode_id, 4))
            observations.append((result, row, source.feedback, source.last_outcome,
                                 source.last_outcome_index, events))
            assert source.last_outcome['status'] == status and source.last_outcome_index == 4
            assert events.count('execute') == (0 if saved else 1)
    assert observations[0] == observations[1]


def test_inherited_finish_preserves_root_facts_and_release(tmp_path):
    runtime = module('runtime')
    observations = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            source = root(workflow).source
            if use_original:
                source = original_source_class(runtime)(workflow, source.path, source.request, source.scope)
            calls = []
            workflow.pending_handles = lambda _source: ['controlled_pending']
            workflow.episode_bindings.current_report_facts = lambda _context: {'original_unknown': True}
            async def release(episode_id):
                calls.append(episode_id)
            workflow.release = release
            value = asyncio.run(source.finish(None)).as_record()
            observations.append((runtime._plain(value), calls))
            assert value['original_unknown'] is True
    assert observations[0] == observations[1]
def write_instruction_source(directory, axis):
    """Keep required synthetic instruction data with the test implementation."""
    evidence = {
        'case_group': 'scientific_head_boundary_fixture',
        'case_id': 'synthetic_instruction',
        'source_url': 'https://example.org/scientific-head-fixture',
        'source_locator': 'synthetic instruction record',
        'observation': 'Engineering instruction data; no scientific result.',
        'limit': 'No biological evidence or target support is asserted.',
    }
    bodies = [{
        'entry_version': 'evidence_axis_instruction_v1', 'id': axis.upper(),
        'slot': 'evidence_axis', 'name': 'Synthetic '+axis.upper()+' instructions',
        'description': 'Exercise this axis binding without interpreting evidence.',
        'investigation_instructions': 'Preserve the original assigned question and unknown result.',
        'evidence': [deepcopy(evidence)],
    }]
    for identity in ('P01', 'P02'):
        bodies.append({
            'id': identity, 'slot': 'thought_pattern', 'name': 'Fixture '+identity,
            'description': 'Compare two explicitly unresolved explanations.',
            'use_when': 'The controlled engineering comparison remains unresolved.',
            'live_alternatives': ['First fixture explanation', 'Second fixture explanation'],
            'decision_guidance': ['Inspect the selected fixture outcome.'],
            'outcome_contingencies': [{'if_observed': 'The fixture is unavailable',
                                      'then_consider': 'Retain the unresolved result.'}],
            'boundary': 'An instruction choice supplies no evidence or credit.',
            'evidence': [deepcopy(evidence)],
        })
    entries, rows = [], []
    for body in bodies:
        identity = body['id']
        relative = 'entries/'+identity+'.json'
        path = directory/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body)+'\n')
        evidence_id = 'E-'+identity+'-01'
        entries.append({**{key: body[key] for key in ('id', 'slot', 'name', 'description')},
                        'detail_path': relative, 'source_evidence_ids': [evidence_id]})
        rows.append({'evidence_id': evidence_id, 'option_id': identity, **evidence})
    (directory/'index.json').write_text(json.dumps({
        'format': 'research_three_slot_options_v1', 'status': 'Engineering fixture only',
        'slots': [{'slot': 'evidence_axis', 'catalog': 'axes.json', 'count': 1},
                  {'slot': 'thought_pattern', 'catalog': 'thoughts.json', 'count': 2}],
        'entries': entries,
    })+'\n')
    (directory/'option_sources.json').write_text(json.dumps({
        'meaning': 'Synthetic instruction provenance, never scientific evidence.', 'rows': rows,
    })+'\n')


def test_caller_registered_annotation_source_retains_precedence(tmp_path):
    runtime = module('runtime')
    class CallerSource(runtime.DecisionSource):
        instruction_composer = staticmethod(lambda source, context: 'Retain the caller-supplied instruction.')
    class CallerBinding:
        """Explicit custom public protocol fixture, not an application owner."""
        roles = entry_roles = ('annotation',)
        decision_source_type = CallerSource
        def __init__(self, services):
            self.services = services
        def child_roles(self, role):
            return ()
        def as_record(self):
            return {'version': 'controlled_custom_annotation', 'roles': list(self.roles)}
        def credit_kind(self, role):
            return 'scientific'
        def assignment_schema(self, role):
            return runtime._object({})
        def permitted_common_actions(self, context):
            return ('tool', 'reason', 'wait')
        def allowed_children(self, parent, caller_capabilities):
            return ()
        def prepare_assignment(self, parent, role, selection, scope, operation_key):
            return selection
        def instructions(self, context):
            return 'Retain the caller-supplied instruction.'
        def decision_context(self, context, current_view):
            return {}
        def catalog(self, context):
            return []
        execute = staticmethod(forbidden)
        def fact_sources(self, role):
            return {}
        def facts(self, context, completion_snapshot):
            return {}
        def resolve(self, context, reference, namespace):
            return False
        def validate_report(self, context, form, original_schema):
            return None
        def credit_view(self, context, receiver_selection):
            return {'credit': 0.0}
    class OriginalWorkflow(runtime.Workflow):
        __init__ = original_function(runtime, 'Workflow', '__init__')
        build = original_function(runtime, 'Workflow', 'build')
    class AdmittedCallerBinding(CallerBinding):
        def child_roles(self, role):
            # The pre-existing generic improvement grain must remain reachable.
            # No child is selected or executed by this compatibility control.
            return ('improvement',)
    for label, workflow_class in (('original', OriginalWorkflow), ('candidate', runtime.Workflow)):
        with pytest.raises(ValueError, match="EpisodeTree has unreachable parent grains: \\['improvement'\\]"):
            with actual_workflow(tmp_path / label / 'invalid-original-graph',
                    factories=(CallerBinding,), workflow_class=workflow_class):
                pytest.fail('original_unreachable_graph_was_admitted')
        with actual_workflow(tmp_path / label / 'admitted-original-graph',
                factories=(AdmittedCallerBinding,), workflow_class=workflow_class) as workflow:
            episode = root(workflow)
            assert type(episode.source) is CallerSource
            assert workflow.specialist(episode.source) is workflow.episode_bindings.for_role('annotation')
            assert episode.source.instructions({}) == 'Retain the caller-supplied instruction.'


def test_annotation_job_compatibility_preserves_original_behavior(tmp_path):
    runtime = module('runtime')
    with actual_workflow(tmp_path) as workflow:
        # This compatibility route exists in is_job_source independently of the
        # private registry. Only job projection/exposure are controlled: the
        # actual Workflow.build selector and original source constructor run.
        workflow.job_episodes = SimpleNamespace(roles=('annotation',),
            credit_view=lambda _source: {'credit': 0.0})
        workflow.expose_assigned_job = lambda _source: None
        episode = root(workflow)
        assert workflow.is_job_source(episode.source)
        assert type(episode.source) is module('episode').AnnotationTask
        assert isinstance(episode.source, runtime.DecisionSource)
        before = original_source_class(runtime)(workflow, episode.source.path,
            episode.source.request, episode.source.scope)
        assert vars(episode.source) == vars(before)


def original_envelope(runtime):
    method = deepcopy(original_member('Workflow', 'build'))
    branch, = [node for node in method.body if isinstance(node, ast.If)
               and ast.unparse(node.test) == 'request_assembler is None']
    method.body = branch.body + [ast.Return(value=ast.Tuple(elts=[ast.Name(id=name,
        ctx=ast.Load()) for name in ('path', 'goal', 'message', 'identity', 'request')], ctx=ast.Load()))]
    method.name = 'original_envelope'
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                 str(FIXTURES / 'implicit_parent_runtime.py.source'), 'exec'), namespace)
    return namespace['original_envelope']


@pytest.mark.parametrize('route', ROUTES, ids=ROLE_IDS)
@pytest.mark.parametrize('port', ('normal', 'materialize_failure', 'receipt_failure'))
def test_private_entry_envelope_original_bytes_and_effect_order(tmp_path, route, port):
    runtime = module('runtime')
    observations = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            parent = root(workflow).source
            if use_original:
                parent = predecessor_source(workflow, parent)
            owner = constructed_entry(workflow, tmp_path / str(use_original) / 'entry', route)
            registry = install_entry(workflow, owner)
            role, home, _ = route
            assert registry.for_child(parent.path, role) is owner
            workflow.grains[role] = runtime.Grain(role, 'Original selected work',
                'Original parent contract', workflow.controller)
            events = []
            def materialize(value):
                events.append(('materialize', deepcopy(value)))
                if port == 'materialize_failure':
                    raise ValueError('controlled_original_materialize_failure')
            def bind(child_id, parent_id):
                events.append(('bind', child_id, parent_id))
                if port == 'receipt_failure':
                    raise ValueError('controlled_original_receipt_failure')
                return {'version': 'controlled_original_receipt', 'child': child_id, 'parent': parent_id}
            workflow.launch_instructions.materialize = materialize
            workflow.receipts = SimpleNamespace(bind=bind)
            schema = {'type': 'object', 'properties': {'unknown': {'type': 'boolean'}},
                      'required': ['unknown'], 'additionalProperties': False}
            contract = runtime.TypedReportContract('Retain unresolved input', schema, lambda *_: False)
            method = original_envelope(runtime) if use_original else module('to_child_' + home).assemble_request
            kwargs = {'parent': parent.request.goal, 'parent_path': parent.path,
                'contract': contract, 'initial': {'unknown': True},
                'episode_assignment': {'controlled_payload': 'unknown',
                                       'launch_instructions': {'controlled': 'supplied'}}}
            try:
                path, goal, message, identity, request = method(workflow, role, 'child_5',
                    'Preserve the original parent question', parent.scope, **kwargs)
            except ValueError as error:
                assert port != 'normal'
                observations.append((failure(error), events))
            else:
                assert port == 'normal'
                # Actual selected private source constructor, no initializer,
                # provider, execution or credit claim for the controlled payload.
                child_source = owner.decision_source_type(workflow, path, request, parent.scope)
                assert child_source.episode_id == identity.episode_id
                assert child_source.request is request and child_source.path == path
                assert child_source.path[:-1] == parent.path
                observations.append((path, runtime._plain(request.as_record()),
                                     identity.episode_id, events))
    assert observations[0] == observations[1]
    expected = ['materialize'] if port == 'materialize_failure' else ['materialize', 'bind']
    assert [event[0] for event in observations[0][-1]] == expected


@pytest.mark.parametrize('role', ROLE_IDS)
def test_return_receiver_preserves_original_specialist_failure_first(tmp_path, role):
    runtime = module('runtime')
    observations = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            source = root(workflow).source
            if use_original:
                source = predecessor_source(workflow, source)
            events = []
            def specialist(value):
                events.append(('specialist', value.episode_id))
                raise RuntimeError('original_specialist_selection_failure')
            workflow.specialist = specialist
            workflow.progress_provider = SimpleNamespace(receive_form=forbidden)
            method = original_function(runtime, 'Workflow', '_receive_form') if use_original else runtime.Workflow._receive_form
            with pytest.raises(RuntimeError, match='original_specialist_selection_failure') as caught:
                method(workflow, source, {}, runtime._object({}), 3, child_role=role)
            observations.append((failure(caught.value), events))
            assert events == [('specialist', source.episode_id)]
    assert observations[0] == observations[1]


def test_nested_unbound_annotation_preserves_original_rejection_and_source(tmp_path, monkeypatch):
    runtime = module('runtime')
    observations = []
    for use_original in (True, False):
        with actual_workflow(tmp_path / str(use_original)) as workflow:
            parent = root(workflow).source
            constructed = []
            original_init = runtime.DecisionSource.__init__
            def capture(self, *args, **kwargs):
                constructed.append(type(self))
                return original_init(self, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(runtime.DecisionSource, '__init__', capture)
                method = original_function(runtime, 'Workflow', 'build') if use_original else runtime.Workflow.build
                contract = runtime.TypedReportContract('Original unsupported nested path',
                    runtime._object({'unresolved': {'type': 'boolean'}}), lambda *_: False)
                with pytest.raises(ValueError, match='scientific_task_credit_not_declared:annotation') as caught:
                    method(workflow, 'annotation', 'nested', 'Original unsupported nested path',
                        parent.scope, parent=parent.request.goal, parent_path=parent.path, contract=contract,
                        initial={'unresolved': True})
            assert constructed == [runtime.DecisionSource]
            observations.append(failure(caught.value))
    assert observations[0] == observations[1]


def test_caller_workflow_subclass_keeps_original_public_source(tmp_path):
    runtime = module('runtime')
    class CallerWorkflow(runtime.Workflow):
        pass
    with actual_workflow(tmp_path, workflow_class=CallerWorkflow) as workflow:
        episode = root(workflow)
        assert type(workflow) is CallerWorkflow
        assert type(episode.source) is runtime.DecisionSource
