"""Policy binding validation without a retained case input."""


import pytest

from gene_annotation_episode.case_execution import PolicyBindings


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
