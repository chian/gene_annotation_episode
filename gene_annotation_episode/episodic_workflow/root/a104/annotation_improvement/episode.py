"""The original unregistered A104 improvement; repeated invocations reuse here."""
from types import ModuleType
from .. import runtime as _runtime
from ..runtime import _annotation_original_decision_source as DecisionSource
from ..runtime import _annotation_original_workflow as Workflow
from ..episode import _ordinary_attributes, _original_hooks
from .task import next
from .provider import call
from .task_outcomes import execute
from .instructions import instructions
from .to_parent import finish


def _state(value):
    if type(type(value)) is not type or not _ordinary_attributes(value):
        return None
    state = object.__getattribute__(value, '__dict__')
    return state if type(state) is dict and all(type(key) is str for key in state) else None


def unbound_improvement_domain(workflow):
    if type(workflow) is not Workflow or not _original_hooks(workflow):
        return False
    state = _state(workflow)
    if state is None or state.get('evolutionary_history_evidence_binding') is not None:
        return False
    from ..episode_bindings import EpisodeBindingRegistry
    registry = state.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry:
        return False
    registry_state = _state(registry)
    if registry_state is None:
        return False
    by_role = registry_state.get('_by_role')
    if (type(by_role) is not dict or not all(type(role) is str for role in by_role)
            or 'improvement' in by_role or 'evolutionary_history_evidence' in by_role):
        return False
    # Existing real configured job types expose literal roles. An override or
    # custom getter/membership object retains the original public fallback.
    jobs = state.get('job_episodes')
    if jobs is not None:
        if type(_runtime) is not ModuleType:
            return False
        namespace = vars(_runtime)
        authentic = tuple(namespace.get(name) for name in (
            'HomologySubmission', 'HomologyMonitoring', 'HomologyAcquisition', 'HomologyBindingFamily'))
        if not all(type(cls) is type for cls in authentic) or not any(type(jobs) is cls for cls in authentic):
            return False
        job_state = _state(jobs)
        if job_state is None:
            return False
        roles = job_state.get('roles')
        if 'roles' not in job_state:
            for cls in type.__getattribute__(type(jobs), '__mro__'):
                namespace = type.__getattribute__(cls, '__dict__')
                if 'roles' in namespace:
                    roles = namespace['roles']
                    break
        if type(roles) is not tuple or not all(type(role) is str for role in roles) or 'improvement' in roles:
            return False
    return True


def owns_improvement(workflow, name, parent_path, binding):
    if binding is not None or type(name) is not str or name != 'improvement':
        return False
    if (type(parent_path) is not tuple
            or not all(type(part) is tuple and len(part) == 2
                       and all(type(item) is str and item for item in part) for part in parent_path)):
        return False
    if not unbound_improvement_domain(workflow):
        return False
    roles = tuple(part[0] for part in parent_path)
    if roles and roles[0] == 'annotation':
        state = _state(object.__getattribute__(workflow, '__dict__')['episode_bindings'])
        if 'annotation' in state['_by_role']:
            return False
        roles = roles[1:]
    return all(role == 'improvement' for role in roles)


def is_improvement_parent(workflow, source):
    if type(workflow) is not Workflow or type(source) is not ImprovementTask:
        return False
    state = _state(source)
    if state is None or state.get('workflow') is not workflow:
        return False
    path = state.get('path')
    if (type(path) is not tuple or not path or type(path[-1]) is not tuple
            or len(path[-1]) != 2 or not all(type(item) is str and item for item in path[-1])):
        return False
    return owns_improvement(workflow, path[-1][0], path[:-1], None)


class ImprovementTask(DecisionSource):
    next = next
    call = call
    execute = execute
    finish = finish
    instruction_composer = staticmethod(instructions)
