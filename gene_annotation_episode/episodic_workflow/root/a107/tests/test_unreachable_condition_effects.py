"""Exact retained condition effects, using authenticated original source inputs.

These controls execute only impossible If conditions. They do not instantiate
scientific owners, call native operations, validate restoration, or claim autonomy.
"""
from __future__ import annotations
import ast
import copy
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
AXIS = HERE.parent
FIXTURE = HERE / 'fixtures/organization_original/unreachable_condition_bodies.json'
dump = lambda node: ast.dump(node, include_attributes=False)


class ConditionFailure(RuntimeError):
    pass


def observe(source, asynchronous, case):
    events = []
    class Truth:
        def __bool__(self):
            events.append('comparison_truth')
            raise ConditionFailure('comparison_truth_failed')
    class Role:
        def __eq__(self, other):
            events.append(['compare', other])
            if case == 'comparison_error':
                raise ConditionFailure('comparison_failed')
            if case == 'comparison_truth_error':
                return Truth()
            return other == {'match_launch': 'launch', 'match_hpc': 'hpc', 'match_second': 'hpc_execution'}.get(case, 'other')
    class Parent:
        @property
        def role(self):
            events.append('parent_role')
            if case == 'property_error':
                raise ConditionFailure('parent_role_failed')
            return Role()
    class Row:
        def __getitem__(self, key):
            events.append(['row_getitem', key])
            if case == 'row_missing':
                raise KeyError(key)
            if case == 'row_error':
                raise ConditionFailure('row_lookup_failed')
            return None if case == 'row_response_none' else {'recorded': 'response'}
    def forbidden(*args, **kwargs):
        events.append('forbidden_operation')
        raise AssertionError('an impossible body or skipped predicate was evaluated')
    statement, = ast.parse(source).body
    shell = ast.parse(('async ' if asynchronous else '') + 'def controlled(parent, row):\n    pass\n').body[0]
    shell.body = [statement, ast.Return(ast.Constant('continued'))]
    module = ast.fix_missing_locations(ast.Module(body=[shell], type_ignores=[]))
    namespace = {'is_compact_assignment': forbidden, 'is_compact_launch': forbidden,
        'plain': forbidden, 'self': object()}
    exec(compile(module, '<exact-original-condition-control>', 'exec'), namespace)
    try:
        result = namespace['controlled'](Parent(), None if case == 'row_none' else Row())
        if asynchronous:
            try:
                result.send(None)
            except StopIteration as completed:
                result = completed.value
            else:
                raise AssertionError('unexpected suspension from impossible-body control')
        outcome = {'return': result}
    except Exception as error:
        outcome = {'error_type': type(error).__name__, 'error_args': error.args}
    return {'events': events, 'outcome': outcome}


class UnreachableConditionEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_bytes())
        assert cls.fixture['version'] == 'a107_impossible_body_original_controls_v1'
        assert len(cls.fixture['guards']) == 60

    def test_all_retained_conditions_have_exact_source_and_body_inverse(self):
        for row in self.fixture['guards']:
            with self.subTest(home=row['home'], function=row['function'], predicate=row['test']):
                original, = ast.parse(row['original_source']).body
                candidate, = ast.parse(row['candidate_source']).body
                self.assertEqual(dump(original), row['before_AST'])
                self.assertEqual(dump(candidate), row['after_AST'])
                self.assertEqual(dump(original.test), dump(candidate.test))
                self.assertEqual([dump(item) for item in original.orelse], [dump(item) for item in candidate.orelse])
                self.assertEqual(len(candidate.body), 1)
                self.assertIsInstance(candidate.body[0], ast.Pass)
                restored = copy.deepcopy(candidate); restored.body = copy.deepcopy(original.body)
                self.assertEqual(dump(original), dump(restored))
                path = AXIS / row['home'] / Path(row['path']).name
                owner, = [item for item in ast.parse(path.read_bytes()).body if isinstance(item, ast.ClassDef) and item.name == row['class']]
                function, = [item for item in owner.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == row['function']]
                actual, = [item for item in ast.walk(function) if isinstance(item, ast.If) and ast.unparse(item.test) == row['test']]
                self.assertEqual(dump(actual), row['after_AST'])

    def test_parent_lookup_comparison_truth_and_errors_preserved(self):
        cases = ('match_launch', 'match_hpc', 'match_second', 'no_match', 'property_error', 'comparison_error', 'comparison_truth_error')
        for row in self.fixture['guards']:
            if not row['test'].startswith('parent.role'):
                continue
            for case in cases:
                with self.subTest(home=row['home'], function=row['function'], case=case):
                    before = observe(row['original_source'], row['asynchronous'], case)
                    after = observe(row['candidate_source'], row['asynchronous'], case)
                    self.assertEqual(before, after)
                    self.assertNotIn('forbidden_operation', before['events'])
                    self.assertEqual(before['events'][0], 'parent_role')
                    if case in {'property_error', 'comparison_error', 'comparison_truth_error'}:
                        self.assertEqual(before['outcome']['error_type'], 'ConditionFailure')
                    else:
                        self.assertEqual(before['outcome'], {'return': 'continued'})

    def test_original_row_short_circuit_and_lookup_failures_preserved(self):
        cases = ('row_none', 'row_response_none', 'row_response_present', 'row_missing', 'row_error')
        for row in self.fixture['guards']:
            if row['function'] != 'call':
                continue
            for case in cases:
                with self.subTest(home=row['home'], case=case):
                    before = observe(row['original_source'], row['asynchronous'], case)
                    self.assertEqual(before, observe(row['candidate_source'], row['asynchronous'], case))
                    self.assertEqual(before['events'], [] if case == 'row_none' else [['row_getitem', 'response']])
                    if case in {'row_missing', 'row_error'}:
                        self.assertEqual(before['outcome']['error_type'], 'KeyError' if case == 'row_missing' else 'ConditionFailure')
                    else:
                        self.assertEqual(before['outcome'], {'return': 'continued'})


if __name__ == '__main__':
    unittest.main()
