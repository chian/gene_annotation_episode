"""Private job_results episode behavior for A103."""
from __future__ import annotations
from .to_parent import AcquisitionReport
from .from_parent import AcquisitionAssignment
from .execution_operations import AcquisitionOperations
from .native_event_observation import AcquisitionNativeEvents
from .credit_binding import AcquisitionCreditBinding
from .execution_planning import AcquisitionPlanning
from .internal_summary import AcquisitionSummary
from .goal import AcquisitionGoal
from .binding_record import AcquisitionBindingRecord
from .configuration import AcquisitionConfiguration
from .credit import HomologyEpisodeCredit
from .waiting import HomologyEpisodeWaiting

from importlib import import_module

class HomologyEpisode(AcquisitionConfiguration, AcquisitionBindingRecord, AcquisitionGoal, AcquisitionSummary, AcquisitionPlanning, AcquisitionCreditBinding, AcquisitionNativeEvents, AcquisitionOperations, AcquisitionAssignment, AcquisitionReport, HomologyEpisodeCredit, HomologyEpisodeWaiting):
    yield_controller = staticmethod(import_module(__package__ + '.yield').yield_controller)
    binding_path = 'legacy_improvement/homology_result_acquisition'
    commissioning_parent = 'legacy_improvement'
    entry_roles = ('job_results',)
    roles = ('job_results',)
from .task import HomologyAcquisitionTask
from .decision_presentation import present_job_results_task
HomologyEpisode.decision_source_type = HomologyAcquisitionTask
HomologyEpisode.decision_prompt_renderer = staticmethod(present_job_results_task)
