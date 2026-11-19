"""Credit: the practical requirement credit of the assignment, carried from the old ``credit.py``
(``credit_kind`` 'operational'; ``credit_view`` = ``TerminalExecutionBehavior.credit_view`` = the practical state's
credit view).

It is the library's ``project_practical_credit`` over the assignment, its initial validations and the saved
command receipts, all in the summary: the sum of the credits of the original requirement keys currently
satisfied. It is cumulative and signed: losing an established fact lowers it. Nothing here bounds, clamps or
rescales it. The old ``_closed_credit_*`` snapshot (the view frozen at closure and re-checked against the old
``runtime_forms``/``runtime_episodes``/``runtime_observations`` and receipt-inheritance tables) is old-runner
machinery; the system hands the credit the controller last saw to ``final_to_parent``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.practical_execution_credit import (
    project_practical_credit)


def credit(summary, records):
    return project_practical_credit(summary['assignment'], summary['initial_validations'],
                                    summary['receipts'])['credit']
