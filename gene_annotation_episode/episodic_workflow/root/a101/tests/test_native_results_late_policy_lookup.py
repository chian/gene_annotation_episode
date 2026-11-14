"""Controlled dynamic lookup over the original captured result-reader fixture.

No native work, receipt authentication, source acquisition or Workflow claimed.
The required original policy/late-return files remain separate and unchanged.
"""
from types import MethodType

from .test_native_results_policy_boundaries import selected


def test_subclass_super_credit_retains_dynamic_facts_and_identity(selected):
    s = selected
    original = type(s.host)
    events = []

    class Specialized(original):
        def facts(self, context):
            assert context is s.context
            events.append('facts')
            return {'execution_result_refs': ['record-a']}

        def result_identity(self, reference, scope):
            assert scope is s.context.scope
            events.append(('identity', reference))
            return 'stable-' + reference

        def credit_view(self, context, selection):
            events.append('entry')
            return super().credit_view(context, selection)

    host = object.__new__(Specialized)
    host.__dict__.update(s.host.__dict__)
    del host.result_identity
    answer = host.credit_view(s.context, {'known_record_refs': ['record-a'],
                                         'initial_known_record_refs': []})
    assert answer['credit'] == 2.5
    assert answer['new_acquired_record_count'] == 1
    assert events == ['entry', 'facts', ('identity', 'record-a')]


def test_replacing_instance_facts_after_first_credit_changes_next_read(selected):
    s = selected
    selection = {'known_record_refs': ['record-a'], 'initial_known_record_refs': []}
    def first(self, context):
        assert self is s.host and context is s.context
        return {'execution_result_refs': []}
    def second(self, context):
        assert self is s.host and context is s.context
        return {'execution_result_refs': ['record-a']}
    s.host.facts = MethodType(first, s.host)
    assert s.host.credit_view(s.context, selection)['credit'] == 0
    s.host.facts = MethodType(second, s.host)
    assert s.host.credit_view(s.context, selection)['credit'] == 2.5


def test_completion_reloads_reader_and_selected_action_on_each_call(selected):
    s = selected
    s.host._own_bodies = lambda context: iter(())
    assert s.host.completion(s.context) is None
    assert s.calls == []
    s.host._own_bodies = lambda context: iter([s.body])
    result = s.host.completion(s.context)
    assert result['operation_key'] == s.body['operation_key']
    assert s.calls == [(s.context.episode_id, s.body['operation_key'],
                        s.body['tool_name'], s.body['arguments'])]
    assert result['receipt_sha256'] == s.module.digest(s.body)

    expected_args = (s.context.episode_id, s.body['operation_key'],
                     s.body['tool_name'], s.body['arguments'])
    events = []
    def current_bodies(context):
        assert context is s.context
        events.append(('bodies', context))
        yield s.body
    def no_result(*args):
        assert args == expected_args
        assert args[3] is s.body['arguments']
        events.append(('action', 'none', args))
        return {'result': None}
    s.host._own_bodies = current_bodies
    s.host.owner._selected_result_action = no_result
    assert s.host.completion(s.context) is None
    assert events == [('bodies', s.context), ('action', 'none', expected_args)]
    assert s.calls == [expected_args]

    events.clear()
    def empty_result(*args):
        assert args == expected_args
        assert args[3] is s.body['arguments']
        events.append(('action', 'empty', args))
        return {'result': {}}
    s.host.owner._selected_result_action = empty_result
    assert s.host.completion(s.context) == result
    assert events == [('bodies', s.context), ('action', 'empty', expected_args)]
    assert s.calls == [expected_args]


def test_policy_globals_and_retained_custody_owner_identity(selected):
    s = selected
    host = type(s.host)
    assert host.__module__ == s.module.__name__
    for name in ('__init__', 'resolve', 'result_identity', 'execute', '_validate_body'):
        assert host.__dict__[name].__module__ == s.module.__name__
    assert host.credit_view.__globals__['ContractError'] is s.module.ContractError
    assert host.credit_view.__globals__['plain'] is s.module.plain
    assert host.credit_view.__globals__['VERSION'] == s.module.VERSION
    assert host.facts.__globals__['ORIGIN'] is s.module.ORIGIN
    assert host.facts.__globals__['FAMILY_SOURCES'] is s.module.FAMILY_SOURCES
    assert host.completion.__globals__['digest'] is s.module.digest
