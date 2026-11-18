"""Cached incoming owners for Scientific's four existing nonrecursive requests.

Called only after the original substantive request callback and its dictionary
field reads. No registry, specialist, role-provider or user callback is invoked.
Unsupported mutable/custom shapes preserve the original shared admission path.
The separate recursive child_message_owners module is unchanged.
"""
import sys
from types import FunctionType, GetSetDescriptorType, ModuleType


def _static(cls, name):
    for base in type.__getattribute__(cls, '__mro__'):
        values = type.__getattribute__(base, '__dict__')
        if name in values:
            return values[name]
    return None


def _state(value):
    cls = type(value)
    if type(cls) is not type:
        return None
    if (_static(cls, '__getattribute__') is not object.__getattribute__
            or _static(cls, '__getattr__') is not None
            or type(_static(cls, '__dict__')) is not GetSetDescriptorType):
        return None
    state = object.__getattribute__(value, '__dict__')
    return state if type(state) is dict and all(type(key) is str for key in state) else None


def _current_class(module, name):
    provider = sys.modules.get(__package__.rsplit('.', 1)[0] + '.' + module)
    if type(provider) is not ModuleType:
        return None
    value = vars(provider).get(name)
    return value if type(value) is type else None

_ROUTES = (
    ('launch', 'execution_job_submission', 'ExecutionEpisode', 'prepare_commission'),
    ('monitor', 'execution_progress_assessment', 'MonitorEpisode', 'prepare_commission'),
    ('results', 'execution_result_acquisition', 'ExecutionEpisode', 'prepare_commission'),
    ('literature', 'published_evidence_assessment', 'LiteratureEpisode', 'prepare_request'),
)


def admission_for_prepared_request(workflow, source, preparer, role):
    if type(role) is not str or type(preparer) is not FunctionType:
        return None
    workflow_type = _current_class('runtime', 'Workflow')
    source_type = _current_class('perturbation_evidence.task', 'ScientificInvestigationTask')
    parent_type = _current_class('perturbation_evidence.episode', 'PerturbationEvidenceEpisode')
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
    if not science or any(value != 'perturbation_evidence' for value in science):
        return None
    parent = workflow_state.get('perturbation_evidence_binding')
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
    if type(parent_path) is not str or parent_path != 'perturbation_evidence':
        return None
    by_role, by_path = registry_state.get('_by_role'), registry_state.get('_by_path')
    if (type(by_role) is not dict or type(by_path) is not dict
            or any(type(key) is not str for key in by_role)
            or any(type(key) is not str for key in by_path)
            or by_path.get('perturbation_evidence') is not parent):
        return None
    parents = by_role.get('perturbation_evidence')
    if type(parents) not in (list, tuple) or len(parents) != 1 or parents[0] is not parent:
        return None
    candidates = by_role.get(role)
    if type(candidates) not in (list, tuple):
        return None
    children = []
    for candidate in candidates:
        state = _state(candidate)
        if state is None or any(name in state for name in declaration_names):
            return None
        declared_parent = _static(type(candidate), 'commissioning_parent')
        declared_path = _static(type(candidate), 'binding_path')
        if type(declared_parent) is not str or type(declared_path) is not str:
            return None
        if declared_parent == 'perturbation_evidence':
            if by_path.get(declared_path) is not candidate:
                return None
            children.append(candidate)
    if len(children) != 1:
        return None
    child = children[0]
    for declared_role, home, class_name, function_name in _ROUTES:
        if role != declared_role:
            continue
        child_type = _current_class('perturbation_evidence.' + home + '.episode', class_name)
        if child_type is None or type(child) is not child_type:
            continue
        child_path = _static(child_type, 'binding_path')
        if type(child_path) is not str or child_path != 'perturbation_evidence/' + home:
            return None
        outgoing = sys.modules.get(__package__ + '.to_child_' + home)
        if (type(outgoing) is not ModuleType
                or vars(outgoing).get(function_name) is not preparer):
            return None
        from importlib import import_module
        incoming = import_module(__package__ + '.from_child_' + home)
        return incoming.admit_return
    return None
