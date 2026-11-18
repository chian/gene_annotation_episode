"""Original conditional improvement recursion and configured Homology questions.

Only cached nominal selection is new. Every original request predicate and
failure remains in the substantive endpoint, including nested credit and type
rejections. No path-bound registered child is invented below improvement.
"""
from types import MappingProxyType
from ..child_message_owners import _current_class
from .episode import _state, _static, is_improvement_source

_JOB_ROUTES = (
    ('job_launch', 'homology_job_submission'),
    ('job_monitor', 'homology_job_monitoring'),
    ('job_results', 'homology_result_acquisition'),
)


def exchange_for_child(workflow, source, selection, role):
    if (type(selection) is not dict or any(type(key) is not str for key in selection)
            or type(role) is not str):
        return None
    kind = selection.get('kind')
    if type(kind) is not str or kind not in ('child', 'job_child'):
        return None
    state = _state(workflow)
    if state is None or state.get('sequence_homology_evidence_binding') is not None:
        return None
    improvement = is_improvement_source(workflow, source)
    if kind == 'child':
        if role != 'improvement':
            return None
        if improvement:
            from .to_child_annotation_improvement import prepare_request
            from .from_child_annotation_improvement import admit_return
            return prepare_request, admit_return
        from ..episode import is_annotation_parent
        if is_annotation_parent(workflow, source):
            from ..to_child_annotation_improvement import prepare_request
            from ..from_child_annotation_improvement import admit_return
            return prepare_request, admit_return
        return None
    if not improvement:
        return None
    family = state.get('job_episodes')
    family_type = _current_class('homology_binding_family', 'HomologyBindingFamily')
    if family_type is None or type(family) is not family_type:
        return None
    family_state = _state(family)
    if family_state is None or 'roles' in family_state:
        return None
    members = family_state.get('bindings')
    if type(members) is not MappingProxyType:
        return None
    from gc import get_referents
    referents = get_referents(members)
    if len(referents) != 1 or type(referents[0]) is not dict:
        return None
    backing = referents[0]
    if any(type(key) is not str for key in backing):
        return None
    child = backing.get(role)
    for declared_role, home in _JOB_ROUTES:
        if role != declared_role:
            continue
        owner = _current_class(home + '.episode', 'HomologyEpisode')
        if owner is None or type(child) is not owner:
            return None
        child_state = _state(child)
        if child_state is None or any(name in child_state for name in ('binding_path', 'commissioning_parent', 'roles')):
            return None
        path, parent = _static(owner, 'binding_path'), _static(owner, 'commissioning_parent')
        if type(path) is not str or type(parent) is not str or path != home or parent != 'legacy_annotation':
            return None
        from importlib import import_module
        outgoing = import_module(__package__ + '.to_child_' + home)
        incoming = import_module(__package__ + '.from_child_' + home)
        return outgoing.prepare_request, incoming.admit_return
    return None
