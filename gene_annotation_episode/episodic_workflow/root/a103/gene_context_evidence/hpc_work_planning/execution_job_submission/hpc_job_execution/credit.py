"""Credit: the caller-valued practical progress of the commissioned job.

The credit is the sum of the credits of the original progress requirements that the actual commands' facts
currently satisfy (``project_practical_credit``): requirement keys count, never commands or files. It is cumulative
and signed (losing an established fact lowers it) and is never bounded, clamped or rescaled. A command that
earns nothing leaves it unchanged. The receipts it reads are in the summary: each command's tool returned its
receipt in its outcome (the tool qualified its facts against the original assignment)."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    view = project_practical_credit(summary['assignment'], summary['initial_validations'], summary['receipts'])
    return view['credit']
