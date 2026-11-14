"""Connect actual predefined Root parents to their private message owners.

The runtime retains action, scope, child admission and saved-owner validation.
This source selector changes neither configured availability nor child identity.
Custom bindings and unrelated evidence-axis implementations retain fallback.
"""


def exchange_for_improvement(workflow, source, role):
    """Select only the original implicit task hosts, without admission callbacks."""
    _nominal = _selector_context(workflow, source, role, None)
    if _nominal is None:
        return None
    registry, path = _nominal
    if role != 'improvement':
        return None
    from .episode_bindings import EpisodeBindingRegistry
    registry = registry
    if type(registry) is not EpisodeBindingRegistry or 'improvement' in _static(registry, '_by_role'):
        return None
    from .task import AnnotationTask
    from .legacy_annotation.task import LegacyAnnotationTask
    if type(source) is AnnotationTask and len(path) == 1 and (path[0][0] == 'annotation'):
        from .to_child_legacy_annotation import prepare_request
        from .from_child_legacy_annotation import admit_return, admit_unowned_return
        return (prepare_request, admit_return, admit_unowned_return)
    if type(source) is LegacyAnnotationTask and _implicit_parent(source, path) == 'legacy_annotation':
        from .legacy_annotation.to_child_legacy_annotation import prepare_request
        from .legacy_annotation.from_child_legacy_annotation import admit_return, admit_unowned_return
        return (prepare_request, admit_return, admit_unowned_return)
    return None


def exchange_for_scientific_child(workflow, source, role, *, owner=None):
    """Use supplied nominal definitions; original request performs all lookups.

    Do not call for_child, specialist, child_roles or any provider here. The
    original expanded form and admission retain their existing error order.
    Ambiguous, custom and unsupported contexts keep the shared original path.
    """
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    if role != 'scientific_process':
        return None
    from .episode_bindings import EpisodeBindingRegistry
    registry = registry
    if type(registry) is not EpisodeBindingRegistry:
        return None
    groups = _static(registry, '_owner_groups', None)
    if groups is None:
        if owner is not None:
            return None
        group = registry
    else:
        group = groups.get(owner)
        if group is None:
            return None
    from .scientific_process.episode import ScientificProcessEpisodes
    candidates = _static(group, '_by_role', {}).get(role, ())
    if len(candidates) != 1 or type(candidates[0]) is not ScientificProcessEpisodes or _plain_field(candidates[0], 'binding_path') != 'scientific_process' or (_plain_field(candidates[0], 'commissioning_parent') != 'annotation'):
        return None
    from .task import AnnotationTask
    from .scientific_process.decision_source import ScientificDecisionSource
    if type(source) is AnnotationTask and len(path) == 1 and (path[0][0] == 'annotation'):
        from .to_child_scientific_process import prepare_request
        from .from_child_scientific_process import admit_return, admit_unowned_return
        return (prepare_request, admit_return, admit_unowned_return)
    if type(source) is ScientificDecisionSource and path[-1][0] == 'scientific_process':
        from .scientific_process.to_child_scientific_process import prepare_request
        from .scientific_process.from_child_scientific_process import admit_return, admit_unowned_return
        return (prepare_request, admit_return, admit_unowned_return)
    return None


