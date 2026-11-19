"""Credit: the practical requirement credit of the job (the old ``ExecutionEpisodeCredit`` kind ``operational``).

The sum of the credits of the original requirement keys that the actual command receipts currently satisfy,
counted from the baseline validations of the initial context. It is the old ``PracticalState.credit_view()``
(``project_practical_credit``) over what the summary holds: the receipts the command tool returned. Nothing bounds
or rescales it; a fact lost again lowers it."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    view = project_practical_credit(summary['assignment'], summary['initial_validations'], summary['receipts'])
    return view['credit']
