"""Actual own-axis parent fixtures and authenticated original-method oracles.

These controls use the real Workflow, Store, Journal, source constructors and
registry. Provider/native execution is forbidden; explicit callback ports let
tests compare original late lookup and report behavior without scientific work.
"""
from __future__ import annotations
import ast
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

AXIS = __package__.split('.')[-2]
assert AXIS in ('a105', 'a108')
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
FIXTURES = Path(__file__).parent / 'fixtures' / 'implicit_annotation_parent'


def module(name):
    return import_module(PACKAGE + '.' + name.replace('/', '.'))


def forbidden(*args, **kwargs):
    raise AssertionError('implicit_annotation_control_crossed_execution_port')


def original_tree():
    pins = json.loads((FIXTURES / 'original.json').read_text())
    raw = (FIXTURES / 'runtime.py.source').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pins['runtime']['sha256']
    return ast.parse(raw)


def original_member(owner, name):
    cls, = [n for n in original_tree().body if isinstance(n, ast.ClassDef) and n.name == owner]
    member, = [n for n in cls.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(member)


def original_function(owner, name, *, receiving_tail=False):
    """Keep the original function's globals LIVE in the authentic module dict.

    Compiling in a copied namespace alone would conceal the very late-global
    regression under test. FunctionType changes no code/defaults/closure.
    """
    runtime = module('runtime')
    method = original_member(owner, name)
    method.decorator_list = []
    if receiving_tail:
        assert (owner, name) == ('Workflow', '_receive_form')
        target = ast.dump(ast.parse('self.receipts is not None and (not redelivery) and (not self.is_job_source(source))', mode='eval').body)
        start, = [i for i, n in enumerate(method.body)
                  if isinstance(n, ast.If) and ast.dump(n.test) == target]
        method.body = method.body[start:]
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                 str(FIXTURES / 'runtime.py.source'), 'exec'), namespace)
    compiled = namespace[name]
    result = FunctionType(compiled.__code__, vars(runtime), name,
                          compiled.__defaults__, compiled.__closure__)
    result.__kwdefaults__ = compiled.__kwdefaults__
    return result


def original_request():
    """Original unspecialized request block, before endpoint extraction.

    Only the method receiver and its relative import location are relocated.
    Original branches, expression order and live runtime globals stay intact;
    the candidate's selector, transformer and live-global helper are not used.
    """
    pins = json.loads((FIXTURES / 'original.json').read_text())
    raw = (FIXTURES / 'pre_split_runtime.py.source').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pins['pre_split_runtime']['sha256']
    text = raw.decode()
    start = text.index('        scope = self.store.validate_scope(selection["scope"], parent_scope=source.scope)',
                       text.index('    def selected('))
    end = text.index('        # Only detached immutable context remains', start)
    function = ast.parse('def original_request(workflow, source, selection, index):\n' + text[start:end]).body[0]
    class Receiver(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == 'self':
                return ast.copy_location(ast.Name(id='workflow', ctx=node.ctx), node)
            return node
        def visit_ImportFrom(self, node):
            if node.level:
                assert node.level == 1
                node.level = 0
                node.module = PACKAGE + '.' + node.module
            return node
    function = Receiver().visit(function)
    function.body += ast.parse("return {'scope': scope, 'role': role, 'schema': schema, 'report_declaration': report_declaration, 'initial': initial, 'episode_assignment': episode_assignment, 'scientific_process': scientific_process, 'assignment': assignment}").body
    runtime = module('runtime')
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(FIXTURES / 'pre_split_runtime.py.source'), 'exec'), namespace)
    compiled = namespace['original_request']
    return FunctionType(compiled.__code__, vars(runtime), 'original_request',
                        compiled.__defaults__, compiled.__closure__)


def original_instructions():
    """Authentic prompt function with its original live module global mapping."""
    pins = json.loads((FIXTURES / 'original.json').read_text())
    raw = (FIXTURES / 'runtime_prompt.py.source').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pins['runtime_prompt']['sha256']
    function, = [node for node in ast.parse(raw).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'instructions']
    prompt = module('runtime_prompt')
    namespace = dict(vars(prompt))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(FIXTURES / 'runtime_prompt.py.source'), 'exec'), namespace)
    compiled = namespace['instructions']
    return FunctionType(compiled.__code__, vars(prompt), 'instructions',
                        compiled.__defaults__, compiled.__closure__)


