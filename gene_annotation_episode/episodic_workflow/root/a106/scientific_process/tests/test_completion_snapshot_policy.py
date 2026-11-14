"""Private Scientific completion operands; no acquired Scientific action claim."""
import pytest
from ...tests.test_implicit_annotation_parent import no_external
from ...tests.parent_action_policy_checks import assert_scientific_snapshot_boundary

@pytest.mark.parametrize('mode', ['normal', 'missing_initial', 'controller_failure', 'parent_failure'])
def test_scientific_snapshot_original_operand_order(mode):
    assert_scientific_snapshot_boundary(mode)

from ...tests.parent_action_policy_checks import assert_late_scientific_report_consumer

@pytest.mark.parametrize('mode', ['runtime_fallback', 'annotation_report', 'improvement_report'])
def test_actual_facts_entry_preserves_late_scientific_identity(tmp_path, mode):
    assert_late_scientific_report_consumer(tmp_path, mode)
