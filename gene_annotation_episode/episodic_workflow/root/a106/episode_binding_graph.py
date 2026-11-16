"""Path selection over the declared episode binding graph."""


class BindingPathResolver:
    def for_role(self, role):
        """Resolve a role with exactly one provider; never choose between private parents."""
        try:
            candidates = self._by_role[role]
        except KeyError as error:
            raise LookupError('episode_role_not_bound:' + str(role)) from error
        if len(candidates) != 1:
            raise LookupError('episode_role_requires_parent:' + str(role))
        return candidates[0]


    def for_binding_path(self, path):
        """Resolve an explicit predefined implementation identity, without importing code."""
        try:
            return self._by_path[path]
        except KeyError as error:
            raise LookupError('episode_binding_path_not_bound:' + str(path)) from error


    def _child_binding(self, parent, role):
        candidates = self._by_role.get(role, ())
        if not candidates:
            raise LookupError('episode_role_not_bound:' + str(role))
        if parent is None:
            parent_path = None
            matches = [binding for binding in candidates if role in binding.entry_roles
                and binding.commissioning_parent in {'legacy_annotation', 'annotation'}]
        else:
            parent_path = parent.binding_path
            matches = [binding for binding in candidates
                if binding.commissioning_parent == parent_path]
            # Recursive invocations reuse their existing source home. A declared
            # direct child takes precedence over recursion of the same role.
            if not matches and role in parent.roles and role in parent.child_roles(role):
                matches = [parent]
        if len(matches) != 1:
            raise LookupError('episode_child_not_bound:' + str(parent_path) + ':' + str(role))
        return matches[0]


    def for_path(self, path):
        """Replay the declared graph using saved roles; invocation keys select no code."""
        path = tuple(tuple(part) for part in path)
        if not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                                               for item in part) for part in path):
            raise ValueError('episode_binding_runtime_path_required')
        parent = None
        for index, (role, _) in enumerate(path):
            if index == 0 and role == 'annotation' and role not in self._by_role:
                continue
            # Explicit standalone use of one bound episode remains supported,
            # including an episode normally commissioned by another binding.
            parent = self.for_role(role) if index == 0 else self._child_binding(parent, role)
        if parent is None:
            raise LookupError('episode_role_not_bound:' + path[-1][0])
        return parent


    def for_child(self, parent_path, role):
        """Select this parent's private child before preparing its assignment."""
        path = tuple(parent_path)
        parent = (None if len(path) == 1 and path[0][0] == 'annotation'
                  and 'annotation' not in self._by_role else self.for_path(path))
        return self._child_binding(parent, role)


