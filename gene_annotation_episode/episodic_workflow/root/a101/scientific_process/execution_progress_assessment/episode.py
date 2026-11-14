"""Connect the predefined A101 progress-monitoring task, reports, credit and continuation."""
from __future__ import annotations
from .configuration import MonitorConfiguration
from .from_parent import MonitorAssignment
from .to_parent import MonitorReport
from .internal_summary import MonitorSummary
from .received_progress import ReceivedProgress
from .received_progress import OwnProgress
from .progress_operations import ProgressOperations
from .goal import MonitorGoal
from .binding_record import MonitorBindingRecord
from .credit import MonitorEpisodeCredit
from importlib import import_module
MonitorEpisodeYield = import_module('.yield', __package__).MonitorEpisodeYield
from .task import ProgressMonitoringTask
from gene_annotation_episode.episodic_workflow.root.a101.library.monitor_prompt import render_monitor_prompt
from .target_identity import is_blast_job
from .to_child_execution_progress_assessment import prepare_dependency_request
from .from_child_execution_progress_assessment import receive_progress
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from ..to_child_execution_progress_assessment import required_return_sources as scientific_parent_return_sources

class MonitorEpisode(MonitorConfiguration, MonitorAssignment, MonitorReport, MonitorSummary, ReceivedProgress, OwnProgress, ProgressOperations, MonitorGoal, MonitorBindingRecord, MonitorEpisodeCredit, MonitorEpisodeYield):
    binding_path = 'scientific_process/execution_progress_assessment'
    commissioning_parent = 'scientific_process'
    roles = ('monitor',)
    entry_roles = ('monitor',)
    decision_source_type = ProgressMonitoringTask
    decision_prompt_renderer = staticmethod(render_monitor_prompt)

    def prepare_child_request(self, parent, role, assignment):
        self._role(role)
        return prepare_dependency_request(self, parent, plain(assignment))

    def receive_child_progress(self, context, form, schema, operation_key, provider):
        return receive_progress(context, form, schema, operation_key, provider)

    def child_roles(self, role):
        self._role(role)
        return ('monitor',)

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and parent.path[-1][0] == 'scientific_process':
            return scientific_parent_return_sources(self.services)
        return ()

    def permitted_common_actions(self, context):
        self._role(context.role)
        if self.private_yield_binding and is_blast_job(self.services, context):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'child', 'wait', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        assignment = self._assignment(parent.assignment, parent.scope)
        return ('monitor',) if self.services.dependencies(assignment['target_handle'], parent.scope) else ()