@contextmanager
def actual_workflow(directory, *, factories=(), workflow_class=None, job_episodes=None,
                    annotation_child_roles=None):
    runtime = module('runtime')
    directory.mkdir(parents=True, exist_ok=True)
    with module('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        tools = module('tools').ToolRegistry(store)
        workflow = (runtime.Workflow if workflow_class is None else workflow_class)(
            store, tools, object(), directory / 'workflow', 'own-annotation-preservation',
            forbidden, lambda *args, **kwargs: 0.0,
            episode_binding_factories=factories, job_episodes=job_episodes,
            decision_protocol=None, annotation_child_roles=annotation_child_roles)
        yield workflow


def root(workflow, *, key='root', original=False):
    build = original_function('Workflow', 'build') if original else module('runtime').Workflow.build
    return build(workflow, 'annotation', key, 'Preserve the assigned unknown',
                 workflow.store.validate_scope())


def error_record(error):
    return (type(error).__module__, type(error).__qualname__, str(error),
            getattr(error, 'diagnostic', None), getattr(error, 'feedback', None))


class EmptyCatalog:
    """Original library protocol ports with no selectable scientific work."""
    def as_record(self): return {'control': 'no_scientific_work'}
    def headers(self): return ()
    resolve = staticmethod(forbidden)


def scientific(services):
    return module('scientific_process/episode').ScientificProcessEpisode(
        services, library=EmptyCatalog(), tool_library=EmptyCatalog(),
        child_roles=('scientific_process', 'literature'))


def connected_factories():
    """Construct the genuine two private Literature families once per workflow."""
    children = []
    def first(services):
        children.extend(module('published_evidence_assessment/episode').create_binding_tree(services))
        children.extend(module('scientific_process/published_evidence_assessment/episode').create_binding_tree(services))
        assert len(children) == 14
        return scientific(services)
    return (first, *(lambda services, index=index: children[index] for index in range(14)))


SCHEMA = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'const': 'unresolved'}},
          'required': ['qualification'], 'additionalProperties': False}
INITIAL = {'qualification': 'unresolved'}
EDGES = ('annotation-scientific', 'annotation-literature',
         'scientific-scientific', 'scientific-literature')


