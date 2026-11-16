"""Validation of optional native job notification bindings."""


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


