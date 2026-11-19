"""Credit: the commissioned A108 literature task's credit, ``credit_unit`` for each answer to the original commission.

Carried from the old ``credit.py`` (``LiteratureCredit.credit_kind`` 'scientific', ``credit_view`` ->
``services.scientific_credit``, ``credit_projector`` -> ``LiteratureTaskCredit``) at 97308b94c. The projector was a
class of that file itself; this is the same credit re-expressed as ``credit(summary, records)`` over the held records
and the summary: the old reads of ``runtime_actions`` and ``runtime_report_attempts`` are the unit outcomes the summary
lists (this episode has no child, so no admitted child form). Credit is ``credit_unit`` times the number of answers; it
is never bounded, clamped or rescaled here. Revision, activity and repeated reading earn nothing.

The task kinds are ``verified_source_leads`` (one answer per relevant source lead) and ``source_answer`` with
``assessment`` (one current retained, target-eligible assessment anchored in the task's sources) or ``screening`` (one
answer when the own ``no_applicable_evidence`` spans cover every requested span). Any other kind raises where the count
would be made.

An assessment is accepted by the reasoning tool only together with its saved contextual grading sheet (the required
grading of ``literature_required_grading`` runs in the same unit), so no accepted interpretation is credited before its
sheet exists.

Not carried from ``LiteratureTaskCredit.__call__``: the comparison of the credit request with the episode's request
(``literature_task_credit_commission_mismatch``: a check of the commission) and ``store.read_snapshot()`` (``records``
offers no transaction). The old view fields beyond the number (``task_status``, ``unresolved``,
``source_contributions``, ``commission_ref``) are shown by the summary, not here.

``current_assessments`` reads ``FindingValidity`` and ``target_eligible`` through custody (``records``)."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.finding_validity import (
    FindingValidity, target_eligible)
from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, canonical)

VERSION = 'literature_local_task_v1'


def credit_binding(task_key, task):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    unit = ('one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
            else 'one_answer_to_original_commission')
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'], 'unit': unit,
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The old ``lead_dispositions`` over this episode's own validated leads: the latest lead per canonical source for
    the commissioned annotation. With no lead there is nothing to normalize."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def screening_answers(summary):
    """The old ``screening_answers``: the commissioned spans, when the own ``no_applicable_evidence`` declarations
    (with a reason) cover every requested span."""
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
    records that are eligible for the target."""
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
    """The old ``_answers``, after the old ``__call__`` required the proposed annotation to be a hypothesis in scope
    that roots at a target subject of the scope (``literature_task_annotation_outside_scope``,
    ``literature_task_requires_target_annotation``). The roots are those the old ``store._record_roots('hypothesis',
    ...)`` gave: the roots of the hypothesis's subjects, read through ``records.roots``."""
    task, proposed, scope = summary['task'], summary['proposed_annotation_ref'], summary['scope']
    hypothesis = records.require(proposed, {'hypothesis'})
    if not records.reference_subset([proposed], scope):
        raise ContractError('literature_task_annotation_outside_scope')
    roots = {root for ref in hypothesis['subject_refs'] for root in records.roots(ref)}
    if not roots.intersection(scope['subject_refs']):
        raise ContractError('literature_task_requires_target_annotation')
    if task['kind'] == 'verified_source_leads':
        return [lead for lead in lead_dispositions(summary, records) if lead['disposition'] == 'relevant']
    if task['kind'] == 'source_answer' and task['answer_kind'] == 'screening':
        return screening_answers(summary)
    if task['kind'] == 'source_answer' and task['answer_kind'] == 'assessment':
        return assessment_answers(summary, records)
    raise ContractError('literature_a108_task_kind_unrecognized')


def credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task."""
    value = summary['task']['credit_unit'] * len(answers(summary, records))
    if not math.isfinite(value):
        raise ContractError('literature_finite_task_credit_required')
    return value
