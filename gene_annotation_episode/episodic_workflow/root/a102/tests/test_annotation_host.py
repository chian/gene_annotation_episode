"""Original implicit annotation host now has actual private responsibility owners."""
import pytest
from .annotation_parent_exchange_checks import parent_host
from .annotation_host_checks import (paired_host, build_observation, action_observation,
    report_observation, continuation_observation, mutable_record_observation)

@pytest.mark.parametrize('custom', (False, True))
def test_actual_host_build_state_and_generic_fallback(tmp_path, custom):
    with parent_host(tmp_path) as host:
        paired_host(host, build_observation, custom=custom)

@pytest.mark.parametrize('status', ('completed', 'failed', 'invalid', 'unavailable'))
def test_returned_unit_original_credit_replay_and_state(tmp_path, status):
    with parent_host(tmp_path) as host:
        paired_host(host, action_observation, status)

@pytest.mark.parametrize('mode', ('root', 'typed'))
def test_actual_private_report_facts_saved_reuse(tmp_path, mode):
    with parent_host(tmp_path) as host:
        paired_host(host, report_observation, mode)

@pytest.mark.parametrize('task_aware', (False, True))
def test_original_continuation_factory_and_saved_input(tmp_path, task_aware):
    with parent_host(tmp_path) as host:
        paired_host(host, continuation_observation, task_aware)

def test_private_report_uses_live_original_record_object(tmp_path):
    with parent_host(tmp_path) as host:
        paired_host(host, mutable_record_observation)

def test_actual_private_credit_keeps_original_projection_identity(tmp_path):
    from .annotation_host_checks import credit_observation
    with parent_host(tmp_path) as host:
        paired_host(host, credit_observation)
