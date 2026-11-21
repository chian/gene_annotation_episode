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
    ENDED_SEARCH_STATES, PROVIDER)


def credit(summary, records):
    units, until, prior = summary['units'], summary['until'], summary['prior']
    rows = summary['unit_rows']
    new = not summary['resumed']
    estimate = new and any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows)
    handoff = new and any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows)
    extracted = until == 'extracted'
    ended = extracted and not summary['known_ended'] and any(
        row['event'] == 'check' and row['id'] not in prior['check_refs'] and row['detail']['state'] in ENDED_SEARCH_STATES
        for row in job_rows(records))
    graded = extracted and any(source['provider'] == PROVIDER for source in records.list('source'))
    return ((units['information_unit'] if estimate else 0.0) + (units['handoff_unit'] if handoff else 0.0)
            + (units['information_unit'] if ended else 0.0) + (units['graded_unit'] if graded else 0.0))
