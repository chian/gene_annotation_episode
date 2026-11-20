"""Credit: ``prepared_unit`` for each usable prepared-data record newly established: a usable record among the rows
the episode holds whose key is not the key of a record the parent passed. A failed or incomplete record, a hold and a
repeat earn nothing. It is read from the rows the episode holds (``records``), not from what a tool said."""
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_credit)


def credit(summary, records):
    return prepared_credit(records, summary['prepared_unit'], known_keys=summary['prior_data_keys'])
