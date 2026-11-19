"""The native A102 sheets an Episode's tools published are rows of one declared work table; credit reads them back
through the scoped store, beside the source record and its artifact."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.tests.library_probe.harness import (
    calls, open_store, run_plan)

CALLS = 'gene_annotation_episode.episodic_workflow.episode_support.grading.tests.derived_publication_calls:'


def test_a_published_native_sheet_is_read_back_only_with_its_row(tmp_path):
    world = open_store(tmp_path)
    read, = run_plan(world, 'derived', calls((CALLS + 'publish_and_read', {'provider': 'native.a102.features'})))
    assert read['read'] is True
    assert read['not_received'] is None and read['other_provider'] is None
    assert read['unregistered'].endswith('a102_task_native_sheet_custody_required')
    world['store'].close()
