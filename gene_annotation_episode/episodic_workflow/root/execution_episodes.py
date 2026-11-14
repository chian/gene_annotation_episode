"""Original eager execution construction and shared custody."""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.execution_contracts import checked, obj
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.execution_source_declarations import (VERSION, LAUNCH_VERSION, RESULTS_VERSION, RESULT_PROVIDER, _CLOSED_CREDIT, ROLES, KINDS, ROLE_KINDS, TEXT, OFFSET, LIMIT, FILE_LIMIT, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, RESULTS_SCHEMA, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA, NATIVE_SELECTOR_SCHEMA, launch_operation_catalog, native_result_operation_catalog, _outcome, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_VERSION, LUMPY_FILE_SOURCE_SELECTOR_SCHEMA, LUMPY_FILE_SOURCE_SELECTOR_VERSION, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector, is_macs2_file_source_selector, is_lumpy_file_source_selector, ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, SELECTION_SCHEMA, validate_assignment, validate_completion_proof, operation_catalog, confined, PracticalReceiptInformation, LocalFileSourceResults, is_native_hmmer_target, is_native_blast_target, is_native_blast_masking_target, is_native_blast_utility_target, is_native_blast_database_target, is_standard_blast_database_target, is_native_infernal_target, is_native_infernal_preparation_target, is_native_hmmer_preparation_target, is_native_rna_structure_target, is_native_protein_structure_target)

from gene_annotation_episode.episodic_workflow.root.execution_scientific_inputs import ExecutionScientificInputs
from gene_annotation_episode.episodic_workflow.root.execution_blast_custody import ExecutionBlastCustody
from gene_annotation_episode.episodic_workflow.root.execution_result_selection import ExecutionResultSelection
from gene_annotation_episode.episodic_workflow.root.execution_scientific_returns import ExecutionScientificReturns
from gene_annotation_episode.episodic_workflow.root.execution_result_custody import ExecutionResultCustody
from gene_annotation_episode.episodic_workflow.root.execution_received_custody import ExecutionReceivedCustody
from gene_annotation_episode.episodic_workflow.root.execution_closed_credit import ExecutionClosedCredit
from gene_annotation_episode.episodic_workflow.root.execution_resource_information import ExecutionResourceInformation
from gene_annotation_episode.episodic_workflow.root.execution_request_custody import ExecutionRequestCustody
from .execution_resource_construction import resource_execution
CUSTODY_VERSION='root_execution_resource_custody_v1'

