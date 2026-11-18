"""Private A110 scientific assembly and original factories."""
from __future__ import annotations
from .scientific_assignment_contracts import ContractError, ROLE, ROLES
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.received_execution_information import received_execution_information as _received_execution_information
from .initial_information import initial_information as _private_initial_information
from .configuration import ScientificConfiguration
from .binding_record import ScientificBindingRecord
from .goal import ScientificGoal
from .child_commissioning import ScientificChildCommissioning
from .tool_selection import ScientificToolSelection
from .scientific_operations import ScientificScientificOperations
from .internal_summary import ScientificInternalSummary
from .from_parent import ScientificFromParent
from .saved_scientific_state import ScientificSavedScientificState
from .to_parent import ScientificToParent
from .report_integrity import ScientificReportIntegrity
from .received_evidence import ScientificReceivedEvidence
from .source_references import ScientificSourceReferences
from .credit import BiochemicalFeasibilityEvidenceCredit
from importlib import import_module as _import_module
from .yield_estimator import BiochemicalFeasibilityEvidenceYield
from .task import ScientificTask
from .presentation import present_scientific_context

class BiochemicalFeasibilityEvidenceEpisode(ScientificConfiguration, ScientificBindingRecord, ScientificGoal, ScientificChildCommissioning, ScientificToolSelection, ScientificScientificOperations, ScientificInternalSummary, ScientificFromParent, ScientificSavedScientificState, ScientificToParent, ScientificReportIntegrity, ScientificReceivedEvidence, ScientificSourceReferences, BiochemicalFeasibilityEvidenceCredit, BiochemicalFeasibilityEvidenceYield):
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""
    received_execution_information = staticmethod(_received_execution_information)
    initial_information = staticmethod(_private_initial_information)
    binding_path = 'biochemical_feasibility_evidence'
    commissioning_parent = 'legacy_annotation'
    roles = ROLES
    entry_roles = ROLES
    decision_source_type = ScientificTask
    decision_prompt_renderer = staticmethod(present_scientific_context)

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError('biochemical_feasibility_evidence_role_not_bound')

def create_execution_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_job_submission.episode import ExecutionEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_job_submission.local_job_execution.episode import ExecutionEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as Private2
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_result_acquisition.episode import ExecutionEpisode as Private3
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration), Private3(*args, **configuration))

def create_hpc_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.episode import HPCEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.hpc_resource_prediction.episode import HPCEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.hpc_allocation_execution.episode import HPCEpisode as Private2
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))
