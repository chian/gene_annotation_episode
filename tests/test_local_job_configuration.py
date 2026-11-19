"""Caller local job resource configuration."""

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy


@pytest.mark.parametrize("config", [
    {"memory_bytes": 0, "scratch_bytes": 1}, {"memory_bytes": True, "scratch_bytes": 1},
    {"memory_bytes": 1, "scratch_bytes": -1}, {"wall_seconds": 0}, {"memory_byte": 12345},
])
def test_invalid_caller_limits_are_not_silently_replaced(config):
    with pytest.raises((ValueError, TypeError)):
        LocalJobPolicy.from_config(config)


@pytest.mark.parametrize("config", [None, {}, {"memory_bytes": 5 * 1024**3}, {"scratch_bytes": 4 * 1024**3}])
def test_missing_caller_limits_raise_without_packaged_defaults(config):
    with pytest.raises(ValueError):
        LocalJobPolicy.from_config(config)


def test_caller_limits_are_kept_without_a_time_budget():
    policy = LocalJobPolicy.from_config({"memory_bytes": 5 * 1024**3, "scratch_bytes": 4 * 1024**3})
    assert policy.memory_bytes == 5 * 1024**3
    assert policy.scratch_bytes == 4 * 1024**3
    assert not hasattr(policy, 'wall_seconds')
