"""Select only this actual private Scientific parent's recursive exchange.

Read cached nominal identities without resolving paths or invoking a provider
before the original request/receipt boundary. Custom callers retain fallback.
"""
from __future__ import annotations


def exchange_for_child(workflow, source, role):
    if role != 'sequence_homology_evidence' or type(source).__module__ != __package__ + '.task':
        return None
    from .task import ScientificInvestigationTask
    from .episode import SequenceHomologyEvidenceEpisode
    from .. import runtime
    if type(source) is not ScientificInvestigationTask or type(workflow) is not runtime.Workflow:
        return None
    if not source.path or source.path[-1][0] != 'sequence_homology_evidence':
        return None
    parent = workflow.sequence_homology_evidence_binding
    registry = workflow.episode_bindings
    if type(parent) is not SequenceHomologyEvidenceEpisode or type(registry) is not runtime.EpisodeBindingRegistry:
        return None
    if registry._by_path.get('sequence_homology_evidence') is not parent:
        return None
    candidates = registry._by_role.get(role, ())
    if len(candidates) != 1 or candidates[0] is not parent:
        return None
    from .to_child_sequence_homology_evidence import prepare_request
    from .from_child_sequence_homology_evidence import admit_return, receive_report
    return prepare_request, admit_return, receive_report
