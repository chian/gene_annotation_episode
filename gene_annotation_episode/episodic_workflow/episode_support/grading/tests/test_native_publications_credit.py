"""The A104 panel and alignment credits read the native requests and results of the Episode's own tools from
declared work tables; with nothing registered both are zero."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.tests.library_probe.harness import (
    calls, open_store, run_plan)

CALLS = 'gene_annotation_episode.episodic_workflow.episode_support.grading.tests.native_credit_calls:'


def test_credits_over_empty_native_tables_are_zero(tmp_path):
    world = open_store(tmp_path)
    world['store'].create_problem(raw_sequence='ATGGCT', molecule='dna')
    subjects = world['store'].problem()['subject_refs']
    credits, = run_plan(world, 'native', calls((CALLS + 'credit_without_registrations', {})), held=subjects)
    assert credits == {'panel': 0, 'alignment': 0, 'requests': 0, 'results': 0}
    world['store'].close()
