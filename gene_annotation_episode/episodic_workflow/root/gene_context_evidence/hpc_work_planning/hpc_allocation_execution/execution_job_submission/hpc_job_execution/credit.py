"""Credit: the sum of the credits of the original requirements the commands currently satisfy.

The count is of requirement keys, never of commands or files. It is cumulative: losing a fact that was established
gives the ordinary signed loss. It is never bounded or rescaled."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    return project_practical_credit(summary['assignment'], summary['baseline'], summary['receipts'])['credit']
