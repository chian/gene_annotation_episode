"""Private job_monitor original task task_action.py."""
from __future__ import annotations

from .action_admission import HomologyMonitoringTaskActionAdmission

from .action_execution import HomologyMonitoringTaskActionExecution

class HomologyMonitoringTaskAction(HomologyMonitoringTaskActionExecution, HomologyMonitoringTaskActionAdmission):
    pass


from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__)
