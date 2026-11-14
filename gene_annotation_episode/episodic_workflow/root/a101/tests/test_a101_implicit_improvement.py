"""A101's existing improvement source and its original conditional failures.

Actual constructors, Store, Journal, typed request and continuation controller
are used. Supplied returned results exercise the iterator, not wait execution,
native work, model autonomy or successful nested scientific credit.
"""
import ast
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import inspect
import json
import textwrap
import pytest

from .test_a101_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node, own, root,
)


from .a101_implicit_parent_test_context import improvement_workflow, improvement


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_original_nested_improvement_credit_rejection_preserves_request_order(tmp_path, monkeypatch, parent_role):
    runtime = own('runtime')
    context = actual_workflow(tmp_path) if parent_role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        source = (root(workflow) if parent_role == 'annotation' else improvement(workflow)).source
        schema = runtime._object({'unresolved': {'type': 'boolean'}})
        selection = {'kind': 'child', 'scope': runtime._plain(source.scope),
            'goal': 'Inspect this original unresolved annotation question',
            'purpose': 'Return its actual unresolved state', 'schema_json': json.dumps(schema),
            'initial_report_json': '{"unresolved":true}'}
        owner = own(('annotation_improvement.' if parent_role == 'improvement' else '') + 'to_child_annotation_improvement')
        prepare = owner.prepare_request
        entries = []
        def traced(*args, **kwargs):
            entries.append((args[3], args[5]))
            return prepare(*args, **kwargs)
        monkeypatch.setattr(owner, 'prepare_request', traced)
        outcomes = []
        for original in (True, False):
            entries.clear(); workflow.store.db.execute('SAVEPOINT original_improvement_request')
            try:
                with monkeypatch.context() as changed:
                    if original:
                        changed.setattr(workflow, 'build', original_function('Workflow', 'build').__get__(workflow))
                    selected = original_function('Workflow', 'selected') if original else runtime.Workflow.selected
                    with pytest.raises(ValueError, match='^scientific_task_credit_not_declared:improvement$') as error:
                        selected(workflow, source, deepcopy(selection), 0)
                assert entries == ([] if original else [(0, 'improvement')])
                assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0] == 1
                assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
                outcomes.append((type(error.value), error.value.args))
            finally:
                workflow.store.db.execute('ROLLBACK TO original_improvement_request')
                workflow.store.db.execute('RELEASE original_improvement_request')
        assert outcomes[0] == outcomes[1]
