"""Actual own call-expression/selector controls; serial transport is controlled.

These execute the retained call/exchange expression and the real private helper,
not a replacement compatibility helper or an entire scientific workflow.
"""
import ast
import asyncio
from copy import deepcopy
import importlib
import inspect
from pathlib import Path
import textwrap
from types import MethodType, SimpleNamespace

import pytest

BASE = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]
AXIS = BASE.rsplit('.', 1)[1]
HOMES = (('execution_progress_assessment', 'scientific_process.execution_progress_assessment')
    if AXIS == 'a101' else tuple(sorted(str(p.parent.relative_to(ROOT)).replace('/', '.')
        for p in ROOT.rglob('episode.py') if 'class LiteratureEpisode(' in p.read_text())))


def selected_expression(owner, method):
    tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(owner, method))))
    expressions = [node for node in ast.walk(tree) if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func) in ('self.complete_decision', 'self.decision_completion()')]
    expression, = expressions
    return deepcopy(expression)


def exercise(home, method, case, monkeypatch):
    providers = importlib.import_module(BASE + '.providers')
    binding_module = importlib.import_module(BASE + '.' + home + '.episode')
    binding = getattr(binding_module, 'MonitorEpisode' if AXIS == 'a101' else 'LiteratureEpisode')
    owner = binding.decision_source_type
    events = []; deliveries = []; result = object(); other_result = object()
    callback_error = RuntimeError('original callback sentinel')
    getter_error = LookupError('original complete getter sentinel')
    forbidden = AssertionError('custom presentation or descriptor was invoked')
    episode = object(); changed_episode = object()
    instructions, context, schema = object(), object(), object()
    expected = (episode, 'REASONING', instructions, context, schema)

    async def custom(*args):
        events.append('custom'); deliveries.append((args, {}))
        if case == 'custom_exception': raise callback_error
        return result

    async def custom_method(self, *args): return await custom(*args)

    def tracked(self, name):
        if name == 'complete':
            events.append('get_complete')
            if case == 'raising_complete': raise getter_error
        if name == 'complete_with_presentation': raise forbidden
        return object.__getattribute__(self, name)

    class Meta(type):
        def __getattribute__(self, name):
            if name == '__dict__': raise forbidden
            return type.__getattribute__(self, name)

    attributes = {'__getattribute__': tracked}
    if case == 'custom_instance_dict':
        def get_dict(self): raise forbidden
        attributes['__dict__'] = property(get_dict)
    cls = (Meta if case == 'custom_metaclass' else type)('ControlledModel',
        (providers.ModelConnection,), attributes)
    if case in ('custom_return', 'custom_exception', 'blocked_presentation_lookup'):
        cls.complete = custom_method
    if case == 'base_complete': monkeypatch.setattr(providers.ModelConnection, 'complete', custom_method)
    if case == 'base_presentation': monkeypatch.setattr(providers.ModelConnection, 'complete_with_presentation', custom_method)
    if case == 'property_complete':
        def get_complete(self): events.append('complete_property'); return custom
        cls.complete = property(get_complete)
    if case == 'raising_presentation':
        def get_presentation(self): raise forbidden
        cls.complete_with_presentation = property(get_presentation)
    if case == 'descriptor_presentation':
        class Descriptor:
            def __get__(self, instance, kind): raise forbidden
        cls.complete_with_presentation = Descriptor()
    provider = object.__new__(cls)
    if case == 'unrelated_borrowed_complete':
        provider = object.__new__(type('OtherProvider', (), {'__getattribute__': tracked}))
        provider.complete = MethodType(providers.ModelConnection.complete, provider)
        provider.complete_with_presentation = MethodType(providers.ModelConnection.complete_with_presentation, provider)
    provider.worker_lock = asyncio.Lock()

    async def serial(self, *args, **kwargs):
        events.append('serial'); deliveries.append((args, kwargs)); return result
    provider._complete_serial = MethodType(serial, provider)
    if case == 'instance_complete': provider.complete = custom
    if case == 'callable_complete':
        class Callable:
            def __getattribute__(self, name):
                if name in ('__func__', '__self__'): raise forbidden
                return object.__getattribute__(self, name)
            async def __call__(self, *args): return await custom(*args)
        provider.complete = Callable()
    if case == 'instance_presentation': provider.complete_with_presentation = custom
    if case == 'instance_original_shadow':
        provider.complete_with_presentation = providers.ModelConnection.complete_with_presentation
    if case == 'nonstring_key':
        class Key:
            def __hash__(self): return hash('complete_with_presentation')
            def __eq__(self, other): raise forbidden
        # Use the authentic object dictionary rather than invoking any override.
        providers.ModelConnection.__dict__['__dict__'].__get__(provider)[Key()] = object()
    if case == 'custom_dict_methods':
        class CustomDict(dict):
            def __contains__(self, key): raise forbidden
            def items(self): raise forbidden
        descriptor = providers.ModelConnection.__dict__['__dict__']
        descriptor.__set__(provider, CustomDict(descriptor.__get__(provider)))
    source = object.__new__(owner)
    source.episode_id = episode
    renderer_cases = {'default', 'custom_instance_dict', 'custom_dict_methods', 'mutate_provider', 'mutate_episode'}
    def specialist(actual):
        assert actual is source and case in renderer_cases
        events.append('specialist'); return binding
    source.workflow = SimpleNamespace(provider=provider, specialist=specialist)
    async def replacement(*args): return other_result
    def project(actual):
        assert actual is schema
        events.append('schema_operand')
        if case == 'raising_complete': raise AssertionError('arguments evaluated before complete lookup')
        if case == 'mutate_provider': source.workflow.provider = SimpleNamespace(complete=replacement)
        if case == 'mutate_episode': source.episode_id = changed_episode
        return actual
    class Request:
        def __getitem__(self, key):
            events.append('request_' + key)
            return project(schema) if key == 'output_schema' else {'instructions': instructions, 'context': context}[key]
    # Compile only the expression read from the actual own method. Helper lookup
    # and its provider selection remain the real private class implementation.
    wrapper = ast.parse('async def invoke(self, instructions, context, schema, request):\n    return None\n')
    wrapper.body[0].body[0].value = selected_expression(owner, method)
    namespace = {'_action_generation_schema': project}
    exec(compile(ast.fix_missing_locations(wrapper), '<actual-own-private-call-expression>', 'exec'), namespace)
    try:
        actual = asyncio.run(namespace['invoke'](source, instructions, context, schema, Request()))
    except BaseException as error:
        assert error is (getter_error if case == 'raising_complete' else callback_error)
        assert case in ('raising_complete', 'custom_exception')
    else:
        assert case not in ('raising_complete', 'custom_exception') and actual is result
    if case == 'raising_complete':
        assert events == ['get_complete'] and deliveries == []
        return
    assert events.count('get_complete') == 1 and events[0] == 'get_complete'
    operand_events = ['schema_operand'] if method == 'call' else [
        'request_instructions', 'request_context', 'request_output_schema', 'schema_operand']
    offset = 2 if case == 'property_complete' else 1
    assert events[offset:offset + len(operand_events)] == operand_events
    assert len(deliveries) == 1
    args, kwargs = deliveries[0]
    assert len(args) == 5 and args[1] == 'REASONING'
    assert all(a is b for i, (a, b) in enumerate(zip(args, expected)) if i != 1)
    assert kwargs == ({'prompt_renderer': binding.decision_prompt_renderer} if case in renderer_cases else {})
    assert events.count('specialist') == (1 if case in renderer_cases else 0)


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('method', ['call', 'exchange_decision'])
@pytest.mark.parametrize('case', ['default', 'custom_return', 'custom_exception'])
def test_each_private_call_preserves_provider_authority(home, method, case, monkeypatch):
    exercise(home, method, case, monkeypatch)


@pytest.mark.parametrize('method', ['call', 'exchange_decision'])
@pytest.mark.parametrize('case', ['base_complete', 'instance_complete', 'callable_complete',
    'property_complete', 'raising_complete', 'raising_presentation', 'descriptor_presentation',
    'instance_presentation', 'instance_original_shadow', 'custom_instance_dict', 'nonstring_key',
    'custom_metaclass', 'mutate_provider', 'mutate_episode', 'blocked_presentation_lookup',
    'base_presentation', 'unrelated_borrowed_complete', 'custom_dict_methods'])
def test_descriptor_and_argument_order_at_actual_call_expression(method, case, monkeypatch):
    exercise(HOMES[0], method, case, monkeypatch)
