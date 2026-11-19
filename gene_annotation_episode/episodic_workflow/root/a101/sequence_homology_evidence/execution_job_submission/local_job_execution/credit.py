"""Credit: the old operational practical credit of ``launch_local`` (``PracticalState.credit_view``). The sum of the
credits of the original requirements currently satisfied, from the receipts of the actions so far over the frozen
initial validations. It is unbounded, never clamped and never rescaled; losing a satisfied requirement lowers it.

The receipts and the baseline are in the summary (the tool returned its receipt; the baseline is a pure function of
the assignment), so no service is read. The old native result families (BLAST masking, utility, databases, HMMER,
BLAST pairwise) projected their own credit views only for an episode that acquires results (role ``results``); this
launch role's credit view was always the practical one."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    view = project_practical_credit(summary['assignment'], summary['initial_validations'], summary['receipts'])
    return view['credit']
