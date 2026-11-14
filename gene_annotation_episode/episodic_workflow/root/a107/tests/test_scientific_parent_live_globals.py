"""Existing Scientific endpoint globals at actual original expression boundaries."""
import pytest
from .scientific_parent_live_globals_checks import ROUTES, paired


@pytest.mark.parametrize('role', [role for role, _ in ROUTES])
def test_request_observes_original_runtime_record_rebinding(role):
    for timing in ('before-call', 'during-callback', 'during-error'):
        paired(role, 'request', timing)


@pytest.mark.parametrize('role', [role for role, _ in ROUTES])
def test_receipt_observes_original_runtime_reference_rebinding(role):
    for timing in ('before-call', 'during-callback', 'during-error'):
        paired(role, 'receipt', timing)
