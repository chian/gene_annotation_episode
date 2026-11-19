"""A107 qualifications and their frozen requests are rows of declared work tables of the Episode that published
them, read back through the scoped store beside the source records they authenticate."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.tests.library_probe.harness import (
    calls, open_store, run_plan)

CALLS = 'gene_annotation_episode.episodic_workflow.episode_support.grading.tests.qualification_calls:'


def test_a_request_and_a_graded_qualification_are_published_as_rows_and_read_back(tmp_path):
    world = open_store(tmp_path)
    store = world['store']
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    subjects = store.problem()['subject_refs']
    published, = run_plan(world, 'qualify', calls((CALLS + 'publish', {'subjects': subjects})), held=subjects)
    assert published['request_rows'] == [published['request']]
    assert published['graded_rows'] == [published['graded']]
    assert published['request_read'] and published['graded_read']
    assert published['other_provider'] is None
    store.close()
