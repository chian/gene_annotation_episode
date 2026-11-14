"""Predefined private HPC resource prediction for A104."""
from importlib import import_module
from .task import ResourcePredictionTask
from .presentation import present_task_context
from .configuration import PredictionConfiguration
from .from_parent import PredictionAssignment
from .to_parent import PredictionReport
from .goal import PredictionGoal
from .internal_summary import PredictionSummary
from .prediction_state import PredictionState
from .prediction_history import PredictionHistory
from .prediction_operations import PredictionOperations
from .portfolio_comparison import PortfolioComparison
from .received_evidence import ReceivedEvidence
from .closed_models import ClosedModels
from .credit import HPCEpisodeCredit
from .queue_observations import QueueObservations
from .binding_record import PredictionBindingRecord
HPCEpisodeYield = import_module(".yield", __package__).HPCEpisodeYield

class HPCEpisode(PredictionConfiguration, PredictionAssignment, PredictionReport, PredictionGoal, PredictionSummary, PredictionState, PredictionHistory, PredictionOperations, PortfolioComparison, ReceivedEvidence, ClosedModels, HPCEpisodeCredit, HPCEpisodeYield, QueueObservations, PredictionBindingRecord):
    binding_path = 'scientific_process/hpc_work_planning/hpc_resource_prediction'
    commissioning_parent = 'scientific_process/hpc_work_planning'
    roles = ('hpc_prediction',)
    decision_source_type = ResourcePredictionTask
    decision_prompt_renderer = staticmethod(present_task_context)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return self.child_roles(parent.role)

    def permitted_common_actions(self, context):
        return ('tool',)
