"""Credit, bounded and read from what the episode holds: four things, each worth its unit once, counted only when new in this
commission (not among the records the parent passed back): an estimate held (``information_unit``), the search launched
(``handoff_unit``: once, however many launches a fix needed), the search known ended (``information_unit``: the first status
record that shows it finished, failed or lost; a status that shows queued or running earns nothing) and the graded result
(``graded_unit``). Each term is counted exactly where ``read_from_parent`` put its unit into the commission's target, so the
credit never exceeds the target, whatever the path (a failed launch, a fix and a second launch earn the estimate and the
handoff once): the estimate and the handoff only when no handoff was passed back, the ended search and the graded result
only for ``until`` ``extracted`` (the first only when the search was not already known ended). A repeat, a fix, a failed unit
and a rejected answer earn nothing."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    ENDED_SEARCH_STATES)


def _earned(summary, records):
    """Which of the four terms the held records and units already earn: ``estimate``, ``handoff``, ``ended``, ``graded``."""
    until, prior = summary['until'], summary['prior']
    rows = summary['unit_rows']
    new = not summary['resumed']
    extracted = until == 'extracted'
    return {
        'estimate': new and any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows),
        'handoff': new and any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows),
        'ended': extracted and not summary['known_ended'] and any(
            row['event'] == 'check' and row['id'] not in prior['check_refs'] and row['detail']['state'] in ENDED_SEARCH_STATES
            for row in job_rows(records)),
        'graded': extracted and any(row['action'] == 'extract' and row['status'] == 'completed' for row in rows)}


def credit(summary, records):
    units, earned = summary['units'], _earned(summary, records)
    return ((units['information_unit'] if earned['estimate'] else 0.0) + (units['handoff_unit'] if earned['handoff'] else 0.0)
            + (units['information_unit'] if earned['ended'] else 0.0) + (units['graded_unit'] if earned['graded'] else 0.0))


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken next (the same bound for every ``arguments``, and for
    ``None``). The credit is four terms, each worth its unit once; an action's ceiling is the sum of the terms it can still
    newly earn, from what is held now. A term not yet earned is available only where ``read_from_parent`` put it into the
    commission's target (the estimate and the handoff only when no handoff was passed back; the ended search and the graded
    result only for ``until`` ``extracted``, the ended search only when not already known ended).

    * ``estimate``: the estimate term (``information_unit``) if it is not yet earned and no handoff was passed back; 0 when
      the check would refuse it (state launched, finished or failed) or the term is earned. It earns nothing else.
    * ``launch``: the handoff term (``handoff_unit``, once however many launches) if not yet earned and no handoff was
      passed back; 0 unless the state is ``estimated`` (an estimate is held, no search running, finished, extracted or
      waiting for a fix), which is all the check lets through.
    * ``fix``: 0. It runs nothing and no term reads it.
    * ``monitor``: the ended term (``information_unit``) if not yet earned, ``until`` is ``extracted`` and the search is not
      already known ended; 0 unless the state is ``launched`` (the check refuses a monitor otherwise). A status that shows
      queued or running earns nothing, so this is the most.
    * ``extract``: the graded term (``graded_unit``) if not yet earned and ``until`` is ``extracted``, plus, because the
      unit also reads the search, the ended term if that is still unearned; 0 unless the state is ``finished``.

    A held-state gate never raises the bound: the terms still unearned are an upper bound whatever the check does."""
    units, earned, state = summary['units'], _earned(summary, records), summary['state']
    extracted = summary['until'] == 'extracted'
    available = {
        'estimate': not earned['estimate'] and not summary['resumed'],
        'handoff': not earned['handoff'] and not summary['resumed'],
        'ended': not earned['ended'] and extracted and not summary['known_ended'],
        'graded': not earned['graded'] and extracted}
    value = {'estimate': units['information_unit'], 'handoff': units['handoff_unit'], 'ended': units['information_unit'],
             'graded': units['graded_unit']}
    if action_type == 'estimate':
        terms = ('estimate',) if state in ('no_estimate', 'estimated', 'extracted') else ()
    elif action_type == 'launch':
        terms = ('handoff',) if state == 'estimated' else ()
    elif action_type == 'fix':
        terms = ()
    elif action_type == 'monitor':
        terms = ('ended',) if state == 'launched' else ()
    elif action_type == 'extract':
        terms = ('graded', 'ended') if state == 'finished' else ()
    else:
        raise ValueError('bvbrc_blast_has_no_action_' + str(action_type))
    return float(sum(value[term] for term in terms if available[term]))
