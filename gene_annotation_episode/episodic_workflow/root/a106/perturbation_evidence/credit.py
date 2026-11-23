"""Credit: the commissioned axis task's credit, ``credit_unit`` for each distinct retained scientific finding about
the proposed annotation that this episode holds.

Carried from the old ``credit.py`` (``PerturbationEvidenceCredit``, ``original_task_projector``) at 97308b94c: credit
kind ``scientific``; the projector ``ScientificFindingProgress(FindingProgressPolicy(credit_unit))`` built from the
assignment's ``context.evidence_task`` (``evidence_axis_task``, ``whole_axis_findings``, A106); the credit view
went through ``services.scientific_credit`` with the assignment and the scope. Here the projector's own function,
``project_finding_progress`` of the library (``findings/perturbation_evidence/investigation_progress.py``), is called
over the records this episode holds; ``ScientificFindingProgress.read_details`` restricted the known assessments to
those of the proposed annotation and that restriction is kept. The old ``known_assessment_refs`` were what the
episode had received (its form and its own reads): they are the assessments it holds now (``records.list``).

``project_finding_progress`` is still in its old Store form (``sqlite3`` spool, ``store.db``, ``store._require``,
``current_revisions``): it is reported BLOCKED-ON-STORE-ACCESS ("library not carried") and is called as written.
Credit is never bounded, clamped or rescaled here; a retained finding earns ``credit_unit`` once, however often it is
represented, and revision, activity and repeated reading earn nothing (the old projector)."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.investigation_progress import (
    FindingProgressPolicy, project_finding_progress)


def finding_progress(records, parent_input, *, details_limit=0, details_offset=0):
    """The old projection of the axis task over the held assessments of the proposed annotation."""
    scope, proposed = parent_input['scope'], parent_input['proposed_annotation_ref']
    records.require(proposed, {'hypothesis'})
    known = [row['id'] for row in records.list('assessment', scope) if row['hypothesis_ref'] == proposed]
    return project_finding_progress(records, scope, FindingProgressPolicy(parent_input['task']['credit_unit']),
                                    known_assessment_refs=known, details_limit=details_limit,
                                    details_offset=details_offset)


def credit(summary, records):
    """``credit_unit`` for each distinct retained finding of the proposed annotation."""
    value = finding_progress(records, summary, details_limit=0)['credit']
    if not math.isfinite(value):
        raise ValueError('finite_investigation_progress_required')
    return value
