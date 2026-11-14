"""Affected conditional Literature commissioning boundaries, without remote work."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import literature_execution_original_contract as original_contract
from literature_execution_boundary_checks import (
    ROOT, PARENTS, ROLES, families, parent_path, binding_path, literature_context,
    saved_axis_commission, own_execution, native_context, incoming, isolated_rows,
)
from literature_execution_request_checks import request_observation
from literature_execution_return_checks import admission_observation


@pytest.fixture(scope='module')
def host(tmp_path_factory):
    with families(tmp_path_factory.mktemp('literature-execution')) as value:
        yield value


@pytest.fixture(scope='module')
def no_api_host(tmp_path_factory):
    with families(tmp_path_factory.mktemp('literature-execution-no-api'), api=False) as value:
        yield value


@pytest.mark.parametrize('parent', PARENTS)
def test_actual_parent_and_all_five_children_resolve_without_role_only_substitution(host, parent):
    from gene_annotation_episode.episodic_workflow.root.predefined_parent_routes import binding_for_path
    actual_parent = host.parents[parent]
    assert host.registry.for_path(parent_path(parent)) is actual_parent
    if parent.startswith('scientific_process/'):
        assert host.registry.for_path(parent_path(parent)[:-1]) is host.scientific
    for role in ROLES:
        path = binding_path(parent, role)
        child = host.registry.for_path(path)
        assert child in host.execution and child.owner is host.execution_owner
        assert host.registry.for_child(path[:-1], role) is child
        assert binding_for_path(host.execution, path) is child
        assert child.entry_roles == ()
        assert child.commissioning_parent == (parent + '/execution_job_submission'
            if role in ('launch_api', 'launch_local', 'launch_hpc') else parent)
    assert host.parents[parent].child_message_exchange('results',
        child_binding=own_execution(host, PARENTS[(PARENTS.index(parent) + 1) % 3], 'results')) is None


@pytest.mark.parametrize('parent', PARENTS)
def test_original_a106_configuration_and_actual_bvbrc_admission(host, parent):
    cls = type(host.parents[parent])
    with pytest.raises(ValueError, match='^a106_intervention_requires_rate_population$'):
        cls(host.services, a106_intervention=True)
    context = literature_context(host, parent)
    assert cls(host.services, rate_population=True).allowed_children(context, ()) == ('literature_strategy',)
    actual = host.parents[parent]
    assert actual.allowed_children(context, ()) == ('literature_strategy', 'launch', 'results')
    # Original for_role is unambiguous in this actual configured parent subset.
    from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
    subset = tuple(item for item in host.execution if item.binding_path.startswith(parent + '/'))
    with patch.object(host.services.workflow, 'episode_bindings', EpisodeBindingRegistry(subset)):
        module = import_module(ROOT + '.' + parent.replace('/', '.') + '.analysis_contract')
        assert module.analysis_children(host.services) == original_contract.analysis_children(host.services)
        assert module._execution(host.services) is original_contract._execution(host.services)
        # An actual service is bound; no scientific adapters or availability are inferred.
        assert module.contract_catalog(host.services) == []


@pytest.mark.parametrize('parent', PARENTS)
def test_native_resources_without_bvbrc_do_not_admit_analysis_children(no_api_host, parent):
    module = import_module(ROOT + '.' + parent.replace('/', '.') + '.analysis_contract')
    assert module.analysis_children(no_api_host.services) == ()
    assert no_api_host.parents[parent].allowed_children(literature_context(no_api_host, parent), ()) == ('literature_strategy',)


@pytest.mark.parametrize('axis', ['A106', 'A105', 'missing'])
def test_axis_scoped_admission_uses_actual_saved_scientific_commission(host, axis):
    from gene_annotation_episode.domain import ContractError
    parent = PARENTS[2]
    actual = type(host.parents[parent])(host.services, axis_scoped_profiles=True)
    with isolated_rows(host):
        if axis != 'missing':
            saved_axis_commission(host, axis)
        if axis == 'missing':
            with pytest.raises(ContractError, match='^literature_original_axis_commission_required$'):
                actual.allowed_children(literature_context(host, parent), ())
        else:
            assert actual.allowed_children(literature_context(host, parent), ()) == (
                ('literature_strategy', 'launch', 'results') if axis == 'A106' else ('literature_strategy',))


@pytest.mark.parametrize('parent', PARENTS)
def test_original_custom_provider_and_lookup_error_identity_remain_supported(host, parent):
    module = import_module(ROOT + '.' + parent.replace('/', '.') + '.analysis_contract')
    custom = SimpleNamespace(api_execution=host.execution_owner.api_execution)
    calls = []
    def resolve(role):
        calls.append(role)
        return custom
    registry = SimpleNamespace(roles=('results',), for_role=resolve)
    with patch.object(host.services.workflow, 'episode_bindings', registry):
        assert module._execution(host.services) is original_contract._execution(host.services) is custom
        assert calls == ['results', 'results']
        error = LookupError('original custom registry failure')
        def fail(role):
            raise error
        registry.for_role = fail
        for read in (module._execution, original_contract._execution):
            with pytest.raises(LookupError) as caught:
                read(host.services)
            assert caught.value is error


@pytest.mark.parametrize('parent', PARENTS)
def test_saved_other_parent_subset_cannot_supply_this_parents_results(host, parent):
    from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
    other = PARENTS[(PARENTS.index(parent) + 1) % 3]
    subset = tuple(item for item in host.execution if item.binding_path.startswith(other + '/'))
    module = import_module(ROOT + '.' + parent.replace('/', '.') + '.analysis_contract')
    with patch.object(host.services.workflow, 'episode_bindings', EpisodeBindingRegistry(subset)):
        assert module._execution(host.services) is None
        assert module.analysis_children(host.services) == ()


@pytest.mark.parametrize('parent', PARENTS)
def test_saved_descriptor_reconstructs_only_its_actual_five_counterparts(host, parent):
    from gene_annotation_episode.episodic_workflow.root.execution_family_composition import construct_family, descriptor_parents
    selected = tuple(item for item in host.execution if item.binding_path.startswith(parent + '/'))
    descriptors = [item.as_record() for item in selected]
    assert descriptor_parents(descriptors) == (parent,)
    rebuilt = construct_family(deepcopy(descriptors), host.services, store=host.store,
        run_id=host.journal.run_id, directory=host.directory / 'reopened' / parent,
        tool_registry=host.tools)
    assert len(rebuilt) == 5
    assert [type(item) for item in rebuilt] == [type(item) for item in selected]
    assert [item.as_record() for item in rebuilt] == descriptors
    assert len({id(item.owner) for item in rebuilt}) == 1
    assert rebuilt[0].owner is not host.execution_owner


@pytest.mark.parametrize('parent', PARENTS)
def test_literature_native_context_invokes_own_state_and_preserves_shared_cache(host, parent):
    # Signed progress/replay arithmetic is already covered by Root160's18 cases.
    # This added boundary checks the previously absent Literature ancestry.
    for role in ('launch_local', 'launch_hpc'):
        binding = own_execution(host, parent, role)
        context, resource = native_context(host, parent, role)
        private = binding._delegate(context)
        prototype = host.execution_owner._practical[resource]
        assert host.execution_owner._delegate(context) is private
        assert private is binding._native_resource_owners[resource]
        assert private.__dict__ is prototype.__dict__
        state = private.state(context)
        assert type(state).__module__ == ROOT + '.' + binding.binding_path.replace('/', '.') + '.resource_state_records'
        assert prototype._states[context.episode_id] is state
        assert private.state(context) is state
        assert state.credit_view()['credit'] == 0
        assert state.completion_proof() is None


EDGES = [(parent, role) for parent in PARENTS for role in ('launch', 'results')]


@pytest.mark.parametrize('parent,role', EDGES, ids=[parent + ':' + role for parent, role in EDGES])
def test_actual_selected_literature_request_matches_original_and_invokes_parent_owner(host, parent, role):
    with isolated_rows(host):
        before = request_observation(host, parent, role, original=True)
    with isolated_rows(host):
        after = request_observation(host, parent, role)
    assert before.error is before.cutoff, (type(before.error).__name__, str(before.error))
    assert after.error is after.cutoff, (type(after.error).__name__, str(after.error))
    assert before.events == after.events
    assert before.built == after.built
    assert before.row == after.row
    assert before.assemblies == []
    assert len(after.assemblies) == 1
    expected = ROOT + '.' + parent.replace('/', '.') + '.to_child_execution_'
    assert after.assemblies[0] == expected + ('job_submission' if role == 'launch' else 'result_acquisition')


@pytest.mark.parametrize('parent,failure', list(zip(PARENTS, ('initial', 'materialize', 'prepare'))))
def test_actual_parent_request_preserves_rejection_order_and_exception_identity(host, parent, failure):
    with isolated_rows(host):
        before = request_observation(host, parent, 'launch', original=True, failure=failure)
    with isolated_rows(host):
        after = request_observation(host, parent, 'launch', failure=failure)
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


RETURNS = [(parent, role, case) for parent, role in EDGES for case in ('fresh', 'saved')]


@pytest.mark.parametrize('parent,role,case', RETURNS, ids=[':'.join(row) for row in RETURNS])
def test_own_typed_return_and_saved_counterpart_identity_match_original(host, parent, role, case):
    from operational_original_runtime import original_admit_return
    with isolated_rows(host):
        before = admission_observation(host, original_admit_return, case, parent, role)
    with isolated_rows(host):
        after = admission_observation(host, incoming(host, parent, role), case, parent, role)
    assert before.output == after.output
    assert before.events == after.events
    assert before.rows == after.rows
    assert before.error is after.error is None
    assert len(after.rows) == 1
    from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
    assert after.rows[0]['parent_episode_id'] == EpisodeRef(host.journal.run_id, parent_path(parent)).episode_id
    assert after.rows[0]['child_episode_id'] == EpisodeRef(host.journal.run_id, binding_path(parent, role)).episode_id
