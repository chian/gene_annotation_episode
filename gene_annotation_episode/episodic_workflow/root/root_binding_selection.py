"""Mechanical ownership of root-commissioned private invocation paths.

Only request inputs are retained while synchronous construction is in progress.
Every owner lookup re-reads actual saved ancestors/actions and revalidates their
selection. No successful authority verdict is cached. Scientific preparation,
task classes and private descriptor implementations remain with their owners.
"""
from contextlib import contextmanager
import json

from .communication import plain
from .episode_return_records import EpisodeReturnRecords
from .method_loop.identities import EpisodeRef, normalize_structural_path
from .receiving_context import BindingContext


MEMBER = 'root_binding_selection'


class RootBindingSelection:
    def _owner_records(self):
        return EpisodeReturnRecords(self.store, self.run_id,
                                    failure_prefix='root_binding_')

    def _root_axis_owner(self, selection):
        from .scientific_process_records import selection_fields
        assignment = selection['assignment']
        process = assignment['selection']
        owner = process[selection_fields(process)[0]]['option_id']
        if owner not in self.episode_bindings.private_owners:
            raise ValueError('root_binding_selected_axis_not_registered')
        return owner

    def _terminal_owner_for_child(self, parent, parent_owner, action, child_path):
        """Authenticate the one explicit Root operational ownership boundary.

        Evidence-axis heads keep their existing private descendants. Only the
        genuine original Root scientific implementation can commission a Root
        Terminal child from a different owned group. Parent/action identities
        and scopes have already been authenticated by the calling traversal.
        """
        if action.get('role') not in {'launch_local', 'launch_hpc'}:
            return None
        registry = self.episode_bindings
        if parent.role == 'scientific_process':
            from .scientific_process.episode import ScientificProcessEpisodes
            # Resolve inside the already authenticated parent group. Calling
            # the public resolver here would recursively traverse ancestry.
            group = registry._selected_group(owner=parent_owner)
            if type(group.for_path(parent.path)) is not ScientificProcessEpisodes:
                return None
        elif parent.role == 'improvement':
            if parent_owner is not None or 'improvement' in registry.roles:
                return None
        elif parent.role == 'annotation':
            if parent_owner is not None or len(parent.path) != 1:
                return None
        else:
            return None
        from .root_operational_selection import original_operational_owner
        return original_operational_owner(self, action,
            parent_path=parent.path, child_path=child_path)

    def binding_selection_for_child(self, source, role, selection, index):
        registry = self.episode_bindings
        if not registry.private_owners:
            return None
        parent = self._owner_records().context(source.episode_id)
        self._owner_records().authenticate(self.binding_context(source))
        owner = self._binding_owner_for_path(parent.path)
        terminal_owner = None
        if role in {'launch_local', 'launch_hpc'}:
            from .method_loop import Episode
            child_path = Episode.identity(self.context, self.grains[role],
                f'child_{index}', parent_path=parent.path).path
            terminal_owner = self._terminal_owner_for_child(parent, owner, selection, child_path)
        if terminal_owner is not None:
            owner = terminal_owner
        elif owner is None:
            if len(parent.path) != 1 or parent.role != 'annotation' or role != 'scientific_process':
                raise ValueError('root_binding_owner_selection_requires_annotation_parent')
            owner = self._root_axis_owner(selection)
        binding = registry.for_child(parent.path, role, owner=owner)
        return {'binding': registry.private_selection(owner, binding.binding_path),
                'parent_episode_id': parent.episode_id, 'decision_index': index}

    def _validate_binding_origin(self, path, scope, selection):
        if len(path) < 2:
            raise ValueError('root_binding_original_selection_required')
        parent, parent_owner = self._binding_lineage(path[:-1])
        return self._check_binding_origin(parent, parent_owner, path, scope, selection)

    def _check_binding_origin(self, parent, parent_owner, path, scope, selection):
        """Check one edge using this traversal's already authenticated parent."""
        if (type(selection) is not dict or set(selection) !=
                {'binding', 'parent_episode_id', 'decision_index'} or
                type(selection['decision_index']) is not int or
                selection['decision_index'] < 0 or len(path) < 2):
            raise ValueError('root_binding_original_selection_required')
        index = selection['decision_index']
        parent_ref = EpisodeRef(self.run_id, path[:-1])
        if (selection['parent_episode_id'] != parent_ref.episode_id or
                path[-1][1] != 'child_' + str(index)):
            raise ValueError('root_binding_parent_action_identity_conflict')
        if parent.episode_id != parent_ref.episode_id or parent.path != path[:-1]:
            raise ValueError('root_binding_parent_context_conflict')
        row = self.journal.row('runtime_actions', parent.episode_id, index)
        if row is None:
            raise ValueError('root_binding_original_action_required')
        action = json.loads(row['action'])
        if (action.get('kind') != 'episode_child' or
                action.get('role') != path[-1][0] or
                self.store.validate_scope(action['scope'], plain(parent.scope)) != plain(scope)):
            raise ValueError('root_binding_original_action_conflict')
        owner = parent_owner
        terminal_owner = self._terminal_owner_for_child(parent, owner, action, path)
        if terminal_owner is not None:
            owner = terminal_owner
        elif owner is None:
            if len(parent.path) != 1 or parent.role != 'annotation' or path[-1][0] != 'scientific_process':
                raise ValueError('root_binding_original_root_parent_required')
            owner = self._root_axis_owner(action)
        registry = self.episode_bindings
        binding = registry.restore_private_selection(selection['binding'], expected_owner=owner)
        # This is the original graph edge check inside one selected group. The
        # parent was read/authenticated by this traversal; invoking the public
        # root resolver again here would recursively reread its whole ancestry.
        group = registry._selected_group(owner=owner)
        if group.for_child(parent.path, path[-1][0]) is not binding:
            raise ValueError('root_binding_original_private_edge_conflict')
        return owner

    def _binding_owner_for_path(self, path):
        """Authenticate the current saved request and every real ancestor."""
        _, owner = self._binding_lineage(path)
        return owner

    def _binding_lineage(self, path):
        """One ordered read/validation pass; no state survives this call."""
        path = normalize_structural_path(path)
        pending = getattr(self, '_constructing_binding_requests', {})
        inherited = None
        parent = None
        for length in range(1, len(path) + 1):
            prefix = path[:length]
            identity = EpisodeRef(self.run_id, prefix)
            row = self.journal.row('runtime_episodes', identity.episode_id)
            if row is not None:
                context = self._owner_records().context(identity.episode_id)
            elif prefix in pending and pending[prefix]['request'] is not None:
                request = pending[prefix]['request']
                message = request['message']
                context = BindingContext(self.run_id, identity.episode_id,
                    prefix[-1][0], prefix, message['scope'],
                    message.get('episode_assignment', {}), request)
                self._owner_records().authenticate(context, allow_unsaved=True)
            else:
                raise ValueError('root_binding_saved_ancestor_required')
            selected = plain(context.request['message']).get(MEMBER)
            if selected is None:
                if inherited is not None:
                    raise ValueError('root_binding_descendant_selection_missing')
            else:
                owner = self._check_binding_origin(parent, inherited, prefix, context.scope, selected)
                if inherited is not None and inherited != owner:
                    from .terminal_binding_catalogue import OWNER as TERMINAL_OWNER
                    if owner != TERMINAL_OWNER:
                        raise ValueError('root_binding_descendant_owner_conflict')
                inherited = owner
            parent = context
        return parent, inherited

    @contextmanager
    def binding_construction(self, path, scope, selection):
        """Validate before task selection, receipts, launch or initialization."""
        path = normalize_structural_path(path)
        row = self.journal.row('runtime_episodes', EpisodeRef(self.run_id, path).episode_id)
        if row is not None:
            saved = self._owner_records().context(row['episode_id'])
            original = plain(saved.request['message']).get(MEMBER)
            if selection is not None and selection != original:
                raise ValueError('root_binding_restored_selection_conflict')
            selection = original
            if plain(saved.scope) != plain(scope):
                raise ValueError('root_binding_restored_scope_conflict')
            self._binding_owner_for_path(path)
        if selection is not None:
            self._validate_binding_origin(path, scope, selection)
        elif len(path) > 1:
            if row is None:
                raise ValueError('root_binding_new_child_selection_required')
            # Ownerless historical records are not rewritten. Unowned mode
            # retains the original graph, and one explicit owner group works.
            # Multiple groups remain unsupported until real saved descriptor
            # authority can establish the historical group; roles/keys alone
            # must not manufacture that authority.
            self.episode_bindings.for_path(path)
        pending = self._constructing_binding_requests
        if path in pending:
            raise ValueError('root_binding_concurrent_same_path_construction')
        pending[path] = {'request': None}
        try:
            yield selection
        finally:
            del pending[path]

    def _construction_request(self, path, request):
        if not self.episode_bindings.private_owners:
            return
        path = normalize_structural_path(path)
        self._constructing_binding_requests[path]['request'] = plain(request.as_record())

    def scientific_binding(self, context=None):
        registry = self.episode_bindings
        if not getattr(registry, 'private_owners', ()):
            return self._legacy_scientific_process_binding
        if 'scientific_process' not in registry.roles:
            return None
        if context is None:
            return registry.for_role('scientific_process')
        owner = self._binding_owner_for_path(context.path)
        if owner is None and len(registry.private_owners) > 1:
            return None
        return registry.for_role('scientific_process', owner=owner)

    @property
    def scientific_process_binding(self):
        # Preserve unambiguous public callers. Context-free multiple-head access
        # must fail, never select the first registered library/provenance owner.
        return self.scientific_binding()

    @scientific_process_binding.setter
    def scientific_process_binding(self, binding):
        # Existing unowned callers could assign this public attribute. Keep that
        # legacy contract; explicitly owned registrations are immutable.
        if getattr(self.episode_bindings, 'private_owners', ()):
            raise ValueError('root_binding_owner_registration_is_immutable')
        self._legacy_scientific_process_binding = binding

    @property
    def has_scientific_binding(self):
        if not getattr(self.episode_bindings, 'private_owners', ()):
            return self._legacy_scientific_process_binding is not None
        return 'scientific_process' in self.episode_bindings.roles
