"""Private job_monitor episode behavior for A103."""
from __future__ import annotations
from .to_parent import MonitorReport
from .from_parent import MonitorAssignment
from .execution_operations import MonitorOperations
from .native_event_observation import MonitorNativeEvents
from .credit_binding import MonitorCreditBinding
from .execution_planning import MonitorPlanning
from .internal_summary import MonitorSummary
from .goal import MonitorGoal
from .binding_record import MonitorBindingRecord
from .configuration import MonitorConfiguration
from .credit import HomologyEpisodeCredit
from .waiting import HomologyEpisodeWaiting

from importlib import import_module

class HomologyEpisode(MonitorConfiguration, MonitorBindingRecord, MonitorGoal, MonitorSummary, MonitorPlanning, MonitorCreditBinding, MonitorNativeEvents, MonitorOperations, MonitorAssignment, MonitorReport, HomologyEpisodeCredit, HomologyEpisodeWaiting):
    yield_controller = staticmethod(import_module(__package__ + '.yield_estimator').yield_controller)
    binding_path = 'legacy_improvement/homology_job_monitoring'
    commissioning_parent = 'legacy_improvement'
    entry_roles = ('job_monitor',)
    roles = ('job_monitor',)
from .task import HomologyMonitoringTask
from .decision_presentation import present_monitor_task
HomologyEpisode.decision_source_type = HomologyMonitoringTask
HomologyEpisode.decision_prompt_renderer = staticmethod(present_monitor_task)
