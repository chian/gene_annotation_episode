"""Requested native threads remain statistics under the owned workload quota."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_recording import HomologyStatistics


@pytest.fixture
def jobs():
    return SimpleNamespace(
        config={
            'max_cpu': 1,
            'job_limits': {'memory_bytes': 5 * 1024**3, 'scratch_bytes': 1024**2},
            'executable': {'sha256': 'a' * 64},
            'reference_database': {'sha256': 'b' * 64},
        },
        search_modes=('native_defaults',),
    )


@pytest.mark.parametrize('cpu', [1, 2, 64])
def test_requested_threads_are_recorded_without_changing_configuration(tmp_path, jobs, cpu):
    original = deepcopy(jobs.config)
    statistics = HomologyStatistics(tmp_path / 'history.sqlite', 'homology-test', None, None)
    execution = statistics.execution_class_for_query(jobs, query_fasta='>query\nMPEPTIDE\n', cpu=cpu)
    assert execution.cpu_threads == cpu
    assert execution.query_residues == 8
    assert execution.memory_bytes == 5 * 1024**3
    assert jobs.config == original
    assert not statistics.history_path.exists()


@pytest.mark.parametrize('cpu', [0, -1, True])
def test_invalid_requested_thread_metadata_still_fails(tmp_path, jobs, cpu):
    statistics = HomologyStatistics(tmp_path / 'history.sqlite', 'homology-test', None, None)
    with pytest.raises(ValueError, match='^cpu_outside_caller_allocation$'):
        statistics.execution_class_for_query(jobs, query_fasta='>query\nMPEPTIDE\n', cpu=cpu)
    assert not statistics.history_path.exists()
