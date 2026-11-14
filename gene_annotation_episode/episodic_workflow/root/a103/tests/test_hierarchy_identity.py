"""Four physical homes retain actual registry/task paths and byte operands."""
from .hierarchy_identity_checks import check_moved_parent_and_children, check_real_descriptor_policy_operand


def test_actual_annotation_parent_and_three_homology_paths(tmp_path):
    check_moved_parent_and_children(tmp_path / 'homology')


def test_actual_affected_descriptor_policy_operand(tmp_path):
    check_real_descriptor_policy_operand(tmp_path / 'descriptors')
