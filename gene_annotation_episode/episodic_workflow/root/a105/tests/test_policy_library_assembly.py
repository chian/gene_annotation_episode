import pytest
from . import policy_assembly_checks as checks


@pytest.mark.parametrize('home', ('custom', 'scientific'))
def test_standalone_schema_retains_original_live_lookup(tmp_path, home):
    checks.paired_schema(tmp_path, home)


@pytest.mark.parametrize('saved', (False, True), ids=('fresh_late_job', 'saved_current_facts'))
def test_standalone_report_retains_original_callbacks(tmp_path, saved):
    checks.paired_fallback_facts(tmp_path, saved=saved)


def test_standalone_report_selects_private_scientific_snapshot_late(tmp_path):
    checks.paired_late_scientific_snapshot(tmp_path, 'custom')
