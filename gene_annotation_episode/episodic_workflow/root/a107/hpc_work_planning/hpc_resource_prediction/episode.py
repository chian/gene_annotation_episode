"""Predefined private HPC resource prediction for A107."""
from gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.hpc_resource_prediction.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.hpc_resource_prediction.received_api_reports import received_api_reports as _received_api_reports
from .initial_information import initial_information as _private_initial_information
from importlib import import_module
from .task import ResourcePredictionTask
from gene_annotation_episode.episodic_workflow.root.a107.library.hpc_prompt import render_hpc_prompt
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
    received_execution_information = staticmethod(_received_execution_information)
    received_api_reports = staticmethod(_received_api_reports)
    initial_information = staticmethod(_private_initial_information)
    binding_path = 'hpc_work_planning/hpc_resource_prediction'
    commissioning_parent = 'hpc_work_planning'
    roles = ('hpc_prediction',)
    decision_source_type = ResourcePredictionTask
    decision_prompt_renderer = staticmethod(render_hpc_prompt)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return self.child_roles(parent.role)

    def permitted_common_actions(self, context):
        return ('tool',)
