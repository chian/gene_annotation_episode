"""Credit: the A105 head's finding progress on its own unbounded scale.

Carried from the old ``credit.py`` (``original_task_projector``: ``ScientificFindingProgress(FindingProgressPolicy(
credit_unit))`` for the declared ``evidence_axis_task_v1`` / ``whole_axis_findings`` task). The projector's formula
is the library's own and is unchanged: ``finding_unit`` times the number of distinct retained, current,
target-eligible typed findings among the assessments this Episode holds; revision, activity and repeated reading
earn nothing and annotation support stays separate.

What a child returns is its credit, its per-annotation scores, the features of its subscoring rows and its sheet states;
its assessments stay inside the child. The head's credit is its own (owner, 2026-11-21): the strongest evidence at the
closest relationship on the latest sheet state it holds minus that of the sheet it was given (library:
``literature_strongest_evidence``). The children's credits are shown in the summary and never added. Never bounded,
clamped or rescaled."""
from method_loop import UNBOUNDED
import math

from .task import TOOLS

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_strongest_evidence import (
    evidence_gain)
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
    """The strongest evidence at the closest relationship for the proposed annotation on the latest sheet state this head
    holds, minus the same on the sheet state it was given (``strongest_evidence``; 0 when it was given none). Counted as
    soon as a graded sheet is held: no assessment or reasoning commit switches it on or off (a write-up of the head's own
    earns nothing), and no model step stands between a graded result and its being counted. A child's credit is
    information in the summary and is never added (owner, 2026-11-21)."""
    value = evidence_gain(records, summary['sheet_state_refs'], summary['given_sheet_state_refs'],
                          summary['proposed_annotation_ref'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if the action ``action_type`` with ``arguments`` is the next unit.

    The credit is the rise of the strongest evidence at the closest relationship held on the sheet. ``arguments`` is what the
    unit is called with: for a tool the ``ToolCall`` arguments, for a child the ``ChildCall`` arguments (``{'objective',
    'scope', 'assignment'}``).

    * Every tool, ``reason`` included: 0. None of them changes a sheet; a write-up fills no grading sheet.
    * ``literature``: its pages can return a result stronger or closer than the best held, by an amount nothing held now
      bounds (how many papers its searches reach, what they measure): ``UNBOUNDED``.
    * ``experimental_activity_evidence`` (a narrower head): the same, through its own children: ``UNBOUNDED``.

    Where no finite bound exists the ceiling is ``UNBOUNDED`` (the owner: UNBOUNDED where truly unbounded), never a made-up number."""
    if action_type == 'reason':
        return 0.0
    if action_type == 'literature':
        return UNBOUNDED   # the sheet credit of every page below it; nothing held limits how many papers it reaches
    if action_type == 'experimental_activity_evidence':
        return UNBOUNDED   # the narrower head returns its children's credit, which has no limit held now
    if action_type in TOOLS:
        return 0.0
    raise LookupError('no_such_action_type:' + action_type)
