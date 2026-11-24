"""Credit, bounded and read from what the episode holds: ``structure_search_child.bounded_credit`` (an estimate held, the job launched,
the job known ended and the graded result: each worth its unit once and counted only when new in this commission; there is no model
term: the child has no ``get_model``)."""
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ENDED_JOB_STATES, bounded_credit)


def credit(summary, records):
    return bounded_credit(summary, records, PROVIDER)


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over every arguments it can take
    now; the bound does not depend on the arguments, so a given ``arguments`` gets the same figure).

    The credit (``structure_search_child.bounded_credit``) is four terms, each earned once and only for what is new in this commission:
    an estimate held (information_unit), the job launched (handoff_unit), the job known ended (information_unit) and the graded result
    held (graded_unit; only when ``until`` is ``extracted``). A unit can add at most the terms it can still newly earn; each action's
    check refuses it outside one state, and a refused action has ceiling 0.

    * ``estimate``: the estimate term, once: information_unit, unless the commission resumes a job (nothing of it is new), an estimate
      was already completed (the term is held for good), or a job is launched, finished or failed (refused).
    * ``launch``: the handoff term, once: handoff_unit, only in state ``estimated`` (the gate: an estimate held, no job running,
      finished or extracted, no failure waiting), not resumed, and not when a launch already completed.
    * ``monitor``: the ended term: information_unit, only when ``until`` is ``extracted``, the state is ``launched`` (the only state the
      check accepts), the job was not already known ended and no status already showed it ended.
    * ``extract``: only in state ``finished`` with ``until`` ``extracted``: graded_unit unless a graded source of the provider is
      already held, plus information_unit for the ended term only when it could still be unearned (not known ended and no own status
      row showing the end; the extract's check requires a finished status, so this is normally 0).
    * ``fix``: 0. It records the model's choice and creates no record the credit reads.
    """
    if action_type not in ('estimate', 'launch', 'monitor', 'extract', 'fix'):
        raise ValueError('partner_cofolding_unknown_action_type:' + str(action_type))
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
        graded = any(source['provider'] == PROVIDER for source in records.list('source'))
        return (0.0 if graded else float(units['graded_unit'])) + (float(units['information_unit']) if ended_open else 0.0)
    return 0.0
