import pytest
from . import policy_assembly_checks as checks


@pytest.mark.parametrize('late_job', (False, True), ids=('current_policy', 'late_job_policy'))
def test_annotation_schema_owns_original_policy(tmp_path, late_job):
    checks.paired_schema(tmp_path, 'annotation', late_job=late_job)


@pytest.mark.parametrize('placement', ('instance', 'class'))
def test_annotation_next_keeps_workflow_override(tmp_path, placement):
    checks.private_next_override(tmp_path, 'annotation', placement)


def test_annotation_report_selects_private_scientific_snapshot_late(tmp_path):
    checks.paired_late_scientific_snapshot(tmp_path, 'annotation')
