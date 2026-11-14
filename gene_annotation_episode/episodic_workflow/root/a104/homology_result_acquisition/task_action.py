"""Private job_results original task task_action.py."""
from __future__ import annotations

from .action_admission import HomologyAcquisitionTaskActionAdmission

from .action_execution import HomologyAcquisitionTaskActionExecution

class HomologyAcquisitionTaskAction(HomologyAcquisitionTaskActionExecution, HomologyAcquisitionTaskActionAdmission):
    pass


from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__)
