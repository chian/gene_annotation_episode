"""A106 current/original boundaries; controlled ports are named explicitly.

Real Store, ToolRegistry, Workflow, Journal, parent source, binding registry,
configured child constructors and typed report contract are used. These controls
do not select science, a model, native work, or a full restored workflow.
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
from types import SimpleNamespace, FunctionType
import textwrap
import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
FIXTURES = Path(__file__).parent / 'fixtures' / 'implicit_annotation_parent'
ROUTES = {'launch': 'execution_job_submission', 'monitor': 'execution_progress_assessment',
          'results': 'execution_result_acquisition', 'literature': 'published_evidence_assessment',
          'scientific_process': 'scientific_process'}

def module(name): return importlib.import_module(PACKAGE + '.' + name)
def forbidden(*args, **kwargs): raise AssertionError('unselected_external_or_scientific_port')
def shape(n): return ast.dump(n, include_attributes=False)

def original_tree():
    pins = json.loads((FIXTURES / 'sources.json').read_text())
    data = (FIXTURES / 'runtime.py.source').read_bytes()
    assert hashlib.sha256(data).hexdigest() == pins['runtime']['sha256']
    return ast.parse(data)

def original_member(owner, name):
    cls, = [n for n in original_tree().body if isinstance(n, ast.ClassDef) and n.name == owner]
    item, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(item)

def original_function(owner, name):
    namespace = dict(vars(module('runtime')))
    tree = ast.Module(body=[original_member(owner, name)], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), str(FIXTURES / 'runtime.py.source'), 'exec'), namespace)
    before = namespace[name]
    value = FunctionType(before.__code__, vars(module('runtime')), before.__name__, before.__defaults__)
    value.__kwdefaults__ = before.__kwdefaults__
    return value

def original_class():
    cls, = [n for n in original_tree().body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    namespace = dict(vars(module('runtime')))
    exec(compile(ast.Module(body=[deepcopy(cls)], type_ignores=[]), str(FIXTURES / 'runtime.py.source'), 'exec'), namespace)
    cls = namespace['DecisionSource']
    for name, before in tuple(vars(cls).items()):
        if not inspect.isfunction(before): continue
        value = FunctionType(before.__code__, vars(module('runtime')), before.__name__, before.__defaults__)
        value.__kwdefaults__ = before.__kwdefaults__
        value.__qualname__ = before.__qualname__
        setattr(cls, name, value)
    return cls

@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)

@contextmanager
def actual_workflow(directory, *, cls=None):
    directory.mkdir(parents=True, exist_ok=True)
    rt = module('runtime')
    with module('state').Store(directory / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        tools = module('tools').ToolRegistry(store)
        numerical = module('numerical')
        def controller(path, initial, **kwargs):
            return numerical.YieldController('a106_original_boundary', initial, 0.5,
                numerical.YieldParameters(uncertainty_alpha=0.05))
        workflow = (cls or rt.Workflow)(store, tools, SimpleNamespace(complete=forbidden),
            directory / 'workflow', 'a106-parent-preservation', controller,
            lambda *_args, **_kwargs: 0.0, decision_protocol=None,
            episode_binding_factories=())
        yield workflow

def root(workflow, key='root'):
    return workflow.build('annotation', key, 'Preserve the original unknown', workflow.store.validate_scope())

def predecessor_source(workflow, source):
    return original_class()(workflow, source.path, source.request, source.scope)

def failure(error):
    return {'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'diagnostic': getattr(error, 'diagnostic', None),
            'feedback': getattr(error, 'feedback', None)}

def test_public_class_members_live_globals_and_c3():
    rt = module('runtime')
    old = original_class()
    assert rt.DecisionSource.__bases__ == (object,)
    assert rt.DecisionSource.__module__ == rt.__name__
    for name, before in vars(old).items():
        if not inspect.isfunction(before): continue
        after = vars(rt.DecisionSource)[name]
        assert after.__globals__ is vars(rt), name
        assert after.__name__ == before.__name__ and after.__qualname__ == before.__qualname__
        assert after.__defaults__ == before.__defaults__ and after.__kwdefaults__ == before.__kwdefaults__
        actual, = ast.parse(textwrap.dedent(inspect.getsource(after))).body
        assert shape(actual) == shape(original_member('DecisionSource', name))
    class Left(rt.DecisionSource): pass
    class Right(rt.DecisionSource): pass
    class Diamond(Left, Right): pass
    assert Diamond.__mro__ == (Diamond, Left, Right, rt.DecisionSource, object)

def test_actual_constructor_saved_request_and_goal(tmp_path):
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert type(source) is module('episode').AnnotationTask
        assert source.path == (('annotation', 'root'),)
        assert source.request.goal.as_record()['objective'] == 'Preserve the original unknown'
        reconstructed = root(workflow).source
        assert reconstructed.episode_id == source.episode_id
        assert reconstructed.request.as_record() == source.request.as_record()
        with pytest.raises(module('runtime').WorkflowError, match='reconstructed immutable assignment differs'):
            workflow.build('annotation', 'root', 'Changed original goal', source.scope)

def test_actual_custom_workflow_keeps_original_source(tmp_path):
    rt = module('runtime')
    class CustomWorkflow(rt.Workflow): pass
    with actual_workflow(tmp_path, cls=CustomWorkflow) as workflow:
        assert type(root(workflow).source) is rt.DecisionSource

def test_rebound_public_source_factory_retains_original_selection(tmp_path, monkeypatch):
    rt = module('runtime')
    original = rt._annotation_original_DecisionSource
    class CallerSource(original): pass
    monkeypatch.setattr(rt, 'DecisionSource', CallerSource)
    with actual_workflow(tmp_path) as workflow:
        assert type(root(workflow).source) is CallerSource
    assert module('episode').AnnotationTask.__bases__ == (original,)

def test_existing_private_instance_keeps_original_fallback_after_rebinding(tmp_path, monkeypatch):
    rt = module('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert type(source) is module('episode').AnnotationTask
        previous = workflow.specialist
        workflow.specialist = lambda value: previous(value)
        monkeypatch.setattr(rt, 'DecisionSource', lambda *_args: forbidden())
        workflow.journal.row = lambda *_args: {'request': json.dumps({'schema': {}, 'context': {}}),
            'purpose': 'wrong_original_purpose', 'response': None}
        with pytest.raises(rt.WorkflowError, match='saved decision contract differs'):
            asyncio.run(source.call({}, {}))

@pytest.mark.parametrize('hook', ['specialist', 'is_job_source'])
def test_rebound_original_hook_is_not_called_early(tmp_path, hook):
    rt = module('runtime')
    traces = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            events = []
            previous = getattr(workflow, hook)
            def traced(source):
                events.append(hook)
                return previous(source)
            setattr(workflow, hook, traced)
            method = original_function('Workflow', 'build') if original else rt.Workflow.build
            episode = method(workflow, 'annotation', 'root', 'Original goal', workflow.store.validate_scope())
            assert type(episode.source) is rt.DecisionSource
            traces.append((events, episode.source.request.as_record()))
    assert traces[0] == traces[1]

def test_selector_does_not_call_custom_comparison_or_job_property():
    rt, owner = module('runtime'), module('episode')
    workflow = object.__new__(rt.Workflow)
    workflow.episode_bindings = module('episode_bindings').EpisodeBindingRegistry()
    class Name(str):
        def __eq__(self, other): forbidden()
        __hash__ = str.__hash__
    class Jobs:
        @property
        def roles(self): forbidden()
    workflow.job_episodes = Jobs()
    assert owner.owns_annotation_root(workflow, Name('annotation'), (), None) is False
    assert owner.owns_annotation_root(workflow, 'annotation', (), None) is False

@pytest.mark.parametrize('where', ['workflow', 'registry', 'source'])
def test_optional_selector_does_not_call_instance_dict_subclass(tmp_path, where):
    owner = module('episode')
    class State(dict):
        def get(self, *args, **kwargs): forbidden()
        def __contains__(self, key): forbidden()
        def __iter__(self): forbidden()
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        target = {'workflow': workflow, 'registry': workflow.episode_bindings, 'source': source}[where]
        target.__dict__ = State(vars(target))
        assert owner.is_annotation_parent(workflow, source) is False
        if where != 'source':
            assert owner.owns_annotation_root(workflow, 'annotation', (), None) is False

def test_actual_constructor_dict_subclass_retains_original_fallback(tmp_path):
    rt = module('runtime')
    class State(dict):
        def get(self, *args, **kwargs): forbidden()
        def __contains__(self, key): forbidden()
    records = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            workflow.__dict__ = State(vars(workflow))
            build = original_function('Workflow', 'build') if original else rt.Workflow.build
            episode = build(workflow, 'annotation', 'root', 'Original goal', workflow.store.validate_scope())
            assert type(episode.source) is rt.DecisionSource
            records.append(episode.source.request.as_record())
    assert records[0] == records[1]

def test_original_global_rebinding_reaches_moved_constructor(tmp_path, monkeypatch):
    rt = module('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        events = []
        previous = rt._plain
        def plain(value):
            events.append(value)
            return previous(value)
        monkeypatch.setattr(rt, '_plain', plain)
        moved = rt.DecisionSource(workflow, source.path, source.request, source.scope)
        assert events and moved.report_values == source.report_values
        assert rt.DecisionSource.__init__.__globals__['_plain'] is plain

@pytest.mark.parametrize('method', ['call', 'execute'])
def test_mid_call_path_change_retains_original_scientific_validation(tmp_path, method):
    observations = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            if original: source = predecessor_source(workflow, source)
            events = []
            previous = workflow.journal.row
            def row(table, *keys):
                events.append(('row', table))
                source.path = (('annotation', 'root'), ('scientific_process', 'callback_change'))
                return previous(table, *keys)
            def validate(context):
                events.append(('validate', context.path))
                raise RuntimeError('original_scientific_validation_after_callback')
            workflow.journal.row = row
            workflow.scientific_process_binding = SimpleNamespace(validate_execution_context=validate)
            with pytest.raises(RuntimeError, match='original_scientific_validation_after_callback'):
                if method == 'call': asyncio.run(source.call({}, {}))
                else: asyncio.run(source.execute({'kind': 'tool', 'tool': 'unselected', 'arguments': {}}, 3))
            observations.append(events)
            assert events[-1][0] == 'validate'
    assert observations[0] == observations[1]

def test_mid_call_global_exception_rebinding_is_live(tmp_path, monkeypatch):
    rt = module('runtime')
    class ReboundOriginalFailure(RuntimeError): pass
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            if original: source = predecessor_source(workflow, source)
            def row(*args):
                monkeypatch.setattr(rt, 'WorkflowError', ReboundOriginalFailure)
                return {'request': json.dumps({'schema': {}, 'context': {}}),
                        'purpose': 'wrong_original_purpose', 'response': None}
            workflow.journal.row = row
            with pytest.raises(ReboundOriginalFailure, match='saved decision contract differs'):
                asyncio.run(source.call({}, {}))

@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
@pytest.mark.parametrize('saved', [False, True])
def test_returned_or_saved_action_keeps_observation_and_failure(tmp_path, status, saved):
    rt = module('runtime')
    observations = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            if original: source = predecessor_source(workflow, source)
            events = []
            workflow.journal.measure = lambda *_args: nullcontext()
            selection = {'kind': 'tool', 'tool': 'controlled.return', 'arguments': {}}
            returned = {'status': status, 'record_refs': [], 'changed_record_refs': [],
                        'feedback': {'category': 'controlled_original_outcome', 'status': status}}
            def execute(*args, **kwargs):
                events.append('execute')
                return deepcopy(returned)
            workflow.execute = execute
            workflow.receive_native_outcome = lambda *_args: events.append('native_custody')
            workflow.receive_outcome = lambda *_args: events.append('outcome_custody')
            async def score(_source, _index, value):
                events.append('score_port')
                return value
            workflow.automatic_score_updates = score
            workflow.pending_work = lambda *_args: []
            workflow.controller_value = lambda _source, index, credit: {'index': index, 'credit': credit}
            if saved:
                workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                    'decision_index': 4, 'action': rt._json(selection), 'result': rt._json(returned), 'credit': None})
            try:
                value = {'returned': asyncio.run(source.execute(selection, 4))}
            except rt.ActionFailure as error:
                value = {'failure': failure(error)}
            row = dict(workflow.journal.row('runtime_actions', source.episode_id, 4))
            observations.append((value, row, source.feedback, source.last_outcome, events))
            assert events.count('execute') == (0 if saved else 1)
            assert source.last_outcome_index == 4 and source.last_outcome['status'] == status
    assert observations[0] == observations[1]

@pytest.mark.parametrize('kind', ['list', 'dict_subclass'])
def test_credit_invalid_snapshot_precedes_dispatch(tmp_path, kind):
    class Dictionary(dict): pass
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        workflow.specialist = forbidden
        workflow.is_job_source = forbidden
        for fn in (original_function('Workflow', 'source_credit_view'), module('runtime').Workflow.source_credit_view):
            with pytest.raises(TypeError, match='credit_binding_snapshot_must_be_dict'):
                fn(workflow, source, binding_snapshot=[] if kind == 'list' else Dictionary())

@pytest.mark.parametrize('port', ['ordinary', 'original_task', 'journal_failure', 'factory_failure'])
def test_controller_original_identity_journal_factory_order(tmp_path, monkeypatch, port):
    rt, numerical = module('runtime'), module('numerical')
    observations = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            events = []
            prior_identity, prior_row = rt.Episode.identity, workflow.journal.row
            def identity(*args, **kwargs):
                events.append('identity')
                return prior_identity(*args, **kwargs)
            def row(*args):
                events.append('journal')
                if port == 'journal_failure': raise RuntimeError('original_journal_failure')
                return prior_row(*args)
            def factory(path, initial, **kwargs):
                events.append('factory')
                if port == 'factory_failure': raise RuntimeError('original_factory_failure')
                return numerical.YieldController('original', initial, 0.5,
                    numerical.YieldParameters(uncertainty_alpha=0.05))
            if port == 'original_task': factory.requires_original_task = True
            workflow.journal.row, workflow.controller_factory = row, factory
            fn = original_function('Workflow', 'controller') if original else rt.Workflow.controller
            with monkeypatch.context() as patch:
                patch.setattr(rt.Episode, 'identity', staticmethod(identity))
                try:
                    controller = fn(workflow, source.path)
                    value = (type(controller).__name__, controller.controller.cost,
                             controller.controller.settings.as_record())
                except RuntimeError as error:
                    value = failure(error)
            assert events[:2] == ['identity', 'journal']
            observations.append((value, events))
    assert observations[0] == observations[1]

@pytest.mark.parametrize('saved', [False, True])
def test_report_actual_saved_and_fresh_body(tmp_path, saved):
    observations = []
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            if original: source = predecessor_source(workflow, source)
            if saved:
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': module('runtime')._json({'credit': 2.0, 'interpretations': {'original': True}}),
                    'form': module('runtime')._json({'ready': True})})
            fn = original_function('Workflow', 'facts') if original else module('runtime').Workflow.facts
            observations.append(fn(workflow, source))
    assert observations[0] == observations[1]

# This existing permanent fixture constructs the actual complete A106 families.
# Its source pin is retained by the packager; no replacement child is introduced.
from .test_private_multi_parent_construction import full_workflow

@pytest.mark.parametrize('role,home', list(ROUTES.items()))
def test_real_child_registry_and_invalid_scope_boundary(full_workflow, monkeypatch, role, home):
    store, workflow = full_workflow
    monkeypatch.setattr(workflow, 'project_credit', lambda *_args, **_kwargs: 0.0)
    numerical = module('numerical')
    monkeypatch.setattr(workflow, 'controller_factory', lambda _path, initial, **_kwargs:
        numerical.YieldController('a106_actual_child_boundary', initial, 0.5,
            numerical.YieldParameters(uncertainty_alpha=0.05)))
    source = root(workflow, 'route_' + role).source
    child = workflow.episode_bindings.for_child(source.path, role)
    assert child.binding_path == home
    assert workflow.episode_bindings.for_path(source.path + ((role, 'child'),)) is child
    exchange = module('child_message_owners').exchange_for_child(workflow, source, role)
    assert exchange[0] is module('to_child_' + home).prepare_request
    assert exchange[1] is module('from_child_' + home).admit_return
    assert exchange[2] is module('from_child_' + home).admit_unowned_return
    before = store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
    selection = {'kind': 'episode_child', 'role': role,
        'scope': {'subject_refs': ['unavailable_subject_boundary']},
        'goal': 'Preserve original invalid request', 'purpose': 'Original failure',
        'assignment': {}, 'schema_json': '{}', 'initial_report_json': '{}'}
    try: store.validate_scope(selection['scope'], parent_scope=source.scope)
    except Exception as error: expected_scope_failure = failure(error)
    else: pytest.fail('fixture_scope_must_be_rejected_by_real_store')
    results = []
    for original in (True, False):
        actual_source = predecessor_source(workflow, source) if original else source
        fn = original_function('Workflow', 'selected') if original else module('runtime').Workflow.selected
        try: fn(workflow, actual_source, deepcopy(selection), 17)
        except Exception as error:
            assert not isinstance(error, AssertionError)
            results.append(failure(error))
        else: pytest.fail('invalid_scope_was_not_rejected')
    assert results[0] == results[1]
    assert results[0] == expected_scope_failure
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == before

@pytest.mark.parametrize('role,home', list(ROUTES.items()))
@pytest.mark.parametrize('saved', ['fresh', 'invalid', 'form', 'failure', 'unowned', 'unowned_invalid'])
def test_private_admission_retains_typed_failure_and_saved_custody(role, home, saved):
    rt = module('runtime')
    selection = original_member('Workflow', 'selected')
    unowned = saved.startswith('unowned')
    old, = [n for n in selection.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ('report' if unowned else 'admitted_report')]
    if unowned:
        boundary, = [i for i, n in enumerate(old.body) if isinstance(n, ast.If) and ast.unparse(n.test) == 'child_exchange is not None']
        old = ast.FunctionDef(name='admit_unowned_return', args=old.args, body=old.body[boundary+1:], decorator_list=[])
    else:
        old.body = old.body[1:]  # Main's already-authenticated conditional dispatcher.
        old.name = 'admit_return'
    old.args = ast.parse('def f(self, source, child, index, schema, contract, result, request): pass').body[0].args
    namespace = dict(vars(rt))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[old], type_ignores=[])), '<original-admission>', 'exec'), namespace)
    observations = []
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
              'required': ['ready'], 'additionalProperties': False}
    name = 'admit_unowned_return' if unowned else 'admit_return'
    for fn in (namespace[name], getattr(module('from_child_' + home), name)):
        events = []
        class Ports:
            run_id = 'controlled-original'
            episode_branch_lifecycle = rt.EPISODE_BRANCH_LIFECYCLE
            def __init__(self):
                self.journal = SimpleNamespace(row=lambda *_args: {'result': None})
                self.store = SimpleNamespace(db=SimpleNamespace(execute=self.query))
            def query(self, sql, args):
                events.append(('saved_read', sql, args))
                row = None if saved in ('fresh', 'invalid', 'unowned', 'unowned_invalid') else {
                    'failure': json.dumps({'category': 'original_failure'}) if saved == 'failure' else None,
                    'form': json.dumps({'ready': True}), 'decision_index': 8,
                    'contract': json.dumps({'measurements': {'schema': schema}})}
                return SimpleNamespace(fetchone=lambda: row)
            def save_attempt(self, *args, **kwargs): events.append(('save_attempt', args, kwargs))
            def receive_form(self, *args, **kwargs):
                events.append(('receive_form', args[1:], kwargs))
                return ['original_received_reference']
            def delivery_feedback(self, delivery_ref, error):
                return {'delivery_ref': delivery_ref, **error.diagnostic}
        ports = Ports()
        source = SimpleNamespace(episode_id='parent')
        child = SimpleNamespace(source=SimpleNamespace(episode_id='child'))
        request = SimpleNamespace(goal=SimpleNamespace(goal_id='goal'))
        contract = rt.TypedReportContract('Original readiness', schema, lambda *_args: True)
        result = rt.Record({'form': {'ready': 'invalid_boolean' if 'invalid' in saved else True}})
        try: value = fn(ports, source, child, 8, schema, contract, result, request)
        except rt.ReportDeliveryError as error: value = ('failure', error.feedback.as_record())
        observations.append((value, events))
    assert observations[0] == observations[1]
    if 'invalid' in saved or saved == 'failure':
        assert observations[0][0][0] == 'failure'
