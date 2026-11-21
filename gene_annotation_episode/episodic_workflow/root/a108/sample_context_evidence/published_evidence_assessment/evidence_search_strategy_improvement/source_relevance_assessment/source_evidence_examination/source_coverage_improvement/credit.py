"""Credit: the filling of the grading sheets the leaf saved and nothing else (owner, 2026-11-21: credit is earned through
filling out the grading sheet and nothing else). Counted as soon as a graded sheet is held: the library's ``sheet_amount``
over the sheets of the leaf's own finding, each sheet's own ``evidence_amount`` read through ``records``. ``credit_unit`` of
the commissioned task is the setting that makes the credit comparable with the other axes. A source lead (a model's note)
earns nothing and is returned only as information; the chunks or windows read earn nothing; a ``no_applicable_evidence``
declaration saves no sheet and earns nothing. An A108 accepted interpretation reaches the held records only through the
``extract`` action of ``task.py``, which saves its subscoring sheet in the same unit (``AGENTS.md``, "Required literature
evidence processing"). Never bounded, clamped or rescaled here. EXPERT_REVIEW: owner to confirm the measure."""
import math

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    sheet_amount)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    canonical)

VERSION = 'literature_sheet_credit_v1'


def credit_binding(task_key, task):
    """The credit definition the model is shown."""
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'],
            'unit': 'one_distinct_graded_contextual_observation_in_a_held_sheet', 'revision_credit': False,
            'activity_credit': False, 'lead_credit': False, 'coverage_credit': False, 'annotation_support': 'separate'}


def lead_dispositions(summary, records):
    """The latest lead per source identity, for the commissioned annotation: information only. With no lead there is
    nothing to normalize."""
    if not summary['source_leads']:
        return []
    normalizer, current = FindingIdentity(records), {}
    for lead in summary['source_leads']:
        if lead['proposed_annotation_ref'] == summary['proposed_annotation_ref']:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def credit(summary, records):
    """``credit_unit`` times the evidence amount of the sheets the leaf saved."""
    value = summary['task']['credit_unit'] * sheet_amount(records, summary['finding'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit. The one action, ``extract``, saves sheets that
    count as many observations as the window holds, with no finite bound: ``UNBOUNDED``; any other action type is not
    offered and cannot earn."""
    if action_type != 'extract':
        return 0.0
    return UNBOUNDED
