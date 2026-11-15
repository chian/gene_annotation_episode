"""Controlled routing/authentication coverage, not private scientific execution."""
from dataclasses import replace
import inspect
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.workflow_setup import WorkflowSetup
from gene_annotation_episode.episodic_workflow.root.tests.root_binding_owner_support import (
    MEMBER, OWNERS, actual_owner_root, detached, engineering_edge, narrower_scope,
    rewrite_action, rewrite_request,
)


@pytest.fixture(scope='module')
def original_root(tmp_path_factory):
    with actual_owner_root(tmp_path_factory.mktemp('actual-owner-routing')) as root:
        yield root


@pytest.fixture
def root(original_root):
    # Original Store.transaction rolls back only engineering rows between cases.
    # The marker is fixture cleanup, never a caught application/test exception.
    class RollBackFixture(Exception):
        pass
    try:
        with original_root.store.transaction():
            try:
                yield original_root
            finally:
                original_root.assert_no_execution()
            raise RollBackFixture
    except RollBackFixture:
        pass




@pytest.mark.parametrize('owner', OWNERS)
def test_registered_objects_and_descriptors_are_the_original_private_tree(root, owner):
    registry = root.workflow.episode_bindings
    assert registry.private_owners == OWNERS
    for binding in root.groups[owner]:
        selected = registry.private_selection(owner, binding.binding_path)
        assert registry.for_binding_path(binding.binding_path, owner=owner) is binding
        assert registry.restore_private_selection(selected, expected_owner=owner) is binding
        assert selected['descriptor'] == binding.as_record()
        selected['descriptor']['binding_id'] = 'caller-mutated-detached-copy'
        assert registry.private_selection(owner, binding.binding_path)['descriptor'] == binding.as_record()
    assert root.groups['A105'][0] is not root.groups['A108'][0]
    assert type(root.groups['A105'][0].library) is not type(root.groups['A108'][0].library)


def test_ambiguous_roles_and_paths_require_owner_and_duplicate_registration_rejects(root):
    registry = root.workflow.episode_bindings
    with pytest.raises(LookupError, match='root_binding_owner_required'):
        registry.for_role('scientific_process')
    with pytest.raises(LookupError, match='root_binding_path_requires_unique_owner'):
        registry.for_binding_path('scientific_process')
    with pytest.raises(ValueError, match='duplicate_episode_binding_path'):
        EpisodeBindingRegistry((root.groups['A105'][0], root.groups['A105'][0]), owners=('A105', 'A105'))
    with pytest.raises(ValueError, match='root_binding_owner_registration_is_immutable'):
        registry.register(root.groups['A105'][0])


def test_original_unowned_and_single_group_path_lookup_remain_available(root):
    originals = root.groups['A105']
    legacy = EpisodeBindingRegistry(originals)
    single = EpisodeBindingRegistry(originals, owners=('A105',) * len(originals))
    path = (*root.context.path, ('scientific_process', 'legacy-invocation'), ('literature', 'legacy-child'))
    assert legacy.for_path(path) is originals[1]
    assert single.for_path(path) is originals[1]
    assert legacy.as_record() == [item.as_record() for item in originals]
    with pytest.raises(LookupError, match='root_binding_owner_required'):
        EpisodeBindingRegistry((*originals, *root.groups['A108']),
            owners=('A105',) * len(originals) + ('A108',) * len(root.groups['A108'])).for_path(path)


@pytest.mark.parametrize('owner', OWNERS)
def test_explicit_owner_report_sources_use_only_original_group(root, owner):
    originals = root.groups[owner]
    expected = EpisodeBindingRegistry(originals)
    actual = root.workflow.episode_bindings
    assert actual.received_report_sources('literature', owner=owner) == expected.received_report_sources('literature')
    if owner == 'A108':
        # Preserve the original seven-child group's overlapping external fields.
        for registry, options in ((expected, {}), (actual, {'owner': owner})):
            with pytest.raises(ValueError, match='received_report_field_conflict:received_report_sources'):
                registry.received_report_sources('scientific_process', **options)
    assert list(actual._report_source_bindings('scientific_process', owner=owner)) == list(originals)
    with pytest.raises(LookupError, match='root_binding_owner_required'):
        actual.received_report_sources('scientific_process')


