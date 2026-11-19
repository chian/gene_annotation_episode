"""Credit: the old operational practical credit. The sum of the credits of the original requirements currently
satisfied, from the receipts of the actions so far over the frozen initial validations. It is unbounded, never
clamped and never rescaled; losing a satisfied requirement lowers it.

The receipts and the baseline are in the summary (the tool returned its receipt; the baseline is a pure function of
the assignment), so no service is read."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    view = project_practical_credit(summary['assignment'], summary['initial_validations'], summary['receipts'])
    return view['credit']
