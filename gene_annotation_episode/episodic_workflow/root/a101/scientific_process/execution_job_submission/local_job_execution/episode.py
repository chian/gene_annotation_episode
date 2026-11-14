"""Connect private A101 launch_local operational responsibilities."""
from __future__ import annotations
from .task import OperationalTask
from .execution_contracts import KINDS, ROLE_KINDS, plain
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import _blast_reference_source
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_axis_summaries import _blast_axis_summaries
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
from .yield_estimator import ExecutionEpisodeYield
from .configuration import OperationalConfiguration
from .binding_record import OperationalBindingRecord
from .goal import OperationalGoal
from .from_parent import OperationalAssignment
from .to_parent import OperationalReport
from .received_evidence import ReceivedOperationalEvidence
from .internal_summary import OperationalSummary
from .execution_state import OperationalExecutionState
from .native_input_custody import NativeInputCustody
from .execution_operations import OperationalOperations
from .result_acquisition import OperationalResultAcquisition
from .from_parent_launch import LaunchParentAssignment

class ExecutionEpisode(LaunchParentAssignment, OperationalConfiguration, OperationalBindingRecord, OperationalGoal, OperationalAssignment, OperationalReport, ReceivedOperationalEvidence, OperationalSummary, OperationalExecutionState, NativeInputCustody, OperationalOperations, OperationalResultAcquisition, ExecutionEpisodeCredit, ExecutionEpisodeYield):
    _blast_reference_source = staticmethod(_blast_reference_source)
    _blast_axis_summaries = staticmethod(_blast_axis_summaries)
    decision_source_type = OperationalTask
    _private_practical_estimator_owner = ('launch_local', ExecutionEpisodeYield.practical_estimator, ExecutionEpisodeYield._private_practical_estimator)
    binding_path = 'scientific_process/execution_job_submission/local_job_execution'
    commissioning_parent = 'scientific_process/execution_job_submission'
    roles = ('launch_local',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return ()

    def allowed_children(self, parent, caller_capabilities):
        self.credit_kind(parent.role)
        return ()

    def permitted_common_actions(self, context):
        self.credit_kind(context.role)
        return ('tool',)

    def context_hook_applies(self, context):
        """Own role hooks; the original Launch parent admits external delivery."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'launch_local' if role in ('launch', 'launch_local', 'launch_hpc', 'launch_api', 'results') else False
