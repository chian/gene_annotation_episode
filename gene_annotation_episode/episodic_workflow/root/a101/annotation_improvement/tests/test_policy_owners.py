"""Improvement's actual shared-form selection; common oracle stays shared."""
from ...tests.test_a101_parent_policy_owners import check_parent_form_callbacks_and_complete_result
from ...tests.test_a101_implicit_parent_protocol import no_external_execution


def test_improvement_form_callbacks_and_complete_result(tmp_path, monkeypatch):
    check_parent_form_callbacks_and_complete_result(tmp_path, monkeypatch, 'improvement')
