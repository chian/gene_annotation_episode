"""Read fixed message declarations without advancing runtime callbacks.

These reads select a private definition only. The original request still reads
its live providers, path, selection, admission and assignment at their original
positions. Custom containers/descriptors use the original shared fallback.
"""
from inspect import getattr_static
import sys
from types import ModuleType


_MISSING = object()


def _static(value, name, default=None):
    return getattr_static(value, name, default)


def _sequence(value):
    return type(value) is tuple or type(value) is list


def _strings(value):
    return _sequence(value) and all(type(item) is str for item in value)


def _plain_field(value, name):
    field = _static(value, name)
    return field if type(field) is str else None


def _plain_path(source):
    path = _static(source, 'path')
    if not _sequence(path) or not path:
        return None
    if any(not _strings(part) or len(part) != 2 for part in path):
        return None
    return path


def _group(group):
    from ..episode_bindings import EpisodeBindingRegistry
    if type(group) is not EpisodeBindingRegistry:
        return False
    by_role, bindings = _static(group, '_by_role'), _static(group, '_bindings')
    if type(by_role) is not dict or not _sequence(bindings):
        return False
    if any(type(key) is not str or not _sequence(value) for key, value in by_role.items()):
        return False
    return True


def _registry(registry):
    if not _group(registry):
        return False
    groups = _static(registry, '_owner_groups', _MISSING)
    if groups is None:
        return True
    return (type(groups) is dict
            and all(type(key) is str and _group(value) for key, value in groups.items()))


def selector_context(workflow, source, role, owner=None):
    if type(role) is not str or (owner is not None and type(owner) is not str):
        return None
    registry, path = _static(workflow, 'episode_bindings'), _plain_path(source)
    if not _registry(registry) or path is None:
        return None
    return registry, path


def declared_roles(registry):
    # All keys were checked before membership/get; str subclasses cannot run
    # equality or hashing during this additional declaration-only inspection.
    return tuple(_static(registry, '_by_role')) if _registry(registry) else ()


def implicit_parent(source, path):
    from ..task import AnnotationTask
    from ..legacy_annotation.task import LegacyAnnotationTask
    if type(source) is AnnotationTask and len(path) == 1 and path[0][0] == 'annotation':
        return 'annotation'
    if type(source) is LegacyAnnotationTask and path[-1][0] == 'improvement':
        return 'legacy_annotation'
    return None


def cached_parent(registry, source, path):
    """The actual supplied private type; no registry resolver/provider call."""
    if not _registry(registry):
        return None
    groups = _static(registry, '_owner_groups')
    supplied = (registry,) if groups is None else tuple(groups.values())
    matches = []
    for group in supplied:
        for binding in _static(group, '_bindings'):
            roles = _static(binding, 'roles')
            if not _strings(roles):
                return None
            declared = _static(binding, 'decision_source_type')
            if (declared is type(source) and path[-1][0] in roles
                    and _plain_field(binding, 'binding_path') is not None):
                if not any(binding is previous for previous in matches):
                    matches.append(binding)
    return matches[0] if len(matches) == 1 else None


def registered_child(registry, parent_source, role, owner):
    if (not _registry(registry) or type(parent_source) is not str
            or type(role) is not str or (owner is not None and type(owner) is not str)):
        return None
    groups = _static(registry, '_owner_groups')
    if groups is None:
        if owner is not None:
            return None
        group = registry
    else:
        group = groups.get(owner)
        if group is None:
            return None
    matches = []
    for binding in _static(group, '_bindings'):
        roles = _static(binding, 'roles')
        parent = _static(binding, 'commissioning_parent')
        if not _strings(roles) or (parent is not None and type(parent) is not str):
            return None
        if role in roles and parent == parent_source:
            matches.append(binding)
    return matches[0] if len(matches) == 1 else None


def declared_exchange(parent, role, *, child_binding=_MISSING):
    """Call only the fixed private declaration, never a replacement callback.

Each actual private episode module retains the original staticmethod object
beside its class. Instance/class replacements fall back before invocation.
The declaration body itself remains in its original private episode module.
"""
    owner = type(parent)
    module_name = type.__getattribute__(owner, '__module__')
    if type(module_name) is not str:
        return None
    module = sys.modules.get(module_name)
    if type(module) is not ModuleType:
        return None
    declared = vars(module).get('_declared_child_message_exchange')
    if type(declared) is not staticmethod or _static(parent, 'child_message_exchange') is not declared:
        return None
    callback = declared.__func__
    if child_binding is _MISSING:
        return callback(role)
    return callback(role, child_binding=child_binding)


def homology_child_path(workflow, source, role):
    """Fixed role/home declaration only; custody validation remains late."""
    from .homology_episode_family import HomologyEpisodes
    if type(role) is not str or type(_static(workflow, 'job_episodes')) is not HomologyEpisodes:
        return None
    path = _plain_path(source)
    if path is None or implicit_parent(source, path) is None:
        return None
    if path[0][0] not in ('annotation', 'improvement') or any(part[0] != 'improvement' for part in path[1:]):
        return None
    homes = {'job_launch': 'homology_job_submission',
             'job_monitor': 'homology_job_monitoring',
             'job_results': 'homology_result_acquisition'}
    home = homes.get(role)
    if home is None:
        return None
    return ('legacy_annotation/' if path[-1][0] == 'improvement' else '') + home
