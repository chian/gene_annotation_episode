"""Actual root registry mechanics with explicit engineering binding fixtures.

No scientific episode, immediate axis head, source alias or controller is built.
The fixtures satisfy the real protocol and fail if metadata lookup attempts work.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root import episode_bindings as registry_module
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext


class BindingProbe:
    """Test-only protocol implementation; all execution ports are forbidden."""
    def __init__(self, role, *, path=None, parent=None, entry=False, children=(), value=None):
        self.roles = (role,)
        self.entry_roles = self.roles if entry else ()
        if path is not None:
            self.binding_path, self.commissioning_parent = path, parent
        self.children, self.value, self.calls = children, value, []
        self.descriptor = {'binding': 'explicit_engineering_fixture', 'role': role,
            'configuration': {'supplied_null': None, 'nested': [1, {'value': 'preserved'}]},
            'historical_provenance': {'release': 'earlier-engineering-fixture'},
            'implementation_identity': 'original-descriptor-field'}

    def as_record(self):
        return deepcopy(self.descriptor)

    def child_roles(self, role):
        assert role in self.roles
        return self.children

    def credit_kind(self, role):
        assert role in self.roles
        return 'operational'

    def assignment_schema(self, role):
        raise AssertionError('metadata lookup constructed an assignment')

    def permitted_common_actions(self, context):
        raise AssertionError('metadata lookup selected work')

    def allowed_children(self, parent, caller_capabilities):
        raise AssertionError('metadata lookup asked to commission work')

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        raise AssertionError('metadata lookup prepared an invocation')

    def instructions(self, context):
        raise AssertionError('metadata lookup entered an episode')

    def decision_context(self, context, current_view):
        raise AssertionError('metadata lookup opened a decision')

    def catalog(self, context):
        raise AssertionError('metadata lookup enumerated execution tools')

    def execute(self, context, tool_name, arguments, operation_key):
        raise AssertionError('metadata lookup executed work')

    def fact_sources(self, role):
        raise AssertionError('registry must use the received-report metadata hook')

    def facts(self, context, completion_snapshot):
        raise AssertionError('metadata lookup synthesized a child result')

    def resolve(self, context, reference, namespace):
        raise AssertionError('metadata lookup resolved scientific evidence')

    def validate_report(self, context, form, original_schema):
        raise AssertionError('metadata lookup validated a scientific result')

    def credit_view(self, context, receiver_selection):
        raise AssertionError('metadata lookup computed credit')

    def _context(self, name, context):
        assert type(context) is BindingContext
        self.calls.append((name, context))
        return {} if self.value is None else {'selected_fixture_owner': self.value}

    def initial_decision_context(self, context):
        return self._context('initial', context)

    def annotation_axis_yield_context(self, context, credit):
        self.calls.append(('yield_operand', credit))
        return self._context('yield', context)

    def received_report_sources(self, role):
        assert type(role) is str
        self.calls.append(('metadata', role))
        return {} if self.value is None else {'selected_fixture_owner': {
            'type': 'number', 'meaning': self.value}}

    def received_report_facts(self, context):
        return self._context('facts', context)

    def current_report_facts(self, context):
        return self._context('current_facts', context)

    def received_report_closure_facts(self, context):
        self._context('closure_facts', context)
        return {} if self.value is None else {'closed_fixture_owner': self.value}

    def contract_information_profile(self, context):
        self._context('profile', context)
        return None if self.value is None else 'profile-' + self.value

    def resolve_received_reference(self, context, reference, namespace):
        self._context('resolve_received', context)
        return None if self.value is None else True

    def validate_received_report(self, context, form, schema):
        self._context('validate_received', context)

    def initial_references(self, context):
        self._context('initial_refs', context)
        return [] if self.value is None else ['fixture_ref_' + self.value]

    def received_form_references(self, context, form, schema, operation_key):
        self._context('form_refs', context)
        return [] if self.value is None else ['fixture_ref_' + self.value]

    def received_evidence_tokens(self, context):
        self._context('tokens', context)
        return [] if self.value is None else ['fixture_token_' + self.value]


@pytest.fixture
def branch_case():
    left = BindingProbe('left_parent', path='fixture/left', parent='annotation',
        entry=True, children=('inspection',))
    right = BindingProbe('right_parent', path='fixture/right', parent='annotation',
        entry=True, children=('inspection',))
    left_child = BindingProbe('inspection', path='fixture/left/inspection',
        parent=left.binding_path, children=('inspection',), value='left')
    right_child = BindingProbe('inspection', path='fixture/right/inspection',
        parent=right.binding_path, children=('inspection',), value='right')
    bindings = (left, right, left_child, right_child)
    return EpisodeBindingRegistry(bindings), bindings


def parent_path(side, key='original-parent'):
    return (('annotation', 'root'), (side + '_parent', key))


def child_path(side, key='original-child'):
    return (*parent_path(side), ('inspection', key))


def context(path):
    return BindingContext('registry-fixture-run', 'registry-fixture-episode', path[-1][0],
        path, {'subject_refs': []}, {'constraints': {'fixed': True}}, {'original': True})


@pytest.mark.parametrize('side,position', [('left', 2), ('right', 3)])
def test_same_role_is_selected_by_exact_commissioning_parent(branch_case, side, position):
    registry, bindings = branch_case
    selected = bindings[position]
    assert registry.for_child(parent_path(side), 'inspection') is selected
    assert registry.for_path(child_path(side)) is selected
    assert registry.for_path(child_path(side, key='another-invocation')) is selected
    assert registry.for_binding_path(selected.binding_path) is selected
    assert registry.declared_children(side + '_parent') == ('inspection',)
    assert all(not binding.calls for binding in bindings)


def test_ambiguous_role_only_lookup_and_metadata_require_lineage(branch_case):
    registry, _ = branch_case
    with pytest.raises(LookupError, match='episode_role_requires_parent:inspection'):
        registry.for_role('inspection')
    with pytest.raises(LookupError, match='episode_binding_context_required'):
        registry.received_report_sources('inspection')


@pytest.mark.parametrize('legacy_first', [False, True])
def test_legacy_role_cannot_silently_override_a_private_path(legacy_first):
    legacy = BindingProbe('inspection')
    private = BindingProbe('inspection', path='fixture/parent/inspection', parent='fixture/parent')
    registry = EpisodeBindingRegistry((legacy if legacy_first else private,))
    before = deepcopy(registry.as_record())
    with pytest.raises(ValueError, match='duplicate_episode_role:inspection'):
        registry.register(private if legacy_first else legacy)
    assert registry.as_record() == before


def test_duplicate_exact_path_rejects_before_registry_mutation(branch_case):
    registry, bindings = branch_case
    before = deepcopy(registry.as_record())
    duplicate = BindingProbe('another_role', path=bindings[2].binding_path,
        parent=bindings[2].commissioning_parent)
    with pytest.raises(ValueError, match='duplicate_episode_binding_path:fixture/left/inspection'):
        registry.register(duplicate)
    assert registry.as_record() == before
    with pytest.raises(LookupError, match='episode_role_not_bound:another_role'):
        registry.for_role('another_role')


def test_explicit_recursion_reuses_same_private_source_identity(branch_case):
    registry, bindings = branch_case
    recursive = (*child_path('left'), ('inspection', 'recursive-invocation'))
    assert registry.for_path(recursive) is bindings[2]
    assert registry.for_child(child_path('left'), 'inspection') is bindings[2]
    assert registry.for_path((*child_path('right'), ('inspection', 'recursive-invocation'))) is bindings[3]


def test_descriptors_keep_original_fields_and_order_without_path_injection(branch_case):
    registry, bindings = branch_case
    before = [deepcopy(binding.descriptor) for binding in bindings]
    registry.for_path(child_path('left'))
    registry.received_report_sources('inspection', parent_path=parent_path('right'))
    assert registry.as_record() == before
    assert [binding.descriptor for binding in bindings] == before
    assert all('binding_path' not in row for row in registry.as_record())


@pytest.mark.parametrize('side,position', [('left', 2), ('right', 3)])
def test_actual_and_prospective_metadata_use_same_owner_without_fake_invocation(branch_case, monkeypatch, side, position):
    registry, bindings = branch_case
    original_for_path, visited = registry.for_path, []
    def observe_path(path):
        visited.append(tuple(tuple(segment) for segment in path))
        return original_for_path(path)
    monkeypatch.setattr(registry, 'for_path', observe_path)
    supplied_parent = parent_path(side)
    expected = {'selected_fixture_owner': {'type': 'number', 'meaning': side}}
    assert registry.received_report_sources('inspection', parent_path=supplied_parent) == expected
    assert all(path in (supplied_parent[:1], supplied_parent) for path in visited)
    assert ('metadata', 'inspection') in bindings[position].calls
    assert not bindings[5 - position].calls
    visited.clear()
    supplied_actual = child_path(side)
    assert registry.received_report_sources('inspection', path=supplied_actual) == expected
    assert all(path in (supplied_actual[:1], supplied_actual[:2], supplied_actual) for path in visited)
    assert all(name == 'metadata' for binding in bindings for name, _ in binding.calls)


def test_report_metadata_rejects_conflicting_or_wrong_role_paths(branch_case):
    registry, _ = branch_case
    with pytest.raises(ValueError, match='one_report_source_lineage_required'):
        registry.received_report_sources('inspection', path=child_path('left'), parent_path=parent_path('left'))
    with pytest.raises(ValueError, match='report_source_role_path_mismatch'):
        registry.received_report_sources('right_parent', path=child_path('left'))


def test_context_hooks_keep_canonical_identity_and_select_only_private_branch(branch_case):
    registry, bindings = branch_case
    assert registry_module.BindingContext is BindingContext
    received = context(child_path('left'))
    before = received.as_record()
    expected = {'selected_fixture_owner': 'left'}
    assert registry.initial_decision_context(received) == expected
    operand = {'original_signed_credit': -0.375}
    assert registry.annotation_axis_yield_context(received, operand) == expected
    assert registry.received_report_facts(received) == expected
    assert registry.current_report_facts(received) == expected
    assert registry.contract_information_profile(received) == 'profile-left'
    assert registry.resolve_received_reference(received, 'fixture_ref', 'fixture') is True
    registry.validate_received_report(received, {}, {})
    assert registry.initial_references(received) == ['fixture_ref_left']
    assert registry.received_form_references(received, {}, {}, 'original-operation') == ['fixture_ref_left']
    assert registry.received_evidence_tokens(received) == ['fixture_token_left']
    assert all(argument is received for name, argument in bindings[2].calls if name != 'yield_operand')
    assert ('yield_operand', operand) in bindings[2].calls
    assert bindings[3].calls == []
    assert received.as_record() == before
    with pytest.raises(TypeError):
        received.assignment['constraints']['fixed'] = False


def test_closure_facts_are_requested_only_for_actual_completed_snapshot(branch_case):
    registry, bindings = branch_case
    received = context(child_path('left'))
    assert registry.received_report_facts(received, completion_snapshot={}) == {'selected_fixture_owner': 'left'}
    assert not any(name == 'closure_facts' for name, _ in bindings[2].calls)
    assert registry.received_report_facts(received, completion_snapshot={'completion': {'ended_by': 'exhausted'}}) == {
        'selected_fixture_owner': 'left', 'closed_fixture_owner': 'left'}
    assert any(name == 'closure_facts' for name, _ in bindings[2].calls)


@pytest.mark.parametrize('operation,error', [
    ('initial', 'initial_binding_context_field_conflict'),
    ('yield', 'annotation_axis_yield_context_conflict'),
    ('metadata', 'received_report_field_conflict:received_report_sources'),
    ('facts', 'received_report_field_conflict:received_report_facts'),
    ('profile', 'contract_information_profile_conflict'),
    ('reference', 'received_report_reference_conflict'),
])
def test_original_aggregation_conflicts_remain_visible(branch_case, operation, error, monkeypatch):
    registry, bindings = branch_case
    received = context(child_path('left'))
    # A globally unambiguous original hook remains part of aggregation. Its
    # conflict with the selected private owner must not silently overwrite data.
    bindings[0].value = 'conflicting-parent'
    if operation == 'reference':
        monkeypatch.setattr(bindings[0], 'resolve_received_reference', lambda *args: False)
    with pytest.raises(ValueError, match=error):
        if operation == 'initial':
            registry.initial_decision_context(received)
        elif operation == 'yield':
            registry.annotation_axis_yield_context(received, {'credit': 0})
        elif operation == 'metadata':
            registry.received_report_sources('inspection', path=child_path('left'))
        elif operation == 'facts':
            registry.received_report_facts(received)
        elif operation == 'profile':
            registry.contract_information_profile(received)
        else:
            registry.resolve_received_reference(received, 'fixture_ref', 'fixture')


def test_legacy_parent_cannot_acquire_unrelated_private_child_by_unique_role():
    parent = BindingProbe('legacy_parent', entry=True, children=('inspection',))
    private_child = BindingProbe('inspection', path='other_parent/inspection',
        parent='other_parent', value='unrelated')
    registry = EpisodeBindingRegistry((parent, private_child))
    original_descriptors = deepcopy(registry.as_record())
    # Known negative regression in the frozen lineage template: its legacy
    # parent branch currently chooses list(candidates), despite explicit child
    # ownership pointing elsewhere. This test must fail that implementation;
    # do not xfail it or substitute a fake parent binding path.
    with pytest.raises(LookupError, match='episode_child_not_bound'):
        registry.for_child((('annotation', 'root'), ('legacy_parent', 'original-parent')),
            'inspection')
    assert registry.as_record() == original_descriptors
    assert parent.calls == [] and private_child.calls == []


def test_unique_legacy_child_retains_original_role_compatibility():
    parent = BindingProbe('legacy_parent', entry=True, children=('inspection',))
    legacy_child = BindingProbe('inspection', value='legacy')
    registry = EpisodeBindingRegistry((parent, legacy_child))
    original_parent = (('annotation', 'root'), ('legacy_parent', 'original-parent'))
    assert registry.for_child(original_parent, 'inspection') is legacy_child
    assert registry.for_path((*original_parent, ('inspection', 'original-child'))) is legacy_child
    assert registry.for_role('inspection') is legacy_child
    assert parent.calls == [] and legacy_child.calls == []
