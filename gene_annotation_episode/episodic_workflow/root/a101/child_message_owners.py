"""ROOT_A101_TEN_ENTRY_SELECTOR: actual cached annotation child counterparts.

Selection reads nominal cached identities only. Original admission, role lookup,
schema validation and preparation still execute in the selected function at
their original positions. A custom or ambiguous cache takes the public fallback.
"""
import sys
from types import GetSetDescriptorType, MappingProxyType, ModuleType

_ROUTES = (
    ('episode_child', 'launch', 'execution_job_submission', 'ExecutionEpisode'),
    ('episode_child', 'monitor', 'execution_progress_assessment', 'MonitorEpisode'),
    ('episode_child', 'results', 'execution_result_acquisition', 'ExecutionEpisode'),
    ('job_child', 'job_launch', 'homology_job_submission', 'HomologyEpisode'),
    ('job_child', 'job_monitor', 'homology_job_monitoring', 'HomologyEpisode'),
    ('job_child', 'job_results', 'homology_result_acquisition', 'HomologyEpisode'),
    ('episode_child', 'literature', 'published_evidence_assessment', 'LiteratureEpisode'),
    ('episode_child', 'launch', 'resource_work_submission', 'ResourceEpisode'),
    ('episode_child', 'results', 'resource_result_acquisition', 'ResourceEpisode'),
    ('episode_child', 'scientific_process', 'scientific_process', 'ScientificProcessEpisode'),
)


def _static(cls, name):
    for base in type.__getattribute__(cls, '__mro__'):
        values = type.__getattribute__(base, '__dict__')
        if name in values:
            return values[name]
    return None


def _state(value):
    cls = type(value)
    if (_static(cls, '__getattribute__') is not object.__getattribute__
            or _static(cls, '__getattr__') is not None
            or type(_static(cls, '__dict__')) is not GetSetDescriptorType):
        return None
    state = object.__getattribute__(value, '__dict__')
    return state if type(state) is dict and all(type(key) is str for key in state) else None


def _current_class(module, name):
    provider = sys.modules.get(__package__ + '.' + module)
    if type(provider) is not ModuleType:
        return None
    result = vars(provider).get(name)
    return result if type(result) is type else None


def exchange_for_child(workflow, source, selection, role):
    from .episode import is_annotation_parent
    if not is_annotation_parent(workflow, source):
        return None
    if (type(selection) is not dict or not all(type(key) is str for key in selection)
            or type(role) is not str):
        return None
    kind = selection.get('kind')
    if type(kind) is not str or kind not in ('episode_child', 'job_child'):
        return None
    candidates = [row for row in _ROUTES if row[0] == kind and row[1] == role]
    if not candidates:
        return None
    workflow_state = _state(workflow)
    if workflow_state is None:
        return None
    chosen = None
    if kind == 'job_child':
        family = workflow_state.get('job_episodes')
        family_type = _current_class('homology_binding_family', 'HomologyBindingFamily')
        if family_type is None or type(family) is not family_type:
            return None
        family_state = _state(family)
        if family_state is None or 'roles' in family_state:
            return None
        members = family_state.get('bindings')
        if type(members) is not MappingProxyType:
            return None
        # The original constructor wraps a real dict, but callers can replace
        # this public attribute. A proxy over a custom Mapping must not execute
        # new __iter__/get callbacks during our optional selector.
        from gc import get_referents
        backing = get_referents(members)
        if len(backing) != 1 or type(backing[0]) is not dict:
            return None
        backing = backing[0]
        if not all(type(key) is str for key in backing):
            return None
        chosen = backing.get(role)
    else:
        registry = workflow_state.get('episode_bindings')
        registry_type = _current_class('episode_bindings', 'EpisodeBindingRegistry')
        if registry_type is None or type(registry) is not registry_type:
            return None
        state = _state(registry)
        if state is None:
            return None
        by_role, by_path = state.get('_by_role'), state.get('_by_path')
        if (type(by_role) is not dict or type(by_path) is not dict
                or not all(type(key) is str for key in by_role)
                or not all(type(key) is str for key in by_path)):
            return None
        bindings = by_role.get(role, ())
        if type(bindings) not in (list, tuple):
            return None
        roots = []
        for binding in bindings:
            state = _state(binding)
            if state is None:
                return None
            if any(key in state for key in ('roles', 'entry_roles', 'binding_path', 'commissioning_parent')):
                return None
            parent = _static(type(binding), 'commissioning_parent')
            path = _static(type(binding), 'binding_path')
            entries = _static(type(binding), 'entry_roles')
            if (type(parent) is not str or type(path) is not str or type(entries) is not tuple
                    or not all(type(entry) is str for entry in entries)):
                return None
            if parent in ('legacy_annotation', 'annotation') and role in entries:
                if by_path.get(path) is not binding:
                    return None
                roots.append(binding)
        if len(roots) != 1:
            return None
        chosen = roots[0]
    chosen_state = _state(chosen)
    if chosen_state is None or any(key in chosen_state for key in ('binding_path', 'commissioning_parent', 'roles', 'entry_roles')):
        return None
    for _, _, home, name in candidates:
        owner = _current_class(home + '.episode', name)
        if owner is None or type(chosen) is not owner:
            continue
        path = _static(owner, 'binding_path')
        parent = _static(owner, 'commissioning_parent')
        if (type(path) is not str or type(parent) is not str or path != home
                or parent != 'legacy_annotation'):
            return None
        # All comparison operands above are authenticated built-in strings.
        from importlib import import_module
        outgoing = import_module(__package__ + '.to_child_' + home)
        incoming = import_module(__package__ + '.from_child_' + home)
        return outgoing.prepare_request, incoming.admit_return
    return None
