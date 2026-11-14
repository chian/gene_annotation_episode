"""Original conditional improvement task and two real parent boundaries."""
import pytest

from .improvement_host_checks import (improvement_host, paired_host, build_observation,
    action_observation, report_observation, continuation_observation,
    mutable_record_observation, credit_observation, nested_continuation_observation)


@pytest.mark.parametrize('custom', (False, True))
def test_actual_improvement_build_state_and_generic_fallback(tmp_path, custom):
    with improvement_host(tmp_path) as host:
        paired_host(host, build_observation, custom=custom)


@pytest.mark.parametrize('status', ('completed', 'failed', 'invalid', 'unavailable'))
def test_returned_unit_original_credit_replay_and_state(tmp_path, status):
    with improvement_host(tmp_path) as host:
        paired_host(host, action_observation, status)


@pytest.mark.parametrize('mode', ('root', 'typed'))
def test_actual_improvement_report_and_saved_reuse(tmp_path, mode):
    with improvement_host(tmp_path) as host:
        paired_host(host, report_observation, mode)


@pytest.mark.parametrize('task_aware', (False, True))
def test_original_root_continuation_and_saved_input(tmp_path, task_aware):
    with improvement_host(tmp_path) as host:
        paired_host(host, continuation_observation, task_aware)


def test_nested_task_aware_continuation_preserves_original_unavailable_error(tmp_path):
    with improvement_host(tmp_path, root_role='annotation') as host:
        paired_host(host, nested_continuation_observation)


def test_improvement_report_uses_live_original_record_object(tmp_path):
    with improvement_host(tmp_path) as host:
        paired_host(host, mutable_record_observation)


def test_improvement_credit_uses_actual_projection_identity(tmp_path):
    with improvement_host(tmp_path) as host:
        paired_host(host, credit_observation)