def connected_exchange(directory, edge, scenario, *, original, custom_registry=False):
    """Actual selected child unit, typed report, journal and failure callback.

    Scientific preparation and child construction receive explicit controlled
    results. No scientific assignment/process is claimed by those supplied ports.
    """
    runtime = module('runtime')
    parent_name, child_name = edge.split('-')
    role = 'scientific_process' if child_name == 'scientific' else 'literature'
    events, owners, built = [], [], []
    with actual_workflow(directory, factories=connected_factories(),
                         annotation_child_roles=('scientific_process', 'literature')) as workflow:
        annotation = root(workflow).source
        parent_path = annotation.path
        if parent_name == 'annotation':
            source = annotation
        else:
            path = parent_path + (('scientific_process', 'parent'),)
            request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(annotation.request.goal,
                objective='Original scientific parent', result_contract=SCHEMA),
                runtime.Record({'scope': annotation.scope, 'initial_report': INITIAL}))
            source = module('scientific_process/task').ScientificTask(workflow, path, request, annotation.scope)
        registry = workflow.episode_bindings
        if custom_registry:
            class CustomRegistry(type(registry)):
                @property
                def roles(self):
                    events.append('custom_registry_roles')
                    return super().roles
            registry = CustomRegistry(registry._bindings)
            workflow.episode_bindings = registry
        workflow.episode_branch_lifecycle = runtime.EPISODE_BRANCH_LIFECYCLE if scenario == 'saved-return' else None
        workflow.receipts = None
        workflow.wait_inputs_version = None
        workflow.completed_action_inputs_version = None
        workflow.root_action_boundary = None
        workflow.validate_child_choice = lambda *a, **kw: events.append('validate_child_choice')
        workflow.permits_common_action = lambda *a: a[-1] != 'wait'
        workflow._closed_child_commission = lambda *a: None
        workflow.available_child_roles = lambda *a: ('scientific_process', 'literature')
        workflow.expanded_contract_form = lambda *a: events.append('expanded_form') or (deepcopy(SCHEMA), None)
        workflow.child_initial_report_input = lambda *a: json.dumps(INITIAL)
        workflow.resolver = lambda *a, **kw: (lambda *a: True)
        workflow.validate_report = lambda value, scope, **kw: events.append(('validate_report', deepcopy(value)))
        workflow.source_credit_view = lambda actual: events.append('original_credit') or {'credit': 0.375}
        workflow.controller_value = lambda actual, index, value: runtime.Record({'original_credit': value})
        workflow.launch_instructions = SimpleNamespace(materialize=lambda value: events.append(('materialize', value)))
        workflow.receive_form = lambda actual, form, schema, index, **kw: events.append(
            ('receive_form', deepcopy(form), index, kw)) or []
        prepared_assignment = {'controlled_assignment': 'same original port result'}
        prepared_process = {'controlled_process': 'same original port result'}
        def prepare(context, actual_role, assignment, scope, key, **kwargs):
            events.append(('prepare_invocation', actual_role, deepcopy(assignment), deepcopy(kwargs)))
            return {'assignment': prepared_assignment, 'scientific_process': prepared_process}
        def assignment(context, actual_role, value, scope, key):
            events.append(('prepare_assignment', actual_role, deepcopy(value)))
            return prepared_assignment
        def build(actual_role, key, objective, scope, **kwargs):
            events.append('build')
            assert kwargs['episode_assignment'] is prepared_assignment
            assert kwargs['scientific_process'] is (prepared_process if role == 'scientific_process' else None)
            request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(kwargs['parent'],
                objective=objective, result_contract=SCHEMA),
                runtime.Record({'scope': scope, 'initial_report': kwargs['initial']}), kwargs['contract'])
            path = kwargs['parent_path'] + ((actual_role, key),)
            child_binding = registry.for_child(source.path, actual_role)
            child_source = child_binding.decision_source_type(workflow, path, request, scope)
            built.append({'path': path, 'request': request.as_record(), 'assignment': kwargs['episode_assignment']})
            return runtime.Episode(workflow.grains[actual_role], key, child_source, request, forbidden)
        workflow.build = build
        selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(source.scope),
            'goal': 'Original child objective', 'purpose': 'Retain an unresolved qualification',
            'assignment': {'launch_instructions': None}}
        selector = module('child_message_owners')
        exchange = selector.exchange_for_parent(workflow, source, role)
        assert (exchange is None) == custom_registry
        events.clear()
        with ExitStack() as stack:
            scientific_binding = workflow.scientific_process_binding
            stack.enter_context(patch.object(scientific_binding, 'prepare_invocation', prepare))
            stack.enter_context(patch.object(scientific_binding, 'validate_execution_context',
                                             lambda *a: events.append('validate_execution_context')))
            stack.enter_context(patch.object(scientific_binding, 'allowed_children',
                                             lambda *a: ('scientific_process', 'literature')))
            for binding in registry._bindings:
                if getattr(binding, 'roles', ()) == ('literature',):
                    stack.enter_context(patch.object(binding, 'prepare_assignment', assignment))
            for callback in exchange or ():
                if callback is None:
                    continue
                def observed(*args, _callback=callback, **kwargs):
                    owners.append((_callback.__module__, _callback.__name__))
                    return _callback(*args, **kwargs)
                stack.enter_context(patch.object(import_module(callback.__module__), callback.__name__, observed))
            call = original_function('Workflow', 'selected') if original else runtime.Workflow.selected
            unit = call(workflow, source, deepcopy(selection), 7)
            form = {'qualification': 'invented'} if scenario == 'invalid-return' else INITIAL
            failure = None
            try:
                result = asyncio.run(unit.synthesize_report(runtime.Record({'form': form}), None, unit.child.request))
                if scenario == 'saved-return':
                    assert asyncio.run(unit.synthesize_report(runtime.Record({'form': form}), None,
                                                             unit.child.request)) == result
            except runtime.ReportDeliveryError as error:
                failure = error_record(error)
                result = unit.receive_failure(error).as_record()
            action = dict(workflow.journal.row('runtime_actions', source.episode_id, 7))
            attempts = [dict(row) for row in workflow.store.db.execute(
                'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
                (workflow.run_id, source.episode_id))]
        return {'events': events, 'owners': owners, 'built': built, 'action': action,
                'attempts': attempts, 'result': result, 'failure': failure,
                'last_outcome': source.last_outcome, 'last_outcome_index': source.last_outcome_index,
                'feedback': source.feedback}


def paired_exchange(directory, edge, scenario, *, custom_registry=False):
    old = connected_exchange(directory / 'old', edge, scenario, original=True, custom_registry=custom_registry)
    new = connected_exchange(directory / 'new', edge, scenario, original=False, custom_registry=custom_registry)
    assert {k: v for k, v in old.items() if k != 'owners'} == {k: v for k, v in new.items() if k != 'owners'}
    assert old['owners'] == []
    assert bool(new['owners']) is (not custom_registry)
    return new


