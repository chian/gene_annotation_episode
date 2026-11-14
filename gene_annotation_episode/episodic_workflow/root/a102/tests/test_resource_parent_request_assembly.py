"""Original behavior controls and separate desired parent-ownership assertions."""
import pytest
from .resource_request_boundary_checks import CHILDREN, EDGES, PACKAGE, invoke, setup


@pytest.mark.parametrize('parent_home,role,child_home', EDGES,
    ids=[parent + '::' + role for parent, role, _ in EDGES])
def test_selected_envelope_matches_original_axis_boundary(parent_home, role, child_home):
    old, live = setup(parent_home, role, child_home), setup(parent_home, role, child_home)
    assert invoke(old, original=True) == invoke(live) == {'status': 'captured'}
    assert live.captures == old.captures and live.events == old.events
    request = live.captures[0]['request']
    assert request['goal']['parent_goal_id'] == live.source.request.goal.goal_id
    assert live.captures[0]['path'] == (*live.source.path, (role, 'child_7'))
    inheritance = request['message']['knowledge_inheritance']
    assert inheritance['parent'] == live.source.episode_id
    assert inheritance['child'] != inheritance['parent']
    assert request['message']['episode_assignment'] == live.assignment
    assert [event[0] for event in live.events].count('materialize') == 2
    assert [event[0] for event in live.events].count('bind') == 1
    assert [event[0] for event in live.events][-2:] == ['constructor', 'transaction_exit']


@pytest.mark.parametrize('parent_home,role,child_home', EDGES,
    ids=[parent + '::' + role for parent, role, _ in EDGES])
def test_selected_route_uses_named_private_parent_owner_once(parent_home, role, child_home):
    """Desired ownership check: baseline without private owners should fail."""
    live = setup(parent_home, role, child_home)
    assert invoke(live) == {'status': 'captured'}
    assert live.selectors == [role]
    assert live.assemblies == [PACKAGE + '.' + parent_home.replace('/', '.')
        + '.to_child_' + child_home.rsplit('/', 1)[-1]]


@pytest.mark.parametrize('role,child,failure', [(role, child, failure) for role, child in CHILDREN
    for failure in ('materialize', 'bind', 'typed_declaration', 'invalid_parent')],
    ids=[role + '::' + failure for role, _ in CHILDREN
        for failure in ('materialize', 'bind', 'typed_declaration', 'invalid_parent')])
def test_original_error_identity_and_side_effect_order(role, child, failure):
    old = setup('resource_work_submission', role, 'resource_work_submission/' + child, failure)
    live = setup('resource_work_submission', role, 'resource_work_submission/' + child, failure)
    expected, actual = invoke(old, original=True), invoke(live)
    assert expected['status'] == actual['status'] == 'raised'
    assert actual == expected and live.events == old.events
    if failure in ('materialize', 'bind'):
        assert live.caught_error is live.injected_error
        assert old.caught_error is old.injected_error
    assert live.captures == old.captures == []
    names = [event[0] for event in live.events]
    if failure == 'materialize':
        assert actual['type'] is ValueError
        assert actual['message'] == 'controlled_original_envelope_materialization_failure'
        assert names.count('materialize') == 2 and names.count('bind') == 0
    elif failure == 'bind':
        assert actual['type'] is ValueError
        assert actual['message'] == 'controlled_original_receipt_binding_failure'
        assert names.count('materialize') == 2 and names.count('bind') == 1
    elif failure == 'typed_declaration':
        assert actual['type'] is live.runtime.ContractInformationError
        assert actual['code'] == 'saved_contract_declaration_mismatch'
        assert actual['field'] == 'declaration'
        assert names.count('materialize') == 1 and names.count('bind') == 0
    else:
        assert failure == 'invalid_parent' and actual['type'] is TypeError
        assert actual['message'] == 'a child Goal requires an EpisodeGoal parent'
        assert names.count('materialize') == 1 and names.count('bind') == 0
    assert names.count('constructor') == 0 and names[-1] == 'transaction_exit'


@pytest.mark.parametrize('role,child', CHILDREN, ids=[role for role, _ in CHILDREN])
def test_unselected_direct_build_retains_original_fallback_and_optional_operands(role, child):
    old = setup('resource_work_submission', role, 'resource_work_submission/' + child)
    live = setup('resource_work_submission', role, 'resource_work_submission/' + child)
    assert invoke(old, original=True, direct=True) == invoke(live, direct=True) == {'status': 'captured'}
    assert live.captures == old.captures and live.events == old.events
    assert live.selectors == live.assemblies == []
    message = live.captures[0]['request']['message']
    assert message['job_assignment'] == {'original': 'job'}
    assert message['scientific_process'] == {'original': 'optional scientific operand'}
    assert [event[0] for event in live.events].count('materialize') == 1
