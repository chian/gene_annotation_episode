"""Existing annotation-improvement's actual incoming constructor boundary."""
import pytest

from ...tests.test_a101_implicit_parent_protocol import no_external_execution
from ...tests.a101_incoming_constructor_checks import (
    check_original_constructor_order, check_real_request_and_defining_owner,
    check_late_live_schema_callback,
)


@pytest.mark.parametrize('case', ('null', 'report', 'invalid_schema', 'message_failure'))
def test_improvement_incoming_original_order(tmp_path, monkeypatch, case):
    check_original_constructor_order(tmp_path, monkeypatch, 'annotation_improvement.', case)


def test_improvement_incoming_real_request_and_owner(tmp_path):
    check_real_request_and_defining_owner(tmp_path, 'annotation_improvement.')


def test_improvement_incoming_live_schema(tmp_path, monkeypatch):
    check_late_live_schema_callback(tmp_path, monkeypatch, 'annotation_improvement.')
