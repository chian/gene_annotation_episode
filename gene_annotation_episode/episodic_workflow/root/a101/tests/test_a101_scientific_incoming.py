"""Original connected Scientific saved/failure/nonreceipt custody on six edges.

Actual parent/child constructors, registry and selected callbacks are exercised.
Filled Scientific context and downstream receiving remain explicit supplied
ports; no model, native acquisition or Scientific instruction execution occurs.
"""
import pytest
from .test_a101_implicit_parent_protocol import no_external_execution, own
from .a101_scientific_incoming_checks import ROUTES, genuine_host, observe, original_rows




@pytest.mark.parametrize('route', ROUTES, ids=[row[0] for row in ROUTES])
def test_optional_scientific_counterpart_does_not_read_custom_metaclass(tmp_path, route):
    home, _, role, _, _ = route
    with genuine_host(tmp_path, route) as (workflow, source, binding):
        module = own('scientific_process.to_child_' + home)
        prepare = module.prepare_request if role == 'literature' else module.prepare_commission
        selector = own('scientific_process.incoming_message_owners').admission_for_prepared_request
        assert selector(workflow, source, prepare, role) is not None
        calls = []
        class CustomMeta(type):
            @property
            def __mro__(cls):
                calls.append('custom_mro')
                raise AssertionError('optional_selector_invoked_custom_metaclass')
        class UnknownCandidate(metaclass=CustomMeta): pass
        registry = workflow.episode_bindings
        original = registry._by_role[role]
        registry._by_role[role] = [*original, UnknownCandidate()]
        try:
            assert selector(workflow, source, prepare, role) is None
            assert calls == []
        finally:
            registry._by_role[role] = original
