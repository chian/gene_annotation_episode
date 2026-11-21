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
    """For an ``a105_experiments`` task the credit is what the page children earned (OWNER_DECISION 10: the page updates the
    subscoring sheet and produces the credit; this level only receives it and computes nothing). Each page starts from the
    sheet the previous page returned, so the page credits add up. The other task kinds keep the library's task credit."""
    if summary['task']['kind'] != 'a105_experiments':
        return task_credit(summary, records)
    value = math.fsum(child['credit'] for child in summary['child_returns'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


_SLACK = 1e-9
# The tools that write the records a task kind's answers read (the python tool names of ``task.TOOL_NAMES``).
_QUANTITY_WRITERS = ('literature_quantity_populate',)
_ASSEMBLY_WRITERS = ('literature_a105_aggregate', 'literature_assay_grading_populate', 'reason')
_ADMITTING = ('state_query',)   # admits already stored records into custody, so can make a held answer appear


def _lead_in(arguments):
    """Whether a ``reason`` call carries a source lead (the envelope the task builds, or the model's own arguments)."""
    if arguments is None:
        return True
    inner = arguments.get('arguments', arguments) if hasattr(arguments, 'get') else arguments
    return hasattr(inner, 'get') and 'source_lead' in inner


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over every
    arguments it can take now). A call the episode does not offer earns 0.

    a105_experiments task. The credit is the sum of the page children's credits and nothing else, so every tool and
    ``reason`` earn 0. A page child's credit is credit_unit times the mean over the commissioned classes of the change
    of the row resolution R (R in 0..1, a placeholder row counts 0) from the sheet states it was handed. Each page is
    handed the sheet the previous page returned, so the page credits telescope: the total never exceeds
    credit_unit times the number of candidates K (the annotations the sheet holds scores for, at least one) minus what
    the sheet already held. The most the next page adds is credit_unit * K minus the credit held now, at least 0.

    Other task kinds: credit is credit_unit times the answers, and each kind has a fixed most.
    verified_source_leads: one answer per relevant source, read only from the Episode's own ``reason`` outcomes (one
    validated source lead each) and from the lead sources a child returned. ``reason`` with a source lead adds at most
    one source (credit_unit); without one it adds 0; tools add 0. The page child can return any number of lead
    sources (it can acquire and judge new ones) with no finite bound: that ceiling is ``UNBOUNDED``.
    screening: one answer, once the commissioned spans are covered, by ``reason`` declarations or a child's return:
    ``reason`` and the page child can each add credit_unit minus what is held; tools add 0.
    assessment: one answer (the first current retained anchored assessment of the task's sources): ``reason`` (which
    writes assessments), the page child and ``state_query`` (which admits stored records so an existing assessment
    becomes held) can each add credit_unit minus what is held; other tools add 0.
    measurement: one answer (a populated quantity sheet of the commissioned selection): the quantity population
    tool, the page child and ``state_query`` can add credit_unit minus what is held; the rest 0.
    a105_assembly: one answer (an aggregation sheet over the commissioned experiments from current grading sheets):
    the aggregation and grading population tools, ``reason`` (saves grading sheets), the page child and
    ``state_query`` can add credit_unit minus what is held; the rest 0."""
    from .task import offered_actions
    if action_type not in offered_actions(summary, ctx):
        return 0.0
    task = summary['task']
    unit = task['credit_unit']
    held = credit(summary, records)
    if task['kind'] == 'a105_experiments':
        if action_type != 'page':
            return 0.0
        total = unit * max(1, len(summary['scores']))
        return max(0.0, total - held) + _SLACK * total
    kind, answer = task['kind'], task.get('answer_kind')
    if kind == 'verified_source_leads':
        if action_type == 'reason':
            return unit if _lead_in(arguments) else 0.0
        if action_type == 'page':
            return UNBOUNDED   # a page can return any number of lead sources
        return 0.0
    remaining = max(0.0, unit - held) + _SLACK * unit
    if answer == 'screening':
        writers = ('reason', 'page')
    elif answer == 'assessment':
        writers = ('reason', 'page', *_ADMITTING)
    elif answer == 'measurement':
        writers = (*_QUANTITY_WRITERS, 'page', *_ADMITTING)
    else:
        writers = (*_ASSEMBLY_WRITERS, 'page', *_ADMITTING)
    return remaining if action_type in writers else 0.0