def exchange_for_child(workflow, source, role, *, owner=None):
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    scientific_exchange = exchange_for_scientific_child(workflow, source, role, owner=owner)
    if scientific_exchange is not None:
        return scientific_exchange
    if role in ('launch_local', 'launch_hpc'):
        from .terminal_binding_catalogue import PARENT_ENTRIES, binding_class
        from .operational_child_message_owners import _registered_child
        parent_source = None
        if _implicit_parent(source, path) == 'annotation':
            parent_source = 'annotation'
        elif _implicit_parent(source, path) == 'legacy_annotation' and 'improvement' not in _declared_roles(registry):
            parent_source = 'legacy_annotation'
        elif path[-1][0] == 'scientific_process':
            from .scientific_process.episode import ScientificProcessEpisodes
            if type(_cached_parent(registry, source, path)) is ScientificProcessEpisodes:
                parent_source = 'scientific_process'
        child = None if parent_source is None else _registered_child(registry, parent_source, role, owner)
        matches = [entry for entry in PARENT_ENTRIES if entry[2] == role and _plain_field(child, 'binding_path') == entry[3]]
        if len(matches) == 1 and type(child) is binding_class(matches[0][3]):
            parent = matches[0][0]
            if parent == 'annotation':
                if len(path) != 1 or path[0][0] != 'annotation':
                    raise ValueError('private_terminal_parent_identity_required')
                if role == 'launch_local':
                    from .to_child_local_job_execution import prepare_request
                    from .from_child_local_job_execution import admit_return
                else:
                    from .to_child_hpc_job_execution import prepare_request
                    from .from_child_hpc_job_execution import admit_return
            elif parent == 'legacy_annotation':
                if path[-1][0] != 'improvement' or 'improvement' in _declared_roles(registry):
                    raise ValueError('private_terminal_parent_identity_required')
                if role == 'launch_local':
                    from .legacy_annotation.to_child_local_job_execution import prepare_request
                    from .legacy_annotation.from_child_local_job_execution import admit_return
                else:
                    from .legacy_annotation.to_child_hpc_job_execution import prepare_request
                    from .legacy_annotation.from_child_hpc_job_execution import admit_return
            elif parent == 'scientific_process':
                from .scientific_process.episode import ScientificProcessEpisodes
                if path[-1][0] != 'scientific_process' or type(_cached_parent(registry, source, path)) is not ScientificProcessEpisodes:
                    raise ValueError('private_terminal_parent_identity_required')
                if role == 'launch_local':
                    from .scientific_process.to_child_local_job_execution import prepare_request
                    from .scientific_process.from_child_local_job_execution import admit_return
                else:
                    from .scientific_process.to_child_hpc_job_execution import prepare_request
                    from .scientific_process.from_child_hpc_job_execution import admit_return
            else:
                raise ValueError('private_terminal_parent_identity_required')
            return (prepare_request, admit_return)
    monitor_exchange = exchange_for_monitor_child(workflow, source, role, owner=owner)
    if monitor_exchange is not None:
        return monitor_exchange
    from .operational_child_message_owners import exchange_for_child as operational_exchange
    exchange = operational_exchange(workflow, source, role, owner=owner)
    if exchange is not None:
        return exchange
    from .literature_child_message_owners import exchange_for_child as literature_exchange
    return literature_exchange(workflow, source, role, owner=owner)