@pytest.mark.parametrize('owner', OWNERS)
def test_saved_recursive_ancestry_routes_to_original_objects(root, owner):
    head, _, _ = engineering_edge(root, root.context, owner=owner)
    recursive, _, _ = engineering_edge(root, head, owner=owner)
    literature, _, _ = engineering_edge(root, recursive, owner=owner, role='literature')
    assert root.workflow._binding_owner_for_path(literature.path) == owner
    assert root.workflow.episode_bindings.for_path(head.path) is root.groups[owner][0]
    assert root.workflow.episode_bindings.for_path(recursive.path) is root.groups[owner][0]
    assert root.workflow.episode_bindings.for_path(literature.path) is root.groups[owner][1]
    assert root.workflow.scientific_binding(literature) is root.groups[owner][0]
    other = 'A108' if owner == 'A105' else 'A105'
    with pytest.raises(ValueError, match='root_binding_path_owner_conflict'):
        root.workflow.episode_bindings.for_path(literature.path, owner=other)


@pytest.mark.parametrize('changed,code', (
    ('owner', 'root_binding_selected_owner_conflict'),
    ('index', 'root_binding_parent_action_identity_conflict'),
    ('parent', 'root_binding_parent_action_identity_conflict'),
    ('descriptor', 'root_binding_selected_descriptor_conflict'),
    ('scope', 'root_binding_original_action_conflict'),
))
def test_changed_saved_child_request_is_revalidated_on_next_lookup(root, changed, code):
    child, _, _ = engineering_edge(root, root.context)
    assert root.workflow._binding_owner_for_path(child.path) == 'A105'
    other_scope = narrower_scope(root)
    def change(request):
        selected = request['message'][MEMBER]
        if changed == 'owner':
            selected['binding'] = root.workflow.episode_bindings.private_selection('A108', 'scientific_process')
        elif changed == 'index':
            selected['decision_index'] += 1
        elif changed == 'parent':
            selected['parent_episode_id'] = child.episode_id
        elif changed == 'descriptor':
            selected['binding']['descriptor']['binding_id'] = 'altered-original-descriptor'
        else:
            request['message']['scope'] = other_scope
    rewrite_request(root, child, change)
    with pytest.raises(ValueError, match=code):
        root.workflow._binding_owner_for_path(child.path)


@pytest.mark.parametrize('changed', ('kind', 'role', 'scope', 'owner'))
def test_changed_original_action_is_revalidated_without_authority_cache(root, changed):
    parent = root.context
    child, _, _ = engineering_edge(root, parent)
    assert root.workflow._binding_owner_for_path(child.path) == 'A105'
    def change(action):
        if changed == 'kind':
            action['kind'] = 'tool'
        elif changed == 'role':
            action['role'] = 'literature'
        elif changed == 'scope':
            action['scope'] = narrower_scope(root)
        else:
            action['assignment']['selection']['evidence_axis'] = root.groups['A108'][0].library.reference('A108')
    rewrite_action(root, parent, 0, change)
    expected = 'root_binding_selected_owner_conflict' if changed == 'owner' else 'root_binding_original_action_conflict'
    with pytest.raises(ValueError, match=expected):
        root.workflow._binding_owner_for_path(child.path)


@pytest.mark.parametrize('change', ('omission', 'owner_switch'))
def test_descendant_cannot_omit_or_switch_inherited_owner(root, change):
    head, _, _ = engineering_edge(root, root.context)
    recursive, _, _ = engineering_edge(root, head)
    leaf, _, _ = engineering_edge(root, recursive, role='literature')
    assert root.workflow._binding_owner_for_path(leaf.path) == 'A105'
    def alter(request):
        if change == 'omission':
            request['message'].pop(MEMBER)
        else:
            request['message'][MEMBER]['binding'] = root.workflow.episode_bindings.private_selection('A108', 'scientific_process')
    rewrite_request(root, recursive, alter)
    expected = 'root_binding_descendant_selection_missing' if change == 'omission' else 'root_binding_selected_owner_conflict'
    with pytest.raises(ValueError, match=expected):
        root.workflow._binding_owner_for_path(leaf.path)


@pytest.mark.parametrize('change', ('run', 'path'))
def test_actual_return_reader_rejects_foreign_context_identity(root, change):
    child, _, _ = engineering_edge(root, root.context)
    wrong = replace(child, run_id='other-run') if change == 'run' else replace(child, path=(*root.context.path, ('scientific_process', 'other-key')))
    with pytest.raises(ValueError, match='root_binding_context_conflict'):
        root.records.authenticate(wrong)
    assert root.records.authenticate(child) is child


def test_saved_path_change_and_missing_ancestor_are_not_inferred(root):
    child, _, _ = engineering_edge(root, root.context)
    assert root.workflow._binding_owner_for_path(child.path) == 'A105'
    row = root.workflow.journal.row('runtime_episodes', child.episode_id)
    row['path'] = json.dumps([*root.context.path, ('scientific_process', 'wrong-key')])
    root.workflow.journal.save('runtime_episodes', row)
    with pytest.raises(ValueError, match='root_binding_context_conflict'):
        root.workflow._binding_owner_for_path(child.path)
    with pytest.raises(ValueError, match='root_binding_saved_ancestor_required'):
        root.workflow._binding_owner_for_path((*root.context.path, ('scientific_process', 'missing-child')))


