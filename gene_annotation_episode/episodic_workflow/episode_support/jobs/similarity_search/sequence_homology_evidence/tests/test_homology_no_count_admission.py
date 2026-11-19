"""Offline selected thread operands under the enclosing workflow CPU quota."""
from importlib import import_module

import pytest


AXIS = __package__.rsplit('.tests', 1)[0]


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture
def jobs(tmp_path):
    source = import_module('gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence.homology_jobs')
    executable = tmp_path / 'unexecuted-fixture'
    executable.write_text('Synthetic executable identity; never executed.\n')
    executable.chmod(0o700)
    database = tmp_path / 'reference.faa'
    database.write_text('>synthetic\nMA\n')
    value = source.HomologyJobs.create(
        tmp_path / 'jobs',
        executable=source.FileAsset(executable, source.digest(executable)),
        reference_database=source.FileAsset(database, source.digest(database)),
        policy=import_module('gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_jobs').LocalJobPolicy(1024, 1024),
        max_cpu=1,
    )
    try:
        yield value
    finally:
        value.close()


@pytest.mark.parametrize('cpu', [0, -1, True])
def test_selected_threads_still_require_a_positive_integer(jobs, cpu):
    with pytest.raises(ValueError):
        jobs.order(query_ref='subject_synthetic', query_fasta='>query\nMA\n',
                   cpu=cpu, operation_key='invalid-selection')
    assert jobs.db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0
