"""Original private Resource walker and six actual named proof receivers.

The adapter result-reader callback is an explicit port. Its original selection,
error and returned reference semantics remain real; no native work is launched.
"""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from .hierarchy_oracles import PACKAGE, original_resource_received

HOMES = ('resource_work_submission', 'scientific_process/resource_work_submission')
KINDS = ('api', 'local', 'hpc')


def observe(home, kind, before, mode):
    module = import_module(PACKAGE + '.' + home.replace('/', '.') + '.received_messages')
    current = module.ResourceReceivedMessages.received_form_references
    call = original_resource_received(home) if before else current
    events, owners = [], []
    source = object.__new__(module.ResourceReceivedMessages)
    failure = RuntimeError('original returned handoff callback failure')
    context = object()
    key = 'same original operation'

    class CustomHandoff(dict):
        def get(self, name, default=None):
            events.append(('custom_handoff_get', name))
            return super().get(name, default)

    def receive(actual_context, handoff, schema, actual_key):
        assert actual_context is context and actual_key == key
        events.append(('callback', deepcopy(handoff), schema))
        if mode == 'error':
            raise failure
        return ['proof:b', 'proof:a', 'proof:b']

    adapter = SimpleNamespace() if mode == 'missing' else SimpleNamespace(received_form_references=receive)
    def select(value):
        events.append(('adapter', deepcopy(value)))
        return adapter
    source._adapter = select
    handoff = {'resource_selection': {'kind': kind}, 'original_input': 17}
    if mode == 'custom':
        handoff = CustomHandoff(handoff)
    form = {'rows': [{'value': handoff}]}
    schema = {'properties': {'rows': {'items': {'properties': {
        'value': {'x-source': 'execution_handoff'}}}}}}
    owner = import_module(PACKAGE + '.' + home.replace('/', '.') + '.from_child_' + kind + '_resource_work_execution')
    actual = owner.receive_handoff
    def observed(*args):
        owners.append(actual.__module__)
        return actual(*args)
    with patch.object(owner, 'receive_handoff', observed):
        try:
            value = call(source, context, form, schema, key)
            result = ('returned', value)
        except Exception as error:
            result = ('raised', type(error), str(error), error is failure)
    return result, events, owners


def check_receivers(mode):
    for home in HOMES:
        for kind in KINDS:
            old = observe(home, kind, True, mode)
            new = observe(home, kind, False, mode)
            assert old[:2] == new[:2] and old[2] == []
            assert bool(new[2]) is (mode != 'custom')
            if mode in ('value', 'custom'):
                assert new[0] == ('returned', ['proof:a', 'proof:b'])
                assert [event[0] for event in new[1]] == ['adapter', 'callback']
            elif mode == 'missing':
                assert new[0][1:3] == (ValueError, 'resource_information_handoff_proof_missing')
                assert [event[0] for event in new[1]] == ['adapter']
            else:
                assert new[0][-1] is True
                assert [event[0] for event in new[1]] == ['adapter', 'callback']


def check_receiver_native_namespace():
    for home in HOMES:
        module = import_module(PACKAGE + '.' + home.replace('/', '.') + '.received_messages')
        method = module.ResourceReceivedMessages.received_form_references
        for kind in KINDS:
            owner = import_module(PACKAGE + '.' + home.replace('/', '.') + '.from_child_' + kind + '_resource_work_execution')
            for getter in (owner._get_getattr, owner._get_ValueError):
                assert getter.__globals__ is method.__globals__
                assert getter.__builtins__ is method.__builtins__
        assert module._handoff_receiver({'resource_selection': {'kind': 'undeclared'}}) is None
        class CustomKind(str):
            def __eq__(self, value):
                raise AssertionError('new selector compared a custom kind')
        class CustomKey(str):
            def __hash__(self):
                return str.__hash__(self)
            def __eq__(self, value):
                raise AssertionError('new selector compared a custom key')
        custom = {CustomKey('resource_selection'): {'kind': 'api'}}
        assert module._handoff_receiver(custom) is None
        assert module._handoff_receiver({'resource_selection': {'kind': CustomKind('api')}}) is None
