"""A107 received execution information."""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a107.domain import identity
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical, checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a107.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_local_assignment_validation import confined
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment, GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a107.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_practical_receipt_reader import HistoricalPracticalReceiptReader as TerminalExecutionEpisodes
from gene_annotation_episode.episodic_workflow.root.a107.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_acquisition import is_native_blast_masking_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_acquisition import is_native_blast_utility_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_acquisition import is_native_infernal_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_protein_structure_acquisition import is_native_protein_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import LocalFileSourceResults, SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION, FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_file_selector_declarations import MACS2_SELECTOR_SCHEMA as MACS2_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_SELECTOR_VERSION as MACS2_FILE_SOURCE_SELECTOR_VERSION, LUMPY_SELECTOR_SCHEMA as LUMPY_FILE_SOURCE_SELECTOR_SCHEMA, LUMPY_SELECTOR_VERSION as LUMPY_FILE_SOURCE_SELECTOR_VERSION, is_macs2_file_source_selector, is_lumpy_file_source_selector
VERSION = 'execution_episodes_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULT_PROVIDER = 'episode.execution_result'
_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
ROLE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
BLAST_GRADED_REQUEST_VERSION = 'blast_database_grader_return_request_v1'
BLAST_GRADED_REQUEST_SCHEMA = obj({'version': {'const': BLAST_GRADED_REQUEST_VERSION}, 'resource_id': TEXT, 'return_type': {'const': 'blast_database_sheet_v1'}, 'query_subject_ref': TEXT, 'database': TEXT}, ['version', 'resource_id', 'return_type', 'query_subject_ref'])
BLAST_GRADED_RETURN_SOURCE = 'ncbi_blast_database_grader_result'
BLAST_GRADED_RETURN_SCHEMA = {'type': 'array', 'items': obj({'result_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'grading_artifact_ref': {'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}, 'sheet_schema': {'const': 'blast_database_sheet_v1'}, 'query_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'database': TEXT}), 'x-source': BLAST_GRADED_RETURN_SOURCE}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])

class HistoricalReceivedExecutionOwner:
    roles = ROLES
    entry_roles = ('launch', 'results')
    replaces_default_instructions = True

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
        from gene_annotation_episode.episodic_workflow.root.a107.numerical import YieldController, YieldParameters
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
                from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_native_flux_balance_bindings import validate_flux_balance_bindings
                if kind != 'local':
                    raise ValueError('native_flux_balance_resource_execution_binding_unfinished:' + kind)
                validate_flux_balance_bindings(configuration['native_flux_balance'])
            if 'native_fluorescence' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_fluorescence_contracts import validate_fluorescence_bindings
                if kind != 'local':
                    raise ValueError('native_fluorescence_resource_execution_binding_unfinished:' + kind)
                validate_fluorescence_bindings(configuration['native_fluorescence'])
            if 'native_expression_nmf' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_contracts import validate_expression_nmf_bindings
                if kind != 'local':
                    raise ValueError('native_expression_nmf_resource_execution_binding_unfinished:' + kind)
                validate_expression_nmf_bindings(configuration['native_expression_nmf'])
            if 'native_macs2_peak' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.macs2_request_contracts import validate_macs2_peak_bindings
                if kind != 'local':
                    raise ValueError('native_macs2_peak_resource_execution_binding_unfinished:' + kind)
                validate_macs2_peak_bindings(configuration['native_macs2_peak'])
            if 'native_lumpy' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.lumpy_request_contracts import validate_lumpy_bindings
                if kind != 'local':
                    raise ValueError('native_lumpy_resource_execution_binding_unfinished:' + kind)
                validate_lumpy_bindings(configuration['native_lumpy'])
            if 'native_homer_motif' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.homer_binding_metadata import validate_homer_bindings
                if kind != 'local':
                    raise ValueError('native_homer_resource_execution_binding_unfinished:' + kind)
                validate_homer_bindings(configuration['native_homer_motif'])
            if 'native_atac_differential' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.atac_execution_contracts import validate_atac_bindings
                if kind != 'local':
                    raise ValueError('native_atac_resource_execution_binding_unfinished:' + kind)
                validate_atac_bindings(configuration['native_atac_differential'])
            if 'native_chromatin_interactions' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_request_contracts import validate_chromatin_bindings
                if kind != 'local':
                    raise ValueError('native_chromatin_resource_execution_binding_unfinished:' + kind)
                validate_chromatin_bindings(configuration['native_chromatin_interactions'])
            if 'native_genomic_overlap' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_native_genomic_overlap_contracts import validate_genomic_overlap_bindings
                if kind != 'local':
                    raise ValueError('native_genomic_overlap_resource_execution_binding_unfinished:' + kind)
                validate_genomic_overlap_bindings(configuration['native_genomic_overlap'])
            if 'native_protein_structure' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_protein_structure_contracts import validate_protein_structure_bindings
                if kind != 'local':
                    raise ValueError('native_protein_structure_resource_execution_binding_unfinished:' + kind)
                validate_protein_structure_bindings(configuration['native_protein_structure'])
            if 'native_molecular_sequence' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.library.molecular_binding_metadata import validate_native_molecular_sequence_bindings
                if kind != 'local':
                    raise ValueError('native_molecular_sequence_resource_execution_binding_unfinished:' + kind)
                validate_native_molecular_sequence_bindings(configuration['native_molecular_sequence'])
            if 'native_rna_structure' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_contracts import validate_rna_structure_bindings
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
                from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_tool_info import validate_native_hmmer_bindings
                validate_native_hmmer_bindings(configuration['native_hmmer'])
            if 'native_blast_masking' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_tool_info import validate_native_blast_masking_bindings
                if kind != 'local':
                    raise ValueError('native_blast_masking_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_masking_bindings(configuration['native_blast_masking'])
            if 'native_blast_utility' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_tool_info import validate_native_blast_utility_bindings
                if kind != 'local':
                    raise ValueError('native_blast_utility_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_utility_bindings(configuration['native_blast_utility'])
            if 'native_blast' in configuration and kind != 'local':
                raise ValueError('native_blast_resource_execution_binding_unfinished:' + kind)
            if 'native_blast' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_tool_info import validate_native_blast_bindings
                validate_native_blast_bindings(configuration['native_blast'])
            if 'native_infernal' in configuration and kind != 'local':
                raise ValueError('native_infernal_resource_execution_binding_unfinished:' + kind)
            if 'native_infernal' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_tool_info import validate_native_infernal_bindings
                validate_native_infernal_bindings(configuration['native_infernal'])
            if 'native_infernal_preparation' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_infernal_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])
            if 'native_hmmer_preparation' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_hmmer_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
            if kind != 'api':
                inventory = self.initial_information.get(resource_id)
                self._practical[resource_id] = TerminalExecutionEpisodes(services, directory=self.directory, resources={kind: configuration}, store=store, initial_information={} if inventory is None else {kind: inventory})
        from gene_annotation_episode.episodic_workflow.root.a107.api_service_execution import APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items() if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store, run_id=run_id, directory=self.directory, configuration=api_resources, tool_registry=tool_registry, handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit, received_input_reader=getattr(services, 'read_received_molecular_input', None))
        from gene_annotation_episode.episodic_workflow.root.a107.execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id, directory=self.directory, resources=self.resources, api_execution=self.api_execution, log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        self.local_file_sources = LocalFileSourceResults(self)
        if services is not None:
            bind_peak_reader = getattr(tool_registry, 'bind_macs2_peak_capture_reader', None)
            if callable(bind_peak_reader):
                bind_peak_reader(self.run_id, self.read_macs2_peak_capture_selection)
        self.molecular_sequence_results = None
        if services is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.molecular_sequence_results import MolecularSequenceResults
            self.molecular_sequence_results = MolecularSequenceResults(self)
            bind_molecular_results = getattr(tool_registry, 'bind_molecular_sequence_results', None)
            if callable(bind_molecular_results):
                bind_molecular_results(self.molecular_sequence_results)
            bind_execution_owner = getattr(tool_registry, 'bind_execution_owner', None)
            if callable(bind_execution_owner):
                bind_execution_owner(self)
        from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_execution_inputs import FluxBalanceExecutionInputs
        self.flux_balance_inputs = FluxBalanceExecutionInputs(self)
        from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import FluxBalanceRequestBindings
        self.flux_balance_requests = FluxBalanceRequestBindings(self)
        from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import Macs2PeakRequestBindings
        self.macs2_peak_requests = Macs2PeakRequestBindings(self)
        from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import LumpyRequestBindings
        self.lumpy_requests = LumpyRequestBindings(self)
        for practical in self._practical.values():
            practical.flux_balance_input_reader = self.flux_balance_inputs.for_start
        from gene_annotation_episode.episodic_workflow.root.a107.native_protein_structure_results import NativeProteinStructureResults
        from gene_annotation_episode.episodic_workflow.root.a107.native_protein_structure_returns import NativeProteinStructureReturns
        self.native_protein_structure_results = NativeProteinStructureResults(self)
        self.native_protein_structure_returns = NativeProteinStructureReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a107.native_fluorescence_results import NativeFluorescenceResults
        from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_returns import FluorescenceReturns
        self.native_fluorescence_results = NativeFluorescenceResults(self)
        self.native_fluorescence_returns = FluorescenceReturns(self)
        self.native_flux_balance_results = self.native_flux_balance_returns = None
        ordinary_fba = getattr(tool_registry, 'ordinary_flux_balance_backend', None)
        if ordinary_fba is not None or any((configuration.get('native_flux_balance') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.flux_balance_native_result_acquisition import NativeFluxBalanceResults
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.flux_balance_received_result_authority import FluxBalanceReturns
            self.native_flux_balance_results = NativeFluxBalanceResults(self)
            self.native_flux_balance_returns = FluxBalanceReturns(self, ordinary_backend=ordinary_fba)
        self.native_expression_nmf_results = self.native_expression_nmf_returns = None
        if any((configuration.get('native_expression_nmf') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_results import NativeExpressionNMFResults
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_returns import ExpressionNMFReturns
            self.native_expression_nmf_results = NativeExpressionNMFResults(self)
            self.native_expression_nmf_returns = ExpressionNMFReturns(self)
        self.atac_results = self.atac_returns = None
        if any((configuration.get('native_atac_differential') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.atac_native_result_acquisition import NativeAtacDifferentialResults
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.atac_received_result_authority import AtacDifferentialReturns
            self.atac_results = NativeAtacDifferentialResults(self)
            self.atac_returns = AtacDifferentialReturns(self)
        self.native_chromatin_interaction_results = self.native_chromatin_interaction_returns = None
        if any((configuration.get('native_chromatin_interactions') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.chromatin_native_result_acquisition import NativeChromatinInteractionResults
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.chromatin_received_result_authority import ChromatinInteractionReturns
            self.native_chromatin_interaction_results = NativeChromatinInteractionResults(self)
            self.native_chromatin_interaction_returns = ChromatinInteractionReturns(self)
        self.native_genomic_overlap_results = self.native_genomic_overlap_returns = None
        if any((configuration.get('native_genomic_overlap') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.genomic_overlap_native_result_acquisition import NativeGenomicOverlapResults
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.genomic_overlap_received_result_authority import GenomicOverlapReturns
            self.native_genomic_overlap_results = NativeGenomicOverlapResults(self)
            self.native_genomic_overlap_returns = GenomicOverlapReturns(self)
        self.native_rna_structure_results = self.native_rna_structure_returns = None
        self.rna_structure_comparison_results = self.rna_structure_comparison_returns = None
        if any((configuration.get('native_rna_structure') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_results import NativeRNAStructureResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_returns import NativeRNAStructureReturns
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import NativeRNAStructureComparisonResults
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_returns import RNAStructureComparisonReturns
            self.native_rna_structure_results = NativeRNAStructureResults(self)
            self.native_rna_structure_returns = NativeRNAStructureReturns(self)
            self.rna_structure_comparison_results = NativeRNAStructureComparisonResults(self)
            self.rna_structure_comparison_returns = RNAStructureComparisonReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_results import NativeHMMERResults
        self.native_hmmer_results = NativeHMMERResults(self)
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_results import NativeBLASTMaskingResults
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_returns import NativeBLASTMaskingReturns
        self.native_blast_masking_results = NativeBLASTMaskingResults(self)
        self.native_blast_masking_returns = NativeBLASTMaskingReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_results import NativeBLASTUtilityResults
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_returns import NativeBLASTUtilityReturns
        self.native_blast_utility_results = NativeBLASTUtilityResults(self)
        self.native_blast_utility_returns = NativeBLASTUtilityReturns(self)
        self.native_blast_results = self.native_blast_returns = None
        self.native_blast_standard_database_results = self.native_blast_standard_database_returns = None
        if any((configuration.get('native_blast_standard_database') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import StandardBLASTDatabaseResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_returns import StandardBLASTDatabaseReturns
            self.native_blast_standard_database_results = StandardBLASTDatabaseResults(self)
            self.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(self)
        self.native_blast_database_results = self.native_blast_database_returns = None
        if any((configuration.get('native_blast_database') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import NativeBLASTDatabaseResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_returns import NativeBLASTDatabaseReturns
            self.native_blast_database_results = NativeBLASTDatabaseResults(self)
            self.native_blast_database_returns = NativeBLASTDatabaseReturns(self)
        if any((configuration.get('native_blast') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_results import NativeBLASTResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_returns import NativeBLASTReturns
            self.native_blast_results = NativeBLASTResults(self)
            self.native_blast_returns = NativeBLASTReturns(self)
        self.native_infernal_results = self.native_infernal_returns = None
        if any((configuration.get('native_infernal') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_results import NativeInfernalResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_returns import NativeInfernalReturns
            self.native_infernal_results = NativeInfernalResults(self)
            self.native_infernal_returns = NativeInfernalReturns(self)
        self.native_infernal_preparation_results = self.native_infernal_preparation_returns = None
        if any((configuration.get('native_infernal_preparation') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_results import NativeInfernalPreparationResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_returns import NativeInfernalPreparationReturns
            self.native_infernal_preparation_results = NativeInfernalPreparationResults(self)
            self.native_infernal_preparation_returns = NativeInfernalPreparationReturns(self)
        self.native_hmmer_preparation_results = self.native_hmmer_preparation_returns = None
        if any((configuration.get('native_hmmer_preparation') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_results import NativeHmmerPreparationResults
            from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_returns import NativeHmmerPreparationReturns
            self.native_hmmer_preparation_results = NativeHmmerPreparationResults(self)
            self.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(self)

    def as_record(self):
        return {'binding_id': 'execution_episodes', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id) if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = []
            if internal and self.resources[resource_id].get('native_flux_balance'):
                from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_flux_balance_contracts import flux_balance_schema
                for binding in self.resources[resource_id]['native_flux_balance']:
                    alternatives.append({'allOf': [flux_balance_schema('FBARequestedJob'), {'properties': {'native_flux_balance': {'properties': {'operation': {'const': binding['operation']}, 'mode': {'const': binding['mode']}, 'software': {'const': deepcopy(binding['software'])}, 'model_input': {'properties': {'format': {'enum': deepcopy(binding['model_formats'])}}}}}}}]})
            fluorescence = self.resources[resource_id].get('native_fluorescence', [])
            if fluorescence:
                from gene_annotation_episode.episodic_workflow.root.a107.library.fluorescence_configured_tool_contracts import fluorescence_tool_contracts
                alternatives.extend((row['input_schema'] for row in fluorescence_tool_contracts(fluorescence, resource_kind=kind, resource_id=resource_id)))
            nmf = self.resources[resource_id].get('native_expression_nmf', [])
            if nmf:
                from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_tool_info import expression_nmf_tool_contracts
                alternatives.extend((row['input_schema'] for row in expression_nmf_tool_contracts(nmf, resource_kind=kind, resource_id=resource_id)))
            macs2_peak = self.resources[resource_id].get('native_macs2_peak', [])
            if macs2_peak and internal:
                from gene_annotation_episode.episodic_workflow.root.a107.library.macs2_request_contracts import macs2_peak_execution_schema
                alternatives.append(macs2_peak_execution_schema('RequestedJob', bindings=macs2_peak))
            lumpy = self.resources[resource_id].get('native_lumpy', [])
            if lumpy and internal:
                from gene_annotation_episode.episodic_workflow.root.a107.library.lumpy_request_contracts import lumpy_execution_schema
                alternatives.append(lumpy_execution_schema('RequestedJob', bindings=lumpy))
            atac = self.resources[resource_id].get('native_atac_differential', [])
            if atac:
                from gene_annotation_episode.episodic_workflow.root.a107.library.atac_configured_tool_contracts import atac_tool_contracts
                alternatives.extend((row['input_schema'] for row in atac_tool_contracts(atac, resource_kind=kind, resource_id=resource_id)))
            chromatin = self.resources[resource_id].get('native_chromatin_interactions', [])
            if chromatin:
                from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_configured_tool_contracts import chromatin_interaction_tool_contracts
                alternatives.extend((row['input_schema'] for row in chromatin_interaction_tool_contracts(chromatin, resource_kind=kind, resource_id=resource_id)))
            overlap = self.resources[resource_id].get('native_genomic_overlap', [])
            if overlap:
                from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_configured_tool_contracts import genomic_overlap_tool_contracts
                alternatives.extend((row['input_schema'] for row in genomic_overlap_tool_contracts(overlap, resource_kind=kind, resource_id=resource_id)))
            protein = self.resources[resource_id].get('native_protein_structure', [])
            if protein:
                from gene_annotation_episode.episodic_workflow.root.a107.library.protein_structure_configured_tool_contracts import protein_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in protein_structure_tool_contracts(protein, resource_kind='local', resource_id=resource_id)))
            rna = self.resources[resource_id].get('native_rna_structure', [])
            if rna:
                from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_tool_info import rna_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in rna_structure_tool_contracts(rna, resource_kind=kind, resource_id=resource_id)))
            database = self.resources[resource_id].get('native_blast_standard_database')
            if database:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                alternatives.extend((row['input_schema'] for row in standard_blast_database_tool_contracts(database['bindings'], resource_kind=kind, resource_id=resource_id)))
            database = self.resources[resource_id].get('native_blast_database')
            if database:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_tool_info import native_blast_database_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_database_tool_contracts(database['bindings'], resource_kind=kind, resource_id=resource_id)))
            native = self.resources[resource_id].get('native_hmmer', [])
            if native:
                from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_tool_info import native_hmmer_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_hmmer_tool_contracts(native, resource_kind=kind, resource_id=resource_id)))
            masking = self.resources[resource_id].get('native_blast_masking', [])
            if masking:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_tool_info import native_blast_masking_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_masking_tool_contracts(masking, resource_kind=kind, resource_id=resource_id)))
            utility = self.resources[resource_id].get('native_blast_utility', [])
            if utility:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_tool_info import native_blast_utility_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_utility_tool_contracts(utility, resource_kind=kind, resource_id=resource_id)))
            blast = self.resources[resource_id].get('native_blast', [])
            if blast:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_tool_info import native_blast_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_blast_tool_contracts(blast, resource_kind=kind, resource_id=resource_id)))
            infernal = self.resources[resource_id].get('native_infernal', [])
            if infernal:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_tool_info import native_infernal_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_tool_contracts(infernal, resource_kind=kind, resource_id=resource_id)))
            preparation = self.resources[resource_id].get('native_infernal_preparation', [])
            if preparation:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_preparation_tool_contracts(preparation, resource_kind=kind, resource_id=resource_id)))
            hmmer_preparation = self.resources[resource_id].get('native_hmmer_preparation', [])
            if hmmer_preparation:
                from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_hmmer_preparation_tool_contracts(hmmer_preparation, resource_kind=kind, resource_id=resource_id)))
            if alternatives:
                schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]}
            else:
                schema['properties']['requested_job'] = deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        lumpy_compact = []
        if compact and kind == 'local' and self.resources[resource_id].get('native_lumpy'):
            from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import resource_assignment_schema
            lumpy_compact.append(resource_assignment_schema(resource_id, selected=selected, bindings=self.resources[resource_id]['native_lumpy']))
        if compact and kind == 'local' and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected), *lumpy_compact]}
        if compact and kind == 'local' and self.resources[resource_id].get('native_macs2_peak'):
            from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected, bindings=self.resources[resource_id]['native_macs2_peak']), *lumpy_compact]}
        if lumpy_compact:
            return {'anyOf': [schema, *lumpy_compact]}
        return schema

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        if role == 'results':
            schema = deepcopy(RESULTS_SCHEMA)
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
            schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': MACS2_FILE_SOURCE_SELECTOR_VERSION}}}, 'then': deepcopy(MACS2_FILE_SOURCE_SELECTOR_SCHEMA)})
            schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': LUMPY_FILE_SOURCE_SELECTOR_VERSION}}}, 'then': deepcopy(LUMPY_FILE_SOURCE_SELECTOR_SCHEMA)})
            from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'native_blast_masking_result_selector_v1'}}}, 'then': deepcopy(NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)})
            from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'enum': ['native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2']}}}, 'then': deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)})
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_result_contracts import FLUORESCENCE_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'fluorescence_result_selector_v1'}}}, 'then': deepcopy(FLUORESCENCE_RESULT_SELECTOR_SCHEMA)})
            if self.native_expression_nmf_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_result_contracts import EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'expression_nmf_result_selector_v1'}}}, 'then': deepcopy(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA)})
            if self.native_flux_balance_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.library.flux_balance_result_selection import FBA_RESULT_SELECTOR_SCHEMA
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'flux_balance_result_selector_v1'}}}, 'then': deepcopy(FBA_RESULT_SELECTOR_SCHEMA)})
            if self.atac_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.library.atac_result_selection import atac_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'atac_differential_result_selector_v1'}}}, 'then': atac_result_selector_schema()})
            if self.native_chromatin_interaction_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_result_selection import chromatin_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'chromatin_interaction_result_selector_v1'}}}, 'then': chromatin_result_selector_schema()})
            if self.native_rna_structure_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import RESULT_SELECTOR_SCHEMA
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
                alternatives = [*deepcopy(RESULT_SELECTOR_SCHEMA['oneOf']), deepcopy(RNA_COMPARISON_SELECTOR_SCHEMA)]
                versions = [branch['properties']['version']['const'] for branch in alternatives]
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'enum': versions}}}, 'then': {'oneOf': alternatives}})
            if any((configuration.get('native_protein_structure') for configuration in self.resources.values())):
                from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_selection import protein_structure_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'protein_structure_result_selector_v1'}}}, 'then': protein_structure_result_selector_schema()})
            if self.native_genomic_overlap_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_result_selection_schema import genomic_overlap_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'genomic_overlap_result_selector_v1'}}}, 'then': genomic_overlap_result_selector_schema()})
            return schema
        if role == 'launch':
            schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: {'anyOf': [self._request_schema(key, selected=False, internal=internal, compact=False), {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA), 'properties': {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA['properties']), 'resource_id': {'const': key}}}]} if self.resources[key].get('service') == 'ncbi_blast' else self._request_schema(key, selected=False, internal=internal, compact=False) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
            schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
            alternatives = [schema]
            if any((value.get('native_flux_balance') for value in self.resources.values())):
                from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            if any((value.get('native_macs2_peak') for value in self.resources.values())):
                from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            if any((value.get('native_lumpy') for value in self.resources.values())):
                from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            return {'anyOf': alternatives} if len(alternatives) > 1 else schema
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        config = self.resources[resource_id]
        kind = KINDS[config['kind']]
        from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, validate_compact_assignment as validate_lumpy_assignment
        if is_lumpy_assignment(value):
            if kind != 'local' or not config.get('native_lumpy'):
                raise ValueError('lumpy_request_binding_unavailable')
            return validate_lumpy_assignment(value, resource_id, bindings=config['native_lumpy'])
        from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, validate_compact_assignment as validate_macs2_assignment
        if is_macs2_assignment(value):
            if kind != 'local' or not config.get('native_macs2_peak'):
                raise ValueError('macs2_peak_request_binding_unavailable')
            return validate_macs2_assignment(value, resource_id, bindings=config['native_macs2_peak'])
        from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import is_compact_assignment, validate_compact_assignment
        if is_compact_assignment(value):
            if kind != 'local' or not config.get('native_flux_balance'):
                raise ValueError('flux_balance_request_binding_unavailable')
            return validate_compact_assignment(value, resource_id)
        value = self.api_execution.validate_assignment(value) if kind == 'api' else validate_assignment(value)
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if kind != 'api':
            if value['resource_kind'] != kind:
                raise ValueError('execution_resource_kind_conflict')
            confined(value['workspace'], config['workspace'])
            operations = self._practical[resource_id]._operations(kind)
            validator = getattr(operations, 'validate_assignment', None)
            if validator is not None:
                validator({**value, 'resource_id': resource_id})
        return value

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch', internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                checked(request, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
                if request['resource_id'] != resource_id or self.resources[resource_id].get('service') != 'ncbi_blast':
                    raise ValueError('blast_database_grader_resource_conflict')
                continue
            self._validate_request(request, resource_id=resource_id)
            if scope is not None and KINDS[self.resources[resource_id]['kind']] == 'api':
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    def _blast_launch_requirement(self, request, resource_id, scope):
        """Bind this launch's query and optional database from its parent request."""
        checked(request, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
        if request['resource_id'] != resource_id:
            raise ValueError('blast_database_grader_resource_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        return {'return_type': request['return_type'], 'query_subject_ref': subject_ref, 'query_length': len(sequence), 'query_sha256': hashlib.sha256(sequence.encode()).hexdigest(), 'database': request.get('database')}

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
                raise ValueError('invalid_execution_resource_constraints')

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:') or (isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.protein_sequence_ancestry import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                return False
        if self.native_protein_structure_results.owns_reference(reference):
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

    def _genomic_overlap_reference_access(self, context, reference, namespace):
        host = self.native_genomic_overlap_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_genomic_overlap_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_genomic_overlap_returns.resolve_received(context, reference, namespace)

    def _fluorescence_reference_access(self, context, reference, namespace):
        host = self.native_fluorescence_results
        if not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_fluorescence_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _fluorescence_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'fluorescence_result_selector_v1'

    def _retained_fluorescence_target(self, context, assignment, scope):
        if not self._fluorescence_selector(assignment):
            return None
        if context.role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_result_contracts import validate_fluorescence_selector
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_return_views import CONTEXT_SOURCE, requested_fluorescence_sources
            selector = validate_fluorescence_selector(assignment['selector'])
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if bool(selector['context_fields']) != (CONTEXT_SOURCE in requested_fluorescence_sources(schema)):
                raise ValueError('fluorescence_context_selection_mismatch')
        return self.native_fluorescence_results.retained_target(context, assignment, scope)

    def _expression_nmf_reference_access(self, context, reference, namespace):
        host = self.native_expression_nmf_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_expression_nmf_returns.resolve_received(context, reference, namespace)

    def _flux_balance_reference_access(self, context, reference, namespace):
        if self.native_flux_balance_returns is not None and self.native_flux_balance_returns.ordinary_backend is not None and (context.role in {'annotation', 'partner_presence_evidence'}) and (namespace in {None, 'artifact'}) and self.native_flux_balance_returns.resolve_received(context, reference, namespace):
            return True
        host = self.native_flux_balance_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_flux_balance_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _flux_balance_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'flux_balance_result_selector_v1'

    def _retained_flux_balance_target(self, context, assignment, scope):
        if not self._flux_balance_selector(assignment):
            return None
        if self.native_flux_balance_results is None:
            raise ValueError('native_flux_balance_results_binding_unavailable')
        return self.native_flux_balance_results.retained_target(context, assignment, scope)

    @staticmethod
    def _expression_nmf_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'expression_nmf_result_selector_v1'

    def _retained_expression_nmf_target(self, context, assignment, scope):
        if not self._expression_nmf_selector(assignment):
            return None
        if self.native_expression_nmf_results is None:
            raise ValueError('native_expression_nmf_results_binding_unavailable')
        return self.native_expression_nmf_results.retained_target(context, assignment, scope)

    def _atac_reference_access(self, context, reference, namespace):
        host = self.atac_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (reference in [supplied['sheet']['artifact_ref'], *(row['file']['artifact_ref'] for row in supplied['tables'])]):
                self.atac_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.atac_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _atac_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'atac_differential_result_selector_v1'

    def _retained_atac_target(self, context, assignment, scope):
        if not self._atac_selector(assignment):
            return None
        if self.atac_results is None:
            raise ValueError('native_atac_results_binding_unavailable')
        return self.atac_results.retained_target(context, assignment, scope)

    def read_macs2_peak_capture_selection(self, context, capture_source_refs, *, before_decision_index=None):
        """Read explicitly received generic captures against their original MACS2 seal.

        Current delivery authenticates before private custody or seal bytes.
        Original target/start controls are retained records; this read never
        consults the original workspace, input bytes or installed software.
        Generic capture provenance is preserved, and an unselected sibling in
        a wrapper does not become a received File or Source.
        """
        from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import EpisodeReturnRecords
        from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
        from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import FILE_PROVIDER, RESULT_PROVIDER, RECEIPT_VERSION
        from gene_annotation_episode.episodic_workflow.root.a107.native_file_capture import NativeFileCaptureError, retained_native_file
        from gene_annotation_episode.episodic_workflow.root.a107.library.macs2_request_contracts import POLICY, macs2_peak_plan, validate_macs2_peak_seal, validate_macs2_peak_original_controls
        from gene_annotation_episode.episodic_workflow.root.a107.library.atac_control_json import decode_json
        from gene_annotation_episode.episodic_workflow.root.a107.received_native_file_inputs import received_file_context

        def require(condition, code):
            if not condition:
                raise ValueError('macs2_peak_capture_' + code)
        require(isinstance(context, BindingContext) and context.run_id == self.run_id, 'context_conflict')
        require(type(capture_source_refs) in (list, tuple) and bool(capture_source_refs) and all((type(ref) is str for ref in capture_source_refs)) and (len(set(capture_source_refs)) == len(capture_source_refs)), 'source_selection_invalid')
        require(before_decision_index is None or (type(before_decision_index) is int and before_decision_index >= 0), 'cutoff_invalid')
        known, _ = received_file_context(self.store, context, failure_prefix='macs2_peak_capture_', baseline=False)
        records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='macs2_peak_capture_')
        selected = []
        for reference in capture_source_refs:
            require(reference in known and (before_decision_index is None or records._received_before(context.episode_id, reference, before_decision_index)), 'source_not_received')
            source = self.store.get(reference)
            require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and (source.get('provider') == FILE_PROVIDER or (source.get('provider') == RESULT_PROVIDER and source.get('version') == RECEIPT_VERSION)), 'source_selection_invalid')
            selected.append((reference, source['provider']))
        plan, source_roles, unavailable_paths = (None, {}, set())
        for reference, provider in selected:
            if provider == FILE_PROVIDER:
                captured = self.local_file_sources.read_source(reference, context.scope)
                require(captured is not None, 'source_receipt_missing')
                target, observation = (captured['target'], captured['observation'])
            else:
                captured = self.local_file_sources.read_wrapper(reference, context.scope)
                require(captured is not None, 'wrapper_receipt_missing')
                target, observation = (captured['target'], captured['observation'])
            require(target['resource_kind'] == 'local' and 'native_macs2_peak' in target['assignment']['requested_job'], 'producer_target_conflict')
            authenticated, original = self.job_progress_provider.targets._native(target['handle'], context.scope)
            require(canonical(authenticated) == canonical(target), 'producer_target_conflict')
            detail = original['receipt']['outcome'].get('native_outcome') or {}
            original_plan = validate_macs2_peak_original_controls(detail.get('native_macs2_peak_plan'), detail.get('native_macs2_peak_handle'), detail.get('native_macs2_peak_request_raw'))
            rebuilt = macs2_peak_plan(target['assignment'], original_plan['identity'], policy=POLICY)
            require(canonical(rebuilt) == canonical(original_plan), 'original_plan_conflict')
            native = observation.get('native', {})
            require(native.get('terminal') is True and native.get('quiescent') is True and (native.get('execution_id') == target['execution_id']) and (native.get('metadata', {}).get('policy') == POLICY), 'original_observation_conflict')
            observed_plan = validate_macs2_peak_original_controls(native.get('native_macs2_peak_plan'), native.get('native_macs2_peak_handle'), native.get('native_macs2_peak_request_raw'))
            require(canonical(observed_plan) == canonical(original_plan) and all((canonical(native.get(key)) == canonical(detail.get(key)) for key in ('native_macs2_peak_handle', 'native_macs2_peak_request_raw'))), 'original_observation_conflict')
            if plan is None:
                plan = original_plan
            else:
                require(canonical(plan) == canonical(original_plan), 'mixed_producer_selection')
            paths = {str(Path(plan['attempt_directory']) / row['relative_path']): row for row in plan['outputs']}
            if provider == FILE_PROVIDER:
                spec = paths.get(captured['resolved_path'])
                require(spec is not None and captured['file'] is not None and (captured['selection']['format'] == spec['format']) and (captured['file']['format'] == spec['format']), 'output_role_conflict')
                require(spec['role'] not in source_roles, 'duplicate_output_role')
                source_roles[spec['role']] = {'source_ref': reference, 'file': deepcopy(captured['file'])}
            else:
                for row in captured['captured_files']:
                    path = row['resolved_path']
                    spec = paths.get(path)
                    if spec is not None and row['file'] is None:
                        require(row['selection']['format'] == spec['format'], 'output_role_conflict')
                        unavailable_paths.add(path)
        require(plan is not None, 'original_plan_required')
        roles = []
        for spec in plan['outputs']:
            supplied = source_roles.get(spec['role'])
            path = str(Path(plan['attempt_directory']) / spec['relative_path'])
            roles.append({'specification': deepcopy(spec), 'source_ref': None if supplied is None else supplied['source_ref'], 'file': None if supplied is None else supplied['file'], 'availability': 'retained' if supplied is not None else 'unavailable' if path in unavailable_paths else 'not_selected', 'qualification': None if supplied is not None else {'code': 'selected_output_unavailable' if path in unavailable_paths else 'output_not_selected'}})
        seal_role = next((row for row in roles if row['specification']['role'] == 'seal'))
        seal = None
        if seal_role['file'] is not None:
            try:
                raw = retained_native_file(self.store, seal_role['file']).read_bytes()
            except NativeFileCaptureError as error:
                if error.code not in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}:
                    raise
                seal_role.update(availability='unavailable', qualification={'code': error.code})
            else:
                seal = validate_macs2_peak_seal(decode_json(raw), plan=plan)
        if seal is None:
            for role in roles:
                if role['specification']['role'] != 'seal':
                    role['qualification'] = {'code': 'producer_seal_unavailable' if seal_role['source_ref'] is not None else 'producer_seal_not_received'}
        else:
            declarations = {row['specification']['role']: row['declaration'] for row in seal['outputs']}
            for role in roles:
                if role['specification']['role'] == 'seal':
                    continue
                declared = declarations[role['specification']['role']]
                file = role['file']
                if file is not None:
                    if declared['state'] != 'present' or file['sha256'] != declared['sha256'] or file['size_bytes'] != declared['size_bytes']:
                        role.update(availability='unavailable', qualification={'code': 'native_output_identity_conflict'})
                elif declared['state'] == 'absent':
                    role.update(availability='unavailable', qualification={'code': 'native_output_absent'})
        return {'plan': deepcopy(plan), 'seal': deepcopy(seal), 'roles': roles}

    def _chromatin_reference_access(self, context, reference, namespace):
        host = self.native_chromatin_interaction_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and any((file.get('artifact_ref') == reference for file in [supplied['sheet'], *supplied['tables']])):
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.native_chromatin_interaction_returns.resolve_received(context, reference, namespace)

    @staticmethod
    def _chromatin_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'chromatin_interaction_result_selector_v1'

    def _retained_chromatin_target(self, context, assignment, scope):
        if not self._chromatin_selector(assignment):
            return None
        if self.native_chromatin_interaction_results is None:
            raise ValueError('native_chromatin_results_binding_unavailable')
        return self.native_chromatin_interaction_results.retained_target(context, assignment, scope)

    @staticmethod
    def _genomic_overlap_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'genomic_overlap_result_selector_v1'

    def _retained_genomic_overlap_target(self, context, assignment, scope):
        if not self._genomic_overlap_selector(assignment):
            return None
        if self.native_genomic_overlap_results is None:
            raise ValueError('native_genomic_overlap_results_binding_unavailable')
        return self.native_genomic_overlap_results.retained_target(context, assignment, scope)

    @staticmethod
    def _masking_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'native_blast_masking_result_selector_v1'

    def _retained_masking_target(self, context, assignment, scope):
        if not self._masking_selector(assignment):
            return None
        return self.native_blast_masking_results.retained_target(context, assignment=assignment, scope=scope)

    def _masking_reference_access(self, context, reference, namespace):
        access = self.native_blast_masking_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_masking_results.applies(context):
            resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    @staticmethod
    def _utility_selector(assignment):
        return assignment.get('selector', {}).get('version') in {'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}

    def _retained_utility_target(self, context, assignment, scope):
        if not self._utility_selector(assignment):
            return None
        return self.native_blast_utility_results.retained_target(context, assignment=assignment, scope=scope)

    def _utility_reference_access(self, context, reference, namespace):
        access = self.native_blast_utility_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    def _validate_blast_launch_selection(self, launch, selected, scope):
        """Apply only this BLAST request's stated query/database constraints."""
        resource_id = selected['resource_id']
        if resource_id not in launch['requests'] or not self._permitted(launch, resource_id):
            raise ValueError('execution_resource_selection_conflict')
        request = launch['requests'][resource_id]
        if request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return
        required = self._blast_launch_requirement(request, resource_id, scope)
        if selected.get('service') != 'ncbi_blast':
            raise ValueError('blast_grader_selected_service_conflict')
        prepared = self.api_execution.services[resource_id].prepare('api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')

    def _blast_target_requirement(self, target, scope):
        """Rebuild the original BLAST return check from its launch request."""
        if target['resource_kind'] != 'api' or target['assignment'].get('service') != 'ncbi_blast':
            return None
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, target['origin_episode_id'])).fetchone()
        if row is None:
            raise ValueError('blast_grader_original_launch_missing')
        path = json.loads(row['path'])
        if len(path) < 2 or path[-2][0] != 'launch':
            raise ValueError('blast_grader_original_launch_path_invalid')
        parent = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(path[:-1]))).fetchone()
        if parent is None:
            raise ValueError('blast_grader_original_parent_missing')
        launch = self._launch(json.loads(parent['request'])['message']['episode_assignment'], scope=scope)
        request = launch['requests'].get(target['resource_id'])
        if request is None or request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return None
        selected = target['assignment']
        if selected.get('service') != 'ncbi_blast':
            raise ValueError('blast_grader_selected_service_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        required_sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        required = {'return_type': request['return_type'], 'query_subject_ref': subject_ref, 'query_length': len(required_sequence), 'query_sha256': hashlib.sha256(required_sequence.encode()).hexdigest(), 'database': request.get('database')}
        prepared = self.api_execution.services[target['resource_id']].prepare('api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')
        handoff = self.api_execution._read_handoff(target['handle'], plain(scope))
        subject_ref = target['assignment']['request']['subject_ref']
        sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
        if handoff['snapshot']['request'].get('query_sha256') != expected:
            raise ValueError('blast_grader_submitted_query_conflict')
        return required

    def _blast_grader_rows(self, context, result_refs, required):
        """Return only original retained database-grader results that meet the request."""
        from gene_annotation_episode.episodic_workflow.root.a107.tool_grading_artifacts import source_tool_grading_entries
        rows = []
        for reference in result_refs:
            body = self.api_execution.read_result(reference, context.scope)
            if body['target']['assignment'].get('service') != 'ncbi_blast':
                continue
            if body['target']['handle'] != plain(context.assignment)['handoff_ref']:
                raise ValueError('blast_grader_result_handoff_conflict')
            source = self.store.get(body['source_ref'])
            graders = source_tool_grading_entries(self.store, source['id'])
            if len(graders) != 1:
                raise ValueError('blast_grader_result_required')
            grading = graders[0]['grading']
            sheet = grading.get('sheet')
            if grading.get('failure') is not None or not isinstance(sheet, dict) or sheet.get('schema') != required['return_type']:
                raise ValueError('blast_grader_result_type_conflict')
            normalized = sheet.get('normalized_result') or {}
            query, search = (normalized.get('query') or {}, normalized.get('search') or {})
            request = search.get('request') or {}
            if normalized.get('mode') != 'database' or normalized.get('resource') != 'api' or query.get('length') != required['query_length'] or (request.get('sequence_sha256') != required['query_sha256']) or (request.get('subject_ref') != body['service_request']['subject_ref']) or (request.get('database') != body['service_request']['database']):
                raise ValueError('blast_grader_result_query_conflict')
            database = search.get('database')
            if not isinstance(database, str) or not database:
                raise ValueError('blast_grader_native_database_missing')
            if required['database'] is not None and database != required['database']:
                raise ValueError('blast_grader_result_database_conflict')
            rows.append({'result_ref': reference, 'grading_artifact_ref': graders[0]['artifact_ref'], 'sheet_schema': sheet['schema'], 'query_sha256': required['query_sha256'], 'database': database})
        return rows

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        """An internal execution view; the immutable episode request stays original."""
        from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, materialized_assignment as materialized_lumpy_assignment
        if is_lumpy_assignment(plain(context.assignment)):
            from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_lumpy_assignment(self.store, context), context.request, context.received_record_refs)
            self.lumpy_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical
        from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, materialized_assignment as materialized_macs2_assignment
        if is_macs2_assignment(plain(context.assignment)):
            from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_macs2_assignment(self.store, context), context.request, context.received_record_refs)
            self.macs2_peak_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical
        from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        if not is_compact_assignment(plain(context.assignment)):
            return context
        from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
        practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_assignment(self.store, context), context.request, context.received_record_refs)
        self.flux_balance_requests.validate_practical_history(context, practical, self._delegate(context))
        return practical

    def _blast_scientific_owner(self, origin_episode_id):
        """Recover the annotation and axis assigned above one original launch."""
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, origin_episode_id)).fetchone()
        if row is None:
            raise ValueError('blast_original_launch_episode_unavailable')
        path = json.loads(row['path'])
        for length in range(len(path), 0, -1):
            if path[length - 1][0] != 'partner_presence_evidence':
                continue
            owner = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)', (self.run_id, json.dumps(path[:length]))).fetchone()
            if owner is None:
                raise ValueError('blast_scientific_owner_unavailable')
            assignment = json.loads(owner['request'])['message']['episode_assignment']
            return {'proposed_annotation_ref': assignment.get('proposed_annotation_ref'), 'evidence_axis': assignment['selection']['evidence_axis']['option_id']}
        return {'proposed_annotation_ref': None, 'evidence_axis': None}

    def annotation_axis_yield_context(self, context, credit):
        if context.role != 'annotation' or self.api_execution is None or (not any((service.service == 'ncbi_blast' for service in self.api_execution.services.values()))):
            return {}
        arms = credit.get('arms', [])
        unresolved = []
        for job in self.api_execution.received_blast_jobs(context, self.job_progress_provider):
            job.update(self._blast_scientific_owner(job['origin_episode_id']))
            if job['result_received'] or job['native_state'] in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}:
                continue
            matches = [arm for arm in arms if arm['proposed_annotation_ref'] == job['proposed_annotation_ref'] and arm['axis'] == job['evidence_axis'] and (arm['subject_ref'] == job['subject_ref'])]
            if len(matches) != 1:
                raise ValueError('blast_pending_job_requires_one_annotation_axis_arm')
            unresolved.append({**{name: matches[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}, 'handoff_ref': job['handoff_ref'], 'native_state': job['native_state']})
        return {'unresolved_annotation_axis_credit': unresolved}

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        if is_macs2_file_source_selector(assignment.get('selector')) or is_lumpy_file_source_selector(assignment.get('selector')):
            self.local_file_sources.admit_handoff(context, assignment)
        if self._has_enrichr():
            target = self.api_execution.closed_enrichr_target(context)
            if target is not None:
                return target
        fba = self._retained_flux_balance_target(context, assignment, context.scope)
        if fba is not None:
            return fba
        masking = self._retained_masking_target(context, assignment, context.scope)
        if masking is not None:
            return masking
        utility = self._retained_utility_target(context, assignment, context.scope)
        if utility is not None:
            return utility
        fluorescence = self._retained_fluorescence_target(context, assignment, context.scope)
        if fluorescence is not None:
            return fluorescence
        nmf = self._retained_expression_nmf_target(context, assignment, context.scope)
        if nmf is not None:
            return nmf
        atac = self._retained_atac_target(context, assignment, context.scope)
        if atac is not None:
            return atac
        chromatin = self._retained_chromatin_target(context, assignment, context.scope)
        if chromatin is not None:
            return chromatin
        overlap = self._retained_genomic_overlap_target(context, assignment, context.scope)
        if overlap is not None:
            return overlap
        retained = self._retained_protein_result(context, assignment, context.scope)
        return retained['body']['intent']['target'] if retained is not None else self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

    def _retained_protein_result(self, context, assignment, scope):
        """Recover target metadata only from received or own completed authority.

        Scientific operand bytes retain their separate selected-use checks. A
        private staged receipt cannot replace a completed original action here.
        """
        assignment = checked(assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        if assignment['selector'].get('version') != 'protein_structure_result_selector_v1':
            return None
        from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import validate_target
        from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_contracts import same
        from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_selection import validate_protein_structure_result_selector
        selector = validate_protein_structure_result_selector(assignment['selector'])
        receipts = self.native_protein_structure_results.receipts
        if selector['acquisition'] == 'retained_sheet_only':
            descriptor = selector['saved_sheet']
            received = self.native_protein_structure_returns.authenticate_received_saved_sheet(context, descriptor, required_use='recalculate')
            custody = descriptor['custody']
            retained = receipts.read_completed(episode_id=custody['result_episode_id'], operation_key=custody['result_operation_key'], scope=plain(scope))
            if not same(received['custody'], custody) or not same(retained['publication']['custody'], custody) or custody['handoff_ref'] != assignment['handoff_ref']:
                raise ValueError('original_commission_mismatch')
        elif context.role == 'results' and same(assignment, plain(context.assignment)):
            completed = receipts.completed_receipts(context)
            qualified = [receipt for receipt in completed if receipt['body']['handoff_proof'] is not None]
            if not qualified:
                return None
            retained = qualified[0]
            if any((not same(receipt['body']['intent']['target'], retained['body']['intent']['target']) for receipt in qualified)):
                raise ValueError('execution_result_original_target_conflict')
        else:
            return None
        target = validate_target(retained['body']['intent']['target'])
        if context.run_id != self.run_id or target['run_id'] != self.run_id or target['handle'] != assignment['handoff_ref'] or (target['resource_kind'] != 'local') or (not is_native_protein_structure_target(target)) or (retained['body']['handoff_proof'] is None):
            raise ValueError('original_commission_mismatch')
        self.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        self.store.validate_scope(target['scope'], parent_scope=plain(scope))
        reader = self.job_progress_provider.targets
        resource_id = target['resource_id']
        configuration = self.resources.get(resource_id)
        if configuration is None or configuration['kind'] != 'local' or (not same(reader.resources.get(resource_id), configuration)) or (resource_id not in reader.operations):
            raise ValueError('practical_execution_resource_identity_conflict')
        confined(target['assignment']['workspace'], configuration['workspace'])
        reader.operations[resource_id].validate_assignment(target['assignment'])
        self._selector(assignment, target)
        return retained

    @staticmethod
    def _comparison_selector(assignment):
        return assignment.get('selector', {}).get('version') == 'native_rna_structure_comparison_selector_v1'

    def _selector(self, assignment, target):
        if is_file_source_selector(assignment.get('selector')):
            return self.local_file_sources.selector(assignment, target)
        native_fba = 'native_flux_balance' in target.get('assignment', {}).get('requested_job', {})
        if self._flux_balance_selector(assignment) or native_fba:
            if self.native_flux_balance_results is None:
                raise ValueError('native_flux_balance_results_binding_unavailable')
            if not native_fba or target.get('resource_kind') != 'local':
                raise ValueError('flux_balance_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.library.flux_balance_result_selection import validate_flux_balance_result_selector
            selector = validate_flux_balance_result_selector(assignment['selector'])
            return validate_flux_balance_result_selector(selector, job=target['assignment']['requested_job']) if selector['mode'] == 'native_result' else selector
        if self._masking_selector(assignment) or is_native_blast_masking_target(target):
            if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import validate_masking_result_selector
            return validate_masking_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
        if self._utility_selector(assignment) or is_native_blast_utility_target(target):
            if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import validate_blast_utility_result_selector
            return validate_blast_utility_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
        native_fluorescence = 'native_fluorescence' in target.get('assignment', {}).get('requested_job', {})
        if self._fluorescence_selector(assignment) or native_fluorescence:
            if not native_fluorescence or target.get('resource_kind') != 'local':
                raise ValueError('fluorescence_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_result_contracts import validate_fluorescence_selector
            return validate_fluorescence_selector(assignment['selector'], job=target['assignment']['requested_job']['native_fluorescence'])
        native_nmf = 'native_expression_nmf' in target.get('assignment', {}).get('requested_job', {})
        if self._expression_nmf_selector(assignment) or native_nmf:
            if self.native_expression_nmf_results is None:
                raise ValueError('native_expression_nmf_results_binding_unavailable')
            if not native_nmf or target.get('resource_kind') != 'local':
                raise ValueError('expression_nmf_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_result_contracts import validate_expression_nmf_result_selector
            return validate_expression_nmf_result_selector(assignment['selector'], job=target['assignment']['requested_job']['native_expression_nmf'])
        native_atac = 'native_atac_differential' in target.get('assignment', {}).get('requested_job', {})
        if self._atac_selector(assignment) or native_atac:
            if self.atac_results is None:
                raise ValueError('native_atac_results_binding_unavailable')
            if not native_atac or target.get('resource_kind') != 'local':
                raise ValueError('atac_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.library.atac_result_selection import validate_atac_result_selector
            return validate_atac_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_atac_differential']['request'])
        native_chromatin = 'native_chromatin_interactions' in target.get('assignment', {}).get('requested_job', {})
        if self._chromatin_selector(assignment) or native_chromatin:
            if self.native_chromatin_interaction_results is None:
                raise ValueError('native_chromatin_results_binding_unavailable')
            if not native_chromatin or target.get('resource_kind') != 'local':
                raise ValueError('chromatin_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_result_selection import validate_chromatin_result_selector
            return validate_chromatin_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_chromatin_interactions']['request'])
        native_overlap = 'native_genomic_overlap' in target.get('assignment', {}).get('requested_job', {})
        if self._genomic_overlap_selector(assignment) or native_overlap:
            if self.native_genomic_overlap_results is None:
                raise ValueError('native_genomic_overlap_results_binding_unavailable')
            if not native_overlap or target.get('resource_kind') != 'local':
                raise ValueError('genomic_overlap_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_selected_result import _selector
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_genomic_overlap_contracts import validate_genomic_overlap_record
            value = validate_genomic_overlap_record('Selector', assignment['selector'])
            value = _selector(value, mode=value['mode'], request=target['assignment']['requested_job']['native_genomic_overlap']['request'])
            if (value['mode'] == 'native_result') != (value['saved_sheet_file'] is None):
                raise ValueError('genomic_overlap_result_saved_sheet_mode_conflict')
            if value['saved_sheet_file'] is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_received_fact_contracts import SAVED_SOURCE, validate_genomic_overlap_fact_values
                validate_genomic_overlap_fact_values(SAVED_SOURCE, [value['saved_sheet_file']])
            return value
        if assignment.get('selector', {}).get('version') == 'protein_structure_result_selector_v1' or is_native_protein_structure_target(target):
            if not is_native_protein_structure_target(target):
                raise ValueError('original_commission_mismatch')
            from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_selection import validate_protein_structure_result_selector
            return validate_protein_structure_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_protein_structure']['request'])
        if self._comparison_selector(assignment):
            if self.rna_structure_comparison_results is None:
                raise ValueError('rna_comparison_results_binding_unavailable')
            if not is_native_rna_structure_target(target):
                raise ValueError('rna_comparison_anchor_required')
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_contracts import validate_rna_comparison_selector
            return validate_rna_comparison_selector(assignment['selector'])
        if is_native_rna_structure_target(target):
            if self.native_rna_structure_results is None:
                raise ValueError('native_rna_structure_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import validate_rna_structure_result_selector
            return validate_rna_structure_result_selector(assignment['selector'], mode=target['assignment']['requested_job']['native_rna_structure']['mode'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import validate_native_blast_result_selector
            return validate_native_blast_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast']['program'])
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import validate_native_infernal_result_selector
            return validate_native_infernal_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_infernal']['program'])
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_infernal_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        value = checked(assignment['selector'], NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
        paths = list(value.get('paths', []))
        if 'path' in value:
            if value['path'] in paths:
                raise ValueError('ambiguous_execution_results_selector')
            paths.append(value['path'])
        if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
            raise ValueError('execution_results_paths_required')
        for path in paths:
            confined(path, target['assignment']['workspace'])
        return value

    def _windows(self, selector):
        values = {path: (0, None) for path in selector.get('paths', [])}
        if 'path' in selector:
            values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
        return values

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id + ':' + episode_id + ':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

    def _validate_result_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
        if not isinstance(body, dict) or set(body) != fields or body['version'] != 'execution_result_information_v2' or (body['run_id'] != self.run_id) or (body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
            raise ValueError('invalid_execution_result_information')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], scope)
        if canonical(target) != canonical(body['target']):
            raise ValueError('execution_result_original_target_conflict')
        selector = self._selector(body['assignment'], target)
        requested = self._windows(selector)
        row = self._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if episode is not None:
            message = json.loads(episode['request'])['message']
            if message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope'] or json.loads(episode['path'])[-1][0] != 'results':
                raise ValueError('execution_result_original_assignment_conflict')
        for window in body['windows']:
            if window['path'] not in requested:
                raise ValueError('execution_result_selector_conflict')
            raw = base64.b64decode(window['bytes_base64'], validate=True)
            start, length = requested[window['path']]
            if window['offset'] < start or window['returned_bytes'] != len(raw) or (length is not None and window['offset'] + len(raw) > start + length) or (window['size_bytes'] < 0):
                raise ValueError('execution_result_window_conflict')
        directory = self.directory / 'execution-results' / digest([self.run_id, body['episode_id']])
        path = directory / (digest(body['operation_key']) + '.receipt.json')
        if not path.exists() or canonical(_read(path)) != canonical(body):
            raise ValueError('execution_result_original_receipt_conflict')
        return row

    def _read_result(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != RESULT_PROVIDER:
            return None
        if source.get('version') == LOCAL_FILE_SOURCE_RECEIPT_VERSION:
            return self.local_file_sources.read_wrapper(reference, scope)
        raw = self.store.get_artifact(source['artifact_ref'])
        body = json.loads(raw)
        row = self._validate_result_body(body, scope)
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([body['run_id'], body['episode_id'], body['operation_key']]), 'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': None, 'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        expected = identity('source', {'origin': 'tool', 'record': payload})
        if reference != expected or raw != canonical(body).encode() or {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != payload:
            raise ValueError('execution_result_source_identity_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if outcome.get('status') != 'completed' or outcome.get('result') != body or reference not in outcome.get('record_refs', []):
                raise ValueError('execution_result_saved_outcome_conflict')
        return body

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from gene_annotation_episode.episodic_workflow.root.a107.episode_receipts import EpisodeReceipts
            table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
            if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone():
                receipts = EpisodeReceipts(self.store, self.run_id)
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(receipts.known(context.episode_id)), 'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
            else:
                rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(dict.fromkeys((ref for row in rows for ref in json.loads(row[0]).get('record_refs', [])))), 'initial_known_record_refs': []}
        supplied = plain(supplied)
        if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
            raise ValueError('execution_receiver_identity_conflict')
        for key in ('known_record_refs', 'initial_known_record_refs'):
            if not isinstance(supplied.get(key), list) or any((not isinstance(ref, str) or not ref for ref in supplied[key])):
                raise ValueError('execution_receiver_references_required')
        if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
            raise ValueError('execution_initial_references_must_be_known')
        return supplied

    def _context_target(self, context, target):
        from gene_annotation_episode.episodic_workflow.root.a107.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding
        if is_lumpy_launch(plain(context.assignment)) or is_lumpy_assignment(plain(context.assignment)):
            own = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            original = read_lumpy_binding(self.store, self.run_id, target['origin_episode_id'])
            if not any((canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])) or canonical(target['assignment']) != canonical(original['requests'][0]['assignment']) or (context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        from gene_annotation_episode.episodic_workflow.root.a107.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding
        if is_macs2_launch(plain(context.assignment)) or is_macs2_assignment(plain(context.assignment)):
            own = read_macs2_binding(self.store, self.run_id, context.episode_id)
            original = read_macs2_binding(self.store, self.run_id, target['origin_episode_id'])
            if not any((canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])) or canonical(target['assignment']) != canonical(original['requests'][0]['assignment']) or (context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        from gene_annotation_episode.episodic_workflow.root.a107.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_launch(plain(context.assignment)) or is_compact_assignment(plain(context.assignment)):
            own = read_request_binding(self.store, self.run_id, context.episode_id)
            original = read_request_binding(self.store, self.run_id, target['origin_episode_id'])
            if not any((row['assignment'] == target['assignment'] for row in own['requests'])) or target['assignment'] != original['requests'][0]['assignment'] or (context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        if context.role == 'launch':
            launch = self._launch(plain(context.assignment), scope=context.scope)
            selected = target['assignment']
            resource_id = target['resource_id']
            request = launch['requests'].get(resource_id)
            if request is not None and request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._validate_blast_launch_selection(launch, selected, context.scope)
                handoff = self.api_execution._read_handoff(target['handle'], plain(context.scope))
                subject_ref = selected['request']['subject_ref']
                sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
                expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
                if handoff['snapshot']['request'].get('query_sha256') != expected:
                    raise ValueError('blast_grader_submitted_query_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target

    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs, results = ({}, {})
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if source.get('provider') != 'episode.practical_receipt' and (not (self.api_execution is not None and self.api_execution.is_handoff_source(reference))):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue
                try:
                    self._context_target(context, target)
                except ValueError:
                    continue
                if returnable:
                    handoffs[reference] = target
            return (selection, handoffs, results)

    def _forwards_bvbrc_reports(self, role):
        return _forwards_bvbrc_reports(self, role)

    def _forwards_minhash_reports(self, role):
        return _forwards_minhash_reports(self, role)

    def received_report_sources(self, role, *, _include_separate_api=True):
        result = {}
        if role in {'annotation', 'partner_presence_evidence'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = self.fact_sources('results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if self.native_flux_balance_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.flux_balance_received_fact_contracts import fba_fact_sources
            sources = fba_fact_sources()
            if self.native_flux_balance_returns.ordinary_backend is None:
                sources = {name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')}
            result.update(sources)
        if role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self._has_enrichr() and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.enrichr_received_contracts import enrichr_fact_sources
            result.update(enrichr_fact_sources())
        if self._has_addgene() and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.addgene_received_fields import addgene_sequence_fact_sources
            result.update(addgene_sequence_fact_sources())
        if role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_return_views import fluorescence_fact_sources
            result.update(fluorescence_fact_sources())
        if self.native_expression_nmf_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import expression_nmf_fact_sources
            result.update(expression_nmf_fact_sources())
        if self.atac_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.atac_received_fact_contracts import atac_fact_sources
            result.update(atac_fact_sources())
        if self.native_chromatin_interaction_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_received_fact_contracts import chromatin_fact_sources
            result.update(chromatin_fact_sources())
        if self.native_genomic_overlap_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_received_fact_contracts import genomic_overlap_fact_sources
            result.update(genomic_overlap_fact_sources())
        if role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_result_views import protein_structure_fact_sources
            result.update(protein_structure_fact_sources())
        if self.rna_structure_comparison_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
            result.update(rna_comparison_fact_sources())
        if self.native_rna_structure_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
            result.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_infernal_preparation_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self._has_rfam() and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import rfam_fact_sources
            result.update(rfam_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import native_infernal_fact_sources
            result.update(native_infernal_fact_sources())
            result['execution_infernal_result_refs'] = self._infernal_reference_source()
        if _include_separate_api:
            received_report_sources_branch_0(self, role, result)
        if _include_separate_api:
            received_report_sources_branch_1(self, role, result)
        if self._has_appservice() and role in {'annotation', 'partner_presence_evidence'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context, *, _include_separate_api=True):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'partner_presence_evidence'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if self.native_flux_balance_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
            result.update(self.native_flux_balance_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self._has_enrichr() and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.api_execution.enrichr_returns.facts_for_closure(context, schema))
        if self._has_addgene() and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.api_execution.addgene_returns.received_facts(context, schema))
        if context.role in {'annotation', 'partner_presence_evidence'} and schema.get('properties') is not None:
            result.update(self.native_fluorescence_returns.facts_for_closure(context, schema))
        if self.native_expression_nmf_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
            result.update(self.native_expression_nmf_returns.facts_for_closure(context, schema))
        if self.atac_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
            result.update(self.atac_returns.facts_for_closure(context, schema))
        if self.native_chromatin_interaction_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
            result.update(self.native_chromatin_interaction_returns.facts_for_closure(context, schema))
        if self.native_genomic_overlap_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
            result.update(self.native_genomic_overlap_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_protein_structure_returns.received_facts(context, schema))
        if self.rna_structure_comparison_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.rna_structure_comparison_returns.received_facts(context, schema))
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_rna_structure_returns.received_facts(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
        if self._has_rfam() and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.api_execution.rfam_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self.native_infernal_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            result.update(self.native_infernal_returns.received_facts(context, schema))
        if _include_separate_api:
            received_report_facts_branch_0(self, context, schema, result)
        if _include_separate_api:
            received_report_facts_branch_1(self, context, schema, result)
        if self._has_appservice() and context.role in {'annotation', 'partner_presence_evidence'}:
            if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            result.update(self.api_execution.homology_returns.received_facts(context, schema))
            result.update(self.api_execution.phylogeny_returns.received_facts(context, schema))
            result.update(self.api_execution.alignment_returns.received_facts(context, schema))
            result.update(self.api_execution.genome_alignment_returns.received_facts(context, schema))
            proteome = self.api_execution.proteome_returns.received_facts(context, schema)
            if set(result).intersection(proteome):
                raise ValueError('received_report_fact_conflict')
            result.update(proteome)
            comparative = self.api_execution.comparative_systems_returns.received_facts(context, schema)
            if set(result).intersection(comparative):
                raise ValueError('received_report_fact_conflict')
            result.update(comparative)
            fastqutils = self.api_execution.fastqutils_returns.received_facts(context, schema)
            if set(result).intersection(fastqutils):
                raise ValueError('received_report_fact_conflict')
            result.update(fastqutils)
            application = self.api_execution.application_returns.received_facts(context, schema)
            if set(result).intersection(application):
                raise ValueError('received_report_fact_conflict')
            result.update(application)
        return result

    def received_report_closure_facts(self, context):
        """Private return bindings, called only by the registry at episode closure."""
        if context.role not in {'annotation', 'partner_presence_evidence'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if self._has_addgene():
            from gene_annotation_episode.episodic_workflow.root.a107.library.addgene_received_fields import CLOSURE_PREFIX
            frozen = self.api_execution.addgene_returns.facts_for_closure(context, schema)
            if CLOSURE_PREFIX in frozen:
                result[CLOSURE_PREFIX] = frozen[CLOSURE_PREFIX]
        if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
            result.update(self.native_flux_balance_returns.ordinary_closure_facts(context, schema))
        return result

    def resolve_received_reference(self, context, reference, namespace, *, _include_separate_api=True):
        captured = self.local_file_sources.reference_access(context, reference, namespace)
        if captured is not None:
            return captured
        fba = self._flux_balance_reference_access(context, reference, namespace)
        if fba is not None:
            return fba
        masking = self._masking_reference_access(context, reference, namespace)
        if masking is not None:
            return masking
        utility = self._utility_reference_access(context, reference, namespace)
        if utility is not None:
            return utility
        if self._has_uniprot():
            resolved = self.api_execution.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_enrichr():
            resolved = self.api_execution.enrichr_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.enrichr_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_addgene():
            resolved = self.api_execution.addgene_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.addgene_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        fluorescence = self._fluorescence_reference_access(context, reference, namespace)
        if fluorescence is not None:
            return fluorescence
        nmf = self._expression_nmf_reference_access(context, reference, namespace)
        if nmf is not None:
            return nmf
        atac = self._atac_reference_access(context, reference, namespace)
        if atac is not None:
            return atac
        chromatin = self._chromatin_reference_access(context, reference, namespace)
        if chromatin is not None:
            return chromatin
        overlap = self._genomic_overlap_reference_access(context, reference, namespace)
        if overlap is not None:
            return overlap
        access = self._protein_reference_access(context, reference, namespace)
        if access is not None:
            return access
        if self.rna_structure_comparison_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
            if namespace in COMPARISON_NAMESPACES:
                return self.rna_structure_comparison_results.resolve(context, reference, namespace) if context.role == 'results' else self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
            access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
        if self.native_rna_structure_results is not None:
            access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if context.role in {'annotation', 'partner_presence_evidence'}:
                resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_rfam() and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.application_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if _include_separate_api:
            _original_api_branch_resolution = resolve_received_reference_branch_0(self, context, reference, namespace)
            if _original_api_branch_resolution is not None:
                return _original_api_branch_resolution
        if _include_separate_api:
            _original_api_branch_resolution = resolve_received_reference_branch_1(self, context, reference, namespace)
            if _original_api_branch_resolution is not None:
                return _original_api_branch_resolution
        for results in (self.native_hmmer_preparation_results, self.native_infernal_preparation_results):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

    def validate_received_report(self, context, form, schema, *, _include_separate_api=True):
        self.local_file_sources.validate_received_report(context, form, schema)
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, schema)
        self.native_blast_masking_returns.validate_received_report(context, form, schema)
        self.native_blast_utility_returns.validate_received_report(context, form, schema)
        if self._has_uniprot():
            self.api_execution.uniprot_returns.validate_received_report(context, form, schema)
        if self._has_enrichr():
            self.api_execution.enrichr_returns.validate_received_report(context, form, schema)
        if self._has_addgene():
            self.api_execution.addgene_returns.validate_received_report(context, form, schema)
        if plain(schema).get('properties') is not None:
            self.native_fluorescence_returns.validate_received_report(context, form, schema)
        if self.native_expression_nmf_returns is not None:
            self.native_expression_nmf_returns.validate_received_report(context, form, schema)
        if self.atac_returns is not None:
            self.atac_returns.validate_received_report(context, form, schema)
        if self.native_chromatin_interaction_returns is not None:
            self.native_chromatin_interaction_returns.validate_received_report(context, form, schema)
        if self.native_genomic_overlap_returns is not None:
            self.native_genomic_overlap_returns.validate_received_report(context, form, schema)
        self.native_protein_structure_returns.validate_received_report(context, form, schema)
        if self.rna_structure_comparison_returns is not None:
            self.rna_structure_comparison_returns.validate_received_report(context, form, schema)
        if self.native_rna_structure_returns is not None:
            self.native_rna_structure_returns.validate_received_report(context, form, schema)
        if self.native_blast_standard_database_returns is not None:
            self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
        if self.native_blast_database_returns is not None:
            self.native_blast_database_returns.validate_received_report(context, form, schema)
        if self.native_hmmer_preparation_returns is not None:
            self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
        if self.native_infernal_preparation_returns is not None:
            self.native_infernal_preparation_returns.validate_received_report(context, form, schema)
        if self._has_rfam():
            self.api_execution.rfam_returns.validate_received_report(context, form, schema)
        if self.native_blast_returns is not None:
            self.native_blast_returns.validate_received_report(context, form, schema)
        if self.native_infernal_returns is not None:
            self.native_infernal_returns.validate_received_report(context, form, schema)
        if self._has_appservice():
            self.api_execution.appservice.validate_received_report(context, form, schema)
            self.api_execution.homology_returns.validate_received_report(context, form, schema)
            self.api_execution.phylogeny_returns.validate_received_report(context, form, schema)
            self.api_execution.alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.genome_alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.proteome_returns.validate_received_report(context, form, schema)
            self.api_execution.comparative_systems_returns.validate_received_report(context, form, schema)
            self.api_execution.fastqutils_returns.validate_received_report(context, form, schema)
            self.api_execution.application_returns.validate_received_report(context, form, schema)
        if _include_separate_api:
            validate_received_report_branch_0(self, context, form, schema)
        if _include_separate_api:
            validate_received_report_branch_1(self, context, form, schema)

    def fact_sources(self, role):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
                values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
        if self.native_flux_balance_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.flux_balance_received_fact_contracts import fba_fact_sources
            sources = fba_fact_sources()
            values.update({name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')})
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        if self._has_uniprot() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import uniprot_fact_sources
            values.update(uniprot_fact_sources())
        if self._has_enrichr() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.enrichr_received_contracts import enrichr_fact_sources
            values.update(enrichr_fact_sources())
        if self._has_addgene() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.addgene_received_fields import addgene_sequence_fact_sources
            values.update(addgene_sequence_fact_sources())
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_return_views import fluorescence_fact_sources
            values.update(fluorescence_fact_sources())
        if self.native_expression_nmf_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import expression_nmf_fact_sources
            values.update(expression_nmf_fact_sources())
        if self.atac_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.atac_received_fact_contracts import atac_fact_sources
            values.update(atac_fact_sources())
        if self.native_chromatin_interaction_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_received_fact_contracts import chromatin_fact_sources
            values.update(chromatin_fact_sources())
        if self.native_genomic_overlap_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_received_fact_contracts import genomic_overlap_fact_sources
            values.update(genomic_overlap_fact_sources())
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_result_views import protein_structure_fact_sources
            values.update(protein_structure_fact_sources())
        if self.rna_structure_comparison_results is not None and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
            values.update(rna_comparison_fact_sources())
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
            values.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self._has_rfam() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import rfam_fact_sources
            values.update(rfam_fact_sources())
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import native_infernal_fact_sources
            values.update(native_infernal_fact_sources())
            values['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values())):
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            values.update(TerminalExecutionEpisodes.fact_sources(None, role))
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database or RNA attempts for partial-output acquisition; failed attempts do not establish a successful native endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER/Infernal/RNA producer bundles retain original attempt outputs matched by digest and requested numerical facts. RNA source delivery alone grants no auxiliary artifacts or unrequested rows.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. RNA results mean complete requested original-bundle or retained-sheet delivery, including specific unavailable values; this does not assert native success. Yielding alone is false.'}
        from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import ORIGIN as hmmer_origin
        from gene_annotation_episode.episodic_workflow.root.a107.native_fluorescence_results import ORIGIN as fluorescence_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin, fluorescence_origin]
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.flux_balance_native_result_acquisition import ORIGIN as fba_origin
            origins.append(fba_origin)
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_results import ORIGIN as nmf_origin
            origins.append(nmf_origin)
        if self.atac_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.atac_native_result_acquisition import ORIGIN as atac_origin, SAVED_ORIGIN as saved_atac_origin
            origins.extend([atac_origin, saved_atac_origin])
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. ATAC records distinguish captured original occurrences from received sheet/table bundles and do not imply native success. No qualified retained data yields null. RNA failed native attempts and saved-sheet recalculations return null even when qualified delivery completes.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        from gene_annotation_episode.episodic_workflow.root.a107.blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        if role == 'results' and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            values[BLAST_GRADED_RETURN_SOURCE] = {'type': 'array', 'meaning': 'Retained output of the original BLAST database grader. Each artifact contains the full grader sheet and probabilities; query and any parent database constraint are checked against the original submission and native report.', 'report_schema': deepcopy(BLAST_GRADED_RETURN_SCHEMA)}
        return values

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_rfam(self):
        return self.api_execution is not None and any((service.service == 'rfam_batch' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    def _has_enrichr(self):
        return self.api_execution is not None and any((service.service == 'enrichr' for service in self.api_execution.services.values()))

    def _has_addgene(self):
        return self.api_execution is not None and any((service.service == 'sequence_support' for service in self.api_execution.services.values()))

    @staticmethod
    def _blast_reference_source():
        return {'type': 'array', 'meaning': 'Native paired BLAST source, observation and reference records actually returned through this boundary. References alone do not deliver unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': 'execution_blast_pairwise_result_refs'}}

    @staticmethod
    def _infernal_reference_source():
        return {'type': 'array', 'meaning': 'Infernal source, observation and model references actually returned through this episode boundary. These references alone do not deliver unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': 'execution_infernal_result_refs'}}

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import homology_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_phylogeny_returns import phylogeny_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_alignment_returns import alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_genome_alignment_returns import genome_alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_proteome_returns import proteome_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_comparative_systems_returns import comparative_systems_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_fastqutils_returns import fastqutils_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_application_returns import application_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **alignment_fact_sources(), **genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(), **fastqutils_fact_sources(), **application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

    def _closed_credit_carrier(self, context):
        """Validate closed runtime metadata without reading scientific payloads."""
        from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import EpisodeReturnRecords
        EpisodeReturnRecords(self.store, self.run_id, failure_prefix='execution_closed_credit_').authenticate(context)
        row = self.store.db.execute('SELECT state,completion,archive FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if context.role not in ROLES or row is None or row['state'] != 'yielded' or (row['completion'] is None) or (row['archive'] is None):
            raise ValueError('execution_closed_credit_carrier_conflict')
        completion, archive = (json.loads(row['completion']), json.loads(row['archive']))
        if type(completion) is not dict or set(completion) != {'actions', 'ended_by'} or type(completion['actions']) is not int or (completion['actions'] < 0) or (type(completion['ended_by']) is not str) or (not completion['ended_by']) or (type(archive) is not dict) or (set(archive) != {'file', 'sha256', 'index_sha256'}) or (type(archive['file']) is not str) or (len(archive['file']) != 69) or (not archive['file'].endswith('.json')) or any((character not in '0123456789abcdef' for character in archive['file'][:-5])) or any((type(archive[key]) is not str or len(archive[key]) != 64 or any((character not in '0123456789abcdef' for character in archive[key])) for key in ('sha256', 'index_sha256'))):
            raise ValueError('execution_closed_credit_carrier_conflict')
        observations = list(self.store.db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)))
        if [row['unit_index'] for row in observations] != list(range(completion['actions'])):
            raise ValueError('execution_closed_credit_history_conflict')
        return {'completion': completion, 'archive': archive, 'history_sha256': digest([list(row) for row in observations])}

    def _closed_credit_receipts(self, context, *, through=None):
        """Pin the original receipt prefix; later delivery never reprices it."""
        from gene_annotation_episode.episodic_workflow.root.a107.episode_receipts import EpisodeReceipts
        from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import _same
        db = self.store.db
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone() is None or db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone() is None:
            return (None, None, None)
        if through is None:
            through = db.execute('SELECT coalesce(max(receipt_index),0) FROM runtime_record_receipts WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()[0]
        if type(through) is not int or through < 0:
            raise ValueError('execution_closed_credit_receipt_conflict')
        own_through, current, seen, manifests, rows = (through, context.episode_id, set(), [], [])
        while current is not None:
            if current in seen:
                raise ValueError('execution_closed_credit_receipt_conflict')
            seen.add(current)
            manifest = EpisodeReceipts.read_manifest(db, self.run_id, current)
            recorded = db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, current)).fetchone()
            if recorded is None or not _same(json.loads(recorded['request'])['message'].get('knowledge_inheritance'), manifest):
                raise ValueError('execution_closed_credit_receipt_conflict')
            manifests.append({'episode_id': current, 'manifest': manifest})
            rows.extend((list(row) for row in db.execute('SELECT receipt_index,episode_id,record_ref,receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND (? IS NULL OR receipt_index<=?) ORDER BY receipt_index', (self.run_id, current, through, through))))
            current, through = (manifest['parent_episode_id'], manifest['through_receipt_index'])
        known = sorted({row[2] for row in rows})
        initial = sorted({row[2] for row in rows if row[1] != context.episode_id or row[3] == 'initial'})
        return ({'through_receipt_index': own_through, 'sha256': digest({'manifests': manifests, 'rows': rows})}, known, initial)

    def _closed_credit_value(self, view):
        if type(view) is not dict or type(view.get('credit')) not in (int, float) or (not math.isfinite(view['credit'])):
            raise ValueError('execution_closed_credit_view_conflict')

    def _closed_credit_facts(self, context, completion_snapshot):
        """Capture the already projected view once, inside the closing facts."""
        if completion_snapshot is None:
            return {}
        capture = completion_snapshot.get('operational_credit_snapshot')
        completion = completion_snapshot.get('completion')
        if capture is None or completion is None:
            return {}
        if self.store.db.execute('SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone() is not None:
            return {}
        if type(capture) is not dict or set(capture) != {'view', 'selection'}:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        capture = json.loads(canonical(plain(capture)))
        carrier = self._closed_credit_carrier(context)
        if completion.get('ended_by') != carrier['completion']['ended_by'] or type(completion.get('units_consumed')) is not int or completion['units_consumed'] != carrier['completion']['actions']:
            raise ValueError('execution_closed_credit_carrier_conflict')
        selection = self._selection(context, capture['selection'])
        prefix, known, initial = self._closed_credit_receipts(context)
        if prefix is not None and (selection['known_record_refs'] != known or selection['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        self._closed_credit_value(capture['view'])
        return {_CLOSED_CREDIT: {'version': _CLOSED_CREDIT, 'context_sha256': digest(context.as_record()), 'binding_sha256': digest(self.as_record()), 'selection': selection, 'receipt_prefix': prefix, 'completion_sha256': digest(carrier['completion']), 'archive_sha256': digest(carrier['archive']), 'history_sha256': carrier['history_sha256'], 'view': capture['view'], 'view_sha256': digest(capture['view'])}}

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.flux_balance_received_fact_contracts import fba_fact_sources
            native_empty.update({source: [] for source in fba_fact_sources()})
            if self.native_flux_balance_results.applies(context):
                return {**native_empty, **self.native_flux_balance_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_return_views import FACT_SOURCES as FLUORESCENCE_SOURCES
        native_empty.update({source: [] for source in FLUORESCENCE_SOURCES})
        if self.native_fluorescence_results.applies(context):
            return {**native_empty, **self.native_fluorescence_results.facts(context)}
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_expression_nmf_results.applies(context):
                return {**native_empty, **self.native_expression_nmf_results.facts(context)}
        if self.atac_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.atac_received_fact_contracts import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.atac_results.applies(context):
                return {**native_empty, **self.atac_results.facts(context)}
        if self.native_chromatin_interaction_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_received_fact_contracts import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_chromatin_interaction_results.applies(context):
                return {**native_empty, **self.native_chromatin_interaction_results.facts(context)}
        if self.native_genomic_overlap_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.library.genomic_overlap_received_fact_contracts import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_genomic_overlap_results.applies(context):
                return {**native_empty, **self.native_genomic_overlap_results.facts(context)}
        from gene_annotation_episode.episodic_workflow.root.a107.protein_structure_result_views import protein_structure_fact_sources
        native_empty.update({source: [] for source in protein_structure_fact_sources()})
        if self.native_protein_structure_results.applies(context):
            return {**native_empty, **self.native_protein_structure_results.facts(context, verify_artifacts=False)}
        if self.rna_structure_comparison_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
            native_empty.update({source: [] for source in rna_comparison_fact_sources()})
            if self.rna_structure_comparison_results.applies(context):
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
                native_empty.update({source: [] for source in rna_structure_fact_sources()})
                return {**native_empty, **self.rna_structure_comparison_results.facts(context)}
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
            if self.native_rna_structure_results.applies(context):
                return {**native_empty, **self.native_rna_structure_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_infernal_preparation_results.applies(context):
                return {**native_empty, **self.native_infernal_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
            if self.native_infernal_results.applies(context):
                return {**native_empty, **self.native_infernal_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        if context.role == 'launch_api' or (context.role == 'results' and self._target(context)['resource_kind'] == 'api'):
            facts = self.api_execution.facts(context, completion_snapshot)
            if context.role == 'results':
                required = self._blast_target_requirement(self._target(context), context.scope)
                if required is not None:
                    facts[BLAST_GRADED_RETURN_SOURCE] = self._blast_grader_rows(context, facts['execution_result_refs'], required)
            return {**native_empty, **facts, 'execution_result_origin': None}
        extra = self._delegate(context).facts(self._practical_context(context), completion_snapshot) if context.role in {'launch_local', 'launch_hpc'} else {}
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            if context.role in {'launch_local', 'launch_hpc'}:
                for reference in extra['practical_receipt_refs']:
                    try:
                        target, _, returnable = read(reference, context.scope)
                        target = self._context_target(context, target)
                        if returnable:
                            handoffs[reference] = target
                    except ValueError:
                        pass
            completed = extra.get('practical_completed', False) if context.role in ROLE_KINDS else any((read(reference, context.scope)[1] for reference in handoffs)) if context.role == 'launch' else self._native_results_complete(context, list(results.values()))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)} if self._has_appservice() else {}), 'execution_blast_hsps': [], 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

    def received_form_references(self, context, form, schema, operation_key, *, _include_separate_api=True):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
        references = []
        native_references = set()
        references.extend(self.local_file_sources.admit_return(context, form, schema, operation_key))
        if self.native_flux_balance_returns is not None:
            references.extend(self.native_flux_balance_returns.record_admission(context, form, schema, operation_key))
        if self._has_uniprot():
            references.extend(self.api_execution.uniprot_returns.record_admission(context, form, schema, operation_key))
        if self._has_enrichr():
            admitted = self.api_execution.enrichr_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        if self._has_addgene():
            admitted = self.api_execution.addgene_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        if plain(schema).get('properties') is not None:
            references.extend(self.native_fluorescence_returns.record_admission(context, form, schema, operation_key))
        if self.native_expression_nmf_returns is not None:
            references.extend(self.native_expression_nmf_returns.record_admission(context, form, schema, operation_key))
        if self.atac_returns is not None:
            references.extend(self.atac_returns.record_admission(context, form, schema, operation_key))
        if self.native_chromatin_interaction_returns is not None:
            references.extend(self.native_chromatin_interaction_returns.record_admission(context, form, schema, operation_key))
        if self.native_genomic_overlap_returns is not None:
            references.extend(self.native_genomic_overlap_returns.record_admission(context, form, schema, operation_key))
        if self.rna_structure_comparison_returns is not None:
            references.extend(self.rna_structure_comparison_returns.record_admission(context, form, schema, operation_key))
        if self._has_rfam():
            references.extend(self.api_execution.rfam_returns.record_admission(context, form, schema, operation_key))
        admitted = self.native_blast_masking_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        admitted = self.native_blast_utility_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        admitted = self.native_protein_structure_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        if self.native_rna_structure_returns is not None:
            admitted = self.native_rna_structure_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_standard_database_returns is not None:
            admitted = self.native_blast_standard_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_database_returns is not None:
            admitted = self.native_blast_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_hmmer_preparation_returns is not None:
            admitted = self.native_hmmer_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_preparation_returns is not None:
            admitted = self.native_infernal_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_returns is not None:
            admitted = self.native_blast_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_returns is not None:
            admitted = self.native_infernal_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.api_execution is not None:
            if _include_separate_api:
                received_form_references_branch_0(self, context, form, schema, operation_key, references)
            if _include_separate_api:
                received_form_references_branch_1(self, context, form, schema, operation_key, references)
            references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.phylogeny_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.genome_alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.comparative_systems_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.fastqutils_returns.record_admission(context, form, schema, operation_key))
            admitted = self.api_execution.application_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') in FAMILY_SOURCES.values():
                for row in form[name]:
                    for reference in [row['source_ref'], row['observation_ref'], *row['reference_refs']]:
                        if reference is None:
                            continue
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == 'execution_blast_hsps':
                for row in form[name]:
                    for field in ('hsp_ref', 'reference_ref'):
                        reference = row[field]
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == BLAST_GRADED_RETURN_SOURCE:
                for row in form[name]:
                    if not self.resolve(context, row['result_ref'], 'execution_result'):
                        raise ValueError('blast_grader_result_reference_unqualified')
                    references.append(row['result_ref'])
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs', 'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and (not self.resolve(context, reference, namespace)):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))

    def resolve(self, context, reference, namespace):
        try:
            fba = self._flux_balance_reference_access(context, reference, namespace)
            if fba is not None:
                return fba
            masking = self._masking_reference_access(context, reference, namespace)
            if masking is not None:
                return masking
            utility = self._utility_reference_access(context, reference, namespace)
            if utility is not None:
                return utility
            if self._has_uniprot():
                resolved = self.api_execution.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if self._has_enrichr():
                resolved = self.api_execution.enrichr_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.enrichr_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if self._has_addgene():
                resolved = self.api_execution.addgene_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.addgene_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            fluorescence = self._fluorescence_reference_access(context, reference, namespace)
            if fluorescence is not None:
                return fluorescence
            nmf = self._expression_nmf_reference_access(context, reference, namespace)
            if nmf is not None:
                return nmf
            atac = self._atac_reference_access(context, reference, namespace)
            if atac is not None:
                return atac
            chromatin = self._chromatin_reference_access(context, reference, namespace)
            if chromatin is not None:
                return chromatin
            overlap = self._genomic_overlap_reference_access(context, reference, namespace)
            if overlap is not None:
                return overlap
            access = self._protein_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if self.rna_structure_comparison_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
                if namespace in COMPARISON_NAMESPACES:
                    return self.rna_structure_comparison_results.resolve(context, reference, namespace) if context.role == 'results' else self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
                access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_rna_structure_results is not None:
                access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import IDENTIFIER_NAMESPACES as RNA_NAMESPACES
                if namespace in RNA_NAMESPACES:
                    return self.native_rna_structure_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if self.native_rna_structure_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_standard_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return self.native_hmmer_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import IDENTIFIER_NAMESPACES as PREPARATION_NAMESPACES
                if namespace in PREPARATION_NAMESPACES:
                    return self.native_infernal_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_rfam():
                from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import IDENTIFIER_NAMESPACES as RFAM_NAMESPACES
                if namespace in RFAM_NAMESPACES:
                    return self.api_execution.rfam_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                    return self.native_blast_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_returns.resolve_received(context, reference, namespace)
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import IDENTIFIER_NAMESPACES as INFERNAL_NAMESPACES
                if namespace in INFERNAL_NAMESPACES:
                    return self.native_infernal_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_infernal_returns.resolve_received(context, reference, namespace)
                if self.native_infernal_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'partner_presence_evidence'}:
                    resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return self.api_execution.alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return self.api_execution.genome_alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return self.api_execution.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return self.api_execution.fastqutils_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
                if namespace in APPLICATION_NAMESPACES:
                    return self.api_execution.application_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.application_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
            if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
                return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
            if self.native_hmmer_results.resolve(context, reference, namespace):
                return True
            source = self.store.get(reference)
            if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
                return namespace in {None, 'source'} and self.local_file_sources.read_source(reference, context.scope) is not None
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                    return False
                if namespace not in {None, 'source', 'execution_result'}:
                    return False
                body = self._read_result(reference, context.scope)
                return bool(body['windows']) if namespace == 'execution_result' else True
            if namespace in {None, 'source', 'execution_handoff'}:
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    return namespace != 'execution_handoff' or self.job_progress_provider.targets.returnable_handoff(target)
                except ValueError:
                    if namespace == 'execution_handoff':
                        return False
            if PracticalReceiptInformation(self.store, self.run_id).resolve(context, reference, namespace):
                return True
            if self.api_execution is not None and self.api_execution.resolve(context, reference, namespace):
                return True
            if self.native_hmmer_preparation_results is not None:
                access = self.native_hmmer_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_infernal_preparation_results is not None:
                access = self.native_infernal_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if source.get('provider') == 'episode.practical_receipt' or (self.api_execution is not None and self.api_execution.is_handoff_source(reference)):
                return False
            if self.services is not None:
                from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

    def validate_report(self, context, form, original_schema):
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, original_schema)
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        if self._has_enrichr():
            from gene_annotation_episode.episodic_workflow.root.a107.library.enrichr_received_fields import OWN_WITNESSES, requested_enrichr_fields
            host = self.api_execution.enrichr_returns
            if requested_enrichr_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if closed is not None and OWN_WITNESSES in closed['facts'] and host._successful_closed(context):
                full_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
                host.facts_for_closure(context, full_schema)
                frozen_facts = closed['facts']
        if self._has_addgene():
            from gene_annotation_episode.episodic_workflow.root.a107.library.addgene_received_fields import OWN_BINDINGS, requested_addgene_fields
            host = self.api_execution.addgene_returns
            if requested_addgene_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if closed is not None and OWN_BINDINGS in closed['facts']:
                full_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
                if OWN_BINDINGS not in host.facts_for_closure(context, full_schema):
                    raise ValueError('addgene_sequence_return_original_schema_conflict')
                frozen_facts = closed['facts']
        if plain(original_schema).get('properties') is not None:
            self.native_fluorescence_returns.validate_received_report(context, form, original_schema)
        if self.native_expression_nmf_returns is not None:
            self.native_expression_nmf_returns.validate_received_report(context, form, original_schema)
        if self.atac_returns is not None:
            self.atac_returns.validate_received_report(context, form, original_schema)
        if self.native_chromatin_interaction_returns is not None:
            self.native_chromatin_interaction_returns.validate_received_report(context, form, original_schema)
        if self.native_genomic_overlap_returns is not None:
            self.native_genomic_overlap_returns.validate_received_report(context, form, original_schema)
        self.native_protein_structure_returns.validate_received_report(context, form, original_schema)
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return False
        if self.native_blast_masking_results.applies(context):
            return False
        if self.native_blast_utility_results.applies(context):
            return False
        if self.native_fluorescence_results.applies(context):
            return False
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return False
        if self.atac_results is not None and self.atac_results.applies(context):
            return False
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return False
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return False
        if self.native_protein_structure_results.applies(context):
            return False
        if is_native_rna_structure_target(self._target(context)):
            return False
        if is_standard_blast_database_target(self._target(context)):
            return False
        if is_native_blast_database_target(self._target(context)):
            return False
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max((window['size_bytes'] for window in windows))
            if length is not None:
                end = min(end, start + length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset'] + window['returned_bytes'])
            if cursor < end:
                return False
        return True
from ..received_api_information.original_received_branches import _forwards_bvbrc_reports, _forwards_minhash_reports, received_report_sources_branch_0, received_report_sources_branch_1, received_report_facts_branch_0, received_report_facts_branch_1, resolve_received_reference_branch_0, resolve_received_reference_branch_1, validate_received_report_branch_0, validate_received_report_branch_1, received_form_references_branch_0, received_form_references_branch_1, initial_minhash_information_branch_0
