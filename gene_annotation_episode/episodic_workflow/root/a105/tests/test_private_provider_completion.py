"""Exact retained/current A105 call expressions over controlled provider boundaries.

No application workflow, native process, model inference or scientific grading
is claimed. Original/current/fixed method bodies are captured source, not a
replacement provider policy. Every private home supplies its own actual bytes.
"""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from .provider_boundary_controls import exercise

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).with_name('fixtures') / 'provider_selector_v3'
MANIFEST = json.loads((FIXTURES / 'manifest.json').read_text())


def retained(name):
    raw = (FIXTURES / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST['files'][name]
    return raw


@pytest.mark.parametrize('home', MANIFEST['homes'])
def test_exact_original_current_private_completion_boundaries(home):
    # The exercised fixed bytes are the actual installed home, never a candidate
    # loaded from runs. Before installation this deliberately exposes missing
    # selector/capture prerequisites; its failure is not a behavioral pass.
    before = retained(home + '/task_decision.py.txt')
    result = exercise('a105', retained('runtime.py.txt'), retained('providers.py.txt'),
        (ROOT / 'providers.py').read_bytes(), before,
        (ROOT / home / 'task_decision.py').read_bytes(), MANIFEST['classes'][home])
    assert result['controlled_exact_method_boundary']
    assert result['controlled_provider_classes_from_captured_source']
    assert result['root_defining_import_observations']
    assert all(row['captures_match_defining_owners'] for row in result['root_defining_import_observations'])
    assert not result['real_provider_workflow_executed']
    assert {record['original_call'] for record in result['records']} == {'call', 'exchange_decision'}


@pytest.mark.parametrize('home', MANIFEST['homes'])
@pytest.mark.parametrize('call_name', ['call', 'exchange_decision'])
def test_retained_original_and_current_operand_identity(home, call_name):
    # Independent pre-repair proof of the original five operands and introduced
    # three-operand callee; executable original/current order probes are below.
    tree = ast.parse(retained(home + '/task_decision.py.txt'))
    cls, = [n for n in tree.body if isinstance(n, ast.ClassDef)
            and n.name == MANIFEST['classes'][home]]
    method, = [n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == call_name]
    current, = [n for n in ast.walk(method) if isinstance(n, ast.Call)
                and ast.unparse(n.func) == 'self.complete_decision']
    runtime = ast.parse(retained('runtime.py.txt'))
    source, = [n for n in runtime.body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    original_method, = [n for n in source.body if isinstance(n, ast.AsyncFunctionDef) and n.name == call_name]
    original, = [n for n in ast.walk(original_method) if isinstance(n, ast.Call)
                 and ast.unparse(n.func) == 'self.workflow.provider.complete']
    dump = lambda node: ast.dump(node, include_attributes=False)
    assert len(original.args) == 5 and not original.keywords and not current.keywords
    assert list(map(dump, current.args)) == list(map(dump, original.args[2:]))


@pytest.mark.parametrize('home', MANIFEST['homes'])
@pytest.mark.parametrize('call_name', ['call', 'exchange_decision'])
@pytest.mark.parametrize('scenario', ['getter_before_schema', 'provider_changed_by_schema',
                                    'episode_changed_by_schema', 'custom_complete'])
def test_actual_installed_call_preserves_original_lookup_and_operands(home, call_name, scenario):
    import asyncio
    from copy import deepcopy
    from types import MethodType, SimpleNamespace
    from .provider_boundary_controls import compiled, method, owner
    original = method(owner(retained('runtime.py.txt'), 'DecisionSource'), call_name)
    live = owner((ROOT / home / 'task_decision.py').read_bytes(), MANIFEST['classes'][home])
    actual = method(live, call_name)
    expressions = {}
    expressions['original'], = [n for n in ast.walk(original) if isinstance(n, ast.Call)
        and ast.unparse(n.func) == 'self.workflow.provider.complete']
    expressions['installed'], = [n for n in ast.walk(actual) if isinstance(n, ast.Call)
        and ast.unparse(n.func) in ('self.complete_decision', 'self.decision_completion()')]
    histories = {}
    for variant in ('original', 'installed'):
        events = []
        answer = object()
        wrong_answer = object()
        getter_error = LookupError('original getter')
        schema_error = ValueError('later schema')
        instructions, context, schema = object(), object(), object()
        episode, changed_episode = object(), object()
        async def selected(*args):
            events.append(('selected', args))
            return answer
        async def replacement(*args):
            events.append(('replacement', args))
            return wrong_answer
        class Provider:
            @property
            def complete(self):
                events.append('complete_lookup')
                if scenario == 'getter_before_schema':
                    raise getter_error
                return selected
            @property
            def complete_with_presentation(self):
                raise AssertionError('custom complete must not probe presentation')
        source = SimpleNamespace(episode_id=episode, workflow=SimpleNamespace(provider=Provider(),
            specialist=lambda source: pytest.fail('custom complete must not select renderer')))
        def project(value):
            assert value is schema
            events.append('schema')
            if scenario == 'getter_before_schema':
                raise schema_error
            if scenario == 'provider_changed_by_schema':
                source.workflow.provider = SimpleNamespace(complete=replacement)
            if scenario == 'episode_changed_by_schema':
                source.episode_id = changed_episode
            return value
        class Request:
            def __getitem__(self, name):
                events.append('request_' + name)
                return project(schema) if name == 'output_schema' else {'instructions': instructions, 'context': context}[name]
        namespace = {'_action_generation_schema': project}
        if variant == 'installed':
            helpers = [n for n in live.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name in ('complete_decision', 'decision_completion')]
            helper, = helpers
            setattr(source, helper.name, MethodType(compiled(helper, namespace), source))
        wrapper = ast.parse('async def invoke(self,instructions,context,schema,request):\n return None').body[0]
        wrapper.body[0] = ast.Return(ast.Await(deepcopy(expressions[variant])))
        invoke = compiled(wrapper, namespace)
        if scenario == 'getter_before_schema':
            with pytest.raises(LookupError) as caught:
                asyncio.run(invoke(source, instructions, context, schema, Request()))
            assert caught.value is getter_error
            assert events == ['complete_lookup']
        else:
            assert asyncio.run(invoke(source, instructions, context, schema, Request())) is answer
            assert events[-1] == ('selected', (episode, 'REASONING', instructions, context, schema))
        histories[variant] = [event if isinstance(event, str) else event[0] for event in events]
    assert histories['original'] == histories['installed']
