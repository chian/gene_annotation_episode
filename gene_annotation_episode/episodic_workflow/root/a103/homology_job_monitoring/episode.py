"""Private job_monitor episode behavior for A103."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.to_parent import MonitorReport
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.from_parent import MonitorAssignment
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.execution_operations import MonitorOperations
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.native_event_observation import MonitorNativeEvents
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.credit_binding import MonitorCreditBinding
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.execution_planning import MonitorPlanning
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.internal_summary import MonitorSummary
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.goal import MonitorGoal
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.binding_record import MonitorBindingRecord
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.configuration import MonitorConfiguration
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.credit import HomologyEpisodeCredit
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.waiting import HomologyEpisodeWaiting

from importlib import import_module

class HomologyEpisode(MonitorConfiguration, MonitorBindingRecord, MonitorGoal, MonitorSummary, MonitorPlanning, MonitorCreditBinding, MonitorNativeEvents, MonitorOperations, MonitorAssignment, MonitorReport, HomologyEpisodeCredit, HomologyEpisodeWaiting):
    yield_controller = staticmethod(import_module(__package__ + '.yield').yield_controller)
    binding_path = 'legacy_annotation/homology_job_monitoring'
    commissioning_parent = 'legacy_annotation'
    entry_roles = ('job_monitor',)
    roles = ('job_monitor',)
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.task import HomologyMonitoringTask
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.decision_presentation import present_monitor_task
HomologyEpisode.decision_source_type = HomologyMonitoringTask
HomologyEpisode.decision_prompt_renderer = staticmethod(present_monitor_task)
