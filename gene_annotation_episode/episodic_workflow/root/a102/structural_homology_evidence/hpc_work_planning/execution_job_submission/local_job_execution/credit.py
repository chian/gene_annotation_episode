"""Credit: the old operational practical credit. The sum of the credits of the original requirements currently
satisfied, projected from the receipts of the commands run so far over the frozen initial validations. It is
unbounded, never clamped and never rescaled; losing a satisfied requirement lowers it.

The receipts and the baseline are in the summary (each command's tool outcome carries its receipt; the baseline is a
pure function of the assignment), so no service is read. The old closed-credit snapshot (credit frozen in the report
at close) is not carried: the system hands the Episode's credit to ``final_to_parent``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    view = project_practical_credit(summary['assignment'], summary['initial_validations'], summary['receipts'])
    return view['credit']
