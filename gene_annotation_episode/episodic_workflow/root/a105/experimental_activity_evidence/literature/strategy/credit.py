"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission
(the old ``credit.py``: ``credit_kind`` 'scientific', ``credit_projector`` ``LiteratureTaskCredit``), computed by the
library's ``literature_task_answers.task_credit`` over this episode's summary and held records. Per task kind the
answers are: the relevant source leads (``verified_source_leads``); the screening of every commissioned span
(``screening``); one current anchored retained assessment (``assessment``); a populated quantity sheet of the
commissioned selection (``measurement``); one current grading sheet per commissioned experiment, matched to a current
assessment (``a105_experiments``); one aggregation sheet over the commissioned experiments (``a105_assembly``). An
accepted interpretation earns credit only through its saved grading sheet. Never bounded, clamped or rescaled."""
from method_loop import UNBOUNDED
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    answers, task_credit)


def credit(summary, records):
    """For an ``a105_experiments`` task the credit is what the web-search child earned (OWNER_DECISION 10: the page updates
    the subscoring sheet and produces the credit; the levels above only receive it and compute nothing). Each run starts
    from the sheet the previous child return held, so the returns add up. The other task kinds keep the library's task
    credit. For a ``verified_source_leads`` task the credit the child returned (its pages' sheet credit) is counted the
    same way, and ``credit_unit`` each is added for the leads this episode's own ``reason`` units validated
    (``own_lead_source_refs``)."""
    task = summary['task']
    if task['kind'] not in ('a105_experiments', 'verified_source_leads'):
        return task_credit(summary, records)
    value = math.fsum(child['credit'] for child in summary['child_returns'])
    if task['kind'] == 'verified_source_leads':
        value += task['credit_unit'] * len(summary['own_lead_source_refs'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over every
    arguments that action type can take now; no bound below depends on the arguments).

    The credit is ``credit_unit`` times the number of answers of the commissioned task, except for an
    ``a105_experiments`` task, where it is the sum of the credits the children returned. Per task kind:

    * ``a105_experiments``: only a child commission earns; the tools and the reasoning commit change no child return,
      so their ceiling is 0. A child returns the credit of the web-search episode, which is ``credit_unit`` times the
      change of the mean resolution R of the commissioned candidate's sheet rows over the child's run (each row's R is
      in 0..1, the credit of an axis is the mean row change). Every child starts from the sheet the previous child
      returned, so the returns telescope: their sum is ``credit_unit`` times (R_end - R_start), at most
      ``credit_unit`` (R_end <= 1, R_start >= 0). A child can therefore add at most ``credit_unit`` less what the
      children have returned so far, not below 0.
    * ``verified_source_leads``: one credit unit per relevant source. A reasoning commit carries at most one source
      lead, so it adds at most one source: ``credit_unit``. Nothing else a tool does enters the leads, so 0. A child
      returns every relevant source it found, and the number of sources it can find has no finite bound (it
      searches, reads and reasons for as many units as its own yield controller lets it run): its ceiling is
      ``UNBOUNDED``.
    * ``source_answer`` ``screening``: one answer, held once the commissioned spans are covered. If covered, every
      action has ceiling 0. Otherwise a reasoning commit (declaring spans without applicable evidence) or a child
      (returning them covered) can earn the one ``credit_unit``; the tools cannot.
    * ``source_answer`` ``assessment``: at most one answer, a current retained anchored assessment, which only a
      reasoning commit saves (or a child's return): the remaining ``credit_unit`` times (1 - answers held), else 0.
    * ``source_answer`` ``measurement``: at most one answer, a populated quantity sheet, which only
      ``literature.quantity.populate`` saves (or a child's return): the remaining ``credit_unit`` times
      (1 - answers held).
    * ``a105_assembly``: at most one answer, an aggregation sheet whose metrics come from current grading sheets:
      the aggregation operation, the grading operation and a reasoning commit (which saves grading sheets) can make
      it hold, as can a child: the remaining ``credit_unit`` times (1 - answers held); the other tools 0.
    An action that is not one of this episode's actions has ceiling 0."""
    task = summary['task']
    unit = task['credit_unit']
    kind, answer = task['kind'], task.get('answer_kind')
    is_child = action_type == 'web_search'
    if kind == 'a105_experiments':
        if not is_child:
            return 0.0
        return max(0.0, unit - credit(summary, records))
    if kind == 'verified_source_leads':
        if action_type == 'reason':
            return float(unit)
        if is_child:
            return UNBOUNDED   # the relevant sources a search child can return have no limit
        return 0.0
    remaining = float(unit) * (1 - len(answers(summary, records)))
    if answer == 'screening':
        return remaining if action_type == 'reason' or is_child else 0.0
    if answer == 'assessment':
        return remaining if action_type == 'reason' or is_child else 0.0
    if answer == 'measurement':
        return remaining if action_type == 'literature_quantity_populate' or is_child else 0.0
    return remaining if (is_child or action_type in (
        'literature_a105_aggregate', 'literature_assay_grading_populate', 'reason')) else 0.0
