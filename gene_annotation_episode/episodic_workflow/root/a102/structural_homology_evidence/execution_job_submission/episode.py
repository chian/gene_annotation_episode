"""Connect the predefined A102 Launch job to its own task and message responsibilities."""
from __future__ import annotations
from .execution_contracts import plain
from .configuration import LaunchConfiguration
from .binding_record import LaunchBindingRecord
from .to_children import LaunchToChildren
from .from_parent import LaunchFromParent
from .goal import LaunchGoal
from .internal_summary import LaunchInternalSummary
from .resource_information import LaunchResourceInformation
from .parent_input_custody import LaunchParentInputCustody
from .retained_protein_reader import LaunchRetainedProteinReader
from .execution_state import LaunchExecutionState
from .api_operations import LaunchApiOperations
from .result_selection import LaunchResultSelection
from .retained_result_acquisition import LaunchRetainedResultAcquisition
from .retained_result_publication import LaunchRetainedResultPublication
from .received_records import LaunchReceivedRecords
from .to_parent import LaunchToParent
from .credit import LaunchCredit
from .closed_credit import LaunchClosedCredit
from .completion import LaunchCompletion
from importlib import import_module as _import_module
from .yield_estimator import ExecutionEpisodeYield
from .task import LaunchTask
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence_prompt import render_selected_execution_prompt

from .action_policy import LaunchActionPolicy

class ExecutionEpisode(LaunchActionPolicy, LaunchConfiguration, LaunchBindingRecord, LaunchToChildren, LaunchFromParent, LaunchGoal, LaunchInternalSummary, LaunchResourceInformation, LaunchParentInputCustody, LaunchRetainedProteinReader, LaunchExecutionState, LaunchApiOperations, LaunchResultSelection, LaunchRetainedResultAcquisition, LaunchRetainedResultPublication, LaunchReceivedRecords, LaunchToParent, LaunchCredit, LaunchClosedCredit, LaunchCompletion, ExecutionEpisodeYield):
    decision_source_type = LaunchTask
    decision_prompt_renderer = staticmethod(render_selected_execution_prompt)
    binding_path = 'structural_homology_evidence/execution_job_submission'
    commissioning_parent = 'structural_homology_evidence'
    roles = ('launch',)
    entry_roles = ('launch',)
    replaces_default_instructions = True