def test_live_private_descriptor_mutation_rejects_instead_of_using_cached_selection(root):
    child, _, _ = engineering_edge(root, root.context)
    assert root.workflow._binding_owner_for_path(child.path) == 'A105'
    head = root.groups['A105'][0]
    old = head._child_roles
    try:
        head._child_roles = ('scientific_process',)
        with pytest.raises(ValueError, match='root_binding_registered_descriptor_changed'):
            root.workflow._binding_owner_for_path(child.path)
    finally:
        head._child_roles = old
    assert root.workflow._binding_owner_for_path(child.path) == 'A105'


@pytest.mark.parametrize('raise_inside', (False, True), ids=('normal', 'exception'))
def test_actual_pending_request_seam_authenticates_and_always_cleans_up(root, raise_inside):
    child, request, selection = engineering_edge(root, root.context, save=False)
    class EngineeringConstructionFailure(Exception):
        pass
    try:
        with root.workflow.binding_construction(child.path, child.scope, selection) as selected:
            assert selected == selection
            root.workflow._construction_request(child.path, request)
            assert root.workflow._binding_owner_for_path(child.path) == 'A105'
            assert root.workflow.episode_bindings.for_path(child.path) is root.groups['A105'][0]
            with pytest.raises(ValueError, match='root_binding_concurrent_same_path_construction'):
                with root.workflow.binding_construction(child.path, child.scope, selection):
                    pytest.fail('same pending path admitted twice')
            if raise_inside:
                raise EngineeringConstructionFailure
    except EngineeringConstructionFailure:
        assert raise_inside
    assert root.workflow._constructing_binding_requests == {}
    assert root.workflow.journal.row('runtime_episodes', child.episode_id) is None


def test_saved_request_takes_precedence_and_conflicting_reopen_selection_rejects(root):
    child, request, selected = engineering_edge(root, root.context)
    conflict = detached(selected)
    conflict['binding'] = root.workflow.episode_bindings.private_selection('A108', 'scientific_process')
    with pytest.raises(ValueError, match='root_binding_restored_selection_conflict'):
        with root.workflow.binding_construction(child.path, child.scope, conflict):
            pytest.fail('conflicting saved selection admitted')
    with root.workflow.binding_construction(child.path, child.scope, None) as restored:
        assert restored == selected
        root.workflow._construction_request(child.path, request)
        rewrite_request(root, child, lambda value: value['message'][MEMBER].update(decision_index=99))
        with pytest.raises(ValueError, match='root_binding_parent_action_identity_conflict'):
            root.workflow._binding_owner_for_path(child.path)
    assert root.workflow._constructing_binding_requests == {}


def test_real_store_reopen_reauthenticates_engineering_saved_descendant(tmp_path):
    directory = tmp_path / 'reopened-owner-routing'
    with actual_owner_root(directory) as first:
        child, _, selected = engineering_edge(first, first.context, owner='A108')
        path = child.path
        original = first.workflow.journal.row('runtime_episodes', child.episode_id)['request']
        assert first.workflow._binding_owner_for_path(path) == 'A108'
    with actual_owner_root(directory, initialize=False) as reopened:
        assert reopened.workflow.journal.row('runtime_episodes', child.episode_id)['request'] == original
        assert reopened.workflow._binding_owner_for_path(path) == 'A108'
        assert reopened.workflow.episode_bindings.for_path(path) is reopened.groups['A108'][0]
        with reopened.workflow.binding_construction(path, child.scope, None) as restored:
            assert restored == selected
        rewritten = reopened.records.context(child.episode_id)
        rewrite_request(reopened, rewritten, lambda value: value['message'][MEMBER].update(decision_index=1))
        with pytest.raises(ValueError, match='root_binding_parent_action_identity_conflict'):
            reopened.workflow._binding_owner_for_path(path)


def test_saved_ownerless_child_is_explicitly_unsupported_across_multiple_groups(root):
    child, _, _ = engineering_edge(root, root.context)
    rewrite_request(root, child, lambda request: request['message'].pop(MEMBER))
    before = root.workflow.journal.row('runtime_episodes', child.episode_id)['request']
    with pytest.raises(LookupError, match='root_binding_owner_required'):
        with root.workflow.binding_construction(child.path, child.scope, None):
            pytest.fail('owner inferred from old role/path without saved authority')
    assert root.workflow.journal.row('runtime_episodes', child.episode_id)['request'] == before
    assert root.workflow._constructing_binding_requests == {}
