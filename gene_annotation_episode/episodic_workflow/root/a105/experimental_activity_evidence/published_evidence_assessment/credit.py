"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission
(the old ``credit.py``: ``credit_kind`` 'scientific', ``credit_projector`` ``LiteratureTaskCredit``), computed by the
library's ``literature_task_answers.task_credit`` over this episode's summary and held records. Per task kind the
answers are: the relevant source leads (``verified_source_leads``); the screening of every commissioned span
(``screening``); one current anchored retained assessment (``assessment``); a populated quantity sheet of the
commissioned selection (``measurement``); one current grading sheet per commissioned experiment, matched to a current
assessment (``a105_experiments``); one aggregation sheet over the commissioned experiments (``a105_assembly``). An
accepted interpretation earns credit only through its saved grading sheet. Never bounded, clamped or rescaled."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    task_credit)


def credit(summary, records):
    return task_credit(summary, records)
