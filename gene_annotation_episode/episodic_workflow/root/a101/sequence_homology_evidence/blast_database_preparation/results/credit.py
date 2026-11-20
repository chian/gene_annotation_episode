"""Credit: ``prepared_unit`` for each distinct usable prepared record the Episode holds (``prepared_credit``), the
gain of establishing a usable product (D17). A product that is not usable, a repeat of a held key, a status check, a
wait and a read earn nothing. The rows are read through ``records``, so the credit is of records the Episode holds."""
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_credit)


def credit(summary, records):
    return prepared_credit(records, summary['prepared_unit'])
