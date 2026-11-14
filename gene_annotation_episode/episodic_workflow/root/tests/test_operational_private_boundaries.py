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


def test_resource_profile_descriptor_reads_actual_schema_owner(host):
    import gene_annotation_episode.schema_information_text as schema_owner
    from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
    from gene_annotation_episode.episodic_workflow.root.resource_binding_catalogue import resource_bindings
    owner = ResourceEpisodes(host.services, resource_adapters=(),
                             contract_information_profile=CONTRACT_INFORMATION_PROFILE)
    binding = resource_bindings(owner, parents=('annotation',))[0]
    original_read, observed = Path.read_bytes, []
    defining_path = Path(schema_owner.__file__).resolve()
    absent_root_copy = defining_path.parent / 'episodic_workflow/root/schema_information_text.py'
    def observe(path):
        observed.append(path.resolve())
        return original_read(path)
    with patch.object(Path, 'read_bytes', observe):
        original = binding.as_record()
    assert defining_path in observed and absent_root_copy not in observed
    assert original['configuration']['contract_information_profile'] == CONTRACT_INFORMATION_PROFILE
    assert binding.as_record() == original
    # Alter only the observed operand in memory: the descriptor must depend on
    # the real defining bytes, without writing to the immutable source snapshot.
    def changed_schema(path):
        value = original_read(path)
        return value + b'\n# controlled descriptor operand\n' if path.resolve() == defining_path else value
    with patch.object(Path, 'read_bytes', changed_schema):
        changed = binding.as_record()
    assert changed['implementation_sha256'] != original['implementation_sha256']
    assert {key: value for key, value in changed.items() if key != 'implementation_sha256'} == {
        key: value for key, value in original.items() if key != 'implementation_sha256'}


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


@pytest.mark.parametrize('family,parent,role', REQUESTS, ids=REQUEST_IDS)
def test_actual_selected_route_matches_original_request_and_invokes_private_owner(host, family, parent, role):
    with isolated_rows(host):
        before = request_fixture(host, family, parent, role, original=True)
    with isolated_rows(host):
        after = request_fixture(host, family, parent, role)
    assert before.error is before.cutoff, (type(before.error).__name__, str(before.error))
    assert after.error is after.cutoff, (type(after.error).__name__, str(after.error))
    assert before.events == after.events
    assert before.built == after.built
    assert before.row == after.row
    assert before.assemblies == []
    assert len(after.assemblies) == 1
    assert after.assemblies[0].startswith(ROOT + '.')
    assert '.to_child_' in after.assemblies[0]



def test_actual_resource_hpc_request_preserves_original_pre_submission_rejection(host):
    """Inherited Resource handoff mismatch is preserved, not a working route."""
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.episodic_workflow.root.communication import validate_closed_schema
    route = ('resource', 'hpc_coordination/hpc_allocation_execution', 'launch_hpc')
    with isolated_rows(host):
        before = request_fixture(host, *route, original=True, resource_hpc_negative=True)
    with isolated_rows(host):
        after = request_fixture(host, *route, resource_hpc_negative=True)
    binding = selected_binding(host, *route)
    original_fact_schema = deepcopy(binding.fact_sources('launch_hpc')['execution_handoffs']['report_schema'])
    assert original_fact_schema['x-source'] == 'execution_handoffs'
    assert original_fact_schema['type'] == 'array'
    assert original_fact_schema['items']['type'] == 'object'
    assert original_fact_schema['items']['properties']['version']['const'] == 'execution_handoff_v1'
    expected_schema = {'type': 'object', 'properties': {'fact_0': original_fact_schema},
                       'required': ['fact_0'], 'additionalProperties': False}
    assert before.schema == after.schema == expected_schema
    assert validate_closed_schema(before.schema) == expected_schema
    assert before.required == after.required == ()
    for observed in (before, after):
        assert type(observed.error) is ContractError
        assert str(observed.error) == 'hpc_launch_requires_original_handoff_fact_in_return_form'
        assert observed.error is not observed.cutoff
        assert observed.error is not observed.injected
        assert observed.events == ['validate_child_choice', 'expanded_form']
        assert observed.built == []
        assert observed.row is None
    assert before.assemblies == []
    assert after.assemblies == [ROOT + '.hpc_coordination.hpc_allocation_execution.resource_job_submission.to_child_hpc_resource_execution']


@pytest.mark.parametrize('failure', ['initial', 'materialize', 'prepare'])
def test_actual_selected_error_order_and_exception_identity(host, failure):
    with isolated_rows(host):
        before = request_fixture(host, 'execution', 'annotation', 'launch_local',
                                 original=True, failure=failure)
    with isolated_rows(host):
        after = request_fixture(host, 'execution', 'annotation', 'launch_local', failure=failure)
    assert type(before.error) is type(after.error)
    assert str(before.error) == str(after.error)
    assert before.events == after.events
    assert before.built == after.built == []
    assert before.row is after.row is None
    if failure == 'initial':
        assert 'unknown' in str(after.error)
        assert after.events == ['validate_child_choice', 'expanded_form']
    else:
        assert before.error is before.injected
        assert after.error is after.injected
        assert str(after.error) == 'controlled-' + failure


RETURNS = [(family, case) for family in ('execution', 'resource', 'hpc')
    for case in ('fresh', 'saved', 'saved-failure', 'invalid', 'receive-error', 'redelivery')]


@pytest.mark.parametrize('family,case', RETURNS, ids=[':'.join(parts) for parts in RETURNS])
def test_private_typed_return_matches_original_persistence_and_failure(host, family, case):
    from operational_original_runtime import original_admit_return
    names = {'execution': 'execution_job_submission.from_child_local_job_execution',
             'resource': 'resource_job_submission.from_child_local_resource_execution',
             'hpc': 'hpc_coordination.from_child_hpc_resource_prediction'}
    incoming = import_module(ROOT + '.' + names[family]).admit_return
    with isolated_rows(host):
        before = admission_observation(host, original_admit_return, case)
    with isolated_rows(host):
        after = admission_observation(host, incoming, case)
    assert before.output == after.output
    assert before.events == after.events
    assert before.rows == after.rows
    assert type(before.error) is type(after.error)
    assert str(before.error) == str(after.error)
    assert len(after.rows) == 1
    if case == 'receive-error':
        assert before.error is before.receive_error
        assert after.error is after.receive_error
        assert after.rows[0]['form'] is not None
    elif case in ('saved-failure', 'invalid'):
        assert after.error is not None
        assert after.rows[0]['failure'] is not None
        assert after.events == []
    else:
        assert after.error is None
        assert after.output[1] == ['original-received-reference']
        assert after.events[0][3]['redelivery'] is (case == 'redelivery')