def exchange_for_monitor_child(workflow, source, role, *, owner=None):
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    if role != 'monitor':
        return None
    from .operational_child_message_owners import _registered_child
    parent = _cached_parent(registry, source, path)
    from .execution_monitoring.episode import MonitorEpisodes as Monitor_execution_monitoring
    from .hpc_coordination.execution_monitoring.episode import MonitorEpisodes as Monitor_hpc_coordination_execution_monitoring
    from .hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes as Monitor_hpc_coordination_hpc_allocation_execution_execution_monitoring
    from .legacy_annotation.execution_monitoring.episode import MonitorEpisodes as Monitor_legacy_annotation_execution_monitoring
    from .legacy_annotation.hpc_coordination.execution_monitoring.episode import MonitorEpisodes as Monitor_legacy_annotation_hpc_coordination_execution_monitoring
    from .legacy_annotation.hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes as Monitor_legacy_annotation_hpc_coordination_hpc_allocation_execution_execution_monitoring
    from .scientific_process.execution_monitoring.episode import MonitorEpisodes as Monitor_scientific_process_execution_monitoring
    from .scientific_process.hpc_coordination.execution_monitoring.episode import MonitorEpisodes as Monitor_scientific_process_hpc_coordination_execution_monitoring
    from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes as Monitor_scientific_process_hpc_coordination_hpc_allocation_execution_execution_monitoring
    if any((type(parent) is _expected_type for _expected_type in (Monitor_execution_monitoring, Monitor_hpc_coordination_execution_monitoring, Monitor_hpc_coordination_hpc_allocation_execution_execution_monitoring, Monitor_legacy_annotation_execution_monitoring, Monitor_legacy_annotation_hpc_coordination_execution_monitoring, Monitor_legacy_annotation_hpc_coordination_hpc_allocation_execution_execution_monitoring, Monitor_scientific_process_execution_monitoring, Monitor_scientific_process_hpc_coordination_execution_monitoring, Monitor_scientific_process_hpc_coordination_hpc_allocation_execution_execution_monitoring))):
        return _declared_exchange(parent, role)
    from .hpc_coordination.episode import HPCCoordinationEpisodes as Parent_hpc_coordination
    from .hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_hpc_coordination_hpc_allocation_execution
    from .legacy_annotation.hpc_coordination.episode import HPCCoordinationEpisodes as Parent_legacy_annotation_hpc_coordination
    from .legacy_annotation.hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution
    from .scientific_process.hpc_coordination.episode import HPCCoordinationEpisodes as Parent_scientific_process_hpc_coordination
    from .scientific_process.hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_scientific_process_hpc_coordination_hpc_allocation_execution
    if any((type(parent) is _expected_type for _expected_type in (Parent_hpc_coordination, Parent_hpc_coordination_hpc_allocation_execution, Parent_legacy_annotation_hpc_coordination, Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution, Parent_scientific_process_hpc_coordination, Parent_scientific_process_hpc_coordination_hpc_allocation_execution))):
        child = _registered_child(registry, _plain_field(parent, 'binding_path'), role, owner)
        return _declared_exchange(parent, role, child_binding=child)
    if _implicit_parent(source, path) == 'annotation':
        child = _registered_child(registry, 'annotation', role, owner)
        if type(child) is Monitor_execution_monitoring:
            from .to_child_execution_monitoring import prepare_request
            from .from_child_execution_monitoring import admit_return
            return (prepare_request, admit_return)
        return None
    if _implicit_parent(source, path) == 'legacy_annotation' and 'improvement' not in _declared_roles(registry):
        child = _registered_child(registry, 'legacy_annotation', role, owner)
        if type(child) is Monitor_legacy_annotation_execution_monitoring:
            from .legacy_annotation.to_child_execution_monitoring import prepare_request
            from .legacy_annotation.from_child_execution_monitoring import admit_return
            return (prepare_request, admit_return)
        return None
    if path[-1][0] == 'scientific_process':
        from .scientific_process.episode import ScientificProcessEpisodes
        if type(parent) is not ScientificProcessEpisodes:
            return None
        child = _registered_child(registry, 'scientific_process', role, owner)
        if type(child) is Monitor_scientific_process_execution_monitoring:
            from .scientific_process.to_child_execution_monitoring import prepare_request
            from .scientific_process.from_child_execution_monitoring import admit_return
            return (prepare_request, admit_return)
        return None
    return None


def exchange_for_job_child(workflow, source, role):
    _child_path = _homology_child_path(workflow, source, role)
    if _child_path is None:
        return None
    if _child_path == 'homology_job_monitoring':
        from .to_child_homology_job_monitoring import prepare_request
        from .from_child_homology_job_monitoring import admit_return
        return (prepare_request, admit_return)
    if _child_path == 'homology_job_submission':
        from .to_child_homology_job_submission import prepare_request
        from .from_child_homology_job_submission import admit_return
        return (prepare_request, admit_return)
    if _child_path == 'homology_result_acquisition':
        from .to_child_homology_result_acquisition import prepare_request
        from .from_child_homology_result_acquisition import admit_return
        return (prepare_request, admit_return)
    if _child_path == 'legacy_annotation/homology_job_monitoring':
        from .legacy_annotation.to_child_homology_job_monitoring import prepare_request
        from .legacy_annotation.from_child_homology_job_monitoring import admit_return
        return (prepare_request, admit_return)
    if _child_path == 'legacy_annotation/homology_job_submission':
        from .legacy_annotation.to_child_homology_job_submission import prepare_request
        from .legacy_annotation.from_child_homology_job_submission import admit_return
        return (prepare_request, admit_return)
    if _child_path == 'legacy_annotation/homology_result_acquisition':
        from .legacy_annotation.to_child_homology_result_acquisition import prepare_request
        from .legacy_annotation.from_child_homology_result_acquisition import admit_return
        return (prepare_request, admit_return)
    raise ValueError('private_homology_message_owner_required')

from .library.nominal_child_messages import (selector_context as _selector_context, cached_parent as _cached_parent, registered_child as _cached_child, declared_roles as _declared_roles, declared_exchange as _declared_exchange, homology_child_path as _homology_child_path, implicit_parent as _implicit_parent, _plain_field, _static)
