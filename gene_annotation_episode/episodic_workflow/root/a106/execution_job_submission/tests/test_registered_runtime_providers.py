"""Original provider boundaries for this existing A106 private task."""
import pytest
from gene_annotation_episode.episodic_workflow.root.a106.tests import a106_registered_provider_checks as checks

HOME = 'execution_job_submission'

def test_private_source_providers_and_original_builtin(monkeypatch):
    checks.assert_private_owners(HOME, monkeypatch)

@pytest.mark.parametrize("route,failure", (("uncontracted", True), ("saved_form", False), ("fresh_form", False)), ids=("uncontracted_error", "saved_return", "fresh_return"))
def test_original_report_providers_after_release(route, failure, monkeypatch):
    checks.assert_report_release(HOME, route, failure, monkeypatch)

@pytest.mark.parametrize("mode", ("late_provider", "argument_rebind", "missing"))
def test_mixed_global_callee_before_arguments(mode, monkeypatch):
    checks.assert_mixed_callee_order(HOME, mode, monkeypatch)

@pytest.mark.parametrize("shadow", (False, True), ids=("builtin_fallback", "runtime_shadow"))
def test_mixed_builtin_and_private_completed_work(shadow, monkeypatch):
    checks.assert_mixed_builtin_and_private_helper(HOME, shadow, monkeypatch)

def test_private_exchange_table_stays_lexical(monkeypatch):
    checks.assert_private_exchange_helper(HOME, monkeypatch)

@pytest.mark.parametrize("boundary", ("applies", "capture"))
def test_original_same_role_operand_after_callback(boundary):
    checks.assert_expectation_role(HOME, boundary)

def test_original_report_grain_after_message(monkeypatch):
    checks.assert_report_grain(HOME, monkeypatch)

def test_private_credit_presentation_stays_lexical(monkeypatch):
    checks.assert_private_credit_presentation(HOME, monkeypatch)

