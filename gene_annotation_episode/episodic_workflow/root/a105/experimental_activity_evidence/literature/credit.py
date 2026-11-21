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
    task_credit)


def credit(summary, records):
    """For an ``a105_experiments`` task the credit is what the strategy child earned (OWNER_DECISION 10: the page updates
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
    """The most the credit can rise if the action ``action_type`` with ``arguments`` is the next unit (``arguments``
    None: the most over every arguments the action type can take now). ``u`` is ``summary['task']['credit_unit']``.
    ``arguments`` of a tool is the ``ToolCall`` arguments (``{'arguments': the model's, ...}``).

    By task kind:

    * ``a105_experiments``: the credit is the sum of the strategy child's returned credits and nothing else, so every
      tool is 0. A strategy commission returns the credit of its pages, each the change of 1 - mean resolution of the
      one commissioned claim's rows over a sheet that starts from the sheet the previous return held; those changes
      telescope, so one more return adds at most the remaining 1 - R <= 1, times ``u``: ceiling ``u``.
    * ``verified_source_leads``: credit is ``u`` per relevant lead source. ``reason`` saves at most one source lead
      (the selection carries one ``source_lead``), so ``u``, or 0 when the given arguments carry no ``source_lead``.
      Every other tool is 0 (leads come only from ``reason`` units and child returns). The strategy child returns a
      list of lead sources whose length nothing held bounds: no finite ceiling exists: ``UNBOUNDED``.
    * ``source_answer`` screening: one answer, earned only by ``reason`` (a source-grounded no-applicable-evidence
      declaration) or by a child returning the spans covered. ``reason`` and the strategy commission: the unit not yet
      earned, ``u - credit`` (never below 0); every other tool 0.
    * ``source_answer`` assessment or measurement and ``a105_assembly``: at most one answer, so the credit never
      exceeds ``u``. The access and acquisition tools only read or acquire sources and cannot create the answer
      (an assessment, a quantity sheet, an aggregation sheet): 0. ``reason``, the population operations and the
      strategy commission may create it: the unit not yet earned, ``u - credit`` (0 once answered)."""
    task = summary['task']
    unit = task['credit_unit']
    kind = task['kind']
    from .task import CHILD_SLOTS, LIBRARY_NAMES, TOOL_NAMES
    if action_type not in {*TOOL_NAMES.values(), 'reason', *CHILD_SLOTS}:
        raise LookupError('no_such_action_type:' + str(action_type))
    child = action_type in CHILD_SLOTS
    reads = action_type in {TOOL_NAMES[name] for name in LIBRARY_NAMES}
    if kind == 'a105_experiments':
        return float(unit) if child else 0.0
    remaining = max(0.0, unit - credit(summary, records))
    if kind == 'verified_source_leads':
        if child:
            return UNBOUNDED   # the strategy child returns any number of lead sources
        if action_type != 'reason':
            return 0.0
        if arguments is not None and 'source_lead' not in arguments['arguments']:
            return 0.0
        return float(unit)
    if task.get('answer_kind') == 'screening':
        return remaining if child or action_type == 'reason' else 0.0
    return 0.0 if reads else remaining

