"""Validation of optional native job notification bindings."""

from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.case_execution import PolicyBindings


EVENTS = {'version': 'native_job_events_v1', 'resource_id': 'fixture-host'}


def forbidden(*args, **kwargs):
    raise AssertionError('Caller notification checks must not execute work')


@pytest.mark.parametrize('definition', [
    {}, [], False, 'native_job_events_v1', {'version': 'native_job_events_v1'},
    {'resource_id': 'fixture-host'}, {**EVENTS, 'version': 'native_job_events_v2'},
    {**EVENTS, 'resource_id': ''}, {**EVENTS, 'resource_id': '  '},
    {**EVENTS, 'resource_id': 1}, {**EVENTS, 'extra': True},
])
def test_policy_requires_exact_explicit_native_notification_definition(definition):
    binding = {'kind': 'fixture_unexecuted_policy'}
    with pytest.raises(ValueError, match='invalid_native_job_events_binding'):
        PolicyBindings(forbidden, forbidden, forbidden, forbidden, forbidden,
            binding, binding, binding, binding, binding, native_job_events=definition)


def test_native_notification_is_optional_without_invoking_policy_functions():
    binding = {'kind': 'fixture_unexecuted_policy'}
    legacy = PolicyBindings(forbidden, forbidden, forbidden, forbidden, forbidden,
        binding, binding, binding, binding, binding)
    assert legacy.native_job_events is None
    supplied = replace(legacy, native_job_events=deepcopy(EVENTS))
    assert supplied.native_job_events == EVENTS and legacy.native_job_events is None
