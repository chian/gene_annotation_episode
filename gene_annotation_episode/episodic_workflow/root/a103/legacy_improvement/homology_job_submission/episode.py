"""Private job_launch episode behavior for A103."""
from __future__ import annotations
from .to_parent import SubmissionReport
from .from_parent import SubmissionAssignment
from .execution_operations import SubmissionOperations
from .native_event_observation import SubmissionNativeEvents
from .credit_binding import SubmissionCreditBinding
from .execution_planning import SubmissionPlanning
from .internal_summary import SubmissionSummary
from .goal import SubmissionGoal
from .binding_record import SubmissionBindingRecord
from .configuration import SubmissionConfiguration
from .credit import HomologyEpisodeCredit
from .waiting import HomologyEpisodeWaiting

from importlib import import_module

class HomologyEpisode(SubmissionConfiguration, SubmissionBindingRecord, SubmissionGoal, SubmissionSummary, SubmissionPlanning, SubmissionCreditBinding, SubmissionNativeEvents, SubmissionOperations, SubmissionAssignment, SubmissionReport, HomologyEpisodeCredit, HomologyEpisodeWaiting):
    yield_controller = staticmethod(import_module(__package__ + '.yield').yield_controller)
    binding_path = 'legacy_improvement/homology_job_submission'
    commissioning_parent = 'legacy_improvement'
    entry_roles = ('job_launch',)
    roles = ('job_launch',)
from .task import HomologySubmissionTask
from .decision_presentation import present_job_launch_task
HomologyEpisode.decision_source_type = HomologySubmissionTask
HomologyEpisode.decision_prompt_renderer = staticmethod(present_job_launch_task)