def paired_report(directory, scenario, *, saved=False):
    """Compare real original/current facts after the same explicit late ports."""
    observations = []
    for old in (True, False):
        with actual_workflow(directory / str(old)) as workflow:
            source = root(workflow).source
            events = []
            source.report_basis = []
            source.last_outcome = None
            completion = SimpleNamespace(ended_by='controller', end_reason='controlled yield',
                                         units_consumed=2)
            if saved:
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': json.dumps({'credit': 0.25, 'interpretations': {'old': 'context'}}),
                    'form': None})
                def current(context):
                    events.append('current_report_facts')
                    return {'current_report_marker': 'authenticated current callback'}
                workflow.episode_bindings.current_report_facts = current
            else:
                def project(actual, **kwargs):
                    assert actual is source
                    events.append('credit')
                    if scenario == 'late-job':
                        workflow.is_job_source = lambda source: True
                    return {'credit': 0.375}
                workflow.source_credit_view = project
                workflow.pending_handles = lambda actual: events.append('pending') or ['owned-pending']
                workflow.native_timing_information = None
                workflow.resource_estimator = None
                workflow.project_annotation_score = None
                workflow.job_episodes = SimpleNamespace(facts=lambda actual, **kw:
                    events.append('late_job_facts') or {'job_marker': 'original late job body'})
                workflow.is_job_source = lambda actual: False
                late = SimpleNamespace(facts=lambda context, snapshot:
                    events.append('late_specialist_facts') or {'specialist_marker': 'original late body'})
                prior_snapshot = workflow.store.read_snapshot
                @contextmanager
                def snapshot():
                    events.append('snapshot')
                    with prior_snapshot():
                        if scenario == 'late-specialist':
                            workflow.specialist = lambda actual: late
                        yield
                workflow.store.read_snapshot = snapshot
                def received(context, *, completion_snapshot):
                    events.append('received_facts')
                    assert completion_snapshot['own_action_count'] == 2
                    return {'credit': 99} if scenario == 'conflict' else {'received_marker': 'original receipt'}
                workflow.episode_bindings.received_report_facts = received
            call = original_function('Workflow', 'facts') if old else module('runtime').Workflow.facts
            try:
                value = call(workflow, source, completion_record=completion)
            except ValueError as error:
                assert scenario == 'conflict'
                value = {'error': error_record(error)}
            observations.append((value, events))
    assert observations[0] == observations[1]
    return observations[1]


def paired_outgoing(directory, home, scenario):
    """Real own-axis registry/parents with a late runtime provider mutation."""
    runtime = module('runtime')
    role = 'scientific_process' if home == 'scientific_process' else 'literature'
    observations = []
    for old in (True, False):
        with actual_workflow(directory / str(old), factories=connected_factories(),
                             annotation_child_roles=('scientific_process', 'literature')) as workflow, ExitStack() as stack:
            annotation = root(workflow).source
            path = annotation.path + (('scientific_process', 'parent'),)
            request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(annotation.request.goal,
                objective='Original scientific parent', result_contract=SCHEMA),
                runtime.Record({'scope': annotation.scope, 'initial_report': INITIAL}))
            source = module('scientific_process/task').ScientificTask(workflow, path, request, annotation.scope)
            events = []
            scientific_binding = workflow.scientific_process_binding
            child_binding = workflow.episode_bindings.for_child(source.path, role)
            original_parse = runtime.parse_json_object
            original_validate = runtime.validate_form
            injected = RuntimeError('original late validator result')
            def parse(value):
                events.append('late_parse')
                if AXIS == 'a105' and role == 'literature':
                    workflow.specialist = lambda actual: SimpleNamespace(
                        prepare_child_request=lambda *args: events.append('late_assignment_provider') or args[-1])
                return original_parse(value)
            def validate(*args, **kwargs):
                events.append('late_validate')
                if scenario == 'late-validator-error':
                    raise injected
                return original_validate(*args, **kwargs)
            def expanded(*args):
                events.append('expanded_form')
                stack.enter_context(patch.object(runtime, 'parse_json_object', parse))
                stack.enter_context(patch.object(runtime, 'validate_form', validate))
                return deepcopy(SCHEMA), None
            workflow.expanded_contract_form = expanded
            workflow.child_initial_report_input = lambda *a: json.dumps(INITIAL)
            workflow.annotation_child_roles = ('scientific_process', 'literature')
            workflow.available_child_roles = lambda actual: ('scientific_process', 'literature')
            workflow.launch_instructions = SimpleNamespace(materialize=lambda value: events.append('materialize'))
            def prepare(context, actual_role, assignment, scope, key, **kwargs):
                events.append(('prepare_invocation', actual_role, deepcopy(kwargs)))
                return {'assignment': {'controlled': 'assignment'}, 'scientific_process': {'controlled': 'process'}}
            stack.enter_context(patch.object(scientific_binding, 'prepare_invocation', prepare))
            if role == 'literature':
                stack.enter_context(patch.object(child_binding, 'prepare_assignment',
                    lambda *a: events.append('prepare_assignment') or {'controlled': 'assignment'}))
            selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(source.scope),
                         'goal': 'Original child objective', 'purpose': 'Unresolved qualification',
                         'assignment': {'launch_instructions': None}}
            call = original_request() if old else module('scientific_process/to_child_' + home).prepare_request
            try:
                result = call(workflow, source, selection, 3)
                error = None
            except RuntimeError as caught:
                assert caught is injected
                result, error = None, error_record(caught)
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            observations.append((result, error, events))
    assert observations[0] == observations[1]
    return observations[1]
