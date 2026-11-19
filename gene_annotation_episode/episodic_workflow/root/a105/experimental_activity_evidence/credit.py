"""Credit: the A105 head's finding progress on its own unbounded scale.

Carried from the old ``credit.py`` (``original_task_projector``: ``ScientificFindingProgress(FindingProgressPolicy(
credit_unit))`` for the declared ``evidence_axis_task_v1`` / ``whole_axis_findings`` task). The projector's formula
is the library's own and is unchanged: ``finding_unit`` times the number of distinct retained, current,
target-eligible typed findings among the assessments this Episode holds; revision, activity and repeated reading
earn nothing and annotation support stays separate.

What a child returns is its credit and the controlled features of its grading sheets; its assessments stay inside
the child. The children's graded experiments therefore enter this credit through the features: ``finding_unit`` for
each distinct experiment graded in a returned sheet for the proposed annotation that the head's own sheets do not
already grade. A105 evidence processing: an accepted interpretation earns credit only through its saved subscoring
sheet; the head's own sheets are written by its ``reason`` unit together with the interpretation, and a returned
sheet was written the same way by the child that returns it. Never bounded, clamped or rescaled."""
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


def returned_experiments(summary):
    """The experiments graded for the proposed annotation in sheets the children returned and not in the head's own
    sheets."""
    own = {features['experiment_refs'][0] for features in summary['own_assay_sheets']}
    proposed = [summary['proposed_annotation_ref']]
    return {features['experiment_refs'][0] for features in summary['assay_sheets']
            if features['assertion_refs'] == proposed} - own


def credit(summary, records):
    unit = summary['evidence_task']['credit_unit']
    return float(summary['progress']['credit']) + unit * len(returned_experiments(summary))
