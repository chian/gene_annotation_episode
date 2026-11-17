"""Shared Root policy assembly."""
from __future__ import annotations

def _default_scientific_child_roles(self):
    return (*(() if self.has_scientific_binding else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)

def declared_child_roles(self, role):
    """Literal type edges; availability never creates additional roles."""
    if role in self.episode_bindings.roles:
        return tuple(self.episode_bindings.declared_children(role))
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import declared_annotation_roles
    _root_handled, _root_value = declared_annotation_roles(self, role)
    if _root_handled:
        return _root_value
    if role in self.grain_names:
        return self._default_scientific_child_roles()
    return ()

def available_child_roles(self, source):
    declared = self.declared_child_roles(source.path[-1][0])
    specialist = self.specialist(source)
    roles = tuple(specialist.allowed_children(self.binding_context(source), self.services.capabilities())) if specialist is not None else declared
    if not set(roles) <= set(declared):
        raise _original_child_selection.WorkflowError('available_child_outside_declared_type_edges')
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import filter_annotation_roles
    roles = filter_annotation_roles(self, source, roles)
    return roles

def validate_child_choice(self, source, role, *, selection=None, original=False):
    """Enforce an explicit caller graph before commissioning side effects.

        Absent-marker runs retain their original selection/recovery semantics.
        These are role and ownership checks, not scientific suitability checks.
        """
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import validate_annotation_child_choice
    annotation_axes = validate_annotation_child_choice(self, source, role, selection, original)
    if self.annotation_child_roles is None:
        return
    roles = self.declared_child_roles(source.path[-1][0]) if original else self.available_child_roles(source)
    if role not in roles:
        raise ValueError('child_role_not_available_to_parent')
    if selection is not None:
        kind = selection.get('kind')
        selected_role = selection['role']
        if selected_role != role:
            raise ValueError('child_role_selection_mismatch')
        if kind == 'job_child' and (self.job_episodes is None or role not in self.job_episodes.roles or self.specialist(source) is not None) or (kind == 'episode_child' and role not in self.episode_bindings.roles):
            raise ValueError('child_kind_not_available_to_parent')

def permits_common_action(self, source, action):
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import annotation_common_action
    _root_handled, _root_value = annotation_common_action(self, source, action)
    if _root_handled:
        return _root_value
    binding = self.specialist(source)
    if binding is not None:
        return action in binding.permitted_common_actions(self.binding_context(source))
    return action in {'tool', 'wait'} or not self.is_job_source(source)

from gene_annotation_episode.episodic_workflow.root import child_selection as _original_child_selection
