"""The existing implicit A104 annotation parent; no registry entry."""
from . import runtime as _runtime
from .runtime import _annotation_original_decision_source as DecisionSource
from .runtime import _annotation_original_workflow as Workflow, _annotation_original_workflow_members, _annotation_original_decision_source_members
from .task import next
from .provider import call
from .task_outcomes import execute
from .instructions import instructions
from types import GetSetDescriptorType, ModuleType

def _ordinary_attributes(value):
    lookup = None
    for cls in type.__getattribute__(type(value), '__mro__'):
        definition = type.__getattribute__(cls, '__dict__')
        if '__getattr__' in definition:
            return False
        if lookup is None and '__getattribute__' in definition:
            lookup = definition['__getattribute__']
        if '__dict__' in definition and type(definition['__dict__']) is not GetSetDescriptorType:
            return False
    if lookup is not object.__getattribute__:
        return False
    state = object.__getattribute__(value, '__dict__')
    return type(state) is dict and all(type(key) is str for key in state)

def _original_hooks(workflow):
    if type(workflow) is not Workflow or not _ordinary_attributes(workflow):
        return False
    source_members = type.__getattribute__(DecisionSource, '__dict__')
    if any((name in source_members) is not present or source_members.get(name) is not original for name, present, original in _annotation_original_decision_source_members):
        return False
    instance = object.__getattribute__(workflow, '__dict__')
    declaration = type.__getattribute__(Workflow, '__dict__')
    for name, original in _annotation_original_workflow_members:
        if name in instance or declaration.get(name) is not original:
            return False
    return True

def _nonjob_annotation(workflow):
    jobs = object.__getattribute__(workflow, '__dict__').get('job_episodes')
    if jobs is None:
        return True
    # Exact authentic resource classes have literal roles. No custom property,
    # membership, provider or equality callback is invoked by this selector.
    if type(_runtime) is not ModuleType:
        return False
    namespace = vars(_runtime)
    authentic = tuple(namespace.get(name) for name in ('HomologySubmission', 'HomologyMonitoring', 'HomologyAcquisition', 'HomologyBindingFamily'))
    if not all(type(cls) is type for cls in authentic) or not any(type(jobs) is cls for cls in authentic):
        return False
    if not _ordinary_attributes(jobs):
        return False
    state = object.__getattribute__(jobs, '__dict__')
    if 'roles' in state:
        roles = state['roles']
    else:
        roles = None
        for cls in type.__getattribute__(type(jobs), '__mro__'):
            definition = type.__getattribute__(cls, '__dict__')
            if 'roles' in definition:
                roles = definition['roles']
                break
    return type(roles) is tuple and all(type(role) is str for role in roles) and 'annotation' not in roles

def owns_annotation_root(workflow, name, parent_path, binding):
    if type(workflow) is not Workflow or binding is not None:
        return False
    if type(name) is not str or name != 'annotation':
        return False
    if type(parent_path) is not tuple or len(parent_path) != 0:
        return False
    if not _original_hooks(workflow):
        return False
    from .episode_bindings import EpisodeBindingRegistry
    registry = object.__getattribute__(workflow, '__dict__').get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry or not _ordinary_attributes(registry):
        return False
    declaration = type.__getattribute__(EpisodeBindingRegistry, '__dict__')
    if declaration.get('roles') is not _runtime._annotation_original_registry_roles:
        return False
    by_role = object.__getattribute__(registry, '__dict__').get('_by_role')
    if type(by_role) is not dict or not all(type(item) is str for item in by_role) or name in by_role:
        return False
    return _nonjob_annotation(workflow)

def is_annotation_parent(workflow, source):
    if type(workflow) is not Workflow or type(source) is not AnnotationTask:
        return False
    if not _original_hooks(workflow) or not _ordinary_attributes(source):
        return False
    source_state = object.__getattribute__(source, '__dict__')
    workflow_state = object.__getattribute__(workflow, '__dict__')
    path = source_state.get('path')
    if type(path) is not tuple or len(path) != 1 or type(path[0]) is not tuple or len(path[0]) != 2:
        return False
    role = path[0][0]
    if type(role) is not str or role != 'annotation':
        return False
    from .episode_bindings import EpisodeBindingRegistry
    registry = workflow_state.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry or not _ordinary_attributes(registry):
        return False
    declaration = type.__getattribute__(EpisodeBindingRegistry, '__dict__')
    if declaration.get('roles') is not _runtime._annotation_original_registry_roles:
        return False
    by_role = object.__getattribute__(registry, '__dict__').get('_by_role')
    if type(by_role) is not dict or not all(type(item) is str for item in by_role) or role in by_role:
        return False
    return owns_annotation_root(workflow, role, (), None)

class AnnotationTask(DecisionSource):
    next = next
    call = call
    execute = execute
    instruction_composer = staticmethod(instructions)
