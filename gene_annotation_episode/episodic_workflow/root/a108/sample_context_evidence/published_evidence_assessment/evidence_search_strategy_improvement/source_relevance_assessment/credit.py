"""Credit of the A108 source relevance assessment (this episode's own copy): the differential credit of the graded
subscoring sheets this episode holds, counted as soon as a graded sheet is held (the A101 head's rule, owner, 2026-11-21).

The sheets come up by reference in the finding every child returns (``finding.grading_sheets``, one ``sheet_refs`` each, a
record reference passed in custody); the measure is the library's ``sheet_amount`` over the held sheets: each sheet's own
``evidence_amount`` cell, read through ``records``. ``credit_unit`` of the commissioned task is the setting that makes the
credit comparable with the other axes. A child's returned credit is information in the summary and is never added; a
relevant source lead (a model's note) earns nothing and is returned only as information. Never bounded, clamped or
rescaled here. EXPERT_REVIEW: owner to confirm the measure."""
import math

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    sheet_amount)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, canonical)

VERSION = 'literature_sheet_credit_v1'


def credit_binding(task_key, task):
    """The credit definition the model is shown."""
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'],
            'unit': 'one_distinct_graded_contextual_observation_in_a_held_sheet', 'revision_credit': False,
            'activity_credit': False, 'lead_credit': False, 'child_credit_added': False,
            'annotation_support': 'separate'}


def relevant_lead_sources(summary, records):
    """The distinct sources (by canonical source identity) of the lead sources the child returned, in first-seen order:
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
    """The differential credit of the graded sheets held: ``credit_unit`` times the sheets' evidence amount."""
    value = summary['task']['credit_unit'] * sheet_amount(records, summary['finding'])
    if not math.isfinite(value):
        raise ContractError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (the system's ceiling member).

    * ``source_evidence_examination``: the page child returns every graded sheet its leaves saved, and the number of
      observations they can count has no finite bound: ``UNBOUNDED``.
    * ``run_search``, ``assess_search_results`` and ``fetch_search_hit``: the provider search, Jev's measurement and the
      pick of a hit change no sheet: 0."""
    if action_type == 'source_evidence_examination':
        return UNBOUNDED
    if action_type in ('run_search', 'assess_search_results', 'fetch_search_hit'):
        return 0.0
    raise LookupError('no_such_action_type:' + str(action_type))
