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
