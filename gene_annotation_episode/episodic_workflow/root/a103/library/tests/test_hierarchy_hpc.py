"""Changed late handoff-policy boundaries; no scientific or native execution."""
import pytest
from . import hierarchy_hpc_checks as checks


@pytest.mark.parametrize('mode', ['missing', 'valid', 'late_to_hpc', 'late_away', 'required_first'])
def test_selected_late_contract(mode):
    checks.check_selected(mode)


def test_native_getter_cached_builtins():
    checks.check_getter_identity_and_cached_builtins()


def test_callee_before_generator_and_late_error():
    checks.check_ordered_name_loads()


def test_native_missing_and_builtin_names():
    checks.check_missing_and_builtin_names()


def test_nominal_identity_and_custom_fallback():
    checks.check_nominal_and_custom_fallback()


def test_custom_role_short_circuit():
    checks.check_custom_role_short_circuit()


def test_cold_policy_and_private_task_entry(tmp_path):
    checks.cold_entries(tmp_path / 'cold')
