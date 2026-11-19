"""Window isolation without starting a second local workflow."""

import pytest

from gene_annotation_episode import workflow_budget


def test_window_identity_is_stable_and_separates_services_and_slices():
    first = workflow_budget.window_units('00000000-0000-0000-0000-000000000001')
    second = workflow_budget.window_units('00000000-0000-0000-0000-000000000002')
    assert first == workflow_budget.window_units('00000000-0000-0000-0000-000000000001')
    assert first[0] != second[0] and first[1] != second[1]
    # A hyphenated slice would inherit the old global parent's aggregate cap.
    assert '-' not in first[1]
    with pytest.raises(ValueError, match='stable_codex_window_identity_required'):
        workflow_budget.window_units('')
