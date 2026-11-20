"""Credit, read from what the episode holds, only for what is new: an estimate held (``information_unit``, once: the first
estimate; a revision or a repeat earns nothing), the handoff of each launch (``handoff_unit``), each status request that
shows a fact of its search the earlier ones did not (``information_unit``: ``job_progress.progress_information`` over the
state and the availability of the results) and the graded result (``graded_unit``). A repeat, a failed unit, a fix and a
rejected answer earn nothing."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import progress_information
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    PROVIDER, SOURCE_ACCESSION, STATUS_FIELDS)


def credit(summary, records):
    units = summary['units']
    estimated = summary['state_facts']['estimates_made'] > 0 or summary['state_facts']['launches'] > 0
    handoffs = sum(1 for row in summary['unit_rows'] if row['action'] == 'launch' and row['status'] == 'completed')
    information = progress_information(records, set(), STATUS_FIELDS, units['information_unit'])['credit']
    graded = any(source['provider'] == PROVIDER and source['accession'] == SOURCE_ACCESSION for source in records.list('source'))
    return ((units['information_unit'] if estimated else 0.0) + units['handoff_unit'] * handoffs + information
            + (units['graded_unit'] if graded else 0.0))
