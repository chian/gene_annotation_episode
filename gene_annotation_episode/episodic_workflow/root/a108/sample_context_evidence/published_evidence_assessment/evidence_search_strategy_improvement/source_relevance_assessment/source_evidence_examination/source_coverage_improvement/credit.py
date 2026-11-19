"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission.

Carried from the old ``credit.py`` (``LiteratureCredit.credit_projector`` -> ``LiteratureTaskCredit``; the old
``credit_kind`` 'scientific' and ``credit_view`` over ``services.scientific_credit`` are machinery). The projector
lived in this episode's own old file; this is its private re-expression over the summary and the held records: the
old reads of ``runtime_actions`` are the unit outcomes the summary lists. Credit is ``credit_unit`` times the number
of answers; it is never bounded, clamped or rescaled here. Revision, activity and repeated reading earn nothing.
The old commission checks of ``LiteratureTaskCredit.__call__`` (run/episode/scope/request equality, the annotation
in scope and on the target) are checks of a commission against the Store; a wrong commission fails (rule 1), so
they are not carried.

The A108 task kinds are ``verified_source_leads`` and ``source_answer`` with ``assessment`` or ``screening`` (old
``LiteratureTaskCredit._answers``); another kind raises where the count would be made.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.finding_validity import (
    FindingValidity, target_eligible)
from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    canonical)

VERSION = 'literature_local_task_v1'


def credit_binding(task_key, task):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    unit = ('one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
            else 'one_answer_to_original_commission')
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'], 'unit': unit,
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The old ``lead_dispositions`` over this episode's own validated leads (it has no child, so no admitted child
    form): the latest lead per source identity, for the commissioned annotation."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def screening_answers(summary):
    """The old ``screening_answers``: the commissioned spans, when the own ``no_applicable_evidence`` declarations
    (each with its reason) cover every requested span."""
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
    records that are eligible for the target. Reads through ``FindingValidity`` and ``target_eligible``, which are
    still in the old Store form (``sqlite3`` spool, ``store._assessment_write_extent``, ``store._record_roots``)."""
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
    raise ValueError('literature_a108_task_kind_unrecognized:' + summary['task_key'])


def credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task."""
    value = summary['task']['credit_unit'] * len(answers(summary, records))
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value
