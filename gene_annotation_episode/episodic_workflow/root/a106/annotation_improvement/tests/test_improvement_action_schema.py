"""Improvement-owned actual schema controls; shared original oracle is explicit."""
import pytest
from ...tests.test_implicit_annotation_parent import no_external
from ...tests.parent_action_policy_checks import assert_schema_boundary

@pytest.mark.parametrize('mode', ['normal', 'initial_failure', 'late_global_failure', 'job_callback_failure'])
def test_improvement_schema_original_order(tmp_path, monkeypatch, mode):
    assert_schema_boundary(tmp_path, monkeypatch, 'improvement', mode)
