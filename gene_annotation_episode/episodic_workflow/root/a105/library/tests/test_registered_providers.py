"""Finite live-provider boundaries, with explicit real consumer rosters."""
import pytest

from . import registered_provider_checks as checks


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_selected_task_constructor_keeps_late_episode_plain_order(failure):
    checks.check_tasks('constructor', failure)


@pytest.mark.parametrize('failure', [False, True], ids=['value', 'error'])
def test_received_context_uses_live_original_reference_provider(failure):
    checks.check_tasks('references', failure)


@pytest.mark.parametrize('mode', ['untyped', 'saved', 'fresh'])
def test_selected_finish_keeps_release_record_and_saved_fresh_order(mode):
    checks.check_tasks('finish', mode)


@pytest.mark.parametrize('annotation_axes', [False, True], ids=['scalar', 'saved-annotation'])
def test_yield_presentation_keeps_late_provider_and_standalone_branch(annotation_axes):
    checks.check_yield_rebinding(annotation_axes)


def test_named_request_owners_use_late_original_json_provider():
    checks.check_request_rebinding()


def test_scientific_wait_keeps_live_exception_and_feedback_identity():
    checks.check_wait_rebinding()


def test_current_inputs_keep_original_received_reference_error_order():
    checks.check_input_rebinding()


@pytest.mark.parametrize('family', ['task', 'task_state', 'task_decision',
    'decision_inputs', 'decision_presentation', 'presentation_fields',
    'standalone_presentation', 'waiting', 'to_child'])
def test_changed_owner_cold_entry_keeps_original_runtime_object(tmp_path, family):
    checks.cold_entry(tmp_path / family, family)
