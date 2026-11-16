"""Actual five annotation parent counterparts; cached nominal selection only."""
from inspect import getattr_static
import sys
from .episode_bindings import EpisodeBindingRegistry

def _nominal_child(workflow, role):
    declaration = _DECLARED_CHILDREN.get(role)
    if declaration is None:
        return False
    home, class_name = declaration
    instance = vars(workflow)
    registry = instance.get('episode_bindings')
    if type(registry) is not EpisodeBindingRegistry:
        return False
    values = vars(registry)
    by_role, by_path = values.get('_by_role'), values.get('_by_path')
    if type(by_role) is not dict or type(by_path) is not dict:
        return False
    if any(type(key) is not str for key in by_role) or any(type(key) is not str for key in by_path):
        return False
    candidates = by_role.get(role, ())
    if type(candidates) not in (tuple, list):
        return False
    selected = by_path.get(home)
    loaded = sys.modules.get(__package__ + '.' + home + '.episode')
    nominal = None if loaded is None else vars(loaded).get(class_name)
    if nominal is None or type(selected) is not nominal:
        return False
    declared_path = getattr_static(selected, 'binding_path', None)
    if type(declared_path) is not str or declared_path != home:
        return False
    matches = []
    for candidate in candidates:
        entries = getattr_static(candidate, 'entry_roles', None)
        parent = getattr_static(candidate, 'commissioning_parent', None)
        if type(entries) is not tuple or any(type(value) is not str for value in entries) or type(parent) is not str:
            return False
        if role in entries and parent in ('legacy_annotation', 'annotation'):
            matches.append(candidate)
    return len(matches) == 1 and matches[0] is selected

_DECLARED_CHILDREN = {'launch': ('execution_job_submission', 'ExecutionEpisode'), 'monitor': ('execution_progress_assessment', 'MonitorEpisode'), 'results': ('execution_result_acquisition', 'ExecutionEpisode'), 'literature': ('published_evidence_assessment', 'LiteratureEpisode'), 'scientific_process': ('scientific_process', 'ScientificProcessEpisode')}

def exchange_for_child(workflow, source, role):
    if type(role) is not str or not _nominal_child(workflow, role):
        return None
    if role == 'launch':
        from .to_child_execution_job_submission import prepare_request
        from .from_child_execution_job_submission import admit_return
        return (prepare_request, admit_return)
    if role == 'monitor':
        from .to_child_execution_progress_assessment import prepare_request
        from .from_child_execution_progress_assessment import admit_return
        return (prepare_request, admit_return)
    if role == 'results':
        from .to_child_execution_result_acquisition import prepare_request
        from .from_child_execution_result_acquisition import admit_return
        return (prepare_request, admit_return)
    if role == 'literature':
        from .to_child_published_evidence_assessment import prepare_request
        from .from_child_published_evidence_assessment import admit_return
        return (prepare_request, admit_return)
    if role == 'scientific_process':
        from .to_child_scientific_process import prepare_request
        from .from_child_scientific_process import admit_return
        return (prepare_request, admit_return)
    return None
