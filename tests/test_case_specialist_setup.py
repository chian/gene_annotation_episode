"""Policy binding validation without a retained case input."""

from dataclasses import replace

import pytest

from gene_annotation_episode.case_execution import PolicyBindings


SETUP_PARAMETERS = {'services': {'kind': 'fixture_specialist_setup',
    'revision': 1, 'features': {'monitoring': True, 'resources': []}}}


def test_policy_binding_accepts_optional_paired_setup_without_invocation():
    def unexecuted(*args, **kwargs):
        raise AssertionError('Validation must not invoke policy callables')

    definition = {'kind': 'fixture_unexecuted_policy'}
    legacy = PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
        unexecuted, definition, definition, definition, definition, definition)
    assert legacy.episode_service_factory is legacy.episode_service_binding is None
    supplied = replace(legacy, episode_service_factory=unexecuted,
        episode_service_binding=SETUP_PARAMETERS['services'])
    assert supplied.episode_service_factory is unexecuted
    assert supplied.episode_service_binding is SETUP_PARAMETERS['services']


@pytest.mark.parametrize(('factory', 'definition'), [
    (lambda: None, None),
    (None, {'kind': 'fixture'}),
    (False, {'kind': 'fixture'}),
    (lambda: None, {}),
    (lambda: None, []),
    (lambda: None, {'value': float('nan')}),
    (lambda: None, {'value': float('inf')}),
    (lambda: None, {'value': object()}),
])
def test_policy_binding_rejects_incomplete_or_nonfinite_setup(factory, definition):
    def unexecuted(*args, **kwargs):
        raise AssertionError('Validation must not invoke policy callables')

    binding = {'kind': 'fixture_unexecuted_policy'}
    with pytest.raises((ValueError, TypeError)):
        PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
            unexecuted, binding, binding, binding, binding, binding,
            episode_service_factory=factory, episode_service_binding=definition)
