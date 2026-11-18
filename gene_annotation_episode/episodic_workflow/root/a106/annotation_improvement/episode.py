"""The existing A106 improvement source; recursive invocations reuse this home."""
from inspect import getattr_static
from ..runtime import _annotation_original_DecisionSource as DecisionSource
from ..episode import Workflow, _plain_instance_state, _original_hooks_intact, _original_source_members_intact
from ..episode_bindings import EpisodeBindingRegistry
from .from_parent import __init__ as initialize_source
from .task import next
from .provider import call
from .task_outcomes import execute
from .instructions import instructions
from .to_parent import finish


def _state(value):
    if type(type(value)) is not type:
        return None
    return _plain_instance_state(value)


def unbound_improvement_domain(workflow):
    if type(workflow) is not Workflow or not _original_hooks_intact(workflow):
        return False
    if not _original_source_members_intact(('__init__', 'next', 'call', 'execute', 'finish')):
        return False
    state = _state(workflow)
    if state is None or state.get('perturbation_evidence_binding') is not None:
        return False
    registry = state.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry:
        return False
    registered = _state(registry)
    if registered is None:
        return False
    roles = registered.get('_by_role')
    if type(roles) is not dict or not all(type(role) is str for role in roles):
        return False
    if 'improvement' in roles or 'perturbation_evidence' in roles:
        return False
    jobs = state.get('job_episodes')
    if jobs is not None:
        if _state(jobs) is None:
            return False
        declared = getattr_static(jobs, 'roles', None)
        if type(declared) not in (tuple, list, set, frozenset):
            return False
        if not all(type(role) is str for role in declared) or 'improvement' in declared:
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
        registered = _state(_state(workflow)['episode_bindings'])
        if 'annotation' in registered['_by_role']:
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


def owns_improvement_path(workflow, role, path, binding):
    if (type(path) is not tuple or not path or type(path[-1]) is not tuple
            or len(path[-1]) != 2 or not all(type(item) is str and item for item in path[-1])):
        return False
    if type(role) is not str or role != path[-1][0]:
        return False
    return owns_improvement(workflow, role, path[:-1], binding)


def goal_preparer(workflow, name, parent_path):
    if owns_improvement(workflow, name, parent_path, None):
        from .goal import prepare_goal
        return prepare_goal
    return None


def exchange_for_improvement(workflow, source, selection, role):
    if (type(selection) is not dict or not all(type(key) is str for key in selection)
            or type(role) is not str or role != 'improvement'):
        return None
    kind = selection.get('kind')
    if type(kind) is not str or kind != 'child':
        return None
    from ..episode import is_annotation_parent
    if is_annotation_parent(workflow, source) and unbound_improvement_domain(workflow):
        from ..to_child_annotation_improvement import prepare_request
        from ..from_child_annotation_improvement import admit_return
        return prepare_request, admit_return
    if is_improvement_parent(workflow, source):
        from .to_child_annotation_improvement import prepare_request
        from .from_child_annotation_improvement import admit_return
        return prepare_request, admit_return
    return None


class ImprovementTask(DecisionSource):
    __init__ = initialize_source
    next = next
    call = call
    execute = execute
    finish = finish
    instruction_composer = staticmethod(instructions)
