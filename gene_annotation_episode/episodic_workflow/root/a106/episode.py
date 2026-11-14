"""The existing unregistered A106 annotation parent."""
from inspect import getattr_static
from types import GetSetDescriptorType
from .runtime import _annotation_original_DecisionSource as DecisionSource, Workflow, _annotation_original_hook_identities, _annotation_original_source_members
from .episode_bindings import EpisodeBindingRegistry
from .task import next
from .provider import call
from .task_outcomes import execute
from .instructions import instructions

def _plain_instance_state(value):
    cls = type(value)
    if (getattr_static(cls, '__getattribute__') is not object.__getattribute__
            or getattr_static(cls, '__getattr__', None) is not None
            or type(getattr_static(cls, '__dict__', None)) is not GetSetDescriptorType):
        return None
    state = object.__getattribute__(value, '__dict__')
    return state if type(state) is dict and all(type(key) is str for key in state) else None

def _original_source_members_intact(names):
    members = type.__getattribute__(DecisionSource, '__dict__')
    if 'instruction_composer' in members:
        return False
    return all(members.get(name) is original for name, original in _annotation_original_source_members if name in names)

def _original_hooks_intact(workflow):
    if type(workflow) is not Workflow:
        return False
    if not _original_source_members_intact(('next', 'call', 'execute')):
        return False
    if getattr_static(Workflow, '__getattribute__') is not object.__getattribute__:
        return False
    absent = object()
    for name in ('job_episodes', 'episode_bindings'):
        if getattr_static(Workflow, name, absent) is not absent:
            return False
    instance = _plain_instance_state(workflow)
    if instance is None:
        return False
    registry = instance.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry or _plain_instance_state(registry) is None:
        return False
    for name in ('specialist', 'is_job_source'):
        if name in instance or getattr_static(Workflow, name) is not _annotation_original_hook_identities[name]:
            return False
    return getattr_static(EpisodeBindingRegistry, 'roles') is _annotation_original_hook_identities['registry_roles']

def _plain_job_domain(workflow):
    state = _plain_instance_state(workflow)
    if state is None:
        return False
    job = state.get('job_episodes')
    if job is None:
        return True
    if _plain_instance_state(job) is None:
        return False
    if getattr_static(type(job), '__getattribute__') is not object.__getattribute__:
        return False
    if getattr_static(type(job), '__getattr__', None) is not None:
        return False
    roles = getattr_static(job, 'roles', None)
    if type(roles) not in (tuple, list, set, frozenset):
        return False
    if any((type(role) is not str for role in roles)):
        return False
    return 'annotation' not in roles

def owns_annotation_root(workflow, name, parent_path, binding):
    if type(workflow) is not Workflow or binding is not None or (not _original_hooks_intact(workflow)):
        return False
    if type(name) is not str or type(parent_path) is not tuple:
        return False
    return name == 'annotation' and len(parent_path) == 0 and _plain_job_domain(workflow)

def is_annotation_parent(workflow, source):
    if type(workflow) is not Workflow or type(source) is not AnnotationTask:
        return False
    state = _plain_instance_state(source)
    absent = object()
    if (state is None or any(getattr_static(AnnotationTask, name, absent) is not absent for name in ('workflow', 'path'))
            or state.get('workflow') is not workflow or not _original_hooks_intact(workflow)):
        return False
    path = state.get('path')
    if type(path) is not tuple or len(path) != 1 or type(path[0]) is not tuple or (len(path[0]) != 2):
        return False
    if type(path[0][0]) is not str or path[0][0] != 'annotation':
        return False
    workflow_state = _plain_instance_state(workflow)
    if workflow_state is None:
        return False
    registry = workflow_state.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry:
        return False
    registry_state = _plain_instance_state(registry)
    if registry_state is None:
        return False
    roles = registry_state.get('_by_role')
    if type(roles) is not dict or any(type(role) is not str for role in roles):
        return False
    return 'annotation' not in roles and _plain_job_domain(workflow)

class AnnotationTask(DecisionSource):
    next = next
    call = call
    execute = execute
    instruction_composer = staticmethod(instructions)
