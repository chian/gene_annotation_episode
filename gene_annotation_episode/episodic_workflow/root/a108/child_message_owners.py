"""Actual annotation and Scientific parent admission selectors; no provider probes."""
from __future__ import annotations

def nominal_episode_child(selection):
    if type(selection) is not dict or any(type(key) is not str for key in selection):
        return False
    kind = selection.get('kind')
    return type(kind) is str and kind == 'episode_child'

def exchange_for_parent(workflow, source, role):
    from .episode import is_annotation_parent, safe_cached_registry
    if type(role) is not str or not safe_cached_registry(workflow):
        return None
    if role not in ('sample_context_evidence', 'literature'):
        return None
    from .sample_context_evidence.task import ScientificTask
    from .sample_context_evidence.episode import SampleContextEvidenceEpisode
    registry = workflow.episode_bindings
    annotation = is_annotation_parent(workflow, source)
    if not annotation:
        parent = workflow.sample_context_evidence_binding
        if (type(source) is not ScientificTask or type(parent) is not SampleContextEvidenceEpisode
                or registry._by_path.get('sample_context_evidence') is not parent):
            return None
    if role == 'sample_context_evidence':
        parent = workflow.sample_context_evidence_binding
        candidates = registry._by_role.get(role, ())
        if type(parent) is not SampleContextEvidenceEpisode or len(candidates) != 1 or candidates[0] is not parent:
            return None
        if annotation:
            from .to_child_sample_context_evidence import prepare_request
            from .from_child_sample_context_evidence import admit_return
        else:
            prepare_request = None
            from .sample_context_evidence.from_child_sample_context_evidence import admit_return
    else:
        from .published_evidence_assessment.episode import LiteratureEpisode as EntryLiterature
        from .sample_context_evidence.published_evidence_assessment.episode import LiteratureEpisode as NestedLiterature
        child = registry._by_path.get('published_evidence_assessment' if annotation else 'sample_context_evidence/published_evidence_assessment')
        if (type(child) is not (EntryLiterature if annotation else NestedLiterature)
                or not any(candidate is child for candidate in registry._by_role.get(role, ()))
                or any(type(candidate) is not EntryLiterature and type(candidate) is not NestedLiterature for candidate in registry._by_role.get(role, ()))):
            return None
        if annotation:
            from .to_child_published_evidence_assessment import prepare_request
            from .from_child_published_evidence_assessment import admit_return
        else:
            prepare_request = None
            from .sample_context_evidence.from_child_published_evidence_assessment import admit_return
    return prepare_request, admit_return


def exchange_for_improvement(workflow, source, selection, role):
    from .episode import is_annotation_parent, safe_cached_registry
    from .annotation_improvement.episode import is_improvement_parent
    if (type(selection) is not dict or any(type(key) is not str for key in selection)
            or type(role) is not str or role != 'improvement'
            or not safe_cached_registry(workflow)):
        return None
    kind = selection.get('kind')
    if type(kind) is not str or kind != 'child' or workflow.sample_context_evidence_binding is not None:
        return None
    if 'improvement' in workflow.episode_bindings._by_role:
        return None
    if is_annotation_parent(workflow, source):
        from .to_child_annotation_improvement import prepare_request
        from .from_child_annotation_improvement import admit_return
    elif is_improvement_parent(workflow, source):
        from .annotation_improvement.to_child_annotation_improvement import prepare_request
        from .annotation_improvement.from_child_annotation_improvement import admit_return
    else:
        return None
    return prepare_request, admit_return
