"""Credit, bounded and read from what the episode holds: the shared ``bvbrc_job_child.bounded_credit`` (an estimate held, the
job launched, the job known ended, the graded alignment: each worth its unit once and counted only when new in this
commission)."""
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    bounded_credit)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    PROVIDER)


def credit(summary, records):
    return bounded_credit(summary, records, PROVIDER)
