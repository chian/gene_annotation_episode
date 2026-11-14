"""Pure declared binding graphs for original publisher reconstruction.

The live registry and saved graph share the original path-selection methods.
Saved nodes are metadata only; they cannot execute or construct an episode.
"""
from copy import deepcopy
import json


def _require(condition, code):
    if not condition:
        raise ValueError('episode_binding_graph_' + code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


class BindingPathResolver:
    def for_role(self, role):
        """Retain unambiguous legacy lookup; never choose between private parents."""
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
        parent_path = getattr(parent, 'binding_path', None)
        if parent_path is not None:
            matches = [binding for binding in candidates
                if getattr(binding, 'commissioning_parent', None) == parent_path]
            # Recursive invocations reuse their existing source home. A declared
            # direct child takes precedence over recursion of the same role.
            if not matches and role in parent.roles and role in parent.child_roles(role):
                matches = [parent]
            # Older caller-supplied bindings have no private commissioning path.
            if not matches:
                matches = [binding for binding in candidates
                           if getattr(binding, 'binding_path', None) is None]
        elif parent is None:
            matches = [binding for binding in candidates if role in binding.entry_roles
                and getattr(binding, 'commissioning_parent', 'legacy_annotation')
                    in {'legacy_annotation', 'annotation'}]
        else:
            # A legacy parent has no path identity; only a unique role is safe.
            matches = list(candidates)
        if len(matches) != 1:
            raise LookupError('episode_child_not_bound:' + str(parent_path) + ':' + str(role))
        return matches[0]


    def for_path(self, path):
        """Replay the declared graph using saved roles; invocation keys select no code."""
        path = tuple(tuple(part) for part in path)
        if not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                                               for item in part) for part in path):
            raise ValueError('episode_binding_runtime_path_required')
        candidates = self._by_role.get(path[-1][0], ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
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
        candidates = self._by_role.get(role, ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
        path = tuple(parent_path)
        parent = (None if len(path) == 1 and path[0][0] == 'annotation'
                  and 'annotation' not in self._by_role else self.for_path(path))
        return self._child_binding(parent, role)



def snapshot_graph(registry):
    """Describe the registry's actual supplied objects; no factory or role guess."""
    rows = []
    for binding in registry._bindings:
        rows.append({'descriptor': deepcopy(binding.as_record()),
            'roles': list(binding.roles), 'entry_roles': list(binding.entry_roles),
            'binding_path': getattr(binding, 'binding_path', None),
            'commissioning_parent': getattr(binding, 'commissioning_parent', None),
            'children': {role: list(binding.child_roles(role)) for role in binding.roles}})
    result = {'version': 'episode_binding_graph_v1', 'bindings': rows}
    return result


class _SavedNode:
    def __init__(self, row):
        self.descriptor = deepcopy(row['descriptor'])
        self.roles = tuple(row['roles'])
        self.entry_roles = tuple(row['entry_roles'])
        self.binding_path = row['binding_path']
        self.commissioning_parent = row['commissioning_parent']
        self._children = {role: tuple(children) for role, children in row['children'].items()}

    def child_roles(self, role):
        return self._children[role]


def _descriptor_graph_constraints(row):
    """Reject disagreement with graph declarations already in the descriptor."""
    descriptor = row['descriptor']
    if row['binding_path'] is not None:
        _require(descriptor['binding_id'] == row['binding_path'], 'descriptor_path_conflict')
    containers = [descriptor]
    if type(descriptor.get('configuration')) is dict:
        containers.append(descriptor['configuration'])
    for declared in containers:
        for field in ('roles', 'entry_roles', 'binding_path', 'commissioning_parent'):
            if field in declared:
                _require(_canonical(declared[field]) == _canonical(row[field]), 'descriptor_' + field + '_conflict')
        if 'child_roles' in declared:
            children = declared['child_roles']
            if type(children) is dict:
                _require(_canonical(children) == _canonical(row['children']), 'descriptor_child_roles_conflict')
            else:
                _require(type(children) is list and all(_canonical(children) == _canonical(row['children'][role]) for role in row['roles']), 'descriptor_child_roles_conflict')


class SavedBindingGraph(BindingPathResolver):
    def __init__(self, value, *, expected_descriptors):
        _canonical(value)
        _require(type(value) is dict and set(value) == {'version', 'bindings'}
            and value['version'] == 'episode_binding_graph_v1' and type(value['bindings']) is list, 'record_invalid')
        _require(type(expected_descriptors) is list, 'descriptors_invalid')
        self._by_role, self._by_path, self._bindings = {}, {}, []
        descriptors = []
        for row in value['bindings']:
            _require(type(row) is dict and set(row) == {'descriptor', 'roles', 'entry_roles', 'binding_path', 'commissioning_parent', 'children'}, 'node_invalid')
            _require(type(row['descriptor']) is dict and type(row['descriptor'].get('binding_id')) is str and bool(row['descriptor']['binding_id']), 'descriptor_invalid')
            roles, entries = row['roles'], row['entry_roles']
            _require(type(roles) is list and bool(roles) and all(type(role) is str and role for role in roles) and len(set(roles)) == len(roles), 'roles_invalid')
            _require(type(entries) is list and all(type(role) is str for role in entries) and set(entries) <= set(roles), 'entry_roles_invalid')
            _require(type(row['children']) is dict and set(row['children']) == set(roles), 'children_invalid')
            for children in row['children'].values():
                _require(type(children) is list and all(type(role) is str and role for role in children), 'children_invalid')
            path, parent = row['binding_path'], row['commissioning_parent']
            _require(path is None or type(path) is str and bool(path) and all(part and part not in {'.', '..'} for part in path.split('/')) and type(parent) is str and bool(parent), 'path_invalid')
            _require(path is None or path not in self._by_path, 'duplicate_path')
            _require(not any(role in self._by_role and (path is None or any(node.binding_path is None for node in self._by_role[role])) for role in roles), 'duplicate_legacy_role')
            _descriptor_graph_constraints(row)
            node = _SavedNode(row)
            self._bindings.append(node)
            if path is not None:
                self._by_path[path] = node
            for role in roles:
                self._by_role.setdefault(role, []).append(node)
            descriptors.append(row['descriptor'])
        _require(_canonical(descriptors) == _canonical(expected_descriptors), 'saved_descriptors_conflict')
