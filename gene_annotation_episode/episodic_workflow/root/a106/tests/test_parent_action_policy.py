"""Actual A106 parent policy entry controls with original callback oracles."""
import pytest
from .test_implicit_annotation_parent import no_external
from .parent_action_policy_checks import (
    assert_schema_boundary, assert_permission_boundary, assert_roles_boundary,
    assert_default_roles_boundary, assert_choice_boundary,
    assert_selected_replay_boundary, assert_catalog_boundary, assert_execute_boundary,
)

@pytest.mark.parametrize('mode', ['normal', 'initial_failure', 'late_global_failure', 'job_callback_failure'])
def test_annotation_schema_original_order(tmp_path, monkeypatch, mode):
    assert_schema_boundary(tmp_path, monkeypatch, 'annotation', mode)

@pytest.mark.parametrize('mode', ['wait_blocked', 'wait_callback_failure', 'tool_no_receipts', 'tool_receipts', 'ordinary_fallback'])
def test_root_permission_original_outcome(mode):
    assert_permission_boundary(mode)

@pytest.mark.parametrize('mode', ['root_filter', 'nested_unchanged', 'outside_declared', 'credit_callback_failure'])
def test_root_role_filter_original_order(mode):
    assert_roles_boundary(mode)

@pytest.mark.parametrize('mode', ['bound_scientific', 'unbound_jobs', 'no_jobs', 'job_failure'])
def test_default_role_configuration_original_order(mode):
    assert_default_roles_boundary(mode)

@pytest.mark.parametrize('mode', ['wrong_role', 'malformed_selection', 'scope_failure', 'no_arm', 'fresh_valid', 'saved_original'])
def test_parent_choice_original_admission(mode):
    assert_choice_boundary(mode)

@pytest.mark.parametrize('mode', ['saved_replay', 'fresh_allowed', 'absent_tool', 'journal_failure'])
def test_selected_root_tool_original_replay_gate(mode):
    assert_selected_replay_boundary(mode)

@pytest.mark.parametrize('mode', ['opaque_none', 'wait_entry', 'no_wait', 'callback_failure'])
def test_root_catalog_original_return(mode):
    assert_catalog_boundary(mode)

@pytest.mark.parametrize('mode', ['no_receipts', 'unlisted', 'wait_failure', 'repository_failure', 'failed', 'unavailable'])
def test_root_execute_original_returned_outcome(mode):
    assert_execute_boundary(mode)
