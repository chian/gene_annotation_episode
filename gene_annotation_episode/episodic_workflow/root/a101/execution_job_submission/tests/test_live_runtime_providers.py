"""Original-provider controls owned by this existing private task."""
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.tests import other_task_runtime_provider_checks as checks

HOME = 'execution_job_submission'

def test_private_runtime_provider_ownership(monkeypatch):
    checks.assert_private_owners(HOME)
    checks.assert_conversation_lookup(HOME, monkeypatch)

@pytest.mark.parametrize("boundary", ("applies", "planning", "capture"), ids=("applies", "planning", "capture"))
def test_original_late_own_role(boundary):
    checks.assert_expectation_role(HOME, boundary)

def test_original_report_grain_after_assignment(monkeypatch):
    checks.assert_report_grain(HOME, monkeypatch)

@pytest.mark.parametrize("route,failure", (("uncontracted", False), ("uncontracted", True), ("saved_form", False), ("saved_form", True), ("fresh_form", False), ("fresh_form", True)), ids=("uncontracted-return", "uncontracted-error", "saved-return", "saved-error", "fresh-return", "fresh-error"))
def test_original_report_provider_after_release(route, failure, monkeypatch):
    checks.assert_report_release(HOME, route, failure, monkeypatch)
