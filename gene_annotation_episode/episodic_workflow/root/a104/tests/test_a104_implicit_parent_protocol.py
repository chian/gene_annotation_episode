"""Original A104 parent protocol, live globals and real returned-unit boundaries.

These controls construct the real Store/ToolRegistry/Workflow/source/Journal and
use the original numerical controller. Fixed external results are engineering
ports, not scientific/native execution or an autonomy validation claim.
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
from types import FunctionType, SimpleNamespace
import textwrap
import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
FIXTURE = Path(__file__).parent / 'fixtures' / 'source_request_assembly' / 'a104_implicit_parent_original_runtime.txt'
PIN = 'e3227bc4c23bf0f5f60b311abc45d7d36929f95db789901acd1551c9e0f7b1bc'
def own(name): return importlib.import_module(PACKAGE + '.' + name)
def forbidden(*args, **kwargs): raise AssertionError('external_execution_not_part_of_parent_control')
def original_node(owner, name):
    data = FIXTURE.read_bytes(); assert hashlib.sha256(data).hexdigest() == PIN
    cls, = [n for n in ast.parse(data).body if isinstance(n, ast.ClassDef) and n.name == owner]
    fn, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(fn)
def original_function(owner, name):
    runtime = own('runtime')
    node = original_node(owner, name); node.decorator_list = []
    scratch = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(FIXTURE), 'exec'), scratch)
    fn = scratch[name]
    bound = FunctionType(fn.__code__, vars(runtime), fn.__name__, fn.__defaults__)
    bound.__kwdefaults__ = fn.__kwdefaults__
    return bound

@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)

@contextmanager
def actual_workflow(directory, *, workflow_type=None, receipts=False):
    runtime = own('runtime'); directory.mkdir(parents=True, exist_ok=True)
    with own('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        tools = own('tools').ToolRegistry(store)
        numerical = own('numerical')
        def controller(path, initial):
            return numerical.YieldController('parent-control', initial, .5, numerical.YieldParameters())
        receipt_options = ({'episode_record_receipts': True, 'initial_known_record_refs': []}
                           if receipts else {})
        workflow = (workflow_type or runtime.Workflow)(store, tools, object(), directory / 'workflow',
            'a104-parent-preservation', controller, lambda *_args, **_kwargs: 0.0,
            episode_binding_factories=(), decision_protocol=None, **receipt_options)
        yield workflow

def root(workflow):
    return workflow.build('annotation', 'root', 'Preserve the original unknown question', workflow.store.validate_scope())


def test_public_type_c3_exact_members_and_live_globals():
    runtime = own('runtime')
    data = FIXTURE.read_bytes(); assert hashlib.sha256(data).hexdigest() == PIN
    original, = [n for n in ast.parse(data).body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    assert runtime.DecisionSource.__module__ == runtime.__name__
    assert runtime.DecisionSource.__qualname__ == 'DecisionSource'
    assert runtime.DecisionSource.__bases__ == (object,)
    for node in original.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
        current = inspect.getattr_static(runtime.DecisionSource, node.name)
        assert current.__globals__ is vars(runtime)
        assert current.__qualname__ == 'DecisionSource.' + node.name
        candidate, = ast.parse(textwrap.dedent(inspect.getsource(current))).body
        assert ast.dump(candidate, include_attributes=False) == ast.dump(node, include_attributes=False)
    class Left(runtime.DecisionSource): pass
    class Right(runtime.DecisionSource): pass
    class Diamond(Left, Right): pass
    assert Diamond.__mro__ == (Diamond, Left, Right, runtime.DecisionSource, object)


def test_actual_root_construction_identity_and_saved_reconstruction(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        first = root(workflow)
        assert type(first.source) is own('episode').AnnotationTask
        assert isinstance(first.source, runtime.DecisionSource)
        assert workflow.specialist(first.source) is None
        expected = runtime.Episode.identity(workflow.context, workflow.grains['annotation'], 'root')
        assert first.source.episode_id == expected.episode_id
        saved = dict(workflow.journal.row('runtime_episodes', first.source.episode_id))
        assert json.loads(saved['request']) == runtime._plain(first.source.request.as_record())
        again = root(workflow)
        assert again.source.episode_id == first.source.episode_id
        assert dict(workflow.journal.row('runtime_episodes', first.source.episode_id)) == saved
        for build in (original_function('Workflow', 'build'), runtime.Workflow.build):
            with pytest.raises(runtime.WorkflowError, match='reconstructed immutable assignment differs'):
                build(workflow, 'annotation', 'root', 'Changed original question', first.source.scope)
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()


def test_custom_workflow_fallback_and_original_improvement_private_source(tmp_path):
    runtime = own('runtime')
    class CustomWorkflow(runtime.Workflow): pass
    with actual_workflow(tmp_path / 'custom', workflow_type=CustomWorkflow) as workflow:
        assert type(root(workflow).source) is runtime.DecisionSource
    with actual_workflow(tmp_path / 'ordinary') as workflow:
        original = original_function('Workflow', 'build')(
            workflow, 'improvement', 'existing', 'Original generic compatibility', workflow.store.validate_scope())
        item = workflow.build('improvement', 'existing', 'Original generic compatibility', workflow.store.validate_scope())
        assert type(original.source) is runtime.DecisionSource
        assert type(item.source) is own('annotation_improvement.episode').ImprovementTask
        assert item.source.path == original.source.path
        assert item.source.episode_id == original.source.episode_id
        assert item.source.request.as_record() == original.source.request.as_record()


def test_constructor_reads_rebound_original_global(tmp_path, monkeypatch):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        old = runtime._plain; calls = []
        def observed(value):
            calls.append(value)
            return old(value)
        monkeypatch.setattr(runtime, '_plain', observed)
        clone = own('episode').AnnotationTask(workflow, source.path, source.request, source.scope)
        assert calls and clone.report_values == source.report_values
        assert type(clone).__init__.__globals__ is vars(runtime)


@pytest.mark.parametrize('hook', ('specialist', 'is_job_source'))
def test_custom_hook_falls_back_without_evaluating_hook_in_selector(tmp_path, hook):
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        calls = []
        def callback(*args):
            calls.append(hook)
            raise AssertionError('selector_executed_custom_hook')
        setattr(workflow, hook, callback)
        assert own('episode').is_annotation_parent(workflow, source) is False
        assert calls == []


@pytest.mark.parametrize('method', ('call', 'execute'))
def test_midcall_path_change_retains_original_scientific_guard(tmp_path, monkeypatch, method):
    runtime = own('runtime'); traces = []
    class OriginalGuard(Exception): pass
    for original in (True, False):
        with actual_workflow(tmp_path / str(original)) as workflow:
            source = root(workflow).source
            events = []
            def guard(context):
                events.append(('validate', context.role))
                raise OriginalGuard('actual original Scientific validation')
            workflow.scientific_process_binding = SimpleNamespace(validate_execution_context=guard)
            old = workflow.journal.row
            def row(table, *args):
                if table == ('runtime_model_calls' if method == 'call' else 'runtime_actions'):
                    source.path = (('scientific_process', 'changed-by-original-port'),)
                    events.append(('row', table)); return None
                return old(table, *args)
            workflow.journal.row = row
            fn = original_function('DecisionSource', method) if original else getattr(type(source), method)
            args = ({}, {}) if method == 'call' else ({'kind': 'tool', 'tool': 'unused', 'arguments': {}}, 0)
            with pytest.raises(OriginalGuard, match='actual original Scientific validation'):
                asyncio.run(fn(source, *args))
            assert events[-1] == ('validate', 'scientific_process')
            traces.append(events)
    assert traces[0] == traces[1]


@pytest.mark.parametrize('status', ('completed', 'invalid', 'failed', 'unavailable'))
def test_actual_returned_unit_and_saved_action_keep_original_iterator(tmp_path, monkeypatch, status):
    runtime = own('runtime'); results = []
    # The original pending-work packet observes this clock. Supply the same
    # input to both executions while preserving every returned packet field.
    observed_time = '2026-11-13T00:00:00+00:00'
    monkeypatch.setattr(runtime, '_now', lambda: observed_time)
    for original in (True, False):
        with actual_workflow(tmp_path / str(original), receipts=True) as workflow:
            episode = root(workflow); source = episode.source
            if original:
                source.execute = original_function('DecisionSource', 'execute').__get__(source)
            action = {'kind': 'tool', 'tool': 'episode.estimate_wait', 'arguments': {
                'condition': {'version': 'event_condition_v1', 'events': [], 'reconsider_at': None}}}
            declared, = [entry for entry in workflow.catalog(source.scope, source=source)
                         if entry['name'] == action['tool']]
            assert workflow.receipts is not None
            runtime.Draft202012Validator(declared['input_schema']).validate(action['arguments'])
            # The real observation controller consumes a saved decision context.
            # This supplied response is a declared engineering port; unknown
            # expectations/timing remain unknown and no provider is invoked.
            decision_schema = workflow.action_schema(source)
            decision_context = {'execution_expectations': None}
            decision_response = {'selection': deepcopy(action), 'report_update': {}}
            runtime.Draft202012Validator(decision_schema).validate(decision_response)
            workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
                'call_index': 0, 'purpose': 'decision',
                'request': runtime._json({'context': decision_context, 'schema': decision_schema}),
                'response': runtime._json(decision_response)})
            saved_call = dict(workflow.journal.row('runtime_model_calls', source.episode_id, 0))
            workflow.provider = SimpleNamespace(complete=forbidden)
            call = original_function('DecisionSource', 'call') if original else type(source).call
            response, index, context, schema = asyncio.run(call(source, {}, {}))
            assert (response, index, context, schema) == (decision_response, 0, decision_context, decision_schema)
            assert source.calls == 1
            assert dict(workflow.journal.row('runtime_model_calls', source.episode_id, 0)) == saved_call
            outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [],
                       'feedback': {'category': 'controlled_original_return', 'status': status}}
            calls = []
            workflow.journal.measure = lambda *_args: nullcontext()
            workflow.execute = lambda *_args, **_kwargs: (calls.append('returned'), deepcopy(outcome))[1]
            workflow.receive_native_outcome = lambda *_args: None
            workflow.receive_outcome = lambda *_args: None
            async def scoring(_source, _index, result): return result
            workflow.automatic_score_updates = scoring
            unit = workflow.selected(source, deepcopy(action), 0)
            assert type(unit) is runtime.ActionLeaf
            async def next_unit(view, **kwargs):
                assert view.units_consumed == 0 and not kwargs
                return unit
            source.next = next_unit
            observed = asyncio.run(episode.run_unit_async(workflow.context, expected_label=unit.label))
            row = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
            observations = [dict(r) for r in workflow.store.db.execute('SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?', (workflow.run_id, source.episode_id))]
            assert len(observations) == 1 and calls == ['returned']
            assert runtime.observes_action_outcome('tool', status)
            assert json.loads(row['result'])['status'] == status and row['credit'] is not None
            assert json.loads(row['result'])['pending_work_after_action'] == {
                'version': 'pending_work_v2', 'captured_at': observed_time, 'items': []}
            replayed = asyncio.run(workflow.selected(source, deepcopy(action), 0).acquire_async(workflow.context))
            assert calls == ['returned']
            assert replayed.contribution.controller_input == observed.controller_input
            results.append((json.loads(row['action']), json.loads(row['result']), row['credit'], json.loads(observations[0]['observation'])))
    assert results[0] == results[1]


def test_original_no_receipt_annotation_rejects_tool_before_acquisition(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert workflow.receipts is None
        action = {'kind': 'tool', 'tool': 'controlled.parent_return', 'arguments': {}}
        outcomes = []
        workflow.execute = forbidden
        for selected in (original_function('Workflow', 'selected'), runtime.Workflow.selected):
            with pytest.raises(ValueError, match='^action_not_available_to_episode$') as error:
                selected(workflow, source, deepcopy(action), 0)
            outcomes.append((type(error.value), error.value.args))
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()
        assert outcomes[0] == outcomes[1]


def test_replaced_public_source_constructor_is_not_overridden(tmp_path, monkeypatch):
    runtime = own('runtime')
    original = runtime._annotation_original_decision_source
    class CallerSource(original): pass
    monkeypatch.setattr(runtime, 'DecisionSource', CallerSource)
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert type(source) is CallerSource
        assert own('episode').AnnotationTask.__bases__ == (original,)


@pytest.mark.parametrize('owner', ('workflow', 'source'))
def test_domain_selector_does_not_invoke_rebound_attribute_protocol(tmp_path, monkeypatch, owner):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        cls = type(workflow) if owner == 'workflow' else type(source)
        calls = []
        def getter(self, name):
            calls.append(name)
            raise AssertionError('selector_invoked_custom_getattribute')
        with monkeypatch.context() as changed:
            changed.setattr(cls, '__getattribute__', getter)
            assert own('episode').is_annotation_parent(workflow, source) is False
            assert calls == []


def test_actual_report_facts_snapshot_matches_original(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        original = original_function('Workflow', 'facts')(workflow, source, completion_record=None)
        current = runtime.Workflow.facts(workflow, source, completion_record=None)
        assert current == original
        assert current['credit'] == 0.0
        assert current['committed_record_refs'] == current['changed_record_refs'] == []
        assert current['subject_refs'] == source.scope['subject_refs']
