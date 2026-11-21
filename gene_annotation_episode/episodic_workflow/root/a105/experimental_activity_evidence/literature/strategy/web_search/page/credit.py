"""Credit: the page's credit is the filling of the grading sheet for the claim, and nothing else (owner, 2026-11-21: "it
should earn credit through filling out the grading sheet and nothing else"). It is ``credit_unit`` times the credit of the
page's latest sheet update (A105 scoring paradigm: the update of the subscoring sheet produces the credit in the same
step: the change of the resolution R of the rows, then of 1 - mean R over the classes at the main level, for the proposed
annotation). What a leaf read or stated earns nothing here until it is on the sheet. A repeat of a held fact earns
nothing. Every update regroups all the leaf records from the states the page was given, so the latest update is the
page's whole sheet credit, not an increment. Never bounded, clamped or rescaled."""
import math


def credit(summary, records):
    task = summary['task']
    update = summary['sheet_update']
    sheet = 0.0 if update is None else math.fsum(item['credit'] for item in update['credit'])
    value = task['credit_unit'] * sheet
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the episode's credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over
    every arguments that type can take now). The credit is ``credit_unit`` times the latest sheet update's credit, at
    most 1 (the mean over the classes of R(after) - R(before) with R in [0, 1]), so a rise is at most ``credit_unit``
    minus the credit held now (not
    below 0). Only a leaf child, ``chunk``, ``table`` or ``report``, and ``update_sheet`` (with a leaf record held; without
    one a sheet update cannot exist) can raise it; ``assess_content`` has ceiling 0. ``action_type`` is the name the runner
    records: a tool name (``task.TOOLS``) or a child slot (``task.CHILD_SLOTS``); any other name raises."""
    from . import task as episode_task
    if action_type not in episode_task.TOOLS and action_type not in episode_task.CHILD_SLOTS:
        raise ValueError('ceiling_unknown_action_type:' + repr(action_type))
    if action_type in episode_task.CHILD_SLOTS or (action_type == 'update_sheet' and summary['unused_leaf_record_refs']):
        return max(0.0, summary['task']['credit_unit'] - credit(summary, records))
    return 0.0
