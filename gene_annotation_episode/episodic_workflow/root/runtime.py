"""Root-owned runtime.py"""
from __future__ import annotations
from .task_selection import RootTaskSelection
from .workflow_setup import WorkflowSetup
from .child_commission import ChildCommission
from .child_delivery import ChildDelivery
from .contract_information import ContractInformation
from .child_selection import ChildSelection
from .wait_coordination import WaitCoordination
from .decision_information import DecisionInformation
from .outcome_receipts import OutcomeReceipts
from .credit_projection import CreditProjection
from .report_validation import ReportValidation
from .continuation_observation import ContinuationObservation
from .action_catalog import ActionCatalog
from .action_history import ActionHistory
from .action_execution import ActionExecution
from .report_redelivery import ReportRedelivery
from .episode_construction import EpisodeConstruction

class Workflow(WorkflowSetup, ChildCommission, ChildDelivery, ContractInformation, ChildSelection, WaitCoordination, DecisionInformation, OutcomeReceipts, CreditProjection, ReportValidation, ContinuationObservation, ActionCatalog, ActionHistory, ActionExecution, ReportRedelivery, EpisodeConstruction, RootTaskSelection):
    grain_names = ('annotation', 'improvement')
