"""Credit, bounded and read from what the episode holds: the terms of ``bvbrc_job_child.bounded_credit`` (an estimate held, the
job launched, the job known ended, the graded alignment: each worth its unit once and counted only when new in this
commission), with the graded alignment counted from this episode's own completed ``extract`` unit: a graded alignment the
parent passed is not its result."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    ENDED_JOB_STATES)


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
    arguments it can take now; the bound does not depend on the arguments, so a given ``arguments`` gets the same figure).

    The credit is four terms, each earned once and only for what is new in this
    commission: an estimate held (information_unit), the job launched (handoff_unit), the job known ended (information_unit)
    and the graded alignment held (graded_unit; only when ``until`` is ``extracted``). A unit can add at most the terms it
    can still newly earn; each action's checks (``bvbrc_job_child.check_*``) refuse it outside one state, and a refused action
    has ceiling 0.

    * ``estimate``: the estimate term, once: information_unit, unless the commission resumes a job (nothing of it is new),
      an estimate was already completed (the term is held for good), or a job is launched, finished or failed (refused).
    * ``launch``: the handoff term, once: handoff_unit, only in state ``estimated`` (the gate: an estimate held, no job
      running, finished or extracted, no failure waiting), not resumed, and not when a launch already completed.
    * ``monitor``: the ended term: information_unit, only when ``until`` is ``extracted``, the state is ``launched`` (the
      only state the check accepts), the job was not already known ended and no status already showed it ended.
    * ``extract``: only in state ``finished`` with ``until`` ``extracted``: graded_unit unless an ``extract`` unit of this
      episode already completed, plus information_unit for the ended term only when it could still be unearned (not known ended
      and no own status row showing the end; the extract's check requires a finished status, so this is normally 0).
    * ``fix``: 0. It records the model's choice and creates no record the credit reads.
    """
    if action_type not in ('estimate', 'launch', 'monitor', 'extract', 'fix'):
        raise ValueError('bvbrc_msa_unknown_action_type:' + str(action_type))
    units, rows, state = summary['units'], summary['unit_rows'], summary['state']
    extracted = summary['until'] == 'extracted'
    own_ended = any(row['action'] == 'monitor' and row['status'] == 'completed' and row.get('state') in ENDED_JOB_STATES
                    for row in rows)
    ended_open = extracted and not summary['known_ended'] and not own_ended
    if action_type == 'estimate':
        counted = any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows)
        if summary['resumed'] or counted or state in ('launched', 'finished', 'failed'):
            return 0.0
        return float(units['information_unit'])
    if action_type == 'launch':
        counted = any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows)
        if summary['resumed'] or counted or state != 'estimated':
            return 0.0
        return float(units['handoff_unit'])
    if action_type == 'monitor':
        return float(units['information_unit']) if state == 'launched' and ended_open else 0.0
    if action_type == 'extract':
        if state != 'finished' or not extracted:
            return 0.0
        graded = any(row['action'] == 'extract' and row['status'] == 'completed' for row in rows)
        return (0.0 if graded else float(units['graded_unit'])) + (float(units['information_unit']) if ended_open else 0.0)
    return 0.0
