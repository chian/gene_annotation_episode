"""Shared scientific role/default declaration and typed child-form adapters; actual private bindings and annotation policy own their decisions."""
from __future__ import annotations

def child_form_input(self, source, selection, role):
    if 'schema_json' in selection:
        return selection['schema_json']
    sources = self.root_child_return_sources(source, role)
    if not sources:
        raise _original_runtime.ContractError('child_return_form_required')
    return _original_runtime._json(self.project_credit.child_return_form(self.binding_context(source), role))

def child_initial_report_input(self, source, selection, role):
    if 'initial_report_json' in selection:
        return selection['initial_report_json']
    if not self.root_child_return_sources(source, role):
        raise _original_runtime.ContractError('child_initial_report_required')
    return '{}'

def _default_scientific_child_roles(self):
    return (*(() if self.scientific_process_binding is not None else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)

def declared_child_roles(self, role, *, path=None):
    """Literal type edges; availability never creates additional roles."""
    if role in self.episode_bindings.roles:
        return tuple(self.episode_bindings.for_path(path).child_roles(role)) if path is not None else self.episode_bindings.declared_children(role)
    from gene_annotation_episode.episodic_workflow.root.a108.commissioning_policy import declared_annotation_roles
    annotation_handled, annotation_roles = declared_annotation_roles(self, role)
    if annotation_handled:
        return annotation_roles
    if role in self.grain_names:
        return self._default_scientific_child_roles()
    return ()

def available_child_roles(self, source):
    declared = self.declared_child_roles(source.path[-1][0], path=source.path)
    specialist = self.specialist(source)
    roles = tuple(specialist.allowed_children(self.binding_context(source), self.services.capabilities())) if specialist is not None else declared
    if not set(roles) <= set(declared):
        raise _original_runtime.WorkflowError('available_child_outside_declared_type_edges')
    from gene_annotation_episode.episodic_workflow.root.a108.commissioning_policy import filter_annotation_roles
    return filter_annotation_roles(self, source, roles)

def validate_child_choice(self, source, role, *, selection=None, original=False):
    """Enforce an explicit caller graph before commissioning side effects.

        Absent-marker runs retain their original selection/recovery semantics.
        These are role and account_context checks, not scientific suitability checks.
        """
    from gene_annotation_episode.episodic_workflow.root.a108.commissioning_policy import validate_annotation_commission
    validate_annotation_commission(self, source, role, selection=selection, original=original)
    if self.annotation_child_roles is None:
        return
    roles = self.declared_child_roles(source.path[-1][0], path=source.path) if original else self.available_child_roles(source)
    if role not in roles:
        raise ValueError('child_role_not_available_to_parent')
    if selection is not None:
        kind = selection.get('kind')
        selected_role = selection.get('role', 'improvement')
        if selected_role != role or (kind == 'child' and role != 'improvement'):
            raise ValueError('child_role_selection_mismatch')
        if kind == 'job_child' and (self.job_episodes is None or role not in self.job_episodes.roles or self.specialist(source) is not None) or (kind == 'episode_child' and role not in self.episode_bindings.roles):
            raise ValueError('child_kind_not_available_to_parent')

def permits_common_action(self, source, action):
    from gene_annotation_episode.episodic_workflow.root.a108.commissioning_policy import annotation_action_permission
    annotation_permission = annotation_action_permission(self, source, action)
    if annotation_permission is not None:
        return annotation_permission
    binding = self.specialist(source)
    if binding is not None:
        return action in binding.permitted_common_actions(self.binding_context(source))
    return action in {'tool', 'wait'} or not self.is_job_source(source)

from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
