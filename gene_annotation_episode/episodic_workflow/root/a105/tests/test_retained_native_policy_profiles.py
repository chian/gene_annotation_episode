"""Inert historical receipt profiles; no execution-policy construction or launch.

These pure controls do not authenticate a complete worker receipt. Original
reader integration separately owns request/source pins and correlated records.
"""
from copy import deepcopy
from importlib import import_module
import math

import pytest

PREFIX = __package__.rsplit('.tests', 1)[0] + '.library.retained_input_authority.'
MEMORY, SCRATCH = 21474836480, 4294967296


def profiles():
    return import_module(PREFIX + 'retained_native_read_profiles')


def blast_validate():
    return import_module(PREFIX + 'retained_blast_policy_fields').validate_retained_blast_policy_fields


@pytest.mark.parametrize('archived_wall_field', [False, True])
def test_exact_saved_profile_outputs_keep_their_correlated_fields(archived_wall_field):
    helper = profiles()
    policy = {'memory_bytes': MEMORY, 'scratch_bytes': SCRATCH}
    if archived_wall_field:
        policy['wall_seconds'] = None
    original = deepcopy(policy)
    enforcement = {'memory': 'systemd_cgroup_v2_memory_max', 'swap': 'systemd_memory_swap_max_zero',
        'scratch': 'monitored_visible_allocated_bytes_with_possible_overshoot',
        'per_file_bytes': 'hard_rlimit_fsize_equal_to_scratch_bytes',
        'process_tree': 'systemd_control_group', 'filesystem_sandbox': False}
    cgroup = {'memory_max': MEMORY, 'memory_swap_max': 0, 'kill_mode': 'control-group', 'oom_policy': 'kill'}
    if archived_wall_field:
        enforcement['wall_time'] = 'unset'
        cgroup['runtime_max'] = 'infinity'
    assert helper.retained_policy_matches(policy)
    assert helper.retained_policy(policy) == original
    assert helper.retained_metadata(policy) == {'native_lifecycle_version': 'durable_systemd_native_job_v2',
        'policy': original, 'enforcement': enforcement}
    assert helper.retained_cgroup(policy) == cgroup
    copy = helper.retained_policy(policy)
    copy['memory_bytes'] = 1
    assert policy == original and helper.retained_policy(policy) == original


@pytest.mark.parametrize('changes', [
    {'memory_bytes': True}, {'memory_bytes': float(MEMORY)}, {'memory_bytes': MEMORY + 1},
    {'scratch_bytes': False}, {'scratch_bytes': float(SCRATCH)}, {'scratch_bytes': 0},
    {'wall_seconds': 1}, {'wall_seconds': False}, {'wall_seconds': math.inf},
    {'wall_seconds': math.nan}, {'runtime_max': 'infinity'}, {'extra_field': None},
])
def test_saved_profile_rejects_unrecognized_types_values_and_mixed_fields(changes):
    helper = profiles()
    policy = {'memory_bytes': MEMORY, 'scratch_bytes': SCRATCH, **changes}
    assert not helper.retained_policy_matches(policy)
    for method in (helper.retained_policy, helper.retained_metadata, helper.retained_cgroup):
        with pytest.raises(ValueError, match='unsupported_retained_native_policy'):
            method(policy)


def test_two_profiles_remain_distinct_for_original_cross_record_checks():
    helper = profiles()
    tracked = {'memory_bytes': MEMORY, 'scratch_bytes': SCRATCH}
    archived = {**tracked, 'wall_seconds': None}
    # Pure construction does not erase an authenticated historical distinction.
    assert helper.retained_policy(tracked) != helper.retained_policy(archived)
    assert helper.retained_metadata(tracked) != helper.retained_metadata(archived)
    assert helper.retained_cgroup(tracked) != helper.retained_cgroup(archived)
    assert helper.retained_metadata(archived)['policy'] == archived
    assert helper.retained_metadata(tracked)['policy'] == tracked


@pytest.mark.parametrize('wall', ['absent', None, 1, 0.25])
def test_original_blast_scalar_validation_accepts_historical_data_only(wall):
    policy = {'memory_bytes': 1, 'scratch_bytes': 2}
    if wall != 'absent':
        policy['wall_seconds'] = wall
    original = deepcopy(policy)
    assert blast_validate()(policy) is None
    assert policy == original


@pytest.mark.parametrize('field,value', [
    ('memory_bytes', True), ('memory_bytes', 1.0), ('memory_bytes', 0),
    ('scratch_bytes', False), ('scratch_bytes', 2.0), ('scratch_bytes', -1),
    ('wall_seconds', False), ('wall_seconds', 0), ('wall_seconds', -1),
    ('wall_seconds', math.inf), ('wall_seconds', math.nan), ('wall_seconds', 'infinity'),
])
def test_original_blast_scalar_validation_rejects_invalid_saved_values(field, value):
    policy = {'memory_bytes': 1, 'scratch_bytes': 2, field: value}
    with pytest.raises(ValueError, match='invalid_local_job_' + field):
        blast_validate()(policy)
