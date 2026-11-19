"""Credit: the practical requirement credit of this assignment. It is the sum of the caller-valued requirement
keys that the saved, validated command receipts currently satisfy (the old operational credit view of the
practical state), signed and never bounded, clamped or rescaled. A failed command or one that makes no progress
earns what the receipts then satisfy, which may be nothing."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    return project_practical_credit(summary['assignment'], summary['initial_validations'],
                                    summary['receipts'])['credit']
