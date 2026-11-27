"""Credit, bounded and read from what the episode holds: the terms of ``bvbrc_job_child.bounded_credit`` (an estimate held, the
job launched, the job known ended, the graded analysis: each worth its unit once and counted only when new in this
commission), with the graded analysis counted from this episode's own completed ``extract`` unit: a graded analysis the
parent passed is not its result."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    ENDED_JOB_STATES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_metacats_search import (
    requirement_problems)

ACTION_TYPES = ('estimate', 'launch', 'fix', 'monitor', 'extract')


def credit(summary, records):
    units, until, prior = summary['units'], summary['until'], summary['prior']
    rows = summary['unit_rows']
    new = not summary['resumed']
    estimate = new and any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows)
    handoff = new and any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows)
    extracted = until == 'extracted'
    ended = extracted and not summary['known_ended'] and any(
        row['event'] == 'check' and row['id'] not in prior['check_refs'] and row['detail']['state'] in ENDED_JOB_STATES
        for row in job_rows(records))
    graded = extracted and any(row['action'] == 'extract' and row['status'] == 'completed' for row in rows)
    return ((units['information_unit'] if estimate else 0.0) + (units['handoff_unit'] if handoff else 0.0)
            + (units['information_unit'] if ended else 0.0) + (units['graded_unit'] if graded else 0.0))


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over every
    arguments it can take now; the bound does not depend on the arguments or on ctx, so all give the same number).

    The credit is four terms, each earned once in this commission: an estimate held (information unit; counted when a
    completed ``estimate`` unit row exists and the commission is not a resumed one), the job launched (handoff unit; a
    completed ``launch`` row, not resumed), the job known ended (information unit; only for ``until`` ``extracted``, not
    already known ended, from the first new status row that shows an ended state) and the graded result (graded unit;
    only for ``until`` ``extracted``, from this episode's own completed ``extract`` unit). An action's ceiling is the sum of the terms it
    can still newly earn: the term is read here exactly as ``credit`` reads it, so a term already earned is
    not counted again, and an action the episode's checks refuse in the held state earns nothing.

    * ``estimate``: the information unit when no estimate unit is counted yet (and not resumed), the state is not
      launched, finished or failed (``check_estimate`` refuses those) and the commission's alignment is a held
      alignment product. Otherwise 0. It cannot earn any other term.
    * ``launch``: the handoff unit when no launch unit is counted yet (and not resumed), an estimate is held (the gate)
      and the state is not launched, finished, extracted or failed, and the alignment requirement holds. A launch writes
      a handoff row, not a status row or a graded source, so it earns nothing else. Otherwise 0.
    * ``fix``: 0. It runs nothing and records no estimate, handoff, status row or graded source.
    * ``monitor``: the information unit for the job known ended when ``until`` is ``extracted``, the job is not already
      known ended by the parent, no new status row already shows an ended state, and the state is launched
      (``check_monitor``). One status request adds one status row; the graded result is not touched. Otherwise 0.
    * ``extract``: the graded unit when ``until`` is ``extracted``, no ``extract`` unit of this episode completed yet and the state
      is finished (``check_extract``). An extract adds no status row, so the ended term is not touched. Otherwise 0."""
    if action_type not in ACTION_TYPES:
        raise ValueError('unknown_action_type:' + repr(action_type))
    units, until, prior = summary['units'], summary['until'], summary['prior']
    state, facts = summary['state'], summary['state_facts']
    rows, new = summary['unit_rows'], not summary['resumed']
    if action_type == 'fix':
        return 0.0
    if action_type in ('estimate', 'launch'):
        commission = summary['commission']
        if requirement_problems(records, commission):
            return 0.0
        if action_type == 'estimate':
            earned = any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows)
            blocked = state in ('launched', 'finished', 'failed')
            return float(units['information_unit']) if new and not earned and not blocked else 0.0
        earned = any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows)
        blocked = facts['estimate'] is None or state in ('launched', 'finished', 'extracted', 'failed')
        return float(units['handoff_unit']) if new and not earned and not blocked else 0.0
    if until != 'extracted':
        return 0.0
    if action_type == 'monitor':
        ended = summary['known_ended'] or any(
            row['event'] == 'check' and row['id'] not in prior['check_refs'] and row['detail']['state'] in ENDED_JOB_STATES
            for row in job_rows(records))
        return float(units['information_unit']) if state == 'launched' and not ended else 0.0
    graded = any(row['action'] == 'extract' and row['status'] == 'completed' for row in rows)
    return float(units['graded_unit']) if state == 'finished' and not graded else 0.0
