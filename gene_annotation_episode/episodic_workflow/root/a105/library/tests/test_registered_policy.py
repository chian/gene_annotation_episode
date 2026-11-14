"""Actual registered policy probes and original instruction/context lookup."""
import pytest

from . import registered_policy_checks as checks


@pytest.mark.parametrize('mode', ['ordinary', 'native-present', 'job-error'])
def test_registered_instructions_keep_original_namespace_and_nominal_policy(tmp_path, mode):
    checks.check_instructions(tmp_path, mode)


@pytest.mark.parametrize('mode', ['absent-marker', 'explicit-graph', 'description-error', 'own-scientific-guard'])
def test_registered_context_keeps_actual_optional_job_presentation_and_scientific_probe(tmp_path, mode):
    checks.check_context(tmp_path, mode)


@pytest.mark.parametrize('mode', ['resource-error', 'fresh-receipt', 'saved-receipt'])
def test_registered_fresh_saved_decision_keeps_resource_receipt_and_wait_probes(tmp_path, mode):
    checks.check_decision(tmp_path, mode)


def test_private_instruction_cold_entry_retains_original_prompt_namespace(tmp_path):
    checks.cold_instructions(tmp_path)
