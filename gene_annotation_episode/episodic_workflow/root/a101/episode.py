"""Nominal selection of the existing unregistered A101 annotation parent.

Optional selection never invokes custom instance attribute or mapping methods.
Unsupported mutable shapes retain the original public construction and dispatch.
"""
from types import GetSetDescriptorType, ModuleType

def _static(cls, name):
    if type(cls) is not type:
        return None
    for base in type.__getattribute__(cls, '__mro__'):
        values = type.__getattribute__(base, '__dict__')
        if name in values:
            return values[name]
    return None

def _state(value):
    cls = type(value)
    if _static(cls, '__getattribute__') is not object.__getattribute__ or _static(cls, '__getattr__') is not None or type(_static(cls, '__dict__')) is not GetSetDescriptorType:
        return None
    state = object.__getattribute__(value, '__dict__')
    if type(state) is not dict or not all((type(key) is str for key in state)):
        return None
    return state

def _original_source_members_unchanged(overridden):
    from . import runtime
    if type(runtime) is not ModuleType:
        return False
    namespace = vars(runtime)
    source = namespace.get('_a101_annotation_original_source_type')
    if type(source) is not type or namespace.get('DecisionSource') is not source:
        return False
    values = type.__getattribute__(source, '__dict__')
    for name, present, original in namespace['_a101_parent_original_source_members']:
        if name in overridden and ((name in values) is not present or values.get(name) is not original):
            return False
    return True

def selects_annotation_parent(workflow, name, parent_path, binding):
    from . import runtime as original_runtime
    if not _original_source_members_unchanged(('next', 'call', 'execute', 'decision_state', 'instruction_composer')):
        return False
    from .runtime import Workflow
    from .episode_bindings import EpisodeBindingRegistry
    if type(workflow) is not Workflow or binding is not None or type(name) is not str or (name != 'annotation') or (type(parent_path) is not tuple) or parent_path:
        return False
    state = _state(workflow)
    if state is None:
        return False
    registry = state.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry:
        return False
    registry_state = _state(registry)
    if registry_state is None:
        return False
    roles = registry_state.get('_by_role')
    if type(roles) is not dict or not all((type(role) is str for role in roles)) or 'annotation' in roles:
        return False
    jobs = state.get('job_episodes')
    if jobs is None:
        return True
    from .homology_binding_family import HomologyBindingFamily
    if type(jobs) is not HomologyBindingFamily:
        return False
    job_state = _state(jobs)
    if job_state is None or 'roles' in job_state:
        return False
    declared = _static(HomologyBindingFamily, 'roles')
    return type(declared) is tuple and all((type(role) is str for role in declared)) and (declared == ('job_launch', 'job_monitor', 'job_results'))

def is_annotation_parent(workflow, source):
    from .task import AnnotationTask
    if type(source) is not AnnotationTask:
        return False
    state = _state(source)
    if state is None:
        return False
    path = state.get('path')
    return type(path) is tuple and len(path) == 1 and (type(path[0]) is tuple) and (len(path[0]) == 2) and (type(path[0][0]) is str) and selects_annotation_parent(workflow, path[0][0], (), None)
from .task import AnnotationTask
