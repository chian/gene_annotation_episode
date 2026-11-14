"""Shared original-body oracle for the two A101 private incoming owners.

Consumers are root annotation tests and annotation_improvement/tests. These
checks use real Workflow/Store/identity and typed requests. Observation probes
expose malformed message/schema boundaries without claiming a child execution.
"""
import inspect
from types import SimpleNamespace

import pytest

from .test_a101_implicit_parent_protocol import (
    actual_workflow, original_function, own,
)


def check_original_constructor_order(tmp_path, monkeypatch, home, case):
    runtime = own('runtime')
    original = original_function('DecisionSource', '__init__')
    current = own(home + 'from_parent').__init__
    role = 'improvement' if home else 'annotation'
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
              'required': ['ready'], 'additionalProperties': False}
    with actual_workflow(tmp_path) as workflow:
        scope = workflow.store.validate_scope()
        contract = None if case == 'null' else runtime.TypedReportContract(
            'Original ready form', schema, lambda *_: True)
        request = runtime.EpisodeRequest(
            runtime.EpisodeGoal.root(objective='Preserve original incoming request',
                                     result_contract={'role': role}),
            runtime.Record({'scope': scope, 'initial_report': {'ready': True}}), contract)
        old_identity = runtime.Episode.identity
        old_plain, old_schema = runtime._plain, runtime.interpretation_schema
        observations = []
        for function in (original, current):
            events = []
            def identity(*args, **kwargs):
                events.append('identity')
                return old_identity(*args, **kwargs)
            def plain(value):
                events.append('plain')
                return old_plain(value)
            def interpretation(value):
                events.append('interpretation_schema')
                return old_schema(value)
            monkeypatch.setattr(runtime, 'Episode', SimpleNamespace(identity=identity))
            monkeypatch.setattr(runtime, '_plain', plain)
            monkeypatch.setattr(runtime, 'interpretation_schema', interpretation)
            class Message:
                def as_record(self):
                    events.append('as_record')
                    if case == 'message_failure':
                        raise ValueError('controlled_original_message_failure')
                    return request.message.as_record()
            class Contract:
                @property
                def schema(self):
                    events.append('schema')
                    return {'type': 'array'} if case == 'invalid_schema' else schema
            class RequestProbe:
                @property
                def message(self):
                    events.append('message')
                    return Message()
                @property
                def report_contract(self):
                    events.append('report_contract')
                    return None if case == 'null' else Contract()
            source = object.__new__(runtime.DecisionSource)
            error = None
            try:
                function(source, workflow, ((role, 'incoming'),), RequestProbe(), scope)
            except Exception as caught:
                error = (type(caught), str(caught))
            state = dict(vars(source))
            state.pop('request')
            observations.append((state, error, events))
        assert observations[0] == observations[1]
        state, error, events = observations[0]
        assert events[:3] == ['identity', 'message', 'as_record']
        if case == 'message_failure':
            assert error == (ValueError, 'controlled_original_message_failure')
            assert events == ['identity', 'message', 'as_record']
            assert 'report_values' not in state and 'interpret_schema' not in state
        else:
            # _plain visits the mapping and its Boolean value separately.
            expected = ['plain', 'plain', 'report_contract']
            if case != 'null':
                expected += ['report_contract', 'schema', 'interpretation_schema']
            assert events[3:] == expected
            assert state['report_values'] == {'ready': True}
            if case == 'invalid_schema':
                assert error is not None and 'interpret_schema' not in state
            else:
                assert error is None
                assert state['interpret_schema'] == (
                    runtime._object({}) if case == 'null' else old_schema(schema))
        assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def check_real_request_and_defining_owner(tmp_path, home):
    runtime = own('runtime')
    owner = own(home + 'from_parent')
    cls = own(home + 'episode').ImprovementTask if home else own('episode').AnnotationTask
    assert inspect.getattr_static(cls, '__init__') is owner.__init__
    assert owner.__init__.__globals__ is vars(runtime)
    assert inspect.getsourcefile(owner.__init__) == owner.__file__
    if not home:
        assert inspect.getattr_static(runtime.DecisionSource, '__init__') is owner.__init__
        assert owner.__init__.__module__ == runtime.__name__
        assert owner.__init__.__qualname__ == 'DecisionSource.__init__'
    with actual_workflow(tmp_path) as workflow:
        role = 'improvement' if home else 'annotation'
        scope = workflow.store.validate_scope()
        schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
                  'required': ['ready'], 'additionalProperties': False}
        request = runtime.EpisodeRequest(
            runtime.EpisodeGoal.root(objective='Admit original request', result_contract={'role': role}),
            runtime.Record({'scope': scope, 'initial_report': {'ready': True}}),
            runtime.TypedReportContract('Original ready form', schema, lambda *_: True))
        before = object.__new__(runtime.DecisionSource)
        original_function('DecisionSource', '__init__')(
            before, workflow, ((role, 'incoming'),), request, scope)
        after = cls(workflow, ((role, 'incoming'),), request, scope)
        assert vars(before) == vars(after)
        assert after.request is request and after.scope is scope
        assert after.report_values == {'ready': True}
        assert after.interpret_schema == runtime.interpretation_schema(schema)


def check_late_live_schema_callback(tmp_path, monkeypatch, home):
    runtime = own('runtime')
    role = 'improvement' if home else 'annotation'
    with actual_workflow(tmp_path) as workflow:
        scope = workflow.store.validate_scope()
        old_plain, old_schema = runtime._plain, runtime.interpretation_schema
        observations = []
        for function in (original_function('DecisionSource', '__init__'), own(home + 'from_parent').__init__):
            events = []
            def changed_schema(value):
                events.append(('changed_schema', value))
                raise RuntimeError('original_late_schema_callback')
            def plain(value):
                events.append('plain')
                monkeypatch.setattr(runtime, 'interpretation_schema', changed_schema)
                return old_plain(value)
            monkeypatch.setattr(runtime, '_plain', plain)
            monkeypatch.setattr(runtime, 'interpretation_schema', old_schema)
            request = SimpleNamespace(message=runtime.Record({'initial_report': {'ready': True}}),
                                      report_contract=SimpleNamespace(schema={'original': 'schema port'}))
            source = object.__new__(runtime.DecisionSource)
            with pytest.raises(RuntimeError, match='^original_late_schema_callback$'):
                function(source, workflow, ((role, 'incoming'),), request, scope)
            state = dict(vars(source))
            state.pop('request')
            observations.append((state, events))
        assert observations[0] == observations[1]
        assert observations[0][1] == ['plain', 'plain', ('changed_schema', {'original': 'schema port'})]
        assert 'report_values' in observations[0][0] and 'interpret_schema' not in observations[0][0]
