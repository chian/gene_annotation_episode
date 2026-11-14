"""The organizational successor preserves actual undeclared nested credit/yield."""
from ...tests.hierarchy_identity_checks import check_nested_improvement_refusals


def test_original_nested_credit_and_task_aware_continuation_refusals(tmp_path):
    check_nested_improvement_refusals(tmp_path / 'nested-limits')
