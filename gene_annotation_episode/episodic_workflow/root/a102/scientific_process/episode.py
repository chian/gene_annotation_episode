"""Connect the original own-A102 scientific process."""
from __future__ import annotations
from .scientific_contracts import ContractError, INSTRUCTION_VERSION, ROLE, ROLES, VERSION, _object, deepcopy
from .configuration import ScientificConfiguration
from .goal import ScientificGoal
from .child_commissioning import ScientificChildCommissioning
from .operations import ScientificOperations
from .internal_summary import ScientificInternalSummary
from .from_parent import ScientificFromParent
from .saved_scientific_state import ScientificSavedScientificState
from .to_parent import ScientificToParent
from .report_integrity import ScientificReportIntegrity
from .received_evidence import ScientificReceivedEvidence
from .source_references import ScientificSourceReferences
from .credit import ScientificProcessCredit
from importlib import import_module as _import_module
from .yield_estimator import ScientificProcessYield
from .to_child_published_evidence_assessment import assemble_request as assemble_published_evidence_assessment
from .from_child_published_evidence_assessment import select_report_receiver

class ScientificProcessEpisode(ScientificConfiguration, ScientificGoal, ScientificChildCommissioning, ScientificOperations, ScientificInternalSummary, ScientificFromParent, ScientificSavedScientificState, ScientificToParent, ScientificReportIntegrity, ScientificReceivedEvidence, ScientificSourceReferences, ScientificProcessCredit, ScientificProcessYield):
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""
    binding_path = 'scientific_process'
    commissioning_parent = 'legacy_annotation'
    roles = ROLES
    entry_roles = ROLES

    def __init__(self, services, *, library, tool_library, child_roles, tool_retrieval=None, contract_information_profile=None, yield_bindings=None):
        if not isinstance(child_roles, (tuple, list)) or not child_roles or any((not isinstance(role, str) or not role for role in child_roles)) or (len(set(child_roles)) != len(child_roles)) or (ROLE not in child_roles):
            raise ContractError('scientific_child_roles_invalid')
        self.services, self.library, self.tool_library = (services, library, tool_library)
        self._child_roles = tuple(child_roles)
        self._library_record = _object(library.as_record(), 'scientific_library_invalid')
        self._tools_record = _object(tool_library.as_record(), 'scientific_tool_library_invalid')
        axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'evidence_axis']
        self.replaces_default_instructions = bool(axes) and all((library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION for reference in axes))
        from gene_annotation_episode.episodic_workflow.root.a102.scientific_tool_retrieval import configuration
        self.tool_retrieval = configuration(tool_retrieval)
        from gene_annotation_episode.episodic_workflow.root.a102.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ContractError('unsupported_scientific_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self._yield_bindings = None if yield_bindings is None else _object(yield_bindings, 'scientific_yield_bindings_invalid')
        if self._yield_bindings is not None:
            if not isinstance(self._yield_bindings, dict):
                raise ContractError('scientific_yield_bindings_invalid')
            from gene_annotation_episode.episodic_workflow.root.a102.numerical import BoundedYieldController, CompletionYieldController, YieldController, YieldParameters
            for task, declaration in self._yield_bindings.items():
                if not isinstance(task, str) or ':' not in task or (not isinstance(declaration, dict)) or (set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}) or (declaration['kind'] not in {'accumulation', 'bounded_quality', 'completion'}) or (not isinstance(declaration['parameters'], dict)) or (set(declaration['parameters']) != {'uncertainty_alpha'}) or (not isinstance(declaration['credit_definition'], dict)) or (not declaration['credit_definition']):
                    raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
                try:
                    parameters = YieldParameters(**declaration['parameters'])
                    if declaration['kind'] == 'bounded_quality':
                        BoundedYieldController('configuration', 0, declaration['cutoff'], 1.0, parameters)
                    elif declaration['kind'] == 'completion':
                        CompletionYieldController('configuration', 0, declaration['cutoff'], parameters)
                    else:
                        YieldController('configuration', 0, declaration['cutoff'], parameters)
                except (TypeError, ValueError) as error:
                    raise ContractError('scientific_yield_task_binding_invalid:' + task) from error

    def as_record(self):
        return {'version': VERSION, 'binding_id': ROLE, 'configuration': {'library': deepcopy(self._library_record), 'tool_library': deepcopy(self._tools_record), 'child_roles': list(self._child_roles), **({'tool_retrieval': deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}), **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {}), **({'yield_bindings': deepcopy(self._yield_bindings)} if self._yield_bindings is not None else {})}}

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError('scientific_process_role_not_bound')

    def resource_information_catalog(self, registry):
        from .scientific_commission_catalog import resource_information_catalog
        return resource_information_catalog(self, registry)

    def child_request_assembler(self, role):
        if role == 'literature':
            return assemble_published_evidence_assessment
        return None
    published_evidence_report_receiver = staticmethod(select_report_receiver)

def create_execution_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.execution_job_submission.episode import ExecutionEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.execution_job_submission.api_job_execution.episode import ExecutionEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.execution_job_submission.local_job_execution.episode import ExecutionEpisode as Private2
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as Private3
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.execution_result_acquisition.episode import ExecutionEpisode as Private4
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration), Private3(*args, **configuration), Private4(*args, **configuration))

def create_hpc_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.episode import HPCEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.hpc_resource_prediction.episode import HPCEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.hpc_work_planning.hpc_allocation_execution.episode import HPCEpisode as Private2
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))

def create_resource_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.resource_work_submission.episode import ResourceEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Private2
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as Private3
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process.resource_result_acquisition.episode import ResourceEpisode as Private4
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration), Private3(*args, **configuration), Private4(*args, **configuration))
from .task import ScientificProcessTask
from .decision_presentation import present_scientific_decision
ScientificProcessEpisode.decision_source_type = ScientificProcessTask
ScientificProcessEpisode.decision_prompt_renderer = staticmethod(present_scientific_decision)
