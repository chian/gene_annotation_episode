"""Credit: the A105 head's finding progress on its own unbounded scale.

Carried from the old ``credit.py`` (``original_task_projector``: ``ScientificFindingProgress(FindingProgressPolicy(
credit_unit))`` for the declared ``evidence_axis_task_v1`` / ``whole_axis_findings`` task). The projector's formula
is the library's own and is unchanged: ``finding_unit`` times the number of distinct retained, current,
target-eligible typed findings among the assessments this Episode holds; revision, activity and repeated reading
earn nothing and annotation support stays separate.

What a child returns is its credit, its per-annotation scores, the features of its subscoring rows and its sheet states;
its assessments stay inside the child. The children's credit therefore enters this credit as returned (the page child
credits the change of the resolution of the sheet, see the page ``credit.py``); this level computes nothing from the
scores or features. Never bounded, clamped or rescaled."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress, project_finding_progress)

DETAILS_LIMIT = 24      # the old ScientificFindingProgress.loss_preview_size


def credit_binding(finding_unit):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit)).as_record()


def held_assessment_refs(records, scope):
    """The old ``EpisodeReceipts.known(episode, record_type='assessment')``: the assessments the Episode holds."""
    return [row['id'] for row in records.list('assessment', scope)]


def finding_progress(records, scope, finding_unit):
    """The old ``known_finding_credit``: the projection over the held assessments, with the old details."""
    return project_finding_progress(records, scope, FindingProgressPolicy(finding_unit),
                                    known_assessment_refs=held_assessment_refs(records, scope),
                                    details_limit=DETAILS_LIMIT, details_offset=0)


def credit(summary, records):
    """The head's own finding progress plus what its children earned (OWNER_DECISION 10: the page updates the subscoring
    sheet and produces the credit; the levels above only receive it and compute nothing). The children return only their
    credit, scores, features and sheet states, so the children's credits are added as returned."""
    value = float(summary['progress']['credit']) + math.fsum(child['credit'] for child in summary['child_returns'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value
