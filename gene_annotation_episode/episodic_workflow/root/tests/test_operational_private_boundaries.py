"""Finite real private-family and original-runtime boundary comparisons."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from operational_private_boundary_checks import (
    ROOT, PARENTS, HOSTS, ROLES, HPC_ROLES, families, parent_path, binding_path,
    selected_binding, isolated_rows, request_fixture, admission_observation, native_state_context,
)


@pytest.fixture(scope='module')
def host(tmp_path_factory):
    with families(tmp_path_factory.mktemp('operational-private')) as value:
        yield value


ROUTES = [(family, parent, role) for family in ('execution', 'resource')
          for parent in PARENTS for role in ROLES]
ROUTES += [('hpc', parent, role) for parent in HOSTS for role in HPC_ROLES]
ROUTE_IDS = [family + ':' + parent + ':' + role for family, parent, role in ROUTES]


@pytest.mark.parametrize('family,parent,role', ROUTES, ids=ROUTE_IDS)
def test_actual_private_constructor_and_parent_path(host, family, parent, role):
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_child, binding_for_context
    binding = selected_binding(host, family, parent, role)
    assert binding is not None
    assert type(binding).__module__ == ROOT + '.' + binding.binding_path.replace('/', '.') + '.episode'
    assert binding.roles == (role,)
    path = binding_path(parent, role)
    assert binding_for_child(getattr(host, family), path[:-1], role) is binding
    context = SimpleNamespace(path=path, role=role, run_id=host.journal.run_id)
    assert binding_for_context(getattr(host, family), context) is binding
    assert binding.services is host.services
    assert binding.decision_source_type.__module__.startswith(ROOT + '.' + binding.binding_path.replace('/', '.') + '.')
    if family in ('execution', 'resource'):
        assert binding.owner is getattr(host, family + '_owner')
    else:
        assert binding.store is host.store
    expected_entry = (role,) if parent == 'annotation' and role in ('launch', 'results', 'hpc') else ()
    assert binding.entry_roles == expected_entry


@pytest.mark.parametrize('family', ['execution', 'resource', 'hpc'])
def test_actual_saved_annotation_subset_and_conflicts(host, family):
    modules = {'execution': 'execution_family_composition', 'resource': 'resource_binding_catalogue',
               'hpc': 'hpc_service_composition'}
    module = import_module(ROOT + '.' + modules[family])
    width = 3 if family == 'hpc' else 5
    originals = getattr(host, family)[:width]
    records = [item.as_record() for item in originals]
    if family == 'execution':
        rebuilt = module.construct_family(records, host.services, store=host.store,
            run_id=host.journal.run_id, directory=host.directory / 'reopened', tool_registry=host.tools)
    elif family == 'resource':
        rebuilt = module.construct_family(records, host.services, resource_adapters=())
    else:
        rebuilt = module.construct_family(records, host.services, store=host.store,
            run_id=host.journal.run_id, directory=host.directory / 'reopened')
    assert [item.binding_path for item in rebuilt] == [item.binding_path for item in originals]
    assert [item.as_record() for item in rebuilt] == records
    assert all(item.commissioning_parent in ('annotation', originals[0].binding_path) for item in rebuilt)
    with pytest.raises(ValueError):
        module.validate_family(tuple(reversed(originals)))
    with pytest.raises(ValueError):
        module.validate_family(originals[:-1])
    with pytest.raises(ValueError):
        module.validate_family((*originals, originals[0]))




@pytest.mark.parametrize('family', ['execution', 'resource'])
def test_equal_path_custom_binding_is_not_private_custody(host, family):
    module = import_module(ROOT + ('.execution_family_composition' if family == 'execution'
                                  else '.resource_binding_catalogue'))
    binding = getattr(host, family)[0]
    custom = SimpleNamespace(binding_path=binding.binding_path, roles=binding.roles,
                             owner=getattr(host, family + '_owner'))
    recognize = module.is_execution_binding if family == 'execution' else module.is_resource_binding
    assert not recognize(custom)
    assert module.custody_bindings((custom,)) == (custom,)
    assert module.custody_bindings((binding, custom)) == (getattr(host, family + '_owner'), custom)


@pytest.mark.parametrize('family', ['execution', 'resource', 'hpc'])
def test_parent_selection_rejects_ambiguous_and_unrelated_paths(host, family):
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_context, binding_for_path
    binding = getattr(host, family)[0]
    role = binding.roles[0]
    path = binding_path('annotation', role)
    assert binding_for_path((binding,), (('unregistered_parent', 'x'), (role, 'y'))) is None
    with pytest.raises(LookupError, match='episode_child_not_bound'):
        binding_for_path((binding, binding), path)
    with pytest.raises(ValueError, match='binding_context_path_must_match_role'):
        binding_for_context((binding,), SimpleNamespace(path=path, role='different_role'))


@pytest.mark.parametrize('family', ['execution', 'hpc'])
def test_current_context_credit_calls_actual_selected_private_object(host, family):
    module = import_module(ROOT + ('.execution_binding_catalogue' if family == 'execution'
                                  else '.hpc_service_composition'))
    role = 'launch_local' if family == 'execution' else 'hpc_execution'
    binding = selected_binding(host, family, 'scientific_process', role)
    context = SimpleNamespace(path=binding_path('scientific_process', role), role=role,
                              run_id=host.journal.run_id)
    marker, selection, seen = object(), {'actual': 'receiver'}, []
    def callback(actual_context, actual_selection):
        seen.append((actual_context, actual_selection))
        return marker
    name = 'project_credit' if family == 'execution' else 'credit_view'
    with patch.object(binding, name, callback):
        assert module.project_credit(getattr(host, family), context, selection) is marker
    assert seen == [(context, selection)]


@pytest.mark.parametrize('parent,role', [(parent, role) for parent in PARENTS
    for role in ('launch_local', 'launch_hpc')],
    ids=[parent + ':' + role for parent in PARENTS for role in ('launch_local', 'launch_hpc')])
def test_actual_native_context_selects_private_state_with_original_cache_and_signed_credit(host, parent, role):
    from gene_annotation_episode.episodic_workflow.root.practical_execution_records import assess_validations
    binding = selected_binding(host, 'execution', parent, role)
    context, resource_id = native_state_context(host, parent, role)
    prototype = host.execution_owner._practical[resource_id]
    private = binding._delegate(context)
    assert private is binding._native_resource_owners[resource_id]
    assert private is host.execution_owner._delegate(context)
    assert private is not prototype
    assert private.__dict__ is prototype.__dict__
    assert type(private).__module__ == ROOT + '.' + binding.binding_path.replace('/', '.') + '.resource'
    state = private.state(context)
    assert type(state).__module__ == ROOT + '.' + binding.binding_path.replace('/', '.') + '.resource_state_records'
    assert prototype._states[context.episode_id] is state
    assert private.state(context) is state
    previous, gains = 0, []
    for index, exists in enumerate((True, True, False, False, True)):
        key = 'observed-path-' + str(index)
        outcome = {'facts': {'paths': [{'path': str(host.workspace / 'env'), 'exists': exists,
            'object_type': 'directory' if exists else 'missing', 'sha256': None}]}}
        intent = state.begin(key, 'practical.inspect', {})
        assert intent['state'] == 'new'
        validations = assess_validations(state.assignment, outcome, state.context(),
            checked_at='2026-10-22T20:00:00+00:00', tool_name='practical.inspect')
        receipt = state.finish(key, outcome, validations)
        assert state.begin(key, 'practical.inspect', {})['receipt'] == receipt
        assert state.finish(key, outcome, validations) == receipt
        value = state.credit_view()['credit']
        gains.append(value - previous)
        previous = value
    assert gains == [2, 0, -2, 0, 2]
    assert len(state.receipts()) == 5
    assert state.completion_proof() is None
    # Existing states keep their actual identity even through direct custody.
    original_bindings = host.execution_owner._private_execution_bindings
    try:
        del host.execution_owner._private_execution_bindings
        assert host.execution_owner._delegate(context) is prototype
        assert prototype.state(context) is state
    finally:
        host.execution_owner._private_execution_bindings = original_bindings


REQUESTS = [
    ('execution', 'annotation', 'launch'),
    ('execution', 'legacy_annotation', 'launch_local'),
    ('execution', 'scientific_process', 'launch_api'),
    ('execution', 'hpc_coordination', 'launch_hpc'),
    ('resource', 'annotation', 'launch'),
    ('resource', 'legacy_annotation', 'launch_local'),
    ('resource', 'scientific_process', 'launch_api'),
    ('hpc', 'annotation', 'hpc'),
    ('hpc', 'legacy_annotation', 'hpc_prediction'),
    ('hpc', 'scientific_process', 'hpc_execution'),
]
REQUEST_IDS = [':'.join(parts) for parts in REQUESTS]









RETURNS = [(family, case) for family in ('execution', 'resource', 'hpc')
    for case in ('fresh', 'saved', 'saved-failure', 'invalid', 'receive-error', 'redelivery')]


