"""Credit: the old operational practical credit. The sum of the credits of the original requirements currently
satisfied, from the receipts of the commands so far over the frozen initial validations (old
``ExecutionEpisodeCredit._live_project_credit`` through ``TerminalCredit.credit_view``, the practical state's
``credit_view``). It is unbounded, never clamped and never rescaled; losing a satisfied requirement lowers it.

The receipts and the baseline are in the summary (the tool returned its receipt, the baseline is a pure function of
the assignment), so no service is read. The old ``closed_credit`` view (a credit frozen from receipts of an earlier
closed run) was recorded-run machinery and is not carried."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    return project_practical_credit(summary['assignment'], summary['initial_validations'],
                                    summary['receipts'])['credit']
