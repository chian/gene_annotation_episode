"""Private job_launch original task task_action.py."""
from __future__ import annotations

from .action_admission import HomologySubmissionTaskActionAdmission

from .action_execution import HomologySubmissionTaskActionExecution

class HomologySubmissionTaskAction(HomologySubmissionTaskActionExecution, HomologySubmissionTaskActionAdmission):
    pass


from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__)
