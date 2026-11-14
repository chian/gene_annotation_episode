"""Controlled compatibility boundaries and separately desired private yield ownership."""
import pytest
from .homology_boundary_checks import (HOMES, commissioned, compare_task_context,
    compare_decision, compare_rejected_fresh_reason, compare_controller, assert_private_yield_owner)


@pytest.mark.parametrize('parent,role', HOMES, ids=['-'.join(row) for row in HOMES])
def test_actual_fresh_task_context_matches_original(parent, role, tmp_path):
    with commissioned(tmp_path, parent, role) as value:
        compare_task_context(value)


@pytest.mark.parametrize('parent,role,case', [(*row, case) for row in HOMES
    for case in ('fresh', 'provider_error', 'saved_replay')],
    ids=['-'.join((*row, case)) for row in HOMES for case in ('fresh', 'provider_error', 'saved_replay')])
def test_actual_decision_call_matches_original(parent, role, case, tmp_path):
    with commissioned(tmp_path, parent, role) as value:
        compare_decision(value, case)


@pytest.mark.parametrize('parent,role', HOMES, ids=['-'.join(row) for row in HOMES])
def test_fresh_reason_rejection_matches_original(parent, role, tmp_path):
    with commissioned(tmp_path, parent, role, persistent_rejections=True) as value:
        compare_rejected_fresh_reason(value)


@pytest.mark.parametrize('parent,role,case', [(*row, case) for row in HOMES
    for case in ('plain', 'original_task', 'capture', 'factory_error')],
    ids=['-'.join((*row, case)) for row in HOMES for case in ('plain', 'original_task', 'capture', 'factory_error')])
def test_actual_controller_matches_original(parent, role, case, tmp_path):
    with commissioned(tmp_path, parent, role) as value:
        compare_controller(value, case)


@pytest.mark.parametrize('parent,role', HOMES, ids=['-'.join(row) for row in HOMES])
def test_selected_homology_has_private_yield_owner(parent, role, tmp_path):
    with commissioned(tmp_path, parent, role) as value:
        assert_private_yield_owner(value)
