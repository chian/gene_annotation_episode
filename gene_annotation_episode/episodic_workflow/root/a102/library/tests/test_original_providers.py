"""Actual private owner boundaries against exact own-axis original methods."""
import pytest
from . import provider_checks as checks


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_constructor_keeps_original_late_identity_plain_order(failure):
    checks.check_task_boundary('constructor', failure)


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_received_references_keep_original_provider_identity(failure):
    checks.check_task_boundary('references', failure)


@pytest.mark.parametrize('mode', ['untyped', 'saved', 'fresh'])
def test_report_keeps_saved_fresh_and_awaited_release_provider_order(mode):
    checks.check_task_boundary('finish', mode)


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_response_validator_keeps_original_callee_argument_order(failure):
    checks.check_task_boundary('response', failure)


def test_prompt_retains_own_namespace_late_policy_provider():
    checks.check_prompt()


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_presentation_keeps_own_provider_namespace_and_json_error(failure):
    checks.check_presentation(failure)


def test_receipt_keeps_original_progress_then_reference_order():
    checks.check_receipt()


def test_decision_state_keeps_original_read_snapshot_reference_order():
    checks.check_inputs()


def test_wait_keeps_late_exception_object_and_original_failed_outcome_path():
    checks.check_wait()


@pytest.mark.parametrize('family', ['task_state', 'report_delivery', 'decision_contracts', 'decision_state',
    'instructions', 'presentation', 'request', 'receipt'])
def test_changed_private_entry_loads_its_actual_original_namespace(tmp_path, family):
    checks.cold_entry(tmp_path / family, family)
