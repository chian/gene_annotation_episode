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

from .task import TOOLS

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


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if the action ``action_type`` with ``arguments`` is the next unit.

    The credit is ``finding_unit`` times the distinct retained findings among the held assessments, plus the credits the
    children returned. ``finding_unit`` is ``summary['evidence_task']['credit_unit']``. ``arguments`` is what the unit is
    called with: for a tool the ``ToolCall`` arguments (``{'arguments': the model's tool arguments, 'scope', ...}``), for a
    child the ``ChildCall`` arguments (``{'objective', 'scope', 'assignment'}``).

    * Every tool except ``reason`` (the registry reads and searches, ``process_search``, ``process_entry``,
      ``process_sources``, ``process_revise``): 0. None of them saves an assessment or returns a child credit, so neither
      term of the credit can rise.
    * ``reason``: each assessment the commit saves adds at most one distinct finding key, so at most
      ``finding_unit * len(commit['assessments'])``. The gradings, sheets and other sections add no assessment. A
      commit's assessments are not bounded by anything held now (the schema has no maximum and the commit may create its
      own observations and hypotheses), so with ``arguments`` None there is no finite bound and the call raises.
    * ``literature``: its assessments stay in the child, so only its returned credit enters. By task kind: ``a105_experiments``
      returns the sum of page credits, each the change of 1 - mean resolution of the one commissioned claim's classes over a
      sheet that starts from the sheet the previous run returned, so the sum is at most the remaining 1 - R <= 1, times the
      task's ``credit_unit``; ``source_answer`` (assessment, screening, measurement) and ``a105_assembly`` earn
      ``credit_unit`` for the one answer; ``verified_source_leads`` earns ``credit_unit`` per verified lead source, and the
      number of leads is not bounded by anything held now, so it (and ``arguments`` None, which spans that kind) raises.
    * ``experimental_activity_evidence`` (a narrower head): the child returns its own credit, a count of retained findings
      with no bound held now, so there is no finite ceiling and the call raises.

    Where no finite bound exists the call raises instead of returning a made-up number."""
    unit = summary['evidence_task']['credit_unit']
    if action_type == 'reason':
        if arguments is None:
            raise ValueError('a105_head_ceiling_unbounded:reason_assessments_not_bounded_without_arguments')
        commit = arguments['arguments']['commit']
        return float(unit * len(commit.get('assessments', [])))
    if action_type == 'literature':
        if arguments is None:
            raise ValueError('a105_head_ceiling_unbounded:literature_verified_source_leads_not_bounded')
        task = arguments['assignment']['literature_task']
        if task['kind'] == 'verified_source_leads':
            raise ValueError('a105_head_ceiling_unbounded:verified_source_leads_count_not_bounded')
        return float(task['credit_unit'])
    if action_type == 'experimental_activity_evidence':
        raise ValueError('a105_head_ceiling_unbounded:narrower_head_returns_unbounded_finding_count')
    if action_type in TOOLS:
        return 0.0
    raise LookupError('no_such_action_type:' + action_type)
