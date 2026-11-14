import pytest
from gene_annotation_episode.episodic_workflow.root.a103.tests import commissioning_checks as checks


@pytest.mark.parametrize('scenario', (
    'wait', 'receipt', 'declarations', 'declaration_none', 'late_filter',
    'fresh_arm', 'replay_arm', 'wrong_arm', 'catalog_none', 'catalog_wait',
    'execute_rejection', 'execute_lookup', 'selected_fresh', 'selected_replay', 'return_form'))
def test_original_commissioning_boundaries(tmp_path, scenario):
    checks.paired(tmp_path, scenario)


def test_original_shared_schema_filter_interface(tmp_path):
    checks.schema_filter(tmp_path)
