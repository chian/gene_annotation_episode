"""Permanent original-body controls for actual private Resource call boundaries."""
import pytest

from .resource_decision_boundary_checks import compare_decision_boundary
from .resource_task_checks import HOMES


@pytest.mark.parametrize('home,case', [(home, case) for home in HOMES
    for case in ('fresh', 'provider_error', 'saved_replay')],
    ids=[f'home={home};case={case}' for home in HOMES
         for case in ('fresh', 'provider_error', 'saved_replay')])
def test_actual_private_decision_call_matches_original_body(home, case, tmp_path):
    compare_decision_boundary(home, tmp_path, case)
