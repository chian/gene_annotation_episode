"""Explicit scientific forecast role bindings."""

from dataclasses import replace

import pytest

from gene_annotation_episode.case_execution import PolicyBindings


PLANNING_ROLES = ('annotation', 'scientific_process')


def unexecuted(*args, **kwargs):
    raise AssertionError('Forecast role configuration must not execute policy')


def policy_fixture():
    definition = {'kind': 'fixture_unexecuted_policy'}
    return PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
        unexecuted, definition, definition, definition, definition, definition)


def test_policy_accepts_explicit_unique_forecast_roles_without_running_policy():
    legacy = policy_fixture()
    assert legacy.execution_planning_roles is None
    selected = replace(legacy, execution_planning_roles=PLANNING_ROLES)
    assert selected.execution_planning_roles == PLANNING_ROLES
    assert selected.project_task_credit is legacy.project_task_credit
    assert selected.controller_factory is legacy.controller_factory


@pytest.mark.parametrize('roles', [
    [], ['annotation', 'scientific_process'], (),
    ('annotation', 'annotation'), ('annotation', ''),
    ('scientific process',), ('scientific-process',),
    ('annotation', None), ('annotation', 1), False,
])
def test_policy_rejects_nonexplicit_or_nonunique_forecast_role_names(roles):
    with pytest.raises(ValueError, match='explicit_unique_execution_planning_roles_required'):
        replace(policy_fixture(), execution_planning_roles=roles)
