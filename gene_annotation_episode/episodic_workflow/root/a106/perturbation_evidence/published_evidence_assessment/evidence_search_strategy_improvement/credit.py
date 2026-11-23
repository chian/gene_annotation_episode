"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission.

The one task is ``verified_source_leads``: ``summary['source_leads']`` lists the lead sources each search child's
``read_from_child`` took from its result, in the order of the units. This episode validates no lead of its own (it
reads no paper and commits no reasoning).

Carried from the old ``credit.py`` (``credit_kind`` 'scientific'; ``credit_view`` -> ``services.scientific_credit``;
``credit_projector`` -> ``LiteratureTaskCredit``). That projector lived in the old shared root, which is not read.
This is a private re-expression of its credit, modelled on the library's
``literature/grading/literature_task_credit.py`` (``LiteratureTaskCredit._answers``, ``lead_dispositions``), over the
held records and the summary. Credit is ``credit_unit`` times the number of answers; it is never bounded, clamped or
rescaled here. Revision, activity and repeated reading earn nothing.

Any other task kind raises where the count would be made.
"""
import math

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    canonical)

VERSION = 'literature_local_task'


def credit_binding(task_key, task):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'],
            'unit': 'one_verified_source_for_original_question', 'revision_credit': False, 'activity_credit': False,
            'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The old ``lead_dispositions`` over the leads of the admitted child returns, in unit order: the latest lead per
    source identity, for the commissioned annotation. With no lead there is nothing to normalize."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def answers(summary, records):
    task = summary['task']
    if task['kind'] == 'verified_source_leads':
        return [lead for lead in lead_dispositions(summary, records) if lead['disposition'] == 'relevant']
    raise ValueError('literature_task_kind_not_carried:' + summary['task_key'])


def credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task."""
    value = summary['task']['credit_unit'] * len(answers(summary, records))
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit (``arguments`` None: over every arguments it
    can take now). The credit counts only the lead sources a search child returned, so writing a search and
    ``state_query`` earn 0. A search child returns every relevant source the pages under it verify, and the number of
    hits it can have examined has no finite bound (its own yield controller decides): ``UNBOUNDED``. Any other action
    type raises."""
    if action_type in ('state_query', 'write_search'):
        return 0.0
    if action_type == 'literature_search':
        return UNBOUNDED
    raise ValueError('ceiling_unknown_action_type:' + repr(action_type))
