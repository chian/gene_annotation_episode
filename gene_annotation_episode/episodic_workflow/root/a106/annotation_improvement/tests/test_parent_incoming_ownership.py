"""Improvement-owned incoming request admission controls."""
import pytest
from ...tests.test_implicit_annotation_parent import no_external
from ...tests.parent_incoming_checks import (
    check_incoming_constructor_original_inputs_errors_and_order,
    check_incoming_direct_class_identity_and_genuine_typed_request,
    check_incoming_preserves_live_schema_rebinding_after_message_callback,
)


@pytest.mark.parametrize('case', ['null', 'report', 'invalid_schema', 'message_failure'])
def test_incoming_constructor_original_inputs_errors_and_order(tmp_path, monkeypatch, case):
    check_incoming_constructor_original_inputs_errors_and_order(tmp_path, monkeypatch, 'annotation_improvement.', case)


def test_incoming_direct_class_identity_and_genuine_typed_request(tmp_path):
    check_incoming_direct_class_identity_and_genuine_typed_request(tmp_path, 'annotation_improvement.')


def test_incoming_preserves_live_schema_rebinding_after_message_callback(tmp_path, monkeypatch):
    check_incoming_preserves_live_schema_rebinding_after_message_callback(tmp_path, monkeypatch, 'annotation_improvement.')
