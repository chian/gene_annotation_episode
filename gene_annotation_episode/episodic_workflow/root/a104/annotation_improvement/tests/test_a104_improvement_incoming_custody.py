"""Actual improvement constructor consuming its unchanged shared admission."""
from ...tests.test_a104_incoming_goal_custody import check_real_initializer
from ...tests.test_a104_implicit_parent_protocol import no_external_execution


def test_actual_improvement_incoming_state_matches_original(tmp_path):
    check_real_initializer(tmp_path, 'improvement')