class ExecutionEpisodes(ExecutionScientificInputs, ExecutionBlastCustody, ExecutionResultSelection, ExecutionScientificReturns, ExecutionResultCustody, ExecutionReceivedCustody, ExecutionClosedCredit, ExecutionResourceInformation, ExecutionRequestCustody):
    def __init__(self, services, *, store, directory, run_id, resources, initial_information, tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield=False, results_yield_profiles=None, task_yield_profiles=None):
        self.services, self.store, self.directory = (services, store, Path(directory))
        self.run_id, self.tool_registry = (run_id, tool_registry)
        self.resources = json.loads(canonical(resources))
        self.initial_information = json.loads(canonical(initial_information))
        if not isinstance(self.resources, dict) or not self.resources or any((not isinstance(key, str) or not key or (not isinstance(value, dict)) or (value.get('kind') not in KINDS) for key, value in self.resources.items())):
            raise ValueError('explicit_execution_resources_required')
        if not isinstance(self.initial_information, dict) or not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if type(log_window_bytes) is not int or log_window_bytes < 1 or (not isinstance(log_roles, (tuple, list))) or any((not isinstance(role, str) or not role for role in log_roles)):
            raise ValueError('explicit_execution_log_selection_required')
        self.handoff_unit, self.acquired_record_unit = (handoff_unit, acquired_record_unit)
        self.log_window_bytes, self.log_roles = (log_window_bytes, tuple(log_roles))
        if type(require_private_yield) is not bool:
            raise TypeError('execution_private_yield_binding_requires_boolean')
        self.private_yield_binding = require_private_yield
        profiles = {} if results_yield_profiles is None else plain(results_yield_profiles)
        if not isinstance(profiles, dict) or set(profiles) - {'native_unbounded_local', 'native_unbounded_hpc'}:
            raise ValueError('explicit_results_yield_profiles_invalid')
        from gene_annotation_episode.episodic_workflow.root.numerical import YieldController, YieldParameters
        for key, binding in profiles.items():
            if not isinstance(binding, dict) or set(binding) != {'cutoff', 'parameters'} or (not isinstance(binding['parameters'], dict)) or (type(binding['cutoff']) not in (int, float)) or (not math.isfinite(binding['cutoff'])) or (binding['cutoff'] <= 0):
                raise ValueError('explicit_results_yield_profile_invalid:' + key)
            YieldController('configuration', 0.0, binding['cutoff'], YieldParameters(**binding['parameters']))
        self.results_yield_profiles = profiles
        task_profiles = {} if task_yield_profiles is None else plain(task_yield_profiles)
        if not isinstance(task_profiles, dict) or any((not isinstance(key, str) or not key or (not isinstance(binding, dict)) or (set(binding) != {'cutoff', 'parameters'}) or (not isinstance(binding['parameters'], dict)) or (type(binding['cutoff']) not in (int, float)) or (not math.isfinite(binding['cutoff'])) or (binding['cutoff'] <= 0) for key, binding in task_profiles.items())):
            raise ValueError('explicit_execution_task_yield_profiles_invalid')
        for binding in task_profiles.values():
            YieldController('configuration', 0.0, binding['cutoff'], YieldParameters(**binding['parameters']))
        self.task_yield_profiles = task_profiles
        self._practical = {}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            if 'native_flux_balance' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_flux_balance_bindings import validate_flux_balance_bindings
                if kind != 'local':
                    raise ValueError('native_flux_balance_resource_execution_binding_unfinished:' + kind)
                validate_flux_balance_bindings(configuration['native_flux_balance'])
            if 'native_fluorescence' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_contracts import validate_fluorescence_bindings
                if kind != 'local':
                    raise ValueError('native_fluorescence_resource_execution_binding_unfinished:' + kind)
                validate_fluorescence_bindings(configuration['native_fluorescence'])
            if 'native_expression_nmf' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_expression_nmf_contracts import validate_expression_nmf_bindings
                if kind != 'local':
                    raise ValueError('native_expression_nmf_resource_execution_binding_unfinished:' + kind)
                validate_expression_nmf_bindings(configuration['native_expression_nmf'])
            if 'native_macs2_peak' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_macs2_peak_execution import validate_macs2_peak_bindings
                if kind != 'local':
                    raise ValueError('native_macs2_peak_resource_execution_binding_unfinished:' + kind)
                validate_macs2_peak_bindings(configuration['native_macs2_peak'])
            if 'native_lumpy' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_lumpy_execution import validate_lumpy_bindings
                if kind != 'local':
                    raise ValueError('native_lumpy_resource_execution_binding_unfinished:' + kind)
                validate_lumpy_bindings(configuration['native_lumpy'])
            if 'native_homer_motif' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_homer_execution import validate_homer_bindings
                if kind != 'local':
                    raise ValueError('native_homer_resource_execution_binding_unfinished:' + kind)
                validate_homer_bindings(configuration['native_homer_motif'])
            if 'native_atac_differential' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import validate_atac_bindings
                if kind != 'local':
                    raise ValueError('native_atac_resource_execution_binding_unfinished:' + kind)
                validate_atac_bindings(configuration['native_atac_differential'])
            if 'native_chromatin_interactions' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_contracts import validate_chromatin_bindings
                if kind != 'local':
                    raise ValueError('native_chromatin_resource_execution_binding_unfinished:' + kind)
                validate_chromatin_bindings(configuration['native_chromatin_interactions'])
            if 'native_genomic_overlap' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_contracts import validate_genomic_overlap_bindings
                if kind != 'local':
                    raise ValueError('native_genomic_overlap_resource_execution_binding_unfinished:' + kind)
                validate_genomic_overlap_bindings(configuration['native_genomic_overlap'])
            if 'native_protein_structure' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_contracts import validate_protein_structure_bindings
                if kind != 'local':
                    raise ValueError('native_protein_structure_resource_execution_binding_unfinished:' + kind)
                validate_protein_structure_bindings(configuration['native_protein_structure'])
            if 'native_molecular_sequence' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_tools import validate_native_molecular_sequence_bindings
                if kind != 'local':
                    raise ValueError('native_molecular_sequence_resource_execution_binding_unfinished:' + kind)
                validate_native_molecular_sequence_bindings(configuration['native_molecular_sequence'])
            if 'native_rna_structure' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import validate_rna_structure_bindings
                if kind != 'local':
                    raise ValueError('native_rna_structure_resource_execution_binding_unfinished:' + kind)
                validate_rna_structure_bindings(configuration['native_rna_structure'])
            if 'native_blast_standard_database' in configuration and kind != 'hpc':
                raise ValueError('native_blast_standard_database_hpc_resource_required')
            if 'native_blast_database' in configuration and kind != 'hpc':
                raise ValueError('native_blast_database_hpc_resource_required')
            if 'native_hmmer' in configuration and kind != 'local':
                raise ValueError('native_hmmer_resource_execution_binding_unfinished:' + kind)
            if 'native_hmmer' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_tool_info import validate_native_hmmer_bindings
                validate_native_hmmer_bindings(configuration['native_hmmer'])
            if 'native_blast_masking' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_tool_info import validate_native_blast_masking_bindings
                if kind != 'local':
                    raise ValueError('native_blast_masking_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_masking_bindings(configuration['native_blast_masking'])
            if 'native_blast_utility' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_tool_info import validate_native_blast_utility_bindings
                if kind != 'local':
                    raise ValueError('native_blast_utility_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_utility_bindings(configuration['native_blast_utility'])
            if 'native_blast' in configuration and kind != 'local':
                raise ValueError('native_blast_resource_execution_binding_unfinished:' + kind)
            if 'native_blast' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_tool_info import validate_native_blast_bindings
                validate_native_blast_bindings(configuration['native_blast'])
            if 'native_infernal' in configuration and kind != 'local':
                raise ValueError('native_infernal_resource_execution_binding_unfinished:' + kind)
            if 'native_infernal' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_infernal_tool_info import validate_native_infernal_bindings
                validate_native_infernal_bindings(configuration['native_infernal'])
            if 'native_infernal_preparation' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_infernal_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])
            if 'native_hmmer_preparation' in configuration:
                from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_hmmer_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
            if kind != 'api':
                inventory = self.initial_information.get(resource_id)
                self._practical[resource_id] = resource_execution(services, resource_kind=kind, directory=self.directory, resources={kind: configuration}, store=store, initial_information={} if inventory is None else {kind: inventory})
        from gene_annotation_episode.episodic_workflow.root.api_service_execution import APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items() if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store, run_id=run_id, directory=self.directory, configuration=api_resources, tool_registry=tool_registry, handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit, received_input_reader=getattr(services, 'read_received_molecular_input', None))
        from gene_annotation_episode.episodic_workflow.root.library.execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id, directory=self.directory, resources=self.resources, api_execution=self.api_execution, log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        self.local_file_sources = LocalFileSourceResults(self)
        if services is not None:
            bind_peak_reader = getattr(tool_registry, 'bind_macs2_peak_capture_reader', None)
            if callable(bind_peak_reader):
                bind_peak_reader(self.run_id, self.read_macs2_peak_capture_selection)
        self.molecular_sequence_results = None
        if services is not None:
            from gene_annotation_episode.episodic_workflow.root.molecular_sequence_results import MolecularSequenceResults
            self.molecular_sequence_results = MolecularSequenceResults(self)
            bind_molecular_results = getattr(tool_registry, 'bind_molecular_sequence_results', None)
            if callable(bind_molecular_results):
                bind_molecular_results(self.molecular_sequence_results)
            bind_execution_owner = getattr(tool_registry, 'bind_execution_owner', None)
            if callable(bind_execution_owner):
                bind_execution_owner(self)
        from gene_annotation_episode.episodic_workflow.root.flux_balance_execution_inputs import FluxBalanceExecutionInputs
        self.flux_balance_inputs = FluxBalanceExecutionInputs(self)
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import FluxBalanceRequestBindings
        self.flux_balance_requests = FluxBalanceRequestBindings(self)
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import Macs2PeakRequestBindings
        self.macs2_peak_requests = Macs2PeakRequestBindings(self)
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import LumpyRequestBindings
        self.lumpy_requests = LumpyRequestBindings(self)
        for practical in self._practical.values():
            practical.flux_balance_input_reader = self.flux_balance_inputs.for_start
        from gene_annotation_episode.episodic_workflow.root.native_protein_structure_results import NativeProteinStructureResults
        from gene_annotation_episode.episodic_workflow.root.native_protein_structure_returns import NativeProteinStructureReturns
        self.native_protein_structure_results = NativeProteinStructureResults(self)
        self.native_protein_structure_returns = NativeProteinStructureReturns(self)
        from gene_annotation_episode.episodic_workflow.root.native_fluorescence_results import NativeFluorescenceResults
        from gene_annotation_episode.episodic_workflow.root.fluorescence_returns import FluorescenceReturns
        self.native_fluorescence_results = NativeFluorescenceResults(self)
        self.native_fluorescence_returns = FluorescenceReturns(self)
        self.native_flux_balance_results = self.native_flux_balance_returns = None
        ordinary_fba = getattr(tool_registry, 'ordinary_flux_balance_backend', None)
        if ordinary_fba is not None or any((configuration.get('native_flux_balance') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_flux_balance_results import NativeFluxBalanceResults
            from gene_annotation_episode.episodic_workflow.root.flux_balance_returns import FluxBalanceReturns
            self.native_flux_balance_results = NativeFluxBalanceResults(self)
            self.native_flux_balance_returns = FluxBalanceReturns(self, ordinary_backend=ordinary_fba)
        self.native_expression_nmf_results = self.native_expression_nmf_returns = None
        if any((configuration.get('native_expression_nmf') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_expression_nmf_results import NativeExpressionNMFResults
            from gene_annotation_episode.episodic_workflow.root.expression_nmf_returns import ExpressionNMFReturns
            self.native_expression_nmf_results = NativeExpressionNMFResults(self)
            self.native_expression_nmf_returns = ExpressionNMFReturns(self)
        self.atac_results = self.atac_returns = None
        if any((configuration.get('native_atac_differential') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_atac_differential_results import NativeAtacDifferentialResults
            from gene_annotation_episode.episodic_workflow.root.atac_differential_returns import AtacDifferentialReturns
            self.atac_results = NativeAtacDifferentialResults(self)
            self.atac_returns = AtacDifferentialReturns(self)
        self.native_chromatin_interaction_results = self.native_chromatin_interaction_returns = None
        if any((configuration.get('native_chromatin_interactions') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_chromatin_interaction_results import NativeChromatinInteractionResults
            from gene_annotation_episode.episodic_workflow.root.chromatin_interaction_returns import ChromatinInteractionReturns
            self.native_chromatin_interaction_results = NativeChromatinInteractionResults(self)
            self.native_chromatin_interaction_returns = ChromatinInteractionReturns(self)
        self.native_genomic_overlap_results = self.native_genomic_overlap_returns = None
        if any((configuration.get('native_genomic_overlap') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_genomic_overlap_results import NativeGenomicOverlapResults
            from gene_annotation_episode.episodic_workflow.root.genomic_overlap_returns import GenomicOverlapReturns
            self.native_genomic_overlap_results = NativeGenomicOverlapResults(self)
            self.native_genomic_overlap_returns = GenomicOverlapReturns(self)
        self.native_rna_structure_results = self.native_rna_structure_returns = None
        self.rna_structure_comparison_results = self.rna_structure_comparison_returns = None
        if any((configuration.get('native_rna_structure') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_rna_structure_results import NativeRNAStructureResults
            from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import NativeRNAStructureReturns
            from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_results import NativeRNAStructureComparisonResults
            from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_returns import RNAStructureComparisonReturns
            self.native_rna_structure_results = NativeRNAStructureResults(self)
            self.native_rna_structure_returns = NativeRNAStructureReturns(self)
            self.rna_structure_comparison_results = NativeRNAStructureComparisonResults(self)
            self.rna_structure_comparison_returns = RNAStructureComparisonReturns(self)
        from gene_annotation_episode.episodic_workflow.root.native_hmmer_results import NativeHMMERResults
        self.native_hmmer_results = NativeHMMERResults(self)
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_results import NativeBLASTMaskingResults
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_returns import NativeBLASTMaskingReturns
        self.native_blast_masking_results = NativeBLASTMaskingResults(self)
        self.native_blast_masking_returns = NativeBLASTMaskingReturns(self)
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_results import NativeBLASTUtilityResults
        from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_returns import NativeBLASTUtilityReturns
        self.native_blast_utility_results = NativeBLASTUtilityResults(self)
        self.native_blast_utility_returns = NativeBLASTUtilityReturns(self)
        self.native_blast_results = self.native_blast_returns = None
        self.native_blast_standard_database_results = self.native_blast_standard_database_returns = None
        if any((configuration.get('native_blast_standard_database') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_results import StandardBLASTDatabaseResults
            from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_returns import StandardBLASTDatabaseReturns
            self.native_blast_standard_database_results = StandardBLASTDatabaseResults(self)
            self.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(self)
        self.native_blast_database_results = self.native_blast_database_returns = None
        if any((configuration.get('native_blast_database') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_blast_database_results import NativeBLASTDatabaseResults
            from gene_annotation_episode.episodic_workflow.root.native_blast_database_returns import NativeBLASTDatabaseReturns
            self.native_blast_database_results = NativeBLASTDatabaseResults(self)
            self.native_blast_database_returns = NativeBLASTDatabaseReturns(self)
        if any((configuration.get('native_blast') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_blast_results import NativeBLASTResults
            from gene_annotation_episode.episodic_workflow.root.native_blast_returns import NativeBLASTReturns
            self.native_blast_results = NativeBLASTResults(self)
            self.native_blast_returns = NativeBLASTReturns(self)
        self.native_infernal_results = self.native_infernal_returns = None
        if any((configuration.get('native_infernal') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_infernal_results import NativeInfernalResults
            from gene_annotation_episode.episodic_workflow.root.native_infernal_returns import NativeInfernalReturns
            self.native_infernal_results = NativeInfernalResults(self)
            self.native_infernal_returns = NativeInfernalReturns(self)
        self.native_infernal_preparation_results = self.native_infernal_preparation_returns = None
        if any((configuration.get('native_infernal_preparation') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_infernal_preparation_results import NativeInfernalPreparationResults
            from gene_annotation_episode.episodic_workflow.root.native_infernal_preparation_returns import NativeInfernalPreparationReturns
            self.native_infernal_preparation_results = NativeInfernalPreparationResults(self)
            self.native_infernal_preparation_returns = NativeInfernalPreparationReturns(self)
        self.native_hmmer_preparation_results = self.native_hmmer_preparation_returns = None
        if any((configuration.get('native_hmmer_preparation') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.native_hmmer_preparation_results import NativeHmmerPreparationResults
            from gene_annotation_episode.episodic_workflow.root.native_hmmer_preparation_returns import NativeHmmerPreparationReturns
            self.native_hmmer_preparation_results = NativeHmmerPreparationResults(self)
            self.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(self)

    def as_record(self):
        return {'binding_id': 'root_execution_resource_custody', 'version': CUSTODY_VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}

    def _credit_binding_record(self,context):
        from .execution_binding_catalogue import binding_for_context
        return binding_for_context(self,context).as_record()
