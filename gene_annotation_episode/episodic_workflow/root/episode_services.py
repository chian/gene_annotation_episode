"""Ports from a specialist binding to the existing application services.

This adapter owns no decisions, execution loop, credit formula or work policy.
It keeps bindings independent of Workflow/DecisionSource implementation types.
"""
from __future__ import annotations
import inspect
import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from .communication import plain
from .receiving_context import BindingContext
from .episode_bindings import native_observation_options

from .workflow_tool_services import WorkflowToolServices
from .workflow_reference_access import WorkflowReferenceAccess
from .workflow_credit_services import WorkflowCreditServices
from .workflow_progress_services import WorkflowProgressServices
from .workflow_scientific_provenance import WorkflowScientificProvenance
from .workflow_molecular_operands import WorkflowMolecularOperands
from .workflow_protein_structure import WorkflowProteinStructure
from .workflow_result_receipts import WorkflowResultReceipts
from .workflow_record_access import WorkflowRecordAccess
from .workflow_alignment_results import WorkflowAlignmentResults

class WorkflowServices(WorkflowToolServices, WorkflowReferenceAccess, WorkflowCreditServices, WorkflowProgressServices, WorkflowScientificProvenance, WorkflowMolecularOperands, WorkflowProteinStructure, WorkflowResultReceipts, WorkflowRecordAccess, WorkflowAlignmentResults):

    def __init__(self, workflow):
        self.workflow = workflow

    def supplied_context_preview(self, context, *, limit=12000):
        """Present received caller input before a parent defines a child question.

        This is original task input, not acquired evidence or a generated
        interpretation. A partial preview retains a source handle for reading.
        """
        store = self.workflow.store
        reference = store.problem().get('caller_context_source_ref')
        if reference is None or reference not in context.received_record_refs or (not self.reference_in_scope(reference, context.scope, 'source')):
            return []
        source = store.get(reference)
        body = store.get_artifact(source['artifact_ref'])
        preview = body[:limit].decode('utf-8', errors='ignore')
        return [{'source_ref': reference, 'origin': 'caller', 'representation': 'original', 'content_preview': preview, 'utf8_bytes': len(body), 'complete': len(preview.encode('utf-8')) == len(body)}]

    def literature_rate_repository(self):
        """Expose the selected source-sheet adapter; own no decisions or credit."""
        from .literature_rate_storage import LiteratureRateRepository
        if not hasattr(self, '_literature_rate_repository'):
            self._literature_rate_repository = LiteratureRateRepository(self.workflow.store, self.workflow.run_id)
        else:
            self._literature_rate_repository._ensure_storage()
        return self._literature_rate_repository

    def literature_rate_observation_repository(self):
        """Access selected original XLSX entries and saved requested subsets."""
        from .literature_rate_observation_storage import LiteratureRateObservationRepository
        if not hasattr(self, '_literature_rate_observation_repository'):
            self._literature_rate_observation_repository = LiteratureRateObservationRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_rate_observation_repository

    def literature_calibration_recovery_repository(self):
        """Access selected recovery controls and exact saved numerical subsets."""
        from .literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
        if not hasattr(self, '_literature_calibration_recovery_repository'):
            self._literature_calibration_recovery_repository = LiteratureCalibrationRecoveryRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_calibration_recovery_repository

    def literature_rate_replicate_repository(self):
        """Access explicitly selected raw-rate tables and saved typed subsets."""
        from .literature_rate_replicate_storage import LiteratureRateReplicateRepository
        if not hasattr(self, '_literature_rate_replicate_repository'):
            self._literature_rate_replicate_repository = LiteratureRateReplicateRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_rate_replicate_repository

    def literature_quantity_repository(self):
        """Access committed source-native quantities without owning episode work."""
        from .literature_quantity_storage import LiteratureQuantityRepository
        if not hasattr(self, '_literature_quantity_repository'):
            self._literature_quantity_repository = LiteratureQuantityRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_quantity_repository

    def literature_assay_repository(self):
        """Access source-bound numerical assay calculations; own no decisions."""
        from .literature_assay_storage import LiteratureAssayRepository
        if not hasattr(self, '_literature_assay_repository'):
            self._literature_assay_repository = LiteratureAssayRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_assay_repository

    def literature_amount_repository(self):
        """Access selected source amount components without choosing work."""
        from .literature_amount_storage import LiteratureAmountRepository
        if not hasattr(self, '_literature_amount_repository'):
            self._literature_amount_repository = LiteratureAmountRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_amount_repository

    def literature_optical_repository(self):
        """Access selected optical q/Vq inputs without choosing scientific work."""
        from .literature_optical_storage import LiteratureOpticalRepository
        if not hasattr(self, '_literature_optical_repository'):
            self._literature_optical_repository = LiteratureOpticalRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_optical_repository

    def literature_kinetic_repository(self):
        """Access selected native kinetic parameter components, without choosing work."""
        from .literature_kinetic_storage import LiteratureKineticRepository
        if not hasattr(self, '_literature_kinetic_repository'):
            self._literature_kinetic_repository = LiteratureKineticRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_kinetic_repository

    def literature_ratio_repository(self):
        """Access retained relative-signal components without choosing work."""
        from .literature_ratio_storage import LiteratureRatioRepository
        if not hasattr(self, '_literature_ratio_repository'):
            self._literature_ratio_repository = LiteratureRatioRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_ratio_repository

    def literature_ratio_source_repository(self, *, evidence_origin='reported_source'):
        """Access selected native source-signal cells with the caller's bound origin."""
        from .literature_ratio_source_storage import LiteratureRatioSourceRepository
        if not hasattr(self, '_literature_ratio_source_repositories'):
            self._literature_ratio_source_repositories = {}
        if evidence_origin not in self._literature_ratio_source_repositories:
            repository = LiteratureRatioSourceRepository(self.workflow.store, self.workflow.run_id, evidence_origin=evidence_origin)
            self._literature_ratio_source_repositories[evidence_origin] = repository
        return self._literature_ratio_source_repositories[evidence_origin]

    def literature_binding_interaction_repository(self):
        """Access selected four-cell source binding interaction components."""
        from .literature_binding_interaction_storage import LiteratureBindingInteractionRepository
        if not hasattr(self, '_literature_binding_interaction_repository'):
            self._literature_binding_interaction_repository = LiteratureBindingInteractionRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_binding_interaction_repository

    def literature_controlled_response_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound controlled-response repository; choose no work."""
        from .literature_controlled_response_storage import LiteratureControlledResponseRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_controlled_response_repositories'):
            self._literature_controlled_response_repositories = {}
        if key not in self._literature_controlled_response_repositories:
            self._literature_controlled_response_repositories[key] = LiteratureControlledResponseRepository(self.workflow.store, self.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_controlled_response_repositories[key]

    def literature_gel_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound gel repository; choose no work."""
        from .literature_gel_storage import LiteratureGelRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_gel_repositories'):
            self._literature_gel_repositories = {}
        if key not in self._literature_gel_repositories:
            self._literature_gel_repositories[key] = LiteratureGelRepository(self.workflow.store, self.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_gel_repositories[key]

    def literature_binding_repository(self):
        """Access saved source binding parameters without choosing work."""
        from .literature_binding_storage import LiteratureBindingRepository
        if not hasattr(self, '_literature_binding_repository'):
            self._literature_binding_repository = LiteratureBindingRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_binding_repository

    def literature_binding_model_repository(self):
        """Read and populate explicitly selected conditional binding models."""
        from .literature_binding_model_storage import LiteratureBindingModelRepository
        if not hasattr(self, '_literature_binding_model_repository'):
            self._literature_binding_model_repository = LiteratureBindingModelRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_binding_model_repository

    def literature_transport_repository(self):
        """Access explicitly selected source kinetic-response calculations."""
        from .literature_transport_storage import LiteratureTransportRepository
        if not hasattr(self, '_literature_transport_repository'):
            self._literature_transport_repository = LiteratureTransportRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_transport_repository

    def literature_perturbation_repository(self):
        """Access selected source perturbation/restoration components."""
        from .literature_perturbation_storage import LiteraturePerturbationRepository
        if not hasattr(self, '_literature_perturbation_repository'):
            self._literature_perturbation_repository = LiteraturePerturbationRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_perturbation_repository

    def literature_structure_repository(self):
        """Access selected source-model geometry and local-fit components."""
        from .literature_structure_storage import LiteratureStructureRepository
        if not hasattr(self, '_literature_structure_repository'):
            self._literature_structure_repository = LiteratureStructureRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_structure_repository

    def literature_reaction_repository(self):
        """Access selected reported-reaction constraints and resource budgets."""
        from .literature_reaction_storage import LiteratureReactionRepository
        if not hasattr(self, '_literature_reaction_repository'):
            self._literature_reaction_repository = LiteratureReactionRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_reaction_repository

    def literature_figure_repository(self):
        """Access selected native experimental figure measurements."""
        from .literature_figure_storage import LiteratureFigureRepository
        if not hasattr(self, '_literature_figure_repository'):
            self._literature_figure_repository = LiteratureFigureRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_figure_repository

    def literature_partner_repository(self):
        """Access selected condition-qualified experimental partner components."""
        from .literature_partner_storage import LiteraturePartnerRepository
        if not hasattr(self, '_literature_partner_repository'):
            self._literature_partner_repository = LiteraturePartnerRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_partner_repository

    def itc_parameter_own_facts(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('itc_parameter_receiver_identity_mismatch')
        return self.molecular_own_facts(context, fact_source='itc_binding_parameters')

    def itc_parameter_frozen_facts(self, context):
        return self.molecular_frozen_facts(context, fact_source='itc_binding_parameters')

    def itc_parameter_received_facts(self, context):
        return self.molecular_received_facts(context, fact_source='itc_binding_parameters')

    def molecular_own_facts(self, context, *, fact_source):
        from .molecular_result_facts import own_molecular_facts
        if context.run_id != self.workflow.run_id:
            raise ValueError('molecular_facts_receiver_identity_mismatch')
        return own_molecular_facts(self.workflow.tools, context, read_received=self.read_received_molecular_input, fact_source=fact_source)

    def molecular_frozen_facts(self, context, *, fact_source):
        from .molecular_result_facts import frozen_molecular_facts
        return frozen_molecular_facts(self.workflow.store, self.workflow.run_id, context, fact_source=fact_source)

    def molecular_received_facts(self, context, *, fact_source):
        from .molecular_result_facts import received_molecular_facts
        return received_molecular_facts(self.workflow.store, self.workflow.run_id, context, fact_source=fact_source)

    def protein_structure_action_own_facts(self, context, *, fact_source):
        return self.protein_structure_input_authority().own_facts(context, fact_source=fact_source)

    def protein_structure_action_frozen_facts(self, context, *, fact_source):
        from .protein_structure_action_records import frozen_protein_structure_action_facts
        return frozen_protein_structure_action_facts(self.workflow.store, self.workflow.run_id, context, fact_source=fact_source)

    def protein_structure_action_received_facts(self, context, *, fact_source):
        return self.protein_structure_input_authority().received_facts(context, fact_source=fact_source)

    def scientific_saved_request(self, context: BindingContext, *, active_only=True) -> dict | None:
        """Read an existing request; yielded requests can finish their first form."""
        if type(active_only) is not bool:
            raise ValueError('scientific_saved_request_active_flag_invalid')
        workflow = self.workflow
        journal = workflow.journal
        if context.run_id != workflow.run_id or journal.run_id != workflow.run_id or context.role != 'scientific_process' or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_saved_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if row['run_id'] != context.run_id or row['episode_id'] != context.episode_id or json.loads(row['path']) != plain(context.path):
            raise ValueError('scientific_saved_request_identity_mismatch')
        if row['state'] == 'active':
            if row['completion'] is not None or row['archive'] is not None:
                return None
        elif not active_only and row['state'] == 'yielded':
            if row['completion'] is None or row['archive'] is None:
                return None
            completion, archive = (json.loads(value) for value in (row['completion'], row['archive']))
            if not isinstance(completion, dict) or not completion or (not isinstance(archive, dict)) or (not archive):
                raise ValueError('scientific_saved_request_invalid')
        else:
            return None
        request = json.loads(row['request'])
        if not isinstance(request, dict):
            raise ValueError('scientific_saved_request_invalid')
        return request

    def _restriction_mapping_records(self):
        from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_action_records import RestrictionMappingActionRecords
        return RestrictionMappingActionRecords(self.workflow.store, self.workflow.run_id)

    def restriction_mapping_own_action_results(self, context, *, selection, after_decision_index, limit):
        return self._restriction_mapping_records().own_action_results(context, selection=selection, after_decision_index=after_decision_index, limit=limit)

    def restriction_mapping_frozen_facts(self, context, *, sources):
        return self._restriction_mapping_records().frozen_facts(context, sources=sources)

    def restriction_mapping_reference(self, context, reference, namespace):
        from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_references import RestrictionMappingReferences
        return RestrictionMappingReferences(self.workflow.store, self.workflow.run_id).resolve(context, reference, namespace)

    def scientific_parent_task(self, context):
        """Optionally read original scientific guidance without changing work."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_provenance_receiver_identity_mismatch')
        provenance = getattr(self.workflow, 'scientific_provenance', None)
        return None if provenance is None else provenance.parent_task(context)

    def macs2_peak_monitor_task(self, context, *, assignment=None):
        """Read selected MACS2 guidance only after current target admission.

        Commission preparation passes the selecting parent's actual context;
        a monitor decision uses its own saved context. Neither case constructs
        a Results context, observes the job or receives any new reference.
        """
        from .library.native_macs2_peak_execution import OPERATION, MODE, validate_macs2_peak_native_job
        workflow = self.workflow
        if context.run_id != workflow.run_id:
            raise ValueError('macs2_peak_monitor_receiver_identity_mismatch')
        if context.role == 'scientific_process' and assignment is not None:
            workflow.scientific_process_binding.validate_context(context)
            selection = plain(context.assignment).get('selection', {})
            parent = dict(scientific_question=context.request['goal']['objective'], selected_tool_info=selection.get('child_tool_info', []))
        else:
            parent = self.scientific_parent_task(context)
        if parent is None or not any((row.get('name') == OPERATION and row.get('resources') == 'local' for row in parent.get('selected_tool_info', ()))):
            return None
        from .progress_observations import _ASSIGNMENT
        from gene_annotation_episode.domain import validate_schema
        selected = plain(context.assignment if assignment is None else assignment)
        validate_schema(selected, _ASSIGNMENT)
        reference = selected['target_handle']
        receipts = workflow.receipts
        if receipts is None or reference not in receipts.known(context.episode_id):
            raise ValueError('macs2_peak_monitor_target_not_received')
        if not self.reference_in_scope(reference, context.scope, 'execution_handle'):
            raise ValueError('macs2_peak_monitor_target_outside_scope')
        try:
            owner = workflow.episode_bindings.for_role('results')
        except LookupError:
            return None
        if owner.store is not workflow.store or owner.run_id != workflow.run_id or owner.services is not self:
            raise ValueError('macs2_peak_monitor_owner_identity_mismatch')
        target = owner.job_progress_provider.targets.read_target(reference, plain(context.scope))
        requested = target.get('assignment', {})
        job = requested.get('requested_job', {}).get('native_macs2_peak')
        if target.get('resource_kind') != 'local' or job is None:
            return None
        job = validate_macs2_peak_native_job(job)
        if job['request']['operation'] != OPERATION or job['request']['mode'] != MODE:
            return None
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import macs2_peak_scientific_job_view
        resource_id = target['resource_id']
        return dict(version='selected_execution_task_v1', scientific_question=parent['scientific_question'], selected_tool_info=plain(parent['selected_tool_info']), requests=[dict(resource_id=resource_id, resource_kind='local', endpoint=requested.get('endpoint'), constraints=plain(requested.get('constraints', {})), resource=owner._resource_information(resource_id), job=macs2_peak_scientific_job_view(job))], constraints=plain(requested.get('constraints', {})), selector=selected, result_description=None)

