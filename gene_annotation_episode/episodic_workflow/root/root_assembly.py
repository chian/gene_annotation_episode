"""Private root annotation root assembly."""
from __future__ import annotations
from .scoring import SignedEvidenceRootSupport

def create_signed_evidence_root_workflow(store, tools, provider, directory, run_id, controller_factory, *, assertion_ref=None, initial_known_record_refs, project_credit, credit_binding, comparison_ref=None, selections=(), **options):
    """Attach signed support while retaining the caller's actual progress policy."""
    from .runtime import Workflow
    if 'project_annotation_score' in options or 'annotation_score_binding' in options or options.get('episode_record_receipts', True) is not True:
        raise ValueError('signed_root_owns_annotation_binding_and_requires_receipts')
    options['episode_record_receipts'] = True
    scorer = SignedEvidenceRootSupport(assertion_ref, comparison_ref, selections)
    return Workflow(store, tools, provider, directory, run_id, controller_factory, project_credit, credit_binding=credit_binding, initial_known_record_refs=initial_known_record_refs, project_annotation_score=scorer, annotation_score_binding=scorer.as_record(), **options)
