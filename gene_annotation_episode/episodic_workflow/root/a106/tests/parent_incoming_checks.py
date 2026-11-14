"""A106 incoming constructor placement: original admission/order, not execution.

Real Workflow, Store, identity and valid EpisodeRequest/typed contract inputs
are used. Malformed message/schema and a live-global callback are explicitly
controlled boundary inputs. No source selection, credit or receipt guard is
bypassed to claim a supported commissioned child.
"""
import inspect
from types import SimpleNamespace

import pytest

from .test_implicit_annotation_parent import (
    actual_workflow, module, original_function, failure, no_external,
)


def check_incoming_constructor_original_inputs_errors_and_order(tmp_path, monkeypatch, home, case):
    rt = module('runtime')
    current = module(home + 'from_parent').__init__
    original = original_function('DecisionSource', '__init__')
    role = 'improvement' if home else 'annotation'
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
              'required': ['ready'], 'additionalProperties': False}
    with actual_workflow(tmp_path) as workflow:
        scope = workflow.store.validate_scope()
        goal = rt.EpisodeGoal.root(objective='Preserve original incoming request', result_contract={'role': role})
        contract = None if case == 'null' else rt.TypedReportContract('Original ready form', schema, lambda *_: True)
        request = rt.EpisodeRequest(goal, rt.Record({'scope': scope, 'initial_report': {'ready': True}}), contract)
        old_identity, old_plain, old_schema = rt.Episode.identity, rt._plain, rt.interpretation_schema
        observed = []
        for callback in (original, current):
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
            monkeypatch.setattr(rt, 'Episode', SimpleNamespace(identity=identity))
            monkeypatch.setattr(rt, '_plain', plain)
            monkeypatch.setattr(rt, 'interpretation_schema', interpretation)
            class Message:
                def as_record(self):
                    events.append('as_record')
                    if case == 'message_failure': raise ValueError('controlled_original_message_failure')
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
            # Valid inputs are real typed requests; probes add observation only
            # and expose malformed boundary inputs rejected by the same body.
            probe = RequestProbe()
            source = object.__new__(rt.DecisionSource)
            error = None
            try: callback(source, workflow, ((role, 'incoming'),), probe, scope)
            except Exception as caught: error = failure(caught)
            state = dict(vars(source)); state.pop('request')
            observed.append((state, error, events))
        assert observed[0] == observed[1]
        state, error, events = observed[0]
        assert events[:3] == ['identity', 'message', 'as_record']
        if case == 'message_failure':
            assert error['message'] == 'controlled_original_message_failure'
            assert 'report_values' not in state and 'interpret_schema' not in state
            assert events == ['identity', 'message', 'as_record']
        elif case == 'invalid_schema':
            assert error is not None and 'report_values' in state and 'interpret_schema' not in state
            assert events[3:] == ['plain', 'plain', 'report_contract', 'report_contract', 'schema', 'interpretation_schema']
        else:
            assert error is None and state['report_values'] == {'ready': True}
            assert state['interpret_schema'] == (rt._object({}) if case == 'null' else old_schema(schema))
            assert events[3:] == (['plain', 'plain', 'report_contract'] if case == 'null' else
                ['plain', 'plain', 'report_contract', 'report_contract', 'schema', 'interpretation_schema'])
        assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def check_incoming_direct_class_identity_and_genuine_typed_request(tmp_path, home):
    rt = module('runtime')
    owner = module(home + 'from_parent')
    cls = module(home + 'episode').ImprovementTask if home else module('episode').AnnotationTask
    assert inspect.getattr_static(cls, '__init__') is owner.__init__
    assert owner.__init__.__globals__ is vars(rt)
    if not home:
        assert inspect.getattr_static(rt.DecisionSource, '__init__') is owner.__init__
        assert owner.__init__.__qualname__ == 'DecisionSource.__init__'
    with actual_workflow(tmp_path) as workflow:
        role = 'improvement' if home else 'annotation'
        scope = workflow.store.validate_scope()
        schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
                  'required': ['ready'], 'additionalProperties': False}
        contract = rt.TypedReportContract('Original ready form', schema, lambda *_: True)
        request = rt.EpisodeRequest(rt.EpisodeGoal.root(objective='Admit original request', result_contract={'role': role}),
                                   rt.Record({'scope': scope, 'initial_report': {'ready': True}}), contract)
        before = object.__new__(rt.DecisionSource)
        original_function('DecisionSource', '__init__')(before, workflow, ((role, 'incoming'),), request, scope)
        after = cls(workflow, ((role, 'incoming'),), request, scope)
        assert vars(before) == vars(after)
        assert after.request is request and after.interpret_schema == rt.interpretation_schema(schema)
        assert after.report_values == {'ready': True}


def check_incoming_preserves_live_schema_rebinding_after_message_callback(tmp_path, monkeypatch, home):
    rt = module('runtime')
    role = 'improvement' if home else 'annotation'
    current = module(home + 'from_parent').__init__
    original = original_function('DecisionSource', '__init__')
    with actual_workflow(tmp_path) as workflow:
        scope = workflow.store.validate_scope()
        old_plain, old_schema = rt._plain, rt.interpretation_schema
        observed = []
        for callback in (original, current):
            events = []
            def changed_schema(value):
                events.append(('changed_schema', value))
                raise RuntimeError('original_late_schema_callback')
            def plain(value):
                events.append('plain')
                monkeypatch.setattr(rt, 'interpretation_schema', changed_schema)
                return old_plain(value)
            monkeypatch.setattr(rt, 'interpretation_schema', old_schema)
            monkeypatch.setattr(rt, '_plain', plain)
            request = SimpleNamespace(message=rt.Record({'initial_report': {'ready': True}}),
                                      report_contract=SimpleNamespace(schema={'original': 'schema port'}))
            source = object.__new__(rt.DecisionSource)
            with pytest.raises(RuntimeError, match='^original_late_schema_callback$'):
                callback(source, workflow, ((role, 'incoming'),), request, scope)
            state = dict(vars(source)); state.pop('request')
            observed.append((state, events))
        assert observed[0] == observed[1]
        assert observed[0][1] == ['plain', 'plain', ('changed_schema', {'original': 'schema port'})]
        assert 'report_values' in observed[0][0] and 'interpret_schema' not in observed[0][0]
