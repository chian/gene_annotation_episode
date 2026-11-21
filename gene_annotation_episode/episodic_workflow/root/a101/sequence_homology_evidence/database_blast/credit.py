"""Credit, read from the records the episode holds, only for what is new since what the parent passed back: the
handoff established (``handoff_unit``), each status request that shows a fact of the search the earlier ones did not
(``information_unit``: ``job_progress.progress_information`` over the state and the availability of the results, with
the parent's check records as the baseline) and the graded result established (``graded_unit``). A repeat, a hold and a
failed unit earn nothing."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import progress_information
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    PROVIDER, STATUS_FIELDS, search_view)


def credit(summary, records):
    units, prior = summary['units'], summary['prior']
    search = search_view(records)
    handoff = search is not None and search['handoff']['id'] not in prior['handoff_refs']
    information = progress_information(records, set(prior['check_refs']), STATUS_FIELDS,
                                       units['information_unit'])['credit']
    graded = any(source['provider'] == PROVIDER and source['id'] not in prior['graded_refs']
                 for source in records.list('source'))
    return (units['handoff_unit'] if handoff else 0.0) + information + (units['graded_unit'] if graded else 0.0)


ACTIONS = ('submit', 'check', 'fetch_and_grade', 'hold')


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit (``arguments`` None: over every
    arguments that action type can take now). Credit is the handoff unit (once, for the one search), one information
    unit per newly informative check row, and the graded unit (once: a boolean over graded sources). Each action is
    bounded by the units it alone can newly earn, given the state of the search the summary shows (the same state the
    episode's checks read); an action those checks would refuse earns nothing.

    - ``submit``: the one handoff row it writes is a new handoff, so it can earn ``handoff_unit``; it writes no check
      row and no graded source. Allowed only in the state ``not_submitted`` (no search held, no unrepairable
      failure); otherwise refused: 0.
    - ``check``: one status request writes at most one check row, and a row earns one ``information_unit`` however many
      new facts it shows. Allowed only in the state ``outstanding``; otherwise refused: 0.
    - ``fetch_and_grade``: grades into one source; the graded term is a single unit whatever the number of sources, so
      at most ``graded_unit``. Allowed only in the state ``finished``; otherwise refused: 0.
    - ``hold``: runs nothing: 0.
    """
    units, state = summary['units'], summary['state']
    if action_type == 'submit':
        return float(units['handoff_unit']) if state == 'not_submitted' else 0.0
    if action_type == 'check':
        return float(units['information_unit']) if state == 'outstanding' else 0.0
    if action_type == 'fetch_and_grade':
        return float(units['graded_unit']) if state == 'finished' else 0.0
    if action_type == 'hold':
        return 0.0
    raise ValueError('database_blast has no action type ' + repr(action_type))
