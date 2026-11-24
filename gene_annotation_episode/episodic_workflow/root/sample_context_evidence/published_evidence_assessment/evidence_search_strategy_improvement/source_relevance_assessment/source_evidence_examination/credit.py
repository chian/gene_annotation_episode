"""Credit of the A108 source evidence examination (the page): the filling of the grading sheets of its leaves and nothing
else (owner, 2026-11-21: credit is earned through filling out the grading sheet and nothing else). Counted as soon as a
graded sheet is held, as the A101 head's rule: the library's ``sheet_amount`` over the sheets the page holds (each leaf
returns its sheets by reference in its finding), each sheet's own ``evidence_amount`` read through ``records``.
``credit_unit`` of the commissioned task is the setting that makes the credit comparable with the other axes. No leaf's
returned credit or field count replaces or is added to it, no passage or window read earns anything, and a relevant source
lead (a model's note) earns nothing and is returned only as information. Never bounded, clamped or rescaled here.
EXPERT_REVIEW: owner to confirm the measure."""
import math

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    sheet_amount)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, canonical)

VERSION = 'literature_sheet_credit'


def credit_binding(task_key, task):
    """The credit definition the model is shown."""
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'],
            'unit': 'one_distinct_graded_contextual_observation_in_a_held_sheet', 'revision_credit': False,
            'activity_credit': False, 'lead_credit': False, 'coverage_credit': False, 'child_credit_added': False,
            'annotation_support': 'separate'}


def relevant_lead_sources(summary, records):
    """The distinct sources (by canonical source identity) of the lead sources the leaves returned, in first-seen order:
    information only."""
    refs = summary['returned_lead_source_refs']
    if not refs:
        return []
    normalizer, distinct = FindingIdentity(records), {}
    for ref in refs:
        distinct.setdefault(canonical(normalizer.source(ref)), ref)
    return list(distinct.values())


def lead_return(summary, records):
    """The controlled lead return: the number of relevant lead sources and their references."""
    sources = relevant_lead_sources(summary, records)
    return {'relevant_lead_count': len(sources), 'lead_source_refs': sources}


def credit(summary, records):
    """The filling of the grading sheets held: ``credit_unit`` times the sheets' evidence amount."""
    value = summary['task']['credit_unit'] * sheet_amount(records, summary['finding'])
    if not math.isfinite(value):
        raise ContractError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit. A leaf child saves graded sheets that
    count as many observations as its text holds, with no finite bound the page can state: ``UNBOUNDED``. ``assess_content``
    (Jev's measurement) saves no sheet: 0. ``action_type`` is the name the runner records, a tool name (``task.TOOLS``) or a
    child slot (``task.CHILD_SLOTS``); any other name raises."""
    from . import task as episode_task
    if action_type in episode_task.CHILD_SLOTS:
        return UNBOUNDED
    if action_type in episode_task.TOOLS:
        return 0.0
    raise ValueError('ceiling_unknown_action_type:' + repr(action_type))
