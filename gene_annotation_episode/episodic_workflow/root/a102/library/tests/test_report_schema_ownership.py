"""Finite policy assembly/override checks; no new scientific workflow cohort."""
from types import MethodType, SimpleNamespace
import pytest
from .report_schema_checks import (action_schema, facts, host, invoke, original,
    paired, report_observation, runtime, schema_observation)






@pytest.mark.parametrize('kind', ['class-method', 'instance-callable', 'nominal-selected'])
def test_private_selection_preserves_override(kind):
    events = []
    marker = RuntimeError('original override identity')
    source = object()
    def chosen(workflow, actual, **kwargs):
        assert actual is source
        events.append(('selected', kwargs))
        return marker
    def override(actual, **kwargs):
        assert actual is source
        events.append(('override', kwargs))
        return marker
    workflow = SimpleNamespace()
    if kind == 'nominal-selected':
        bound = MethodType(chosen, workflow)
    elif kind == 'class-method':
        def method(self, actual, **kwargs):
            return override(actual, **kwargs)
        bound = MethodType(method, workflow)
    else:
        bound = override
    assert invoke(bound, chosen, source, completion_record=None) is marker
    assert events == [('selected' if kind == 'nominal-selected' else 'override', {'completion_record': None})]
