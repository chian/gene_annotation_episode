"""Cached incoming owners for Scientific's six existing nonrecursive requests.

Called only after the original substantive request callback and its dictionary
field reads. No registry, specialist, role-provider or user callback is invoked.
Unsupported mutable/custom shapes preserve the original shared admission path.
The separate recursive child_message_owners module is unchanged.
"""
import sys
from types import FunctionType, ModuleType

from ..child_message_owners import _state, _static, _current_class

_ROUTES = (
    ('launch', 'execution_job_submission', 'ExecutionEpisode', 'prepare_commission'),
    ('monitor', 'execution_progress_assessment', 'MonitorEpisode', 'prepare_commission'),
    ('results', 'execution_result_acquisition', 'ExecutionEpisode', 'prepare_commission'),
    ('launch', 'resource_work_submission', 'ResourceEpisode', 'prepare_commission'),
    ('results', 'resource_result_acquisition', 'ResourceEpisode', 'prepare_commission'),
    ('literature', 'published_evidence_assessment', 'LiteratureEpisode', 'prepare_request'),
)


def admission_for_prepared_request(workflow, source, preparer, role):
    if type(role) is not str or type(preparer) is not FunctionType:
        return None
    workflow_type = _current_class('runtime', 'Workflow')
    source_type = _current_class('scientific_process.task', 'ScientificInvestigationTask')
    parent_type = _current_class('scientific_process.episode', 'ScientificProcessEpisode')
    registry_type = _current_class('episode_bindings', 'EpisodeBindingRegistry')
    if (workflow_type is None or type(workflow) is not workflow_type
            or source_type is None or type(source) is not source_type
            or parent_type is None or registry_type is None):
        return None
    workflow_state, source_state = _state(workflow), _state(source)
    if workflow_state is None or source_state is None:
        return None
    if source_state.get('workflow') is not workflow:
        return None
    path = source_state.get('path')
    if (type(path) is not tuple or not path
            or any(type(part) is not tuple or len(part) != 2
                   or any(type(value) is not str or not value for value in part)
                   for part in path)):
        return None
    lineage = tuple(part[0] for part in path)
    science = lineage[1:] if lineage[0] == 'annotation' else lineage
    if not science or any(value != 'scientific_process' for value in science):
        return None
    parent = workflow_state.get('scientific_process_binding')
    registry = workflow_state.get('episode_bindings')
    if type(parent) is not parent_type or type(registry) is not registry_type:
        return None
    parent_state, registry_state = _state(parent), _state(registry)
    if parent_state is None or registry_state is None:
        return None
    declaration_names = ('binding_path', 'commissioning_parent', 'roles', 'entry_roles')
    if any(name in parent_state for name in declaration_names):
        return None
    parent_path = _static(parent_type, 'binding_path')
    if type(parent_path) is not str or parent_path != 'scientific_process':
        return None
    by_role, by_path = registry_state.get('_by_role'), registry_state.get('_by_path')
    if (type(by_role) is not dict or type(by_path) is not dict
            or any(type(key) is not str for key in by_role)
            or any(type(key) is not str for key in by_path)
            or by_path.get('scientific_process') is not parent):
        return None
    parents = by_role.get('scientific_process')
    if type(parents) not in (list, tuple) or len(parents) != 1 or parents[0] is not parent:
        return None
    candidates = by_role.get(role)
    if type(candidates) not in (list, tuple):
        return None
    children = []
    for candidate in candidates:
        if type(type(candidate)) is not type:
            return None
        state = _state(candidate)
        if state is None or any(name in state for name in declaration_names):
            return None
        declared_parent = _static(type(candidate), 'commissioning_parent')
        declared_path = _static(type(candidate), 'binding_path')
        if type(declared_parent) is not str or type(declared_path) is not str:
            return None
        if declared_parent == 'scientific_process':
            if by_path.get(declared_path) is not candidate:
                return None
            children.append(candidate)
    if len(children) != 1:
        return None
    child = children[0]
    for declared_role, home, class_name, function_name in _ROUTES:
        if role != declared_role:
            continue
        child_type = _current_class('scientific_process.' + home + '.episode', class_name)
        if child_type is None or type(child) is not child_type:
            continue
        child_path = _static(child_type, 'binding_path')
        if type(child_path) is not str or child_path != 'scientific_process/' + home:
            return None
        outgoing = sys.modules.get(__package__ + '.to_child_' + home)
        if (type(outgoing) is not ModuleType
                or vars(outgoing).get(function_name) is not preparer):
            return None
        from importlib import import_module
        incoming = import_module(__package__ + '.from_child_' + home)
        return incoming.admit_return, incoming.admit_unowned_return
    return None
