"""Credit: the page's one task, ``verified_source_leads``: ``credit_unit`` for each verified source of the original
question (the latest relevant lead per source identity, for the commissioned annotation).

Private copy of the credit of the sibling reading episodes. ``summary['source_leads']`` lists the relevant source leads
the leaf children returned, in the order of the units. Carried from the old ``LiteratureTaskCredit`` (``lead_dispositions``)
of the library's ``literature/grading/literature_task_credit.py``; the old screening and assessment answers, and the
leads of an own reasoning commit, belong to deleted behaviour (the page reads nothing and commits no reasoning) and are
not carried. Credit is ``credit_unit`` times the number of answers; it is never bounded, clamped or rescaled here.
Revision, activity and repeated reading earn nothing."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    canonical)

VERSION = 'literature_local_task_v1'


def credit_binding(task_key, task):
    """The credit definition the model is shown."""
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'],
            'unit': 'one_verified_source_for_original_question', 'revision_credit': False, 'activity_credit': False,
            'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The latest lead per source identity, for the commissioned annotation. With no lead there is nothing to
    normalize."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def credit(summary, records):
    """``credit_unit`` for each verified source."""
    answers = [lead for lead in lead_dispositions(summary, records) if lead['disposition'] == 'relevant']
    value = summary['task']['credit_unit'] * len(answers)
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit. The page has one source, so at most one lead
    can count: a leaf child (``literature_table``, ``literature_ordered``, ``literature_targeted``) can raise the
    credit by at most ``credit_unit`` minus the credit held now (not below 0); ``assess_content`` can raise nothing.
    Any other action type raises."""
    from . import task as episode_task
    if action_type in episode_task.CHILD_SLOTS:
        return max(0.0, summary['task']['credit_unit'] - credit(summary, records))
    if action_type in episode_task.TOOLS:
        return 0.0
    raise ValueError('ceiling_unknown_action_type:' + repr(action_type))
