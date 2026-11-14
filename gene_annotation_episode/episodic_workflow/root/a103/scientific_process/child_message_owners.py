"""Select only the actual A103 scientific parent's two predefined exchanges.

Selection reads cached registry identities; it does not resolve a path, call a
provider, validate a context, or prepare a child ahead of the original boundary.
"""
from __future__ import annotations


def exchange_for_child(workflow, source, role):
    if type(role) is not str:
        return None
    from .task import ScientificProcessTask
    from .episode import ScientificProcessEpisode
    from .. import runtime as runtime
    if type(source) is not ScientificProcessTask or type(workflow) is not runtime.Workflow:
        return None
    if ((type(source.path) is not tuple and type(source.path) is not list)
            or any((type(part) is not tuple and type(part) is not list) or len(part) != 2
                   or any(type(value) is not str for value in part) for part in source.path)):
        return None
    if not source.path or source.path[-1][0] != 'scientific_process':
        return None
    parent = workflow.scientific_process_binding
    registry = workflow.episode_bindings
    if type(parent) is not ScientificProcessEpisode or type(registry) is not runtime.EpisodeBindingRegistry:
        return None
    if (type(registry._by_role) is not dict or type(registry._by_path) is not dict
            or any(type(key) is not str for key in registry._by_role)
            or any(type(key) is not str for key in registry._by_path)
            or any((type(value) is not list and type(value) is not tuple) for value in registry._by_role.values())):
        return None
    if registry._by_path.get('scientific_process') is not parent:
        return None
    if role == 'scientific_process':
        candidates = registry._by_role.get(role, ())
        if len(candidates) != 1 or candidates[0] is not parent:
            return None
        from .to_child_scientific_process import prepare_request
        from .from_child_scientific_process import admit_return, admit_unowned_return
        return prepare_request, admit_return, admit_unowned_return
    if role == 'literature':
        from .published_evidence_assessment.episode import LiteratureEpisode
        from ..published_evidence_assessment.episode import LiteratureEpisode as StandaloneLiteratureEpisode
        child = registry._by_path.get('scientific_process/published_evidence_assessment')
        candidates = registry._by_role.get(role, ())
        if type(child) is not LiteratureEpisode or not any(candidate is child for candidate in candidates):
            return None
        if any(type(candidate) is not LiteratureEpisode and type(candidate) is not StandaloneLiteratureEpisode for candidate in candidates):
            return None
        from .to_child_published_evidence_assessment import prepare_request
        from .from_child_published_evidence_assessment import admit_return, admit_unowned_return
        return prepare_request, admit_return, admit_unowned_return
    return None
