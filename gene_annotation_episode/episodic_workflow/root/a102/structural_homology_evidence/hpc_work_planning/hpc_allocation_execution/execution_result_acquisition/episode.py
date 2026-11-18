"""Connect this predefined A102 Results task and its original custody/credit/yield responsibilities."""
from __future__ import annotations
from .execution_contracts import plain
from .configuration import ResultsConfiguration
from .action_policy import ResultsActionPolicy
from .binding_record import ResultsBindingRecord
from .child_commissioning import ResultsChildCommissioning
from .from_parent import ResultsFromParent
from .goal import ResultsGoal
from .internal_summary import ResultsInternalSummary
from .resource_information import ResultsResourceInformation
from .parent_input_custody import ResultsParentInputCustody
from .retained_protein_reader import ResultsRetainedProteinReader
from .saved_result_commission import ResultsSavedResultCommission
from .execution_state import ResultsExecutionState
from .acquisition_operations import ResultsAcquisitionOperations
from .result_selection import ResultsResultSelection
from .retained_result_acquisition import ResultsRetainedResultAcquisition
from .retained_result_publication import ResultsRetainedResultPublication
from .received_records import ResultsReceivedRecords
from .to_parent import ResultsToParent
from .credit import ResultsCredit
from .closed_credit import ResultsClosedCredit
from .completion import ResultsCompletion
from importlib import import_module as _import_module
from .yield_estimator import ExecutionEpisodeYield
from .task import ResultsTask
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence_prompt import render_selected_execution_prompt

class ExecutionEpisode(ResultsConfiguration, ResultsActionPolicy, ResultsBindingRecord, ResultsChildCommissioning, ResultsFromParent, ResultsGoal, ResultsInternalSummary, ResultsResourceInformation, ResultsParentInputCustody, ResultsRetainedProteinReader, ResultsSavedResultCommission, ResultsExecutionState, ResultsAcquisitionOperations, ResultsResultSelection, ResultsRetainedResultAcquisition, ResultsRetainedResultPublication, ResultsReceivedRecords, ResultsToParent, ResultsCredit, ResultsClosedCredit, ResultsCompletion, ExecutionEpisodeYield):
    decision_source_type = ResultsTask
    decision_prompt_renderer = staticmethod(render_selected_execution_prompt)
    binding_path = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
    commissioning_parent = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution'
    roles = ('results',)
    entry_roles = ()
    replaces_default_instructions = True

