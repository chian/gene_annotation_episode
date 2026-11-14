"""Select the existing unregistered iterative annotation-improvement source.

The grain is still improvement. These optional nominal guards add no graph,
credit, continuation or assignment permission. Original live methods retain all
invalid-context branches; direct construction adds no earlier admission error.
"""
from types import GetSetDescriptorType, ModuleType
import sys


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
    if (type(cls) is not type or _static(cls, '__getattribute__') is not object.__getattribute__
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


def selects_improvement_parent(workflow, name, parent_path, binding):
    runtime = sys.modules.get(__package__.rsplit('.', 1)[0] + '.runtime')
    if type(runtime) is not ModuleType:
        return False
    namespace = vars(runtime)
    workflow_type = _current_class('runtime', 'Workflow')
    if (workflow_type is None or type(workflow) is not workflow_type or binding is not None
            or type(name) is not str or name != 'improvement'
            or type(parent_path) is not tuple):
        return False
    if namespace.get('DecisionSource') is not namespace.get('_a101_annotation_original_source_type'):
        return False
    from ..episode import _original_source_members_unchanged
    if not _original_source_members_unchanged((
            '__init__', 'call', 'execute', 'next', 'decision_state',
            'instruction_composer', 'suspension_changed', 'finish')):
        return False
    if any(type(part) is not tuple or len(part) != 2
           or any(type(value) is not str or not value for value in part)
           for part in parent_path):
        return False
    lineage = tuple(part[0] for part in parent_path)
    tail = lineage[1:] if lineage and lineage[0] == 'annotation' else lineage
    if any(role != 'improvement' for role in tail):
        return False
    state = _state(workflow)
    if state is None or state.get('scientific_process_binding') is not None:
        return False
    EpisodeBindingRegistry = _current_class('episode_bindings', 'EpisodeBindingRegistry')
    registry = state.get('episode_bindings')
    if EpisodeBindingRegistry is None or type(registry) is not EpisodeBindingRegistry:
        return False
    registry_state = _state(registry)
    if registry_state is None:
        return False
    roles = registry_state.get('_by_role')
    if type(roles) is not dict or any(type(role) is not str for role in roles) or 'improvement' in roles:
        return False
    jobs = state.get('job_episodes')
    if jobs is None:
        return True
    HomologyBindingFamily = _current_class('homology_binding_family', 'HomologyBindingFamily')
    if HomologyBindingFamily is None or type(jobs) is not HomologyBindingFamily:
        return False
    job_state = _state(jobs)
    if job_state is None or 'roles' in job_state:
        return False
    declared = _static(HomologyBindingFamily, 'roles')
    return (type(declared) is tuple and all(type(role) is str for role in declared)
            and declared == ('job_launch', 'job_monitor', 'job_results'))


def is_improvement_source(workflow, source):
    ImprovementTask = _current_class('annotation_improvement.task', 'ImprovementTask')
    if ImprovementTask is None or type(source) is not ImprovementTask:
        return False
    state = _state(source)
    if state is None or state.get('workflow') is not workflow:
        return False
    path = state.get('path')
    if (type(path) is not tuple or not path or type(path[-1]) is not tuple
            or len(path[-1]) != 2 or type(path[-1][0]) is not str):
        return False
    return selects_improvement_parent(workflow, path[-1][0], path[:-1], None)


from .task import ImprovementTask
