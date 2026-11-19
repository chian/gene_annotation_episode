"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission.

Carried from the old ``credit.py`` (``credit_kind`` 'scientific'; ``credit_view`` -> ``services.scientific_credit``;
``credit_projector`` -> ``LiteratureTaskCredit``). That projector lived in the old shared root, which is not read.
This is a private re-expression of its credit, modelled on the library's
``literature/grading/literature_task_credit.py`` (``LiteratureTaskCredit._answers``, ``lead_dispositions``,
``screening_answers``, ``_current_assessments``), over the held records and the summary: the old reads of
``runtime_actions`` are the unit outcomes the summary lists. Credit is ``credit_unit`` times the number of answers;
it is never bounded, clamped or rescaled here. Revision, activity and repeated reading earn nothing.
The held records include those the child returned (custody), so a child's retained assessment counts as one's own, as
the old known_record_refs did.

Task kinds ``verified_source_leads`` and ``source_answer`` with ``assessment`` or ``screening`` are carried. The
three A105 kinds (``source_answer`` measurement, ``a105_experiments``, ``a105_assembly``) are counted by library
functions of ``literature/grading/literature_credit_policy.py`` (``measured_answers``, ``graded_experiment_answers``,
``assembled_answers``) that take the old binding and the old binding context; they are not callable in the final
form, so those kinds raise where the count would be made.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.finding_validity import (
    FindingValidity, target_eligible)
from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    canonical)

VERSION = 'literature_local_task_v1'


def credit_binding(task_key, task):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    unit = ('one_current_graded_assessment_per_original_experiment' if task['kind'] == 'a105_experiments'
            else 'one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
            else 'one_answer_to_original_commission')
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'], 'unit': unit,
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The old ``lead_dispositions`` over this episode's own validated leads and the leads its children returned
    (``summary['source_leads']``, in the order of the units that produced them; the old code merged own results
    and received forms by decision index): the latest lead per source identity, for the commissioned annotation.
    With no lead there is nothing to normalize."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def screening_answers(summary):
    """The old ``screening_answers``: the commissioned spans, when the own ``no_applicable_evidence`` declarations
    cover every requested span (the old function read only this episode's own actions, never a child's)."""
    task = summary['task']
    if task.get('answer_kind') != 'screening':
        return []
    spans = summary['no_applicable_evidence']
    for requested in task['examined']:
        covered = requested['start']
        intervals = sorted((span['start'], span['end']) for span in spans
                           if (span['source_ref'], span['artifact_ref']) == (requested['source_ref'],
                                                                              requested['artifact_ref']))
        for start, end in intervals:
            if start <= covered:
                covered = max(covered, end)
        if covered < requested['end']:
            return []
    return [{'proposed_annotation_ref': summary['proposed_annotation_ref'], 'disposition': 'no_applicable_evidence',
             'examined': task['examined'], 'annotation_support': 'not_assessed'}]


def current_assessments(records, summary):
    """The old ``_current_assessments``: retained current assessments of the proposed annotation among the held
    records that are eligible for the target. Reads through ``FindingValidity`` and ``target_eligible``, which
    are still in the old Store form (``sqlite3``, ``store._assessment_write_extent``)."""
    scope, proposed = summary['scope'], summary['proposed_annotation_ref']
    known = set(records.refs())
    with FindingValidity(records, scope) as validity:
        for record in validity.current_records():
            if (record['id'] in known and record['hypothesis_ref'] == proposed
                    and record.get('investigation_finding', {}).get('status') == 'retained'
                    and target_eligible(records, record, scope)):
                yield record


def assessment_answers(summary, records):
    """The old ``_answers`` assessment branch: the first current retained assessment whose observation is in one of
    the task's sources and is anchored."""
    for record in current_assessments(records, summary):
        observation = records.get(record['observation_ref'])
        if (observation['source_ref'] in summary['task']['source_refs']
                and (observation.get('anchor') is not None or observation.get('visual_anchor') is not None)):
            return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}]
    return []


def answers(summary, records):
    task = summary['task']
    if task['kind'] == 'verified_source_leads':
        return [lead for lead in lead_dispositions(summary, records) if lead['disposition'] == 'relevant']
    if task['kind'] == 'source_answer' and task['answer_kind'] == 'screening':
        return screening_answers(summary)
    if task['kind'] == 'source_answer' and task['answer_kind'] == 'assessment':
        return assessment_answers(summary, records)
    raise ValueError('literature_task_kind_not_carried:' + summary['task_key'])


def credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task."""
    value = summary['task']['credit_unit'] * len(answers(summary, records))
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value
