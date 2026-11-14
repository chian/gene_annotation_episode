"""Finite late-callback and private message selection preservation controls."""
import pytest
from .root_message_callback_checks import (
    EARLY, NOMINAL, LATE, RETURNS, paired_early, paired_nominal, paired_late,
    private_override, paired_return, paired_job_assignment,
)


@pytest.mark.parametrize('scenario', EARLY)
def test_message_original_error_order(tmp_path, scenario):
    paired_early(tmp_path, scenario)


@pytest.mark.parametrize('name', NOMINAL)
def test_message_nominal_private_owner(tmp_path, name):
    paired_nominal(tmp_path, name)


@pytest.mark.parametrize('scenario', LATE)
def test_message_late_callbacks(tmp_path, scenario):
    paired_late(tmp_path, scenario)


@pytest.mark.parametrize('placement', ('class', 'instance'))
def test_message_declaration_override(tmp_path, placement):
    private_override(tmp_path, placement)


@pytest.mark.parametrize('endpoint', RETURNS)
def test_message_live_return_global(tmp_path, endpoint):
    paired_return(tmp_path, endpoint)


@pytest.mark.parametrize('provider_kind', ('public_custom', 'current_private'))
def test_message_job_assignment_owner(tmp_path, provider_kind):
    paired_job_assignment(tmp_path, provider_kind)
