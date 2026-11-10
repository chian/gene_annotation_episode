"""One explicit launch family for the shared episode loop.

The binding routes a selected concrete assignment. Resource operations and
result reads contain no model, resource selection or investigation loop.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .communication import plain, validate_form
from .domain import identity
from .execution_contracts import canonical, checked, digest, obj
from .launch_instructions import SELECTION_SCHEMA, retain_inherited_selection
from .practical_execution_operations import confined
from .practical_execution_records import (ASSIGNMENT_SCHEMA, validate_assignment,
                                         validate_completion_proof, GENERIC_REQUESTED_JOB_SCHEMA)
from .practical_execution_state import _immutable, _read
from .practical_receipt_information import PracticalReceiptInformation
from .terminal_execution_episodes import TerminalExecutionEpisodes, operation_catalog
from .resource_records import INPUT_VERSION_SCHEMA
from .native_hmmer_acquisition import is_native_hmmer_target
from .native_blast_acquisition import is_native_blast_target
from .native_blast_masking_acquisition import is_native_blast_masking_target
from .native_blast_utility_acquisition import is_native_blast_utility_target
from .native_blast_database_acquisition import is_native_blast_database_target
from .native_blast_standard_database_acquisition import is_standard_blast_database_target
from .native_infernal_acquisition import is_native_infernal_target
from .native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from .native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from .native_rna_structure_acquisition import is_native_rna_structure_target
from .native_protein_structure_acquisition import is_native_protein_structure_target
from .local_file_capture_results import (LocalFileSourceResults,
    SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA,
    MACS2_SELECTOR_SCHEMA as MACS2_FILE_SOURCE_SELECTOR_SCHEMA,
    MACS2_SELECTOR_VERSION as MACS2_FILE_SOURCE_SELECTOR_VERSION,
    LUMPY_SELECTOR_SCHEMA as LUMPY_FILE_SOURCE_SELECTOR_SCHEMA,
    LUMPY_SELECTOR_VERSION as LUMPY_FILE_SOURCE_SELECTOR_VERSION,
    RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION,
    FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector,
    is_macs2_file_source_selector, is_lumpy_file_source_selector)


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
FILE_LIMIT = {**LIMIT, 'maximum': 1024*1024}
NATIVE_RESULT_ORIGIN = {
    'content_location': 'current_resource_filesystem',
    'attempt_output_version': 'unverified',
    'window_consistency': 'separate_reads_no_atomic_file_snapshot',
    'completion_basis': 'requested_acquisition_and_observed_successful_attempt',
}
NATIVE_RESULT_ORIGIN_SCHEMA = obj({key: {'type': 'string', 'enum': [value]}
                                  for key, value in NATIVE_RESULT_ORIGIN.items()})
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT,
                      'selector': {'type': 'object'}})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1,
    'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])


def launch_operation_catalog():
    """Declared launch operations, without a target/resource observation."""
    return [{'name': 'execution.capabilities', 'description':
        'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.',
        'input_schema': obj({})}]


def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [
        {'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.',
         'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description':
            'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})},
        {'name': 'execution.results.read', 'description':
            'Acquire one selected bounded byte window within the original requested paths and interval.',
         'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]


def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
        'changed_record_refs': list(references), 'result': result,
        'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


class ExecutionEpisodes:
    roles = ROLES
    entry_roles = ('launch', 'results')
    replaces_default_instructions = True

    def __init__(self, services, *, store, directory, run_id, resources, initial_information,
                 tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles,
                 require_private_yield=False, results_yield_profiles=None,
                 task_yield_profiles=None):
        self.services, self.store, self.directory = services, store, Path(directory)
        self.run_id, self.tool_registry = run_id, tool_registry
        self.resources = json.loads(canonical(resources))
        self.initial_information = json.loads(canonical(initial_information))
        if (not isinstance(self.resources, dict) or not self.resources
                or any(not isinstance(key, str) or not key or not isinstance(value, dict)
                    or value.get('kind') not in KINDS for key, value in self.resources.items())):
            raise ValueError('explicit_execution_resources_required')
        if (not isinstance(self.initial_information, dict)
                or not set(self.initial_information) <= set(self.resources)):
            raise ValueError('initial_inventory_resource_not_bound')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if (type(log_window_bytes) is not int or log_window_bytes < 1
                or not isinstance(log_roles, (tuple, list))
                or any(not isinstance(role, str) or not role for role in log_roles)):
            raise ValueError('explicit_execution_log_selection_required')
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        self.log_window_bytes, self.log_roles = log_window_bytes, tuple(log_roles)
        if type(require_private_yield) is not bool:
            raise TypeError('execution_private_yield_binding_requires_boolean')
        self.private_yield_binding = require_private_yield
        profiles = {} if results_yield_profiles is None else plain(results_yield_profiles)
        if not isinstance(profiles, dict) or set(profiles) - {
                'native_unbounded_local', 'native_unbounded_hpc'}:
            raise ValueError('explicit_results_yield_profiles_invalid')
        from .numerical import YieldController, YieldParameters
        for key, binding in profiles.items():
            if (not isinstance(binding, dict) or set(binding) != {'cutoff', 'parameters'}
                    or not isinstance(binding['parameters'], dict)
                    or type(binding['cutoff']) not in (int, float)
                    or not math.isfinite(binding['cutoff']) or binding['cutoff'] <= 0):
                raise ValueError('explicit_results_yield_profile_invalid:' + key)
            YieldController('configuration', 0., binding['cutoff'],
                YieldParameters(**binding['parameters']))
        self.results_yield_profiles = profiles
        task_profiles = {} if task_yield_profiles is None else plain(task_yield_profiles)
        if (not isinstance(task_profiles, dict) or any(
                not isinstance(key, str) or not key or not isinstance(binding, dict)
                or set(binding) != {'cutoff', 'parameters'}
                or not isinstance(binding['parameters'], dict)
                or type(binding['cutoff']) not in (int, float)
                or not math.isfinite(binding['cutoff']) or binding['cutoff'] <= 0
                for key, binding in task_profiles.items())):
            raise ValueError('explicit_execution_task_yield_profiles_invalid')
        for binding in task_profiles.values():
            YieldController('configuration', 0., binding['cutoff'],
                YieldParameters(**binding['parameters']))
        self.task_yield_profiles = task_profiles
        self._practical = {}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            if 'native_flux_balance' in configuration:
                from .native_flux_balance_bindings import validate_flux_balance_bindings
                if kind != 'local':
                    raise ValueError('native_flux_balance_resource_execution_binding_unfinished:' + kind)
                validate_flux_balance_bindings(configuration['native_flux_balance'])
            if 'native_fluorescence' in configuration:
                from .native_fluorescence_contracts import validate_fluorescence_bindings
                if kind != 'local':
                    raise ValueError('native_fluorescence_resource_execution_binding_unfinished:' + kind)
                validate_fluorescence_bindings(configuration['native_fluorescence'])
            if 'native_expression_nmf' in configuration:
                from .native_expression_nmf_contracts import validate_expression_nmf_bindings
                if kind != 'local':
                    raise ValueError('native_expression_nmf_resource_execution_binding_unfinished:' + kind)
                validate_expression_nmf_bindings(configuration['native_expression_nmf'])
            if 'native_macs2_peak' in configuration:
                from .native_macs2_peak_execution import validate_macs2_peak_bindings
                if kind != 'local':
                    raise ValueError('native_macs2_peak_resource_execution_binding_unfinished:' + kind)
                validate_macs2_peak_bindings(configuration['native_macs2_peak'])
            if 'native_lumpy' in configuration:
                from .native_lumpy_execution import validate_lumpy_bindings
                if kind != 'local':
                    raise ValueError('native_lumpy_resource_execution_binding_unfinished:' + kind)
                validate_lumpy_bindings(configuration['native_lumpy'])
            if 'native_homer_motif' in configuration:
                from .native_homer_execution import validate_homer_bindings
                if kind != 'local':
                    raise ValueError('native_homer_resource_execution_binding_unfinished:' + kind)
                validate_homer_bindings(configuration['native_homer_motif'])
            if 'native_atac_differential' in configuration:
                from .native_atac_differential_contracts import validate_atac_bindings
                if kind != 'local':
                    raise ValueError('native_atac_resource_execution_binding_unfinished:' + kind)
                validate_atac_bindings(configuration['native_atac_differential'])
            if 'native_chromatin_interactions' in configuration:
                from .native_chromatin_interaction_contracts import validate_chromatin_bindings
                if kind != 'local':
                    raise ValueError('native_chromatin_resource_execution_binding_unfinished:' + kind)
                validate_chromatin_bindings(configuration['native_chromatin_interactions'])
            if 'native_genomic_overlap' in configuration:
                from .native_genomic_overlap_contracts import validate_genomic_overlap_bindings
                if kind != 'local':
                    raise ValueError('native_genomic_overlap_resource_execution_binding_unfinished:' + kind)
                validate_genomic_overlap_bindings(configuration['native_genomic_overlap'])
            if 'native_protein_structure' in configuration:
                from .native_protein_structure_contracts import validate_protein_structure_bindings
                if kind != 'local':
                    raise ValueError('native_protein_structure_resource_execution_binding_unfinished:' + kind)
                validate_protein_structure_bindings(configuration['native_protein_structure'])
            if 'native_molecular_sequence' in configuration:
                from .molecular_sequence_tools import validate_native_molecular_sequence_bindings
                if kind != 'local':
                    raise ValueError('native_molecular_sequence_resource_execution_binding_unfinished:' + kind)
                validate_native_molecular_sequence_bindings(configuration['native_molecular_sequence'])
            if 'native_rna_structure' in configuration:
                from .native_rna_structure_contracts import validate_rna_structure_bindings
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
                from .native_hmmer_tool_info import validate_native_hmmer_bindings
                validate_native_hmmer_bindings(configuration['native_hmmer'])
            if 'native_blast_masking' in configuration:
                from .native_blast_masking_tool_info import validate_native_blast_masking_bindings
                if kind != 'local':
                    raise ValueError('native_blast_masking_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_masking_bindings(configuration['native_blast_masking'])
            if 'native_blast_utility' in configuration:
                from .native_blast_utility_tool_info import validate_native_blast_utility_bindings
                if kind != 'local':
                    raise ValueError('native_blast_utility_resource_execution_binding_unfinished:' + kind)
                validate_native_blast_utility_bindings(configuration['native_blast_utility'])
            if 'native_blast' in configuration and kind != 'local':
                raise ValueError('native_blast_resource_execution_binding_unfinished:' + kind)
            if 'native_blast' in configuration:
                from .native_blast_tool_info import validate_native_blast_bindings
                validate_native_blast_bindings(configuration['native_blast'])
            if 'native_infernal' in configuration and kind != 'local':
                raise ValueError('native_infernal_resource_execution_binding_unfinished:' + kind)
            if 'native_infernal' in configuration:
                from .native_infernal_tool_info import validate_native_infernal_bindings
                validate_native_infernal_bindings(configuration['native_infernal'])
            if 'native_infernal_preparation' in configuration:
                from .native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_infernal_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])
            if 'native_hmmer_preparation' in configuration:
                from .native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_hmmer_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
            if kind != 'api':
                inventory = self.initial_information.get(resource_id)
                self._practical[resource_id] = TerminalExecutionEpisodes(services,
                    directory=self.directory, resources={kind: configuration}, store=store,
                    initial_information={} if inventory is None else {kind: inventory})
        from .api_service_execution import APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items()
                         if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store,
            run_id=run_id, directory=self.directory, configuration=api_resources,
            tool_registry=tool_registry, handoff_unit=handoff_unit,
            acquired_record_unit=acquired_record_unit,
            received_input_reader=getattr(services, 'read_received_molecular_input', None))
        from .execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id,
            directory=self.directory, resources=self.resources, api_execution=self.api_execution,
            log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        self.local_file_sources = LocalFileSourceResults(self)
        if services is not None:
            bind_peak_reader = getattr(tool_registry, 'bind_macs2_peak_capture_reader', None)
            if callable(bind_peak_reader):
                bind_peak_reader(self.run_id, self.read_macs2_peak_capture_selection)
        self.molecular_sequence_results = None
        if services is not None:
            from .molecular_sequence_results import MolecularSequenceResults
            self.molecular_sequence_results = MolecularSequenceResults(self)
            bind_molecular_results = getattr(tool_registry, 'bind_molecular_sequence_results', None)
            if callable(bind_molecular_results):
                bind_molecular_results(self.molecular_sequence_results)
            bind_execution_owner = getattr(tool_registry, 'bind_execution_owner', None)
            if callable(bind_execution_owner):
                bind_execution_owner(self)
        from .flux_balance_execution_inputs import FluxBalanceExecutionInputs
        self.flux_balance_inputs = FluxBalanceExecutionInputs(self)
        from .flux_balance_request_binding import FluxBalanceRequestBindings
        self.flux_balance_requests = FluxBalanceRequestBindings(self)
        from .macs2_peak_request_binding import Macs2PeakRequestBindings
        self.macs2_peak_requests = Macs2PeakRequestBindings(self)
        from .lumpy_request_binding import LumpyRequestBindings
        self.lumpy_requests = LumpyRequestBindings(self)
        for practical in self._practical.values():
            practical.flux_balance_input_reader = self.flux_balance_inputs.for_start
        from .native_protein_structure_results import NativeProteinStructureResults
        from .native_protein_structure_returns import NativeProteinStructureReturns
        self.native_protein_structure_results = NativeProteinStructureResults(self)
        self.native_protein_structure_returns = NativeProteinStructureReturns(self)
        # Pure receipt readers remain available after an original deployment is
        # removed. New operations are still limited by actual resource bindings.
        from .native_fluorescence_results import NativeFluorescenceResults
        from .fluorescence_returns import FluorescenceReturns
        self.native_fluorescence_results = NativeFluorescenceResults(self)
        self.native_fluorescence_returns = FluorescenceReturns(self)
        self.native_flux_balance_results = self.native_flux_balance_returns = None
        ordinary_fba = getattr(tool_registry, 'ordinary_flux_balance_backend', None)
        if (ordinary_fba is not None
                or any(configuration.get('native_flux_balance') for configuration in self.resources.values())):
            from .native_flux_balance_results import NativeFluxBalanceResults
            from .flux_balance_returns import FluxBalanceReturns
            self.native_flux_balance_results = NativeFluxBalanceResults(self)
            self.native_flux_balance_returns = FluxBalanceReturns(self, ordinary_backend=ordinary_fba)
        self.native_expression_nmf_results = self.native_expression_nmf_returns = None
        if any(configuration.get('native_expression_nmf') for configuration in self.resources.values()):
            from .native_expression_nmf_results import NativeExpressionNMFResults
            from .expression_nmf_returns import ExpressionNMFReturns
            self.native_expression_nmf_results = NativeExpressionNMFResults(self)
            self.native_expression_nmf_returns = ExpressionNMFReturns(self)
        self.atac_results = self.atac_returns = None
        if any(configuration.get('native_atac_differential') for configuration in self.resources.values()):
            from .native_atac_differential_results import NativeAtacDifferentialResults
            from .atac_differential_returns import AtacDifferentialReturns
            self.atac_results = NativeAtacDifferentialResults(self)
            self.atac_returns = AtacDifferentialReturns(self)
        self.native_chromatin_interaction_results = self.native_chromatin_interaction_returns = None
        if any(configuration.get('native_chromatin_interactions') for configuration in self.resources.values()):
            from .native_chromatin_interaction_results import NativeChromatinInteractionResults
            from .chromatin_interaction_returns import ChromatinInteractionReturns
            self.native_chromatin_interaction_results = NativeChromatinInteractionResults(self)
            self.native_chromatin_interaction_returns = ChromatinInteractionReturns(self)
        self.native_genomic_overlap_results = self.native_genomic_overlap_returns = None
        if any(configuration.get('native_genomic_overlap') for configuration in self.resources.values()):
            from .native_genomic_overlap_results import NativeGenomicOverlapResults
            from .genomic_overlap_returns import GenomicOverlapReturns
            self.native_genomic_overlap_results = NativeGenomicOverlapResults(self)
            self.native_genomic_overlap_returns = GenomicOverlapReturns(self)
        self.native_rna_structure_results = self.native_rna_structure_returns = None
        self.rna_structure_comparison_results = self.rna_structure_comparison_returns = None
        if any(configuration.get('native_rna_structure') for configuration in self.resources.values()):
            from .native_rna_structure_results import NativeRNAStructureResults
            from .native_rna_structure_returns import NativeRNAStructureReturns
            from .rna_structure_comparison_results import NativeRNAStructureComparisonResults
            from .rna_structure_comparison_returns import RNAStructureComparisonReturns
            self.native_rna_structure_results = NativeRNAStructureResults(self)
            self.native_rna_structure_returns = NativeRNAStructureReturns(self)
            self.rna_structure_comparison_results = NativeRNAStructureComparisonResults(self)
            self.rna_structure_comparison_returns = RNAStructureComparisonReturns(self)
        from .native_hmmer_results import NativeHMMERResults
        self.native_hmmer_results = NativeHMMERResults(self)
        # Original received facts remain readable after a deployment is removed.
        # New selected work is restricted to configured local bindings.
        from .native_blast_masking_results import NativeBLASTMaskingResults
        from .native_blast_masking_returns import NativeBLASTMaskingReturns
        self.native_blast_masking_results = NativeBLASTMaskingResults(self)
        self.native_blast_masking_returns = NativeBLASTMaskingReturns(self)
        from .native_blast_utility_results import NativeBLASTUtilityResults
        from .native_blast_utility_returns import NativeBLASTUtilityReturns
        self.native_blast_utility_results = NativeBLASTUtilityResults(self)
        self.native_blast_utility_returns = NativeBLASTUtilityReturns(self)
        self.native_blast_results = self.native_blast_returns = None
        self.native_blast_standard_database_results = self.native_blast_standard_database_returns = None
        if any(configuration.get('native_blast_standard_database') for configuration in self.resources.values()):
            from .native_blast_standard_database_results import StandardBLASTDatabaseResults
            from .native_blast_standard_database_returns import StandardBLASTDatabaseReturns
            self.native_blast_standard_database_results = StandardBLASTDatabaseResults(self)
            self.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(self)
        self.native_blast_database_results = self.native_blast_database_returns = None
        if any(configuration.get('native_blast_database') for configuration in self.resources.values()):
            from .native_blast_database_results import NativeBLASTDatabaseResults
            from .native_blast_database_returns import NativeBLASTDatabaseReturns
            self.native_blast_database_results = NativeBLASTDatabaseResults(self)
            self.native_blast_database_returns = NativeBLASTDatabaseReturns(self)
        if any(configuration.get('native_blast') for configuration in self.resources.values()):
            from .native_blast_results import NativeBLASTResults
            from .native_blast_returns import NativeBLASTReturns
            self.native_blast_results = NativeBLASTResults(self)
            self.native_blast_returns = NativeBLASTReturns(self)
        self.native_infernal_results = self.native_infernal_returns = None
        if any(configuration.get('native_infernal') for configuration in self.resources.values()):
            from .native_infernal_results import NativeInfernalResults
            from .native_infernal_returns import NativeInfernalReturns
            self.native_infernal_results = NativeInfernalResults(self)
            self.native_infernal_returns = NativeInfernalReturns(self)
        self.native_infernal_preparation_results = self.native_infernal_preparation_returns = None
        if any(configuration.get('native_infernal_preparation') for configuration in self.resources.values()):
            from .native_infernal_preparation_results import NativeInfernalPreparationResults
            from .native_infernal_preparation_returns import NativeInfernalPreparationReturns
            self.native_infernal_preparation_results = NativeInfernalPreparationResults(self)
            self.native_infernal_preparation_returns = NativeInfernalPreparationReturns(self)
        self.native_hmmer_preparation_results = self.native_hmmer_preparation_returns = None
        if any(configuration.get('native_hmmer_preparation') for configuration in self.resources.values()):
            from .native_hmmer_preparation_results import NativeHmmerPreparationResults
            from .native_hmmer_preparation_returns import NativeHmmerPreparationReturns
            self.native_hmmer_preparation_results = NativeHmmerPreparationResults(self)
            self.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(self)

    @classmethod
    def retained_protein_structure_reader(cls, store, *, run_id, directory):
        """Construct only this owner's unchanged legacy protein read authority.

        No resource, client, progress, registry or execution state is created.
        The caller supplies metadata sealed from the actual original owner;
        original receipts and typed delivery remain authoritative on every read.
        """
        from .state import Store
        if (not isinstance(store, Store) or type(run_id) is not str or not run_id
                or not isinstance(directory, (str, Path))):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        value = str(directory)
        path = Path(value)
        if (not value or '\0' in value or not path.is_absolute()
                or '..' in path.parts or value != str(path)):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        if store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None:
            raise ValueError('protein_structure_retained_reader_run_missing')
        owner = cls.__new__(cls)
        owner.store, owner.run_id, owner.directory = store, run_id, path
        from .native_protein_structure_results import NativeProteinStructureResults
        from .native_protein_structure_returns import NativeProteinStructureReturns
        owner.native_protein_structure_results = NativeProteinStructureResults(owner)
        owner.native_protein_structure_returns = NativeProteinStructureReturns(owner)
        return owner.native_protein_structure_returns

    def as_record(self):
        return {'binding_id': 'execution_episodes', 'version': VERSION, 'configuration': {
            'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information),
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles),
            **({'require_private_yield': True} if self.private_yield_binding else {}),
            **({'results_yield_profiles': deepcopy(self.results_yield_profiles)}
               if self.results_yield_profiles else {}),
            **({'task_yield_profiles': deepcopy(self.task_yield_profiles)}
               if self.task_yield_profiles else {})}}

    @staticmethod
    def _request_yield_class(request):
        """Classify the original execution request without generated IDs."""
        request = plain(request)
        version = request.get('version')
        if version != 'practical_assignment_v1':
            if version in ('api_execution_assignment_v1', 'api_service_assignment_v1'):
                parts = ['api', request.get('service', 'unknown')]
                for field in ('algorithm', 'database'):
                    if field in request:
                        parts.append(request[field])
                return '_'.join(parts) + '_handoff'
            return 'compact_' + str(version)
        requested = request['requested_job']
        native = sorted(key for key in requested if key.startswith('native_'))
        parts = ['practical', request['resource_kind']]
        parts.extend(native)
        parts.append({'usable_handoff': 'handoff',
            'completed_job_outputs': 'outputs'}[request['endpoint']])
        return '_'.join(parts)

    def _task_yield_profile(self, key):
        binding = self.task_yield_profiles.get(key)
        if binding is None:
            raise ValueError('execution_original_task_yield_profile_required:' + key)
        return binding

    def yield_controller(self, context, initial_credit, epoch):
        """Choose only this admitted execution task's own yield binding."""
        self.credit_kind(context.role)
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        if context.role == 'launch':
            return self._launch_yield_controller(context, initial_credit, epoch)
        if context.role == 'launch_api':
            return self._launch_api_yield_controller(context, initial_credit, epoch)
        if context.role == 'launch_local':
            return self._launch_local_yield_controller(context, initial_credit, epoch)
        if context.role == 'launch_hpc':
            return self._launch_hpc_yield_controller(context, initial_credit, epoch)
        if context.role == 'results':
            return self._results_yield_controller(context, initial_credit, epoch)
        raise ValueError('unknown_execution_episode_role:' + context.role)

    def _launch_yield_controller(self, context, initial_credit, epoch):
        """Cap one next handoff by original request slots still uncredited."""
        from .numerical import (BoundedYieldController, NumericBand, YieldController,
            YieldEstimate, YieldParameters)
        assignment = plain(context.assignment)
        if 'requests' not in assignment:
            raise ValueError('launch_original_request_map_required')
        original = self._launch(assignment, scope=context.scope)
        eligible = {resource_id for resource_id in original['requests']
            if self._permitted(original, resource_id)}
        selected, handoffs, _ = self._received(context)
        initial = set(selected['initial_known_record_refs'])
        already_received = {target['resource_id'] for reference, target in handoffs.items()
            if reference in initial and self.job_progress_provider.targets.usable_handoff(target)}
        remaining = len(eligible - already_received) * self.handoff_unit
        if remaining:
            classes = sorted(self._request_yield_class(original['requests'][resource_id])
                for resource_id in eligible)
            profile = self._task_yield_profile('launch:' + '+'.join(classes))
            return BoundedYieldController(epoch, initial_credit, profile['cutoff'], remaining,
                YieldParameters(**profile['parameters']))
        if initial_credit != 0:
            raise ValueError('launch_no_uncredited_requests_but_nonzero_initial_credit')
        def no_remaining_requests(history, parameters, contexts):
            if any(value != 0 for value in history):
                raise ValueError('launch_credit_without_original_uncredited_request')
            return YieldEstimate(len(history), NumericBand.exact(0), parameters,
                {'remaining_original_request_credit': 0., 'original_request_count': len(eligible)},
                estimator_binding={'version': 'launch_original_request_exhaustion_v1',
                    'forecast': 'exact_zero_when_every_eligible_original_request_was_in_initial_handoffs'})
        return YieldController(epoch, initial_credit, 0., YieldParameters(),
            estimate_with_context=no_remaining_requests)

    def _launch_api_yield_controller(self, context, initial_credit, epoch):
        from .numerical import YieldController, YieldParameters
        from .practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_api:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'],
            YieldParameters(**profile['parameters']),
            estimate_with_context=PracticalYieldEstimator(
                lambda proof: self.verify_completion(context, proof)))

    def _launch_local_yield_controller(self, context, initial_credit, epoch):
        from .numerical import YieldController, YieldParameters
        from .practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_local:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'],
            YieldParameters(**profile['parameters']),
            estimate_with_context=PracticalYieldEstimator(
                lambda proof: self.verify_completion(context, proof)))

    def _launch_hpc_yield_controller(self, context, initial_credit, epoch):
        from .numerical import YieldController, YieldParameters
        from .practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_hpc:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'],
            YieldParameters(**profile['parameters']),
            estimate_with_context=PracticalYieldEstimator(
                lambda proof: self.verify_completion(context, proof)))

    def _results_yield_controller(self, context, initial_credit, epoch):
        from .numerical import (NumericBand, YieldController, YieldEstimate,
            YieldParameters, estimate_bounded_credit_yield)
        from .practical_yield import PracticalYieldEstimator
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = self._target(context)
        selector = self._selector(assignment, target)
        if target['resource_kind'] != 'api' and 'version' not in selector:
            requested = self._windows(selector)
            if not requested:
                raise ValueError('results_original_selector_has_no_requested_bytes')
            if any(length is None for _, length in requested.values()):
                key = 'native_unbounded_' + target['resource_kind']
                if key not in self.results_yield_profiles:
                    raise ValueError('results_original_task_yield_profile_required:' + key)
                profile = self.results_yield_profiles[key]
                return YieldController(epoch, initial_credit, profile['cutoff'],
                    YieldParameters(**profile['parameters']))
            profile = self._task_yield_profile('results:native_finite_' + target['resource_kind'])
            selected, _, results = self._received(context)
            initial = set(selected['initial_known_record_refs'])
            baseline = {ref: body for ref, body in results.items() if ref in initial}
            original_fraction = self._generic_result_selector_progress(context, baseline, set())
            remaining = self.acquired_record_unit * (1. - original_fraction)
            if remaining == 0 and initial_credit != 0:
                raise ValueError('results_no_uncredited_bytes_but_nonzero_initial_credit')
            endpoint = PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
            def finite_result_yield(history, parameters, contexts):
                if contexts and contexts[-1] and contexts[-1].get('practical_completion') is not None:
                    completed = endpoint(history, parameters, contexts)
                    if completed.diagnostics.get('fitting_scope') == 'verified_assignment_endpoint':
                        return completed
                if remaining == 0:
                    if any(value != 0 for value in history):
                        raise ValueError('results_credit_without_original_uncredited_bytes')
                    return YieldEstimate(len(history), NumericBand.exact(0), parameters,
                        {'remaining_original_selector_credit': 0.}, estimator_binding={
                            'version': 'finite_result_selector_exhaustion_v1',
                            'forecast': 'exact_zero_after_all_requested_byte_positions_credited'})
                return estimate_bounded_credit_yield(history, parameters, contexts=contexts,
                    initial_credit=initial_credit, maximum_credit=remaining)
            return YieldController(epoch, initial_credit, profile['cutoff'],
                YieldParameters(**profile['parameters']),
                estimate_with_context=finite_result_yield)
        if target['resource_kind'] == 'api':
            service = target.get('service') or target.get('assignment', {}).get('service')
            if not isinstance(service, str) or not service:
                raise ValueError('results_original_api_service_required_for_yield')
            key = 'results:api_' + service + ('_' + selector['version']
                if 'version' in selector else '')
        else:
            key = 'results:typed_' + target['resource_kind'] + '_' + selector['version']
        profile = self._task_yield_profile(key)
        return YieldController(epoch, initial_credit, profile['cutoff'],
            YieldParameters(**profile['parameters']),
            estimate_with_context=PracticalYieldEstimator(
                lambda proof: self.verify_completion(context, proof)))

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def child_roles(self, role):
        return tuple(ROLE_KINDS) if role == 'launch' else ()

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        if (parent is not None and parent.path[-1][0] == 'scientific_process'
                and getattr(self.services, 'annotation_task_required', lambda: False)()):
            if role == 'launch':
                return ('execution_handoff_refs',)
            if role == 'results':
                return ('execution_result_refs',)
        return ()

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id)
            if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = []
            if internal and self.resources[resource_id].get('native_flux_balance'):
                from .flux_balance_contracts import flux_balance_schema
                for binding in self.resources[resource_id]['native_flux_balance']:
                    alternatives.append({'allOf': [flux_balance_schema('FBARequestedJob'), {
                        'properties': {'native_flux_balance': {'properties': {
                            'operation': {'const': binding['operation']},
                            'mode': {'const': binding['mode']},
                            'software': {'const': deepcopy(binding['software'])},
                            'model_input': {'properties': {'format': {'enum': deepcopy(binding['model_formats'])}}}}}}}]})
            fluorescence = self.resources[resource_id].get('native_fluorescence', [])
            if fluorescence:
                from .native_fluorescence_tool_info import fluorescence_tool_contracts
                alternatives.extend(row['input_schema'] for row in fluorescence_tool_contracts(
                    fluorescence, resource_kind=kind, resource_id=resource_id))
            nmf = self.resources[resource_id].get('native_expression_nmf', [])
            if nmf:
                from .native_expression_nmf_tool_info import expression_nmf_tool_contracts
                alternatives.extend(row['input_schema'] for row in expression_nmf_tool_contracts(
                    nmf, resource_kind=kind, resource_id=resource_id))
            macs2_peak = self.resources[resource_id].get('native_macs2_peak', [])
            if macs2_peak and internal:
                from .native_macs2_peak_execution import macs2_peak_execution_schema
                alternatives.append(macs2_peak_execution_schema('RequestedJob', bindings=macs2_peak))
            lumpy = self.resources[resource_id].get('native_lumpy', [])
            if lumpy and internal:
                from .native_lumpy_execution import lumpy_execution_schema
                alternatives.append(lumpy_execution_schema('RequestedJob', bindings=lumpy))
            atac = self.resources[resource_id].get('native_atac_differential', [])
            if atac:
                from .native_atac_differential_tool_info import atac_tool_contracts
                alternatives.extend(row['input_schema'] for row in atac_tool_contracts(
                    atac, resource_kind=kind, resource_id=resource_id))
            chromatin = self.resources[resource_id].get('native_chromatin_interactions', [])
            if chromatin:
                from .native_chromatin_interaction_tool_info import chromatin_interaction_tool_contracts
                alternatives.extend(row['input_schema'] for row in chromatin_interaction_tool_contracts(
                    chromatin, resource_kind=kind, resource_id=resource_id))
            overlap = self.resources[resource_id].get('native_genomic_overlap', [])
            if overlap:
                from .native_genomic_overlap_tool_info import genomic_overlap_tool_contracts
                alternatives.extend(row['input_schema'] for row in genomic_overlap_tool_contracts(
                    overlap, resource_kind=kind, resource_id=resource_id))
            protein = self.resources[resource_id].get('native_protein_structure', [])
            if protein:
                from .native_protein_structure_tool_info import protein_structure_tool_contracts
                alternatives.extend(row['input_schema'] for row in protein_structure_tool_contracts(
                    protein, resource_kind='local', resource_id=resource_id))
            rna = self.resources[resource_id].get('native_rna_structure', [])
            if rna:
                from .native_rna_structure_tool_info import rna_structure_tool_contracts
                alternatives.extend(row['input_schema'] for row in rna_structure_tool_contracts(
                    rna, resource_kind=kind, resource_id=resource_id))
            database = self.resources[resource_id].get('native_blast_standard_database')
            if database:
                from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                alternatives.extend(row['input_schema'] for row in standard_blast_database_tool_contracts(
                    database['bindings'], resource_kind=kind, resource_id=resource_id))
            database = self.resources[resource_id].get('native_blast_database')
            if database:
                from .native_blast_database_tool_info import native_blast_database_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_database_tool_contracts(
                    database['bindings'], resource_kind=kind, resource_id=resource_id))
            native = self.resources[resource_id].get('native_hmmer', [])
            if native:
                from .native_hmmer_tool_info import native_hmmer_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_hmmer_tool_contracts(
                    native, resource_kind=kind, resource_id=resource_id))
            masking = self.resources[resource_id].get('native_blast_masking', [])
            if masking:
                from .native_blast_masking_tool_info import native_blast_masking_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_masking_tool_contracts(
                    masking, resource_kind=kind, resource_id=resource_id))
            utility = self.resources[resource_id].get('native_blast_utility', [])
            if utility:
                from .native_blast_utility_tool_info import native_blast_utility_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_utility_tool_contracts(
                    utility, resource_kind=kind, resource_id=resource_id))
            blast = self.resources[resource_id].get('native_blast', [])
            if blast:
                from .native_blast_tool_info import native_blast_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_tool_contracts(
                    blast, resource_kind=kind, resource_id=resource_id))
            infernal = self.resources[resource_id].get('native_infernal', [])
            if infernal:
                from .native_infernal_tool_info import native_infernal_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_infernal_tool_contracts(
                    infernal, resource_kind=kind, resource_id=resource_id))
            preparation = self.resources[resource_id].get('native_infernal_preparation', [])
            if preparation:
                from .native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_infernal_preparation_tool_contracts(
                    preparation, resource_kind=kind, resource_id=resource_id))
            hmmer_preparation = self.resources[resource_id].get('native_hmmer_preparation', [])
            if hmmer_preparation:
                from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_hmmer_preparation_tool_contracts(
                    hmmer_preparation, resource_kind=kind, resource_id=resource_id))
            if alternatives:
                schema['properties']['requested_job'] = {
                    'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]}
            else:
                schema['properties']['requested_job'] = deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        lumpy_compact = []
        if compact and kind == 'local' and self.resources[resource_id].get('native_lumpy'):
            from .lumpy_request_binding import resource_assignment_schema
            lumpy_compact.append(resource_assignment_schema(resource_id, selected=selected,
                bindings=self.resources[resource_id]['native_lumpy']))
        if compact and kind == 'local' and self.resources[resource_id].get('native_flux_balance'):
            from .flux_balance_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected), *lumpy_compact]}
        if compact and kind == 'local' and self.resources[resource_id].get('native_macs2_peak'):
            from .macs2_peak_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected,
                bindings=self.resources[resource_id]['native_macs2_peak']), *lumpy_compact]}
        if lumpy_compact:
            return {'anyOf': [schema, *lumpy_compact]}
        return schema

    def child_assignment_schema(self, parent, role):
        """A frozen HPC launch exposes only its already authorized request."""
        if parent.role == 'launch' and role == 'launch_hpc' and any(
                ancestor == 'hpc' for ancestor, _ in parent.path):
            assignment = plain(parent.assignment)
            requests = [request for resource_id, request in assignment['requests'].items()
                        if self._permitted(assignment, resource_id)
                        and request.get('resource_kind') == 'hpc']
            if not requests:
                raise ValueError('frozen_hpc_launch_request_missing')
            return {'type': 'object', 'enum': requests}
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        if role == 'results':
            schema = deepcopy(RESULTS_SCHEMA)
            schema['properties']['selector'].setdefault('allOf', []).append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'const': 'local_file_source_selector_v1'}}},
                'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
            schema['properties']['selector']['allOf'].append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'const': MACS2_FILE_SOURCE_SELECTOR_VERSION}}},
                'then': deepcopy(MACS2_FILE_SOURCE_SELECTOR_SCHEMA)})
            schema['properties']['selector']['allOf'].append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'const': LUMPY_FILE_SOURCE_SELECTOR_VERSION}}},
                'then': deepcopy(LUMPY_FILE_SOURCE_SELECTOR_SCHEMA)})
            from .sequence_masking_result_views import NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'const': 'native_blast_masking_result_selector_v1'}}},
                'then': deepcopy(NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)})
            from .blast_utility_result_views import NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'enum': ['native_blast_utility_result_selector_v1',
                             'native_blast_utility_result_selector_v2']}}},
                'then': deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)})
            from .fluorescence_result_contracts import FLUORESCENCE_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector'].setdefault('allOf', []).append({
                'if': {'required': ['version'], 'properties': {'version': {
                    'const': 'fluorescence_result_selector_v1'}}},
                'then': deepcopy(FLUORESCENCE_RESULT_SELECTOR_SCHEMA)})
            if self.native_expression_nmf_results is not None:
                from .expression_nmf_result_contracts import EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'expression_nmf_result_selector_v1'}}},
                    'then': deepcopy(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA)})
            if self.native_flux_balance_results is not None:
                from .flux_balance_result_selection import FBA_RESULT_SELECTOR_SCHEMA
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'flux_balance_result_selector_v1'}}},
                    'then': deepcopy(FBA_RESULT_SELECTOR_SCHEMA)})
            if self.atac_results is not None:
                from .atac_differential_execution_information import atac_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'atac_differential_result_selector_v1'}}},
                    'then': atac_result_selector_schema()})
            if self.native_chromatin_interaction_results is not None:
                from .chromatin_interaction_execution_information import chromatin_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'chromatin_interaction_result_selector_v1'}}},
                    'then': chromatin_result_selector_schema()})
            if self.native_rna_structure_results is not None:
                from .rna_structure_result_views import RESULT_SELECTOR_SCHEMA
                from .rna_structure_comparison_contracts import RNA_COMPARISON_SELECTOR_SCHEMA
                alternatives = [*deepcopy(RESULT_SELECTOR_SCHEMA['oneOf']),
                    deepcopy(RNA_COMPARISON_SELECTOR_SCHEMA)]
                versions = [branch['properties']['version']['const'] for branch in alternatives]
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {'enum': versions}}},
                    'then': {'oneOf': alternatives}})
            if any(configuration.get('native_protein_structure') for configuration in self.resources.values()):
                from .protein_structure_selection import protein_structure_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'protein_structure_result_selector_v1'}}},
                    'then': protein_structure_result_selector_schema()})
            if self.native_genomic_overlap_results is not None:
                from .genomic_overlap_execution_information import genomic_overlap_result_selector_schema
                schema['properties']['selector'].setdefault('allOf', []).append({
                    'if': {'required': ['version'], 'properties': {'version': {
                        'const': 'genomic_overlap_result_selector_v1'}}},
                    'then': genomic_overlap_result_selector_schema()})
            return schema
        if role == 'launch':
            schema = obj({'version': {'const': LAUNCH_VERSION},
                'requests': {'type': 'object', 'properties': {key: self._request_schema(key, selected=False, internal=internal, compact=False)
                    for key in self.resources}, 'minProperties': 1, 'additionalProperties': False},
                'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)},
                'constraints': {'type': 'object'}})
            schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
            alternatives = [schema]
            if any(value.get('native_flux_balance') for value in self.resources.values()):
                from .flux_balance_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            if any(value.get('native_macs2_peak') for value in self.resources.values()):
                from .macs2_peak_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            if any(value.get('native_lumpy') for value in self.resources.values()):
                from .lumpy_request_binding import launch_assignment_schema
                alternatives.append(launch_assignment_schema(self.resources))
            return {'anyOf': alternatives} if len(alternatives) > 1 else schema
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items()
                        if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        config = self.resources[resource_id]
        kind = KINDS[config['kind']]
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            validate_compact_assignment as validate_lumpy_assignment)
        if is_lumpy_assignment(value):
            if kind != 'local' or not config.get('native_lumpy'):
                raise ValueError('lumpy_request_binding_unavailable')
            return validate_lumpy_assignment(value, resource_id, bindings=config['native_lumpy'])
        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            validate_compact_assignment as validate_macs2_assignment)
        if is_macs2_assignment(value):
            if kind != 'local' or not config.get('native_macs2_peak'):
                raise ValueError('macs2_peak_request_binding_unavailable')
            return validate_macs2_assignment(value, resource_id, bindings=config['native_macs2_peak'])
        from .flux_balance_request_binding import is_compact_assignment, validate_compact_assignment
        if is_compact_assignment(value):
            if kind != 'local' or not config.get('native_flux_balance'):
                raise ValueError('flux_balance_request_binding_unavailable')
            return validate_compact_assignment(value, resource_id)
        value = (self.api_execution.validate_assignment(value)
            if kind == 'api' else validate_assignment(value))
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if kind != 'api':
            if value['resource_kind'] != kind:
                raise ValueError('execution_resource_kind_conflict')
            confined(value['workspace'], config['workspace'])
            operations = self._practical[resource_id]._operations(kind)
            validator = getattr(operations, 'validate_assignment', None)
            if validator is not None:
                # The launch request map already names this resource. A
                # resource child later receives that same explicit identity.
                validator({**value, 'resource_id': resource_id})
        return value

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch', internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            self._validate_request(request, resource_id=resource_id)
            if scope is not None and KINDS[self.resources[resource_id]['kind']] == 'api':
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list)
                    or any(not isinstance(item, str) or not item for item in constraints[key])):
                raise ValueError('invalid_execution_resource_constraints')

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return (resource_id in assignment['requests']
            and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        assignment = self._launch(plain(parent.assignment))
        return tuple(role for role, kind in ROLE_KINDS.items() if any(
            KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id)
            for resource_id, configuration in self.resources.items()))

    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if (isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:')
                or isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None  # Runtime handles are resolved by their durable service, not Store.
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from .protein_structure_operands import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                # A descriptor authorizes its exact original sequence reference.
                # A derived wrapper cannot borrow that permission.
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
            if (selector.get('mode') == 'saved_sheet_recalculation'
                    and isinstance(supplied, dict) and supplied.get('artifact_ref') == reference):
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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
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
            from .fluorescence_result_contracts import validate_fluorescence_selector
            from .fluorescence_return_views import CONTEXT_SOURCE, requested_fluorescence_sources
            selector = validate_fluorescence_selector(assignment['selector'])
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if bool(selector['context_fields']) != (CONTEXT_SOURCE in requested_fluorescence_sources(schema)):
                raise ValueError('fluorescence_context_selection_mismatch')
        return self.native_fluorescence_results.retained_target(context, assignment, scope)

    def _fluorescence_inputs(self, context, assignment):
        if 'native_fluorescence' not in assignment.get('requested_job', {}):
            return []
        from .fluorescence_operands import validate_fluorescence_job_inputs
        return validate_fluorescence_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)


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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_expression_nmf_returns.resolve_received(context, reference, namespace)

    def _flux_balance_reference_access(self, context, reference, namespace):
        if (self.native_flux_balance_returns is not None
                and self.native_flux_balance_returns.ordinary_backend is not None
                and context.role in {'annotation', 'scientific_process'}
                and namespace in {None, 'artifact'}
                and self.native_flux_balance_returns.resolve_received(context, reference, namespace)):
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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and supplied.get('artifact_ref') == reference):
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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and reference in [supplied['sheet']['artifact_ref'],
                        *(row['file']['artifact_ref'] for row in supplied['tables'])]):
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

    def _macs2_peak_inputs(self, context, assignment):
        if 'native_macs2_peak' not in assignment.get('requested_job', {}):
            return []
        from .received_native_file_inputs import validate_macs2_peak_job_inputs
        return validate_macs2_peak_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _lumpy_inputs(self, context, assignment):
        if 'native_lumpy' not in assignment.get('requested_job', {}):
            return []
        from .lumpy_request_binding import validate_lumpy_job_inputs
        return validate_lumpy_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def read_macs2_peak_capture_selection(self, context, capture_source_refs, *, before_decision_index=None):
        """Read explicitly received generic captures against their original MACS2 seal.

        Current delivery authenticates before private custody or seal bytes.
        Original target/start controls are retained records; this read never
        consults the original workspace, input bytes or installed software.
        Generic capture provenance is preserved, and an unselected sibling in
        a wrapper does not become a received File or Source.
        """
        from .episode_return_records import EpisodeReturnRecords
        from .episode_bindings import BindingContext
        from .local_file_capture_results import FILE_PROVIDER, RESULT_PROVIDER, RECEIPT_VERSION
        from .native_file_capture import NativeFileCaptureError, retained_native_file
        from .native_macs2_peak_execution import (
            POLICY, macs2_peak_plan, validate_macs2_peak_seal,
            validate_macs2_peak_original_controls,
        )
        from .native_atac_differential_driver import decode_json
        from .received_native_file_inputs import received_file_context

        def require(condition, code):
            if not condition:
                raise ValueError('macs2_peak_capture_' + code)

        require(isinstance(context, BindingContext) and context.run_id == self.run_id, 'context_conflict')
        require(type(capture_source_refs) in (list, tuple) and bool(capture_source_refs)
            and all(type(ref) is str for ref in capture_source_refs)
            and len(set(capture_source_refs)) == len(capture_source_refs), 'source_selection_invalid')
        require(before_decision_index is None or type(before_decision_index) is int
            and before_decision_index >= 0, 'cutoff_invalid')
        known, _ = received_file_context(self.store, context,
            failure_prefix='macs2_peak_capture_', baseline=False)
        records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='macs2_peak_capture_')
        selected = []
        # Finish every semantic receipt check before any private capture reader.
        for reference in capture_source_refs:
            require(reference in known and (before_decision_index is None or records._received_before(
                context.episode_id, reference, before_decision_index)), 'source_not_received')
            source = self.store.get(reference)
            require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
                and (source.get('provider') == FILE_PROVIDER or source.get('provider') == RESULT_PROVIDER
                    and source.get('version') == RECEIPT_VERSION), 'source_selection_invalid')
            selected.append((reference, source['provider']))

        plan, source_roles, unavailable_paths = None, {}, set()
        for reference, provider in selected:
            if provider == FILE_PROVIDER:
                captured = self.local_file_sources.read_source(reference, context.scope)
                require(captured is not None, 'source_receipt_missing')
                target, observation = captured['target'], captured['observation']
            else:
                captured = self.local_file_sources.read_wrapper(reference, context.scope)
                require(captured is not None, 'wrapper_receipt_missing')
                target, observation = captured['target'], captured['observation']
            require(target['resource_kind'] == 'local'
                and 'native_macs2_peak' in target['assignment']['requested_job'], 'producer_target_conflict')
            authenticated, original = self.job_progress_provider.targets._native(target['handle'], context.scope)
            require(canonical(authenticated) == canonical(target), 'producer_target_conflict')
            detail = original['receipt']['outcome'].get('native_outcome') or {}
            original_plan = validate_macs2_peak_original_controls(detail.get('native_macs2_peak_plan'),
                detail.get('native_macs2_peak_handle'), detail.get('native_macs2_peak_request_raw'))
            rebuilt = macs2_peak_plan(target['assignment'], original_plan['identity'], policy=POLICY)
            require(canonical(rebuilt) == canonical(original_plan), 'original_plan_conflict')
            native = observation.get('native', {})
            require(native.get('terminal') is True and native.get('quiescent') is True
                and native.get('execution_id') == target['execution_id']
                and native.get('metadata', {}).get('policy') == POLICY, 'original_observation_conflict')
            observed_plan = validate_macs2_peak_original_controls(native.get('native_macs2_peak_plan'),
                native.get('native_macs2_peak_handle'), native.get('native_macs2_peak_request_raw'))
            require(canonical(observed_plan) == canonical(original_plan)
                and all(canonical(native.get(key)) == canonical(detail.get(key)) for key in (
                    'native_macs2_peak_handle', 'native_macs2_peak_request_raw')), 'original_observation_conflict')
            if plan is None:
                plan = original_plan
            else:
                require(canonical(plan) == canonical(original_plan), 'mixed_producer_selection')
            paths = {str(Path(plan['attempt_directory']) / row['relative_path']): row for row in plan['outputs']}
            if provider == FILE_PROVIDER:
                spec = paths.get(captured['resolved_path'])
                require(spec is not None and captured['file'] is not None
                    and captured['selection']['format'] == spec['format']
                    and captured['file']['format'] == spec['format'], 'output_role_conflict')
                require(spec['role'] not in source_roles, 'duplicate_output_role')
                source_roles[spec['role']] = {'source_ref': reference, 'file': deepcopy(captured['file'])}
            else:
                # The explicitly received wrapper proves an actual failed
                # selection. Its successful sibling Sources remain unselected.
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
            roles.append({'specification': deepcopy(spec),
                'source_ref': None if supplied is None else supplied['source_ref'],
                'file': None if supplied is None else supplied['file'],
                'availability': 'retained' if supplied is not None else 'unavailable' if path in unavailable_paths else 'not_selected',
                'qualification': None if supplied is not None else {'code':
                    'selected_output_unavailable' if path in unavailable_paths else 'output_not_selected'}})
        seal_role = next(row for row in roles if row['specification']['role'] == 'seal')
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
                    role['qualification'] = {'code': 'producer_seal_unavailable' if seal_role['source_ref'] is not None
                        else 'producer_seal_not_received'}
        else:
            declarations = {row['specification']['role']: row['declaration'] for row in seal['outputs']}
            for role in roles:
                if role['specification']['role'] == 'seal':
                    continue
                declared = declarations[role['specification']['role']]
                file = role['file']
                if file is not None:
                    if (declared['state'] != 'present' or file['sha256'] != declared['sha256']
                            or file['size_bytes'] != declared['size_bytes']):
                        role.update(availability='unavailable', qualification={'code': 'native_output_identity_conflict'})
                elif declared['state'] == 'absent':
                    role.update(availability='unavailable', qualification={'code': 'native_output_absent'})
        return {'plan': deepcopy(plan), 'seal': deepcopy(seal), 'roles': roles}

    def _atac_inputs(self, context, assignment):
        if 'native_atac_differential' not in assignment.get('requested_job', {}):
            return []
        from .atac_differential_operands import validate_atac_job_inputs
        return validate_atac_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

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
            if (selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict)
                    and any(file.get('artifact_ref') == reference
                        for file in [supplied['sheet'], *supplied['tables']])):
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

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _retained_masking_target(self, context, assignment, scope):
        if not self._masking_selector(assignment):
            return None
        return self.native_blast_masking_results.retained_target(
            context, assignment=assignment, scope=scope)

    def _masking_reference_access(self, context, reference, namespace):
        access = self.native_blast_masking_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from .sequence_masking_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_masking_results.applies(context):
            resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    @staticmethod
    def _utility_selector(assignment):
        return assignment.get('selector', {}).get('version') in {
            'native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2'}

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _retained_utility_target(self, context, assignment, scope):
        if not self._utility_selector(assignment):
            return None
        return self.native_blast_utility_results.retained_target(
            context, assignment=assignment, scope=scope)

    def _utility_reference_access(self, context, reference, namespace):
        access = self.native_blast_utility_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        from .blast_utility_result_views import IDENTIFIER_NAMESPACES
        if self.native_blast_utility_results.applies(context):
            resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
        else:
            resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
        if resolved:
            return True
        return False if namespace in IDENTIFIER_NAMESPACES else None

    def _versions(self, versions, scope, *, context, atac_assignments=(), nmf_assignments=(),
                  fluorescence_assignments=(), flux_balance_assignments=(), macs2_peak_assignments=(),
                  lumpy_assignments=()):
        from .execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context,
            atac_assignments=atac_assignments, nmf_assignments=nmf_assignments,
            fluorescence_assignments=fluorescence_assignments,
            flux_balance_assignments=flux_balance_assignments, macs2_peak_assignments=macs2_peak_assignments,
            lumpy_assignments=lumpy_assignments)


    def _expression_nmf_inputs(self, context, assignment):
        if 'native_expression_nmf' not in assignment.get('requested_job', {}):
            return []
        from .expression_nmf_operands import validate_expression_nmf_job_inputs
        return validate_expression_nmf_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _flux_balance_inputs(self, context, assignment, *, input_versions=None):
        if 'native_flux_balance' not in assignment.get('requested_job', {}):
            return []
        from .episode_return_records import EpisodeReturnRecords
        if input_versions is None:
            if context.role == 'launch':
                input_versions = plain(context.assignment)['immutable_input_versions']
            else:
                _, input_versions = self.flux_balance_inputs._original(context)
        frozen = (self.flux_balance_inputs.received(context, required=False)
            if context.role == 'launch_local' and self._matches_flux_balance_assignment(context, assignment) else None)
        binding = (frozen['receipt']['binding'] if frozen is not None else
            self.flux_balance_inputs.validate_selected(context, assignment, input_versions=input_versions))
        if not EpisodeReturnRecords._equal(binding['input_versions'], list(input_versions)):
            raise ValueError('flux_balance_execution_input_original_versions_conflict')
        return list(dict.fromkeys(row['reference'] for row in binding['input_versions']))

    def _matches_flux_balance_assignment(self, context, assignment):
        from .flux_balance_request_binding import is_compact_assignment, materialized_assignment
        original = (materialized_assignment(self.store, context)
            if is_compact_assignment(plain(context.assignment)) else plain(context.assignment))
        return canonical(original) == canonical(assignment)

    def _genomic_overlap_inputs(self, context, assignment):
        if 'native_genomic_overlap' not in assignment.get('requested_job', {}):
            return []
        from .genomic_overlap_operands import validate_genomic_overlap_job_inputs
        return validate_genomic_overlap_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _chromatin_inputs(self, context, assignment):
        if 'native_chromatin_interactions' not in assignment.get('requested_job', {}):
            return []
        from .chromatin_interaction_operands import validate_chromatin_job_inputs
        return validate_chromatin_job_inputs(self.store, context, assignment,
            reference_access=self.resolve_received_reference)

    def _match_request(self, assignment, selected):
        resource_id = selected.get('resource_id')
        if resource_id not in self.resources or not self._permitted(assignment, resource_id):
            raise ValueError('execution_resource_selection_conflict')
        expected = deepcopy(assignment['requests'][resource_id])
        expected['resource_id'] = resource_id
        retain_inherited_selection(assignment.get('launch_instructions'), selected.get('launch_instructions'))
        retain_inherited_selection(expected.get('launch_instructions'), selected.get('launch_instructions'))
        if ({key: value for key, value in selected.items() if key != 'launch_instructions'} !=
                {key: value for key, value in expected.items() if key != 'launch_instructions'}):
            raise ValueError('execution_original_request_conflict')
        selectors = {'allowed_resource_ids', 'allowed_kinds', 'resource_id', 'kind'}
        for key, value in assignment['constraints'].items():
            if key not in selectors and selected['constraints'].get(key) != value:
                raise ValueError('execution_parent_constraint_conflict')

    def _recorded_results_assignment(self, parent, selected, scope, operation_key):
        """Restore a successfully returned original Results commission only."""
        from .episode_receipts import EpisodeReceipts
        from .episode_return_records import EpisodeReturnRecords
        inheritance = parent.request.get('message', {}).get('knowledge_inheritance')
        if inheritance is None:
            return None
        try:
            manifest = EpisodeReceipts.read_manifest(self.store.db, self.run_id, parent.episode_id)
        except ValueError as error:
            if str(error) == 'episode_receipts_not_bound':
                return None
            raise ValueError('recorded_results_receipt_history_invalid') from error
        proof = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_results_')
        proof.authenticate(parent)
        proof._require(proof._equal(inheritance, manifest), 'receipt_context_conflict')
        proof._require(isinstance(operation_key, str), 'operation_required')
        index = proof._admission_index(parent, operation_key + ':typed_form')
        attempt = self.store.db.execute('SELECT child_episode_id,contract,form,failure '
            'FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id, parent.episode_id, index)).fetchone()
        if attempt is None or attempt['form'] is None or attempt['failure'] is not None:
            return None
        try:
            form, contract = json.loads(attempt['form']), json.loads(attempt['contract'])
            schema = contract['measurements']['schema']
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError('recorded_results_original_return_invalid') from error
        if proof.recorded_admission_references(parent, form, schema, index) is None:
            return None
        child = proof.context(attempt['child_episode_id'])
        proof._require(child.role == 'results' and child.path[:-1] == parent.path
            and child.path[-1] == ('results', 'child_' + str(index)), 'original_child_conflict')
        state = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, child.episode_id)).fetchone()
        if state['state'] != 'yielded':
            return None
        action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
        original = json.loads(action['action'])
        proof._require(original.get('kind') == 'episode_child' and original.get('role') == 'results',
            'original_selection_conflict')
        proof._require(proof._equal(selected, original.get('assignment'))
            and proof._equal(selected, child.assignment), 'assignment_conflict')
        proof._require(proof._equal(scope, original.get('scope'))
            and proof._equal(scope, child.scope), 'scope_conflict')
        return plain(child.assignment)

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and role == 'launch':
            from .hpc_episodes import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        if role == 'results':
            if (is_macs2_file_source_selector(selected.get('selector'))
                    or is_lumpy_file_source_selector(selected.get('selector'))):
                self.local_file_sources.admit_handoff(parent, selected)
            recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
            if recorded is not None:
                return recorded
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding)
        if role == 'launch' and is_lumpy_launch(selected):
            return self.lumpy_requests.preview(parent, selected)[0]
        if role == 'launch_local' and is_lumpy_assignment(selected):
            if parent.role != 'launch':
                raise ValueError('resource_child_role_owned_by_launch')
            control = read_lumpy_binding(self.store, self.run_id, parent.episode_id)
            row, = [row for row in control['requests'] if canonical(row['selection']) == canonical(selected)]
            from .episode_return_records import EpisodeReturnRecords
            records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='lumpy_original_')
            records.authenticate(parent)
            index = records._admission_index(parent, operation_key + ':typed_form')
            returned = self.store.db.execute('SELECT form,failure FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (self.run_id, parent.episode_id, index)).fetchone()
            if returned is not None and returned['form'] is not None and returned['failure'] is None:
                child, _, _ = records._attempt(parent, index)
                action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
                    'AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
                if action is None:
                    raise ValueError('lumpy_original_commission_conflict')
                original_selection = json.loads(action['action'])
                closed = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (self.run_id, child.episode_id)).fetchone()
                if (original_selection.get('kind') != 'episode_child' or original_selection.get('role') != role
                        or canonical(original_selection.get('assignment')) != canonical(selected)
                        or canonical(original_selection.get('scope')) != canonical(plain(scope))
                        or child.role != role or canonical(plain(child.assignment)) != canonical(selected)
                        or canonical(plain(child.scope)) != canonical(plain(scope))
                        or closed is None or closed['state'] != 'yielded'
                        or self._closed_operational_credit_view(child, None) is None):
                    raise ValueError('lumpy_original_commission_conflict')
                # This actual returned commission already owns its original
                # lexical input paths. Revalidate its frozen admission, never
                # reinterpret it as a new dispatch from the current Store.
                self.initial_references(child)
                return selected
            original = self._launch(plain(parent.assignment))
            self._match_request(original, selected)
            self._lumpy_inputs(parent, row['assignment'])
            self._versions(row['input_versions'], scope, context=parent, lumpy_assignments=[row['assignment']])
            return selected

        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding)
        if role == 'launch' and is_macs2_launch(selected):
            return self.macs2_peak_requests.preview(parent, selected)[0]
        if role == 'launch_local' and is_macs2_assignment(selected):
            if parent.role != 'launch':
                raise ValueError('resource_child_role_owned_by_launch')
            control = read_macs2_binding(self.store, self.run_id, parent.episode_id)
            row, = [row for row in control['requests'] if canonical(row['selection']) == canonical(selected)]
            from .episode_return_records import EpisodeReturnRecords
            records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='macs2_peak_original_')
            records.authenticate(parent)
            index = records._admission_index(parent, operation_key + ':typed_form')
            returned = self.store.db.execute('SELECT form,failure FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (self.run_id, parent.episode_id, index)).fetchone()
            if returned is not None and returned['form'] is not None and returned['failure'] is None:
                child, _, _ = records._attempt(parent, index)
                action = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
                    'AND episode_id=? AND decision_index=?', (self.run_id, parent.episode_id, index)).fetchone()
                if action is None:
                    raise ValueError('macs2_peak_original_commission_conflict')
                original_selection = json.loads(action['action'])
                closed = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (self.run_id, child.episode_id)).fetchone()
                if (original_selection.get('kind') != 'episode_child' or original_selection.get('role') != role
                        or canonical(original_selection.get('assignment')) != canonical(selected)
                        or canonical(original_selection.get('scope')) != canonical(plain(scope))
                        or child.role != role or canonical(plain(child.assignment)) != canonical(selected)
                        or canonical(plain(child.scope)) != canonical(plain(scope))
                        or closed is None or closed['state'] != 'yielded'
                        or self._closed_operational_credit_view(child, None) is None):
                    raise ValueError('macs2_peak_original_commission_conflict')
                # This actual returned commission already owns its original
                # lexical input paths. Revalidate its frozen admission, never
                # reinterpret it as a new dispatch from the current Store.
                self.initial_references(child)
                return selected
            original = self._launch(plain(parent.assignment))
            self._match_request(original, selected)
            self._macs2_peak_inputs(parent, row['assignment'])
            self._versions(row['input_versions'], scope, context=parent, macs2_peak_assignments=[row['assignment']])
            return selected
        from .flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if role == 'launch' and is_compact_launch(selected):
            return self.flux_balance_requests.preview(parent, selected)[0]
        if role == 'launch_local' and is_compact_assignment(selected):
            if parent.role != 'launch':
                raise ValueError('resource_child_role_owned_by_launch')
            original = self._launch(plain(parent.assignment))
            self._match_request(original, selected)
            control = read_request_binding(self.store, self.run_id, parent.episode_id)
            row, = [row for row in control['requests'] if row['selection'] == selected]
            self._flux_balance_inputs(parent, row['assignment'], input_versions=row['input_versions'])
            self._versions(row['input_versions'], scope, context=parent,
                flux_balance_assignments=[row['assignment']])
            return selected
        if role == 'launch':
            selected = self._launch(selected, scope=scope)
            from .protein_structure_operands import validate_protein_structure_job_inputs
            for request in selected['requests'].values():
                self._masking_inputs(parent, request)
                self._utility_inputs(parent, request)
                self._fluorescence_inputs(parent, request)
                self._expression_nmf_inputs(parent, request)
                self._flux_balance_inputs(parent, request,
                    input_versions=selected['immutable_input_versions'])
                self._macs2_peak_inputs(parent, request)
                self._lumpy_inputs(parent, request)
                self._atac_inputs(parent, request)
                self._chromatin_inputs(parent, request)
                self._genomic_overlap_inputs(parent, request)
                validate_protein_structure_job_inputs(self.store, parent, request,
                    returns=self.native_protein_structure_returns)
            self._versions(selected['immutable_input_versions'], scope, context=parent,
                macs2_peak_assignments=selected['requests'].values(), lumpy_assignments=selected['requests'].values(),
                atac_assignments=selected['requests'].values(), nmf_assignments=selected['requests'].values(),
                fluorescence_assignments=selected['requests'].values(),
                flux_balance_assignments=selected['requests'].values())
            from .native_blast_database_result_publication import validate_native_job_inputs
            from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            for request in selected['requests'].values():
                validate_native_job_inputs(self.store, parent, request)
                validate_standard_blast_job_inputs(self.store, parent, request)
                from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
                validate_rna_structure_job_inputs(self.store, parent, request)
            return selected
        if role == 'results':
            masking_target = self._retained_masking_target(parent, selected, scope)
            utility_target = self._retained_utility_target(parent, selected, scope)
            fluorescence_target = self._retained_fluorescence_target(parent, selected, scope)
            nmf_target = self._retained_expression_nmf_target(parent, selected, scope)
            atac_target = self._retained_atac_target(parent, selected, scope)
            chromatin_target = self._retained_chromatin_target(parent, selected, scope)
            overlap_target = self._retained_genomic_overlap_target(parent, selected, scope)
            retained = self._retained_protein_result(parent, selected, scope)
            flux_balance_target = self._retained_flux_balance_target(parent, selected, scope)
            target = (flux_balance_target if flux_balance_target is not None else
                utility_target if utility_target is not None else
                masking_target if masking_target is not None else
                fluorescence_target if fluorescence_target is not None else
                nmf_target if nmf_target is not None else
                atac_target if atac_target is not None else
                chromatin_target if chromatin_target is not None else
                overlap_target if overlap_target is not None else
                retained['body']['intent']['target'] if retained is not None else
                self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope))
            self._selector(selected, target)
            if is_file_source_selector(selected.get('selector')):
                self.local_file_sources.admit(parent, selected, target)
            if self._masking_selector(selected):
                self.native_blast_masking_results.validate_selected_inputs(parent, selected)
            if self._utility_selector(selected):
                self.native_blast_utility_results.validate_selected_inputs(parent, selected)
            if is_native_protein_structure_target(target):
                from .protein_structure_operands import validate_protein_structure_selected_inputs
                validate_protein_structure_selected_inputs(self.store, parent, selected['selector'],
                    handoff_ref=selected['handoff_ref'], returns=self.native_protein_structure_returns)
            if self._comparison_selector(selected):
                from .rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
                validate_rna_comparison_selected_inputs(self.store, parent, selected['selector'],
                    anchor_handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
            elif is_native_rna_structure_target(target):
                from .native_rna_structure_result_publication import validate_rna_structure_selected_inputs
                validate_rna_structure_selected_inputs(self.store, parent, selected['selector'],
                    handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
            if is_standard_blast_database_target(target):
                from .native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
                validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
            if is_native_blast_database_target(target):
                from .native_blast_database_result_publication import validate_selected_inputs
                validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
            from .bvbrc_data_host import is_bvbrc_request
            if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
                self.api_execution.bvbrc_data.validate_inputs(parent, selected['selector'],
                    request=target['assignment']['request'])
            if target['resource_kind'] == 'api' and target['assignment'].get('service') == 'bvbrc_minhash':
                self.api_execution.minhash.validate_commission_inputs(parent, selected,
                    request=target['assignment']['request'], scope=scope, operation_key=operation_key)
            return selected
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] == 'api':
            selected = self.api_execution.validate_assignment(selected, scope=scope)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._match_request(original, selected)
        self._masking_inputs(parent, selected)
        self._utility_inputs(parent, selected)
        self._fluorescence_inputs(parent, selected)
        self._expression_nmf_inputs(parent, selected)
        self._flux_balance_inputs(parent, selected,
            input_versions=original['immutable_input_versions'])
        self._macs2_peak_inputs(parent, selected)
        self._lumpy_inputs(parent, selected)
        self._atac_inputs(parent, selected)
        self._chromatin_inputs(parent, selected)
        self._genomic_overlap_inputs(parent, selected)
        from .protein_structure_operands import validate_protein_structure_job_inputs
        validate_protein_structure_job_inputs(self.store, parent, selected,
            returns=self.native_protein_structure_returns)
        self._versions(original['immutable_input_versions'], scope, context=parent,
            macs2_peak_assignments=[selected], lumpy_assignments=[selected],
            atac_assignments=[selected], nmf_assignments=[selected], fluorescence_assignments=[selected],
            flux_balance_assignments=[selected])
        from .native_blast_database_result_publication import validate_native_job_inputs
        from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
        from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
        validate_rna_structure_job_inputs(self.store, parent, selected)
        return selected

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        """An internal execution view; the immutable episode request stays original."""
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            materialized_assignment as materialized_lumpy_assignment)
        if is_lumpy_assignment(plain(context.assignment)):
            from .episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path,
                context.scope, materialized_lumpy_assignment(self.store, context), context.request,
                context.received_record_refs)
            self.lumpy_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical

        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            materialized_assignment as materialized_macs2_assignment)
        if is_macs2_assignment(plain(context.assignment)):
            from .episode_bindings import BindingContext
            practical = BindingContext(context.run_id, context.episode_id, context.role, context.path,
                context.scope, materialized_macs2_assignment(self.store, context), context.request,
                context.received_record_refs)
            self.macs2_peak_requests.validate_practical_history(context, practical, self._delegate(context))
            return practical
        from .flux_balance_request_binding import is_compact_assignment, materialized_assignment
        if not is_compact_assignment(plain(context.assignment)):
            return context
        from .episode_bindings import BindingContext
        practical = BindingContext(context.run_id, context.episode_id, context.role, context.path,
            context.scope, materialized_assignment(self.store, context), context.request,
            context.received_record_refs)
        self.flux_balance_requests.validate_practical_history(context, practical, self._delegate(context))
        return practical

    def initialize(self, context):
        from .lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch
        if is_lumpy_launch(plain(context.assignment)):
            self.lumpy_requests.initialize(context)
            return
        if is_lumpy_assignment(plain(context.assignment)):
            self.lumpy_requests.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))

        from .macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch
        if is_macs2_launch(plain(context.assignment)):
            self.macs2_peak_requests.initialize(context)
            return
        if is_macs2_assignment(plain(context.assignment)):
            self.macs2_peak_requests.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        from .flux_balance_request_binding import is_compact_assignment, is_compact_launch
        if is_compact_launch(plain(context.assignment)):
            self.flux_balance_requests.initialize(context)
            return
        if is_compact_assignment(plain(context.assignment)):
            self.flux_balance_requests.initialize(context)
            self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        if self._has_uniprot():
            original = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            self.api_execution.uniprot_returns._selection(context, original)
        if context.role in ROLE_KINDS:
            self._check_parent_inputs(context)
            if 'native_flux_balance' in plain(context.assignment).get('requested_job', {}):
                self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(context)
        if context.role == 'launch':
            value = self._launch(plain(context.assignment), scope=context.scope)
            from .protein_structure_operands import validate_protein_structure_job_inputs
            for request in value['requests'].values():
                self._masking_inputs(context, request)
                self._utility_inputs(context, request)
                self._fluorescence_inputs(context, request)
                self._expression_nmf_inputs(context, request)
                self._flux_balance_inputs(context, request,
                    input_versions=value['immutable_input_versions'])
                self._macs2_peak_inputs(context, request)
                self._lumpy_inputs(context, request)
                self._atac_inputs(context, request)
                self._chromatin_inputs(context, request)
                self._genomic_overlap_inputs(context, request)
                validate_protein_structure_job_inputs(self.store, context, request,
                    returns=self.native_protein_structure_returns)
            self._versions(value['immutable_input_versions'], context.scope, context=context,
                macs2_peak_assignments=value['requests'].values(), lumpy_assignments=value['requests'].values(),
                atac_assignments=value['requests'].values(), nmf_assignments=value['requests'].values(),
                fluorescence_assignments=value['requests'].values(),
                flux_balance_assignments=value['requests'].values())
        else:
            target = self._target(context)
            self._selector(plain(context.assignment), target)
            if (self._flux_balance_selector(plain(context.assignment))
                    or self._masking_selector(plain(context.assignment))
                    or self._utility_selector(plain(context.assignment))
                    or self._fluorescence_selector(plain(context.assignment))
                    or self._expression_nmf_selector(plain(context.assignment))
                    or self._atac_selector(plain(context.assignment))
                    or self._chromatin_selector(plain(context.assignment))
                    or self._genomic_overlap_selector(plain(context.assignment))
                    or self._comparison_selector(plain(context.assignment))
                    or is_native_protein_structure_target(target)):
                self.initial_references(context)
            if target['resource_kind'] == 'api':
                return self.api_execution.initialize(context)
            self._result_directory(context)

    def _check_parent_inputs(self, context):
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            read_request_binding as read_lumpy_binding)
        if is_lumpy_assignment(plain(context.assignment)):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            row, = control['requests']
            self._lumpy_inputs(context, row['assignment'])
            self._versions(row['input_versions'], context.scope, context=context, lumpy_assignments=[row['assignment']])
            return

        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            read_request_binding as read_macs2_binding)
        if is_macs2_assignment(plain(context.assignment)):
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            row, = control['requests']
            self._macs2_peak_inputs(context, row['assignment'])
            self._versions(row['input_versions'], context.scope, context=context, macs2_peak_assignments=[row['assignment']])
            return
        from .flux_balance_request_binding import is_compact_assignment, read_request_binding
        if is_compact_assignment(plain(context.assignment)):
            read_request_binding(self.store, self.run_id, context.episode_id)
            self.flux_balance_inputs.received(context)
            return
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?',
            (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            self._match_request(original, plain(context.assignment))
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._fluorescence_inputs(context, plain(context.assignment))
            self._expression_nmf_inputs(context, plain(context.assignment))
            self._flux_balance_inputs(context, plain(context.assignment),
                input_versions=original['immutable_input_versions'])
            self._macs2_peak_inputs(context, plain(context.assignment))
            self._lumpy_inputs(context, plain(context.assignment))
            self._atac_inputs(context, plain(context.assignment))
            self._chromatin_inputs(context, plain(context.assignment))
            self._genomic_overlap_inputs(context, plain(context.assignment))
            from .protein_structure_operands import validate_protein_structure_job_inputs
            validate_protein_structure_job_inputs(self.store, context, plain(context.assignment),
                returns=self.native_protein_structure_returns)
            self._versions(original['immutable_input_versions'], context.scope, context=context,
                macs2_peak_assignments=[plain(context.assignment)], lumpy_assignments=[plain(context.assignment)],
                atac_assignments=[plain(context.assignment)], nmf_assignments=[plain(context.assignment)],
                fluorescence_assignments=[plain(context.assignment)],
                flux_balance_assignments=[plain(context.assignment)])
            from .native_blast_database_result_publication import validate_native_job_inputs
            from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
            validate_rna_structure_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(self._practical_context(context))

    def _resource_information(self, resource_id):
        config = self.resources[resource_id]
        capability = next(value for value in self.capabilities() if value['resource_id'] == resource_id)
        value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']],
            'availability': capability['availability'], 'tool_names': capability['tool_names'],
            **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable',
                'service', 'base_url') if key in config},
            'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}
        if config['kind'] == 'api':
            facts = {}
            for entry in self.api_execution.capabilities(resource_id):
                reported = entry.get('configuration', {})
                for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                    if name not in reported:
                        continue
                    actual = reported[name]
                    if type(actual) is not bool:
                        raise ValueError('api_configuration_fact_must_be_boolean')
                    if name in facts and facts[name] != actual:
                        raise ValueError('api_configuration_fact_conflict')
                    facts[name] = actual
            if facts:
                value['api_configuration_facts'] = facts
        return value

    def initial_decision_context(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
                'resource_kind': 'local'}], 'execution_initial_information': {}}
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
            'execution_initial_information': deepcopy(self.initial_information),
            'received_bvbrc_values': [] if self.api_execution is None else
                self.api_execution.received_bvbrc_context(context)}
        if (context.role in {'annotation', 'scientific_process'}
                and self.api_execution is not None
                and any(service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            jobs = self.api_execution.received_blast_jobs(context, self.job_progress_provider)
            for job in jobs:
                job.update(self._blast_scientific_owner(job['origin_episode_id']))
            value['received_blast_jobs'] = (self._blast_axis_summaries(jobs)
                if context.role == 'annotation' else jobs)
            value['received_blast_jobs_meaning'] = (
                'Saved original BLAST jobs for received handoffs; root sees one summary per '
                'annotation, axis and subject, while the scientific owner sees its original handles. '
                'Status is only as of observed_at; the scheduling estimate is recalculated '
                'locally as of forecast_as_of without a new provider observation. '
                'No status request is made to build this view. The scientific owner can work locally or '
                'return its handoff upward; the annotation root can choose another axis. A later owner '
                'may monitor or fetch the same handoff without a new submission. Waiting earns no '
                'scientific credit.')
        if self._forwards_minhash_reports(context.role):
            value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            value['received_rna_structure_values'] = self.native_rna_structure_returns.received_context(context)
            value['received_rna_comparison_values'] = self.rna_structure_comparison_returns.received_context(context)
        return value

    def _blast_scientific_owner(self, origin_episode_id):
        """Recover the annotation and axis assigned above one original launch."""
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, origin_episode_id)).fetchone()
        if row is None:
            raise ValueError('blast_original_launch_episode_unavailable')
        path = json.loads(row['path'])
        for length in range(len(path), 0, -1):
            if path[length - 1][0] != 'scientific_process':
                continue
            owner = self.store.db.execute('SELECT request FROM runtime_episodes '
                'WHERE run_id=? AND json(path)=json(?)',
                (self.run_id, json.dumps(path[:length]))).fetchone()
            if owner is None:
                raise ValueError('blast_scientific_owner_unavailable')
            assignment = json.loads(owner['request'])['message']['episode_assignment']
            return {'proposed_annotation_ref': assignment.get('proposed_annotation_ref'),
                    'evidence_axis': assignment['selection']['evidence_axis']['option_id']}
        return {'proposed_annotation_ref': None, 'evidence_axis': None}

    @staticmethod
    def _blast_axis_summaries(jobs):
        """Keep root scheduling input at annotation/axis level."""
        grouped = {}
        for job in jobs:
            key = (job['proposed_annotation_ref'], job['evidence_axis'], job['subject_ref'])
            grouped.setdefault(key, []).append(job)
        summaries = []
        for annotation, axis, subject in sorted(grouped,
                key=lambda key: tuple('' if value is None else value for value in key)):
            rows = grouped[(annotation, axis, subject)]
            active = [row for row in rows if not row['result_received']
                and row['native_state'] not in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}]
            actionable = min(active, key=lambda row: (
                row['native_state'] != 'READY', row['observed_at'], row['handoff_ref'])) if active else None
            summaries.append({'proposed_annotation_ref': annotation, 'evidence_axis': axis,
                'subject_ref': subject, 'original_job_count': len(rows),
                'waiting_count': sum(row['native_state'] in {'accepted', 'WAITING'} for row in active),
                'ready_count': sum(row['native_state'] == 'READY' for row in active),
                'result_received_count': sum(row['result_received'] for row in rows),
                'failed_or_unknown_count': sum(row['native_state'] in
                    {'FAILED', 'UNKNOWN', 'failed', 'unknown'} for row in rows),
                'actionable_handoff_ref': None if actionable is None else actionable['handoff_ref'],
                'status_observed_at': None if actionable is None else actionable['observed_at'],
                'forecast_as_of': None if actionable is None else actionable['forecast_as_of'],
                'latest_progress_failure_code': (None if actionable is None else
                    actionable['latest_progress_failure_code']),
                'estimated_remaining_seconds': (None if actionable is None else
                    (actionable['wait_forecast'] or {}).get('estimated_remaining_seconds'))})
        return summaries

    def annotation_axis_yield_context(self, context, credit):
        if (context.role != 'annotation' or self.api_execution is None
                or not any(service.service == 'ncbi_blast'
                    for service in self.api_execution.services.values())):
            return {}
        arms = credit.get('arms', [])
        unresolved = []
        for job in self.api_execution.received_blast_jobs(context, self.job_progress_provider):
            job.update(self._blast_scientific_owner(job['origin_episode_id']))
            if job['result_received'] or job['native_state'] in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}:
                continue
            matches = [arm for arm in arms
                if arm['proposed_annotation_ref'] == job['proposed_annotation_ref']
                and arm['axis'] == job['evidence_axis']
                and arm['subject_ref'] == job['subject_ref']]
            if len(matches) != 1:
                raise ValueError('blast_pending_job_requires_one_annotation_axis_arm')
            unresolved.append({**{name: matches[0][name] for name in
                ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')},
                'handoff_ref': job['handoff_ref'], 'native_state': job['native_state']})
        return {'unresolved_annotation_axis_credit': unresolved}

    def capabilities(self):
        """Configured operation availability, with no deployment/authentication probe."""
        return [{'resource_id': key, 'kind': KINDS[configuration['kind']],
            'availability': 'unknown', 'observed_at': 'caller_configuration',
            'provenance_refs': [], 'knowledge_entry_ids': [],
            'tool_names': [entry['name'] for entry in (
                self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api'
                else operation_catalog(KINDS[configuration['kind']]))]}
            for key, configuration in self.resources.items()]

    def resource_tool_contracts(self):
        """Information for commissioning the actual configured resource owners.

        These declarations do not enable direct scientific invocation. The
        original launch/results assignment still supplies the job and selector;
        only the selected resource episode can execute each operation.
        """
        contracts = {}
        direct_protein_names = set()
        if getattr(self.tool_registry, '_protein_structure_configuration', None) is not None:
            direct_protein_names = set(self.tool_registry.catalog()) & {
                'inspect_protein_structure', 'extract_protein_structure_sequence',
                'compare_protein_structures'}
        direct_flux_balance = False
        if getattr(self.tool_registry, '_flux_balance_configuration', None) is not None:
            entry = self.tool_registry.catalog().get('perform_flux_balance_analysis', {})
            direct_flux_balance = entry.get('invocation_route', {}).get('kind') == 'direct'
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = (self.api_execution.operation_contracts(resource_id, 'launch_api')
                      if kind == 'api' else operation_catalog(kind))
            results = (self.api_execution.operation_contracts(resource_id, 'results')
                       if kind == 'api' else native_result_operation_catalog())
            for entry_role, owner_role, entries in (
                    ('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    key = entry['name'], kind
                    route = {'entry_role': entry_role, 'resource_id': resource_id,
                             'resource_role': owner_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name])
                            for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources=kind,
                            invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
            if kind == 'api':
                service = self.api_execution.services.get(resource_id)
                if (service is not None and service.service == 'bvbrc_appservice'
                        and ('bvbrc_homology', '1') in service.scientific_adapters):
                    from .bvbrc_homology_tool_info import homology_tool_contracts
                    for entry in homology_tool_contracts(resource_id=resource_id,
                            assignment_schema=self.api_execution.assignment_schema(resource_id)):
                        key = entry['name'], kind
                        if key not in contracts:
                            contracts[key] = entry
                        else:
                            prior = contracts[key]
                            prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                            prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                if service is not None and service.service == 'bvbrc_appservice':
                    if ('bvbrc_genome_alignment', '1') in service.scientific_adapters:
                        from .bvbrc_genome_alignment_tool_info import genome_alignment_tool_contracts
                        for entry in genome_alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_comparative_systems', '1') in service.scientific_adapters:
                        from .bvbrc_comparative_systems_tool_info import comparative_systems_tool_contracts
                        for entry in comparative_systems_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_fastqutils', '2') in service.scientific_adapters:
                        from .bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
                        for entry in fastqutils_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    proteome_versions = tuple(version for version in ('1', '2')
                        if ('bvbrc_proteome', version) in service.scientific_adapters)
                    if proteome_versions:
                        from .bvbrc_proteome_tool_info import proteome_tool_contracts
                        for entry in proteome_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                adapter_versions=proteome_versions):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_msa', 'bvbrc_metacats'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .bvbrc_alignment_tool_info import alignment_tool_contracts
                        for entry in alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_gene_tree', 'bvbrc_codon_tree'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .bvbrc_phylogeny_tool_info import phylogeny_tool_contracts
                        for entry in phylogeny_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
            native_entries = []
            if configuration.get('native_flux_balance'):
                from .native_flux_balance_tool_info import flux_balance_tool_contracts
                native_entries.extend(entry for entry in flux_balance_tool_contracts(
                    configuration['native_flux_balance'], resource_kind=kind, resource_id=resource_id)
                    if entry['name'] != 'perform_flux_balance_analysis' or not direct_flux_balance)
            if configuration.get('native_fluorescence'):
                from .native_fluorescence_tool_info import fluorescence_tool_contracts
                native_entries.extend(fluorescence_tool_contracts(configuration['native_fluorescence'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_expression_nmf'):
                from .native_expression_nmf_tool_info import expression_nmf_tool_contracts
                native_entries.extend(expression_nmf_tool_contracts(configuration['native_expression_nmf'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_macs2_peak'):
                from .native_macs2_peak_execution import macs2_peak_tool_contracts
                native_entries.extend(macs2_peak_tool_contracts(configuration['native_macs2_peak'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_lumpy'):
                from .lumpy_request_binding import lumpy_tool_contracts
                native_entries.extend(lumpy_tool_contracts(configuration['native_lumpy'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_atac_differential'):
                from .native_atac_differential_tool_info import atac_tool_contracts
                native_entries.extend(atac_tool_contracts(configuration['native_atac_differential'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_chromatin_interactions'):
                from .native_chromatin_interaction_tool_info import chromatin_interaction_tool_contracts
                native_entries.extend(chromatin_interaction_tool_contracts(configuration['native_chromatin_interactions'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_genomic_overlap'):
                from .native_genomic_overlap_tool_info import genomic_overlap_tool_contracts
                native_entries.extend(genomic_overlap_tool_contracts(configuration['native_genomic_overlap'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_protein_structure'):
                from .native_protein_structure_tool_info import protein_structure_tool_contracts
                native_entries.extend(entry for entry in protein_structure_tool_contracts(
                    configuration['native_protein_structure'], resource_kind='local', resource_id=resource_id)
                    if entry['name'] not in direct_protein_names)
            if configuration.get('native_rna_structure'):
                from .native_rna_structure_tool_info import rna_structure_tool_contracts
                native_entries.extend(rna_structure_tool_contracts(configuration['native_rna_structure'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_standard_database'):
                from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                native_entries.extend(standard_blast_database_tool_contracts(configuration['native_blast_standard_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_database'):
                from .native_blast_database_tool_info import native_blast_database_tool_contracts
                native_entries.extend(native_blast_database_tool_contracts(configuration['native_blast_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer'):
                from .native_hmmer_tool_info import native_hmmer_tool_contracts
                native_entries.extend(native_hmmer_tool_contracts(configuration['native_hmmer'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_masking'):
                from .native_blast_masking_tool_info import native_blast_masking_tool_contracts
                native_entries.extend(native_blast_masking_tool_contracts(configuration['native_blast_masking'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_utility'):
                from .native_blast_utility_tool_info import native_blast_utility_tool_contracts
                native_entries.extend(native_blast_utility_tool_contracts(configuration['native_blast_utility'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast'):
                from .native_blast_tool_info import native_blast_tool_contracts
                native_entries.extend(native_blast_tool_contracts(configuration['native_blast'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal'):
                from .native_infernal_tool_info import native_infernal_tool_contracts
                native_entries.extend(native_infernal_tool_contracts(configuration['native_infernal'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal_preparation'):
                from .native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                native_entries.extend(native_infernal_preparation_tool_contracts(
                    configuration['native_infernal_preparation'], resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer_preparation'):
                from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                native_entries.extend(native_hmmer_preparation_tool_contracts(
                    configuration['native_hmmer_preparation'], resource_kind=kind, resource_id=resource_id))
            for entry in native_entries:
                key = entry['name'], kind
                if key in contracts:
                    # Different deployment software must remain explicit in
                    # the bound request schema; combine actual alternatives.
                    prior = contracts[key]
                    if prior['description'] != entry['description']:
                        raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                    sections = prior.setdefault('_native_instruction_sections', {
                        route['resource_id']: prior['instructions']
                        for route in prior['invocation_route']['routes']})
                    sections[resource_id] = entry['instructions']
                    if len(set(sections.values())) > 1:
                        prior['instructions'] = '\n\n'.join('Resource '+key+':\n'+value
                            for key, value in sections.items())
                    schemas = prior.setdefault('_native_schemas', [prior['input_schema']])
                    if entry['input_schema'] not in schemas:
                        schemas.append(entry['input_schema'])
                    prior['input_schema'] = {'anyOf': deepcopy(schemas)}
                    prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                else:
                    contracts[key] = deepcopy(entry)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
            entry.pop('_native_instruction_sections', None)
        return [contracts[key] for key in sorted(contracts)]

    def permitted_common_actions(self, context):
        if self.native_protein_structure_results.applies(context):
            return ('tool',)
        if context.role == 'launch':
            if any(role == 'hpc' for role, _ in context.path):
                # This parent synchronously commissions preparation. Queue/run
                # waiting belongs to its HPC parent after a real handoff.
                return ('tool', 'child', 'redeliver_report')
            return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
        if context.role == 'launch_api':
            assignment = self._validate_request(plain(context.assignment))
            if assignment['version'] == 'api_service_assignment_v1':
                return ('tool', 'wait')
        elif context.role == 'results':
            target = self._target(context)
            if (target['resource_kind'] == 'api'
                    and target['assignment']['version'] == 'api_service_assignment_v1'):
                return ('tool', 'wait')
        return ('tool',)

    def instructions(self, context):
        if context.role == 'results':
            from .rna_structure_comparison_presentation import is_rna_comparison_results_context
            assignment = plain(context.assignment)
            if is_rna_comparison_results_context({'execution_assignment': assignment}):
                from .rna_structure_comparison_prompt import rna_comparison_results_instructions
                return rna_comparison_results_instructions(assignment)
            from .rna_structure_presentation import is_rna_structure_results_context
            if is_rna_structure_results_context({'execution_assignment': assignment}):
                from .rna_structure_prompt import rna_structure_results_instructions
                job = self._target(context)['assignment']['requested_job']['native_rna_structure']
                return rna_structure_results_instructions(assignment, job=job)
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).instructions(self._practical_context(context))
        if context.role == 'launch_api':
            assignment = self._validate_request(plain(context.assignment))
            service = assignment['service']
            return (f'Carry out the assigned work through {service} using one selected operation each turn. '
                'Keep the original inputs, request, resource and parent constraints fixed. Choose useful '
                'preparation, service requests, observations or repair from the actual available operations '
                'and received outcomes. Distinguish an immediate returned response from a service job that '
                'continues remotely. Preserve the actual request or job identity and submission uncertainty; '
                'a missing reply does not establish that no job was created. Establish the requested usable '
                'monitoring/results handoff from recorded service facts. The configured controller governs '
                'continuation; verified original handoff completion gives exact zero future credit.')
        if context.role == 'results':
            return ('Acquire the original selected execution results through the original handoff. Choose bounded '
                'status or requested file/page reads using actual preceding outcomes. Preserve partial bytes and '
                'native scores. Native paths expose the current resource filesystem: the exact attempt observation '
                'does not establish that current file bytes were produced by that attempt. Separate read windows '
                'are not an atomic file snapshot. The scientific parent interprets the returned records. Original work, resource '
                'and selector stay fixed. Only actual complete acquisition establishes this endpoint.')
        return ('Choose which permitted concrete execution request to commission on an explicit resource_id. '
            'Capabilities, recorded inventory and timing information inform the choice. Preserve the original '
            'job, immutable inputs, constraints and pinned instructions. A resource child owns iterative execution '
            'in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. '
            'Actual received usable handoff completes this launch endpoint with exact zero future credit.')

    def _with_selected_execution_task(self, context, value):
        """Detach original selected work without changing its commission."""
        assignment = plain(context.assignment)
        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding)
        compact = is_macs2_launch(assignment) or is_macs2_assignment(assignment)
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding)
        if is_lumpy_launch(assignment) or is_lumpy_assignment(assignment):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            requests = {row['resource_id']: row['assignment'] for row in control['requests']}
        elif compact:
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            requests = {row['resource_id']: row['assignment'] for row in control['requests']}
        elif context.role == 'launch':
            requests = assignment.get('requests')
            if not isinstance(requests, dict) or not requests:
                return value
        elif context.role in {'launch_local', 'launch_api'}:
            requests = {assignment.get('resource_id'): assignment}
        elif context.role == 'results':
            target = self._target(context) if self.local_file_sources.applies(context) else value.get('execution_target', {})
            requests = {target.get('resource_id'): target.get('assignment', {})}
        else:
            return value
        def profile_api(request):
            return (isinstance(request, dict)
                and KINDS.get(self.resources.get(request.get('resource_id'), {}).get('kind')) == 'api'
                and ((request.get('version') == 'api_execution_assignment_v1'
                        and request.get('service') == 'ebi_hmmer')
                    or (request.get('version') == 'api_service_assignment_v1'
                        and request.get('service') == 'rfam_batch')))
        if any(not profile_api(request) and (not isinstance(request, dict) or request.get('resource_kind') != 'local'
                or not isinstance(request.get('requested_job'), dict)
                or not any(isinstance(request['requested_job'].get(kind), dict)
                    for kind in ('native_protein_structure', 'native_macs2_peak', 'native_lumpy',
                        'native_genomic_overlap', 'native_chromatin_interactions',
                        'native_atac_differential', 'native_expression_nmf',
                        'native_hmmer', 'native_infernal',
                        'native_hmmer_preparation', 'native_infernal_preparation')))
                for request in requests.values()):
            return value
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        selected = []
        for resource_id, request in requests.items():
            if profile_api(request):
                from .execution_prompt import select_profile_api_execution_values
                # Validate the display operands without changing their original
                # assignment or calling a provider, parser or calculator.
                if (request['resource_id'] != resource_id
                        or select_profile_api_execution_values(request) is None):
                    return value
                selected.append({'resource_id': resource_id, 'resource_kind': 'api',
                    'endpoint': deepcopy(request.get('endpoint')),
                    'constraints': deepcopy(request.get('constraints', {})),
                    'job': deepcopy(request), 'resource': self._resource_information(resource_id)})
                continue
            kind = next(kind for kind in ('native_macs2_peak', 'native_lumpy', 'native_genomic_overlap',
                'native_chromatin_interactions', 'native_atac_differential',
                'native_expression_nmf', 'native_protein_structure',
                'native_hmmer', 'native_infernal',
                'native_hmmer_preparation', 'native_infernal_preparation')
                if isinstance(request['requested_job'].get(kind), dict))
            job = deepcopy(request['requested_job'][kind])
            if kind == 'native_lumpy':
                from .lumpy_request_binding import scientific_job_view
                job = scientific_job_view(job)
            elif kind == 'native_macs2_peak':
                from .macs2_peak_presentation import macs2_peak_scientific_job_view
                job = macs2_peak_scientific_job_view(job)
            elif kind == 'native_genomic_overlap':
                from .genomic_overlap_presentation import genomic_overlap_scientific_job_view
                job = genomic_overlap_scientific_job_view(job)
            elif kind == 'native_chromatin_interactions':
                from .chromatin_interaction_presentation import chromatin_scientific_job_view
                job = chromatin_scientific_job_view(job)
            elif kind == 'native_atac_differential':
                from .atac_differential_presentation import atac_scientific_job_view
                job = atac_scientific_job_view(job)
            elif kind == 'native_expression_nmf':
                from .expression_nmf_presentation import expression_nmf_scientific_job_view
                job = expression_nmf_scientific_job_view(job)
            elif kind in ('native_hmmer', 'native_infernal',
                    'native_hmmer_preparation', 'native_infernal_preparation'):
                from .native_profile_presentation import native_profile_scientific_job_view
                job = native_profile_scientific_job_view(job)
            selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                'endpoint': deepcopy(request.get('endpoint')),
                'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                'resource': self._resource_information(resource_id)})
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1',
            'scientific_question': parent['scientific_question'],
            'selected_tool_info': parent['selected_tool_info'], 'requests': selected,
            'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'),
            'result_description': value.get('execution_target_description')})
        return value

    def decision_context(self, context, current_view):
        from .lumpy_request_binding import is_compact_assignment as is_lumpy_assignment
        if is_lumpy_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {
                'practical_assignment': plain(context.assignment),
                'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress},
                'practical_completed': self.state(context).completion_proof() is not None})

        from .macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment
        if is_macs2_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {
                'practical_assignment': plain(context.assignment),
                'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress},
                'practical_completed': self.state(context).completion_proof() is not None})
        from .flux_balance_request_binding import is_compact_assignment
        if is_compact_assignment(plain(context.assignment)):
            state = self.state(context)
            progress = state.credit_view()
            return {'practical_assignment': plain(context.assignment),
                'practical_progress': {key: deepcopy(progress[key]) for key in
                    ('credit', 'satisfied_keys') if key in progress},
                'practical_completed': state.completion_proof() is not None}
        if context.role in {'launch_local', 'launch_hpc'}:
            value = self._delegate(context).decision_context(context, current_view)
            return self._with_selected_execution_task(context, value)
        value = {'execution_assignment': plain(context.assignment),
                 'execution_progress': self.facts(context, {})}
        if context.role == 'results':
            assignment = plain(context.assignment)
            if self.local_file_sources.applies(context):
                from .local_file_capture_results import ORIGIN
                value['execution_target'] = {'resource_kind': 'local', **(
                    {'output_roles': deepcopy(assignment['selector']['output_roles'])}
                    if (is_macs2_file_source_selector(assignment['selector'])
                        or is_lumpy_file_source_selector(assignment['selector'])) else
                    {'files': deepcopy(assignment['selector']['files'])})}
                value['execution_target_description'] = {
                    'status_operations': ['execution.results.status'],
                    'acquisition_operations': ['execution.results.collect'],
                    'provenance': deepcopy(ORIGIN)}
                return self._with_selected_execution_task(context, value)
            retained = self._retained_protein_result(context, assignment, context.scope)
            if self._flux_balance_selector(assignment):
                from .flux_balance_request_binding import scientific_job_view
                target = self._target(context)
                value['execution_target'] = {'resource_kind': 'local',
                    'request': scientific_job_view(target['assignment']['requested_job']['native_flux_balance'])}
                value['execution_target_description'] = {'operation': 'perform_flux_balance_analysis',
                    'mode': assignment['selector']['mode'],
                    'status_operations': ['execution.results.status'],
                    'acquisition_operations': ['execution.results.collect']}
            elif self._fluorescence_selector(assignment):
                from .fluorescence_execution_information import describe_fluorescence_result
                value['execution_target'] = self._target(context)
                value['execution_target_description'] = describe_fluorescence_result(
                    value['execution_target'], selector=assignment['selector'])
            elif self._expression_nmf_selector(assignment):
                from .expression_nmf_execution_information import describe_expression_nmf_result
                value['execution_target'] = self._target(context)
                value['execution_target_description'] = describe_expression_nmf_result(
                    value['execution_target'], selector=assignment['selector'])
            elif self._atac_selector(assignment):
                from .atac_differential_execution_information import describe_atac_result
                value['execution_target'] = self._target(context)
                value['execution_target_description'] = describe_atac_result(
                    value['execution_target'], selector=assignment['selector'])
            elif self._chromatin_selector(assignment):
                from .chromatin_interaction_execution_information import describe_chromatin_result
                value['execution_target'] = self._target(context)
                value['execution_target_description'] = describe_chromatin_result(
                    value['execution_target'], selector=assignment['selector'])
            elif self._genomic_overlap_selector(assignment):
                from .genomic_overlap_execution_information import describe_genomic_overlap_result
                value['execution_target'] = self._target(context)
                # Historical target metadata suffices here. No native source
                # or current executable/status is needed to describe a saved
                # calculation; original receipt authority is checked by _target.
                value['execution_target_description'] = describe_genomic_overlap_result(
                    value['execution_target'], selector=assignment['selector'])
            elif retained is None:
                value['execution_target'] = self._target(context)
                value['execution_target_description'] = self.job_progress_provider.targets.describe_target(
                    value['execution_target']['handle'], context.scope, selector=assignment['selector'])
            else:
                from .protein_structure_execution_information import describe_protein_structure_result
                value['execution_target'] = retained['body']['intent']['target']
                called = retained['body']['handoff_proof']['body']['receipt']['tool_name']
                value['execution_target_description'] = describe_protein_structure_result(
                    value['execution_target'], called_operation=called, selector=assignment['selector'])
            from .bvbrc_data_host import is_bvbrc_request
            if value['execution_target']['resource_kind'] == 'api' and is_bvbrc_request(
                    value['execution_target']['assignment'].get('request')):
                value['own_bvbrc_values'] = self.api_execution.bvbrc_data.own_values(context)
        if context.role == 'launch_api':
            callback = getattr(self.api_execution, 'decision_context', None)
            if callback is not None:
                value.update(callback(context, current_view))
        return self._with_selected_execution_task(context, value)

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        if (is_macs2_file_source_selector(assignment.get('selector'))
                or is_lumpy_file_source_selector(assignment.get('selector'))):
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
        return (retained['body']['intent']['target'] if retained is not None else
            self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope))

    def _retained_protein_result(self, context, assignment, scope):
        """Recover target metadata only from received or own completed authority.

        Scientific operand bytes retain their separate selected-use checks. A
        private staged receipt cannot replace a completed original action here.
        """
        assignment = checked(assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        if assignment['selector'].get('version') != 'protein_structure_result_selector_v1':
            return None
        from .execution_contracts import validate_target
        from .protein_structure_contracts import same
        from .protein_structure_selection import validate_protein_structure_result_selector
        selector = validate_protein_structure_result_selector(assignment['selector'])
        receipts = self.native_protein_structure_results.receipts
        if selector['acquisition'] == 'retained_sheet_only':
            descriptor = selector['saved_sheet']
            received = self.native_protein_structure_returns.authenticate_received_saved_sheet(
                context, descriptor, required_use='recalculate')
            custody = descriptor['custody']
            retained = receipts.read_completed(episode_id=custody['result_episode_id'],
                operation_key=custody['result_operation_key'], scope=plain(scope))
            if (not same(received['custody'], custody)
                    or not same(retained['publication']['custody'], custody)
                    or custody['handoff_ref'] != assignment['handoff_ref']):
                raise ValueError('original_commission_mismatch')
        elif context.role == 'results' and same(assignment, plain(context.assignment)):
            completed = receipts.completed_receipts(context)
            qualified = [receipt for receipt in completed if receipt['body']['handoff_proof'] is not None]
            if not qualified:
                return None
            retained = qualified[0]
            if any(not same(receipt['body']['intent']['target'], retained['body']['intent']['target'])
                    for receipt in qualified):
                raise ValueError('execution_result_original_target_conflict')
        else:
            return None
        target = validate_target(retained['body']['intent']['target'])
        if (context.run_id != self.run_id or target['run_id'] != self.run_id
                or target['handle'] != assignment['handoff_ref']
                or target['resource_kind'] != 'local' or not is_native_protein_structure_target(target)
                or retained['body']['handoff_proof'] is None):
            raise ValueError('original_commission_mismatch')
        self.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        self.store.validate_scope(target['scope'], parent_scope=plain(scope))
        reader = self.job_progress_provider.targets
        resource_id = target['resource_id']
        configuration = self.resources.get(resource_id)
        if (configuration is None or configuration['kind'] != 'local'
                or not same(reader.resources.get(resource_id), configuration)
                or resource_id not in reader.operations):
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
            from .flux_balance_result_selection import validate_flux_balance_result_selector
            selector = validate_flux_balance_result_selector(assignment['selector'])
            return (validate_flux_balance_result_selector(selector,
                job=target['assignment']['requested_job']) if selector['mode'] == 'native_result' else selector)
        if self._masking_selector(assignment) or is_native_blast_masking_target(target):
            if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_result_target_conflict')
            from .sequence_masking_result_views import validate_masking_result_selector
            return validate_masking_result_selector(assignment['selector'],
                operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
        if self._utility_selector(assignment) or is_native_blast_utility_target(target):
            if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_result_target_conflict')
            from .blast_utility_result_views import validate_blast_utility_result_selector
            return validate_blast_utility_result_selector(assignment['selector'],
                operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
        native_fluorescence = 'native_fluorescence' in target.get('assignment', {}).get('requested_job', {})
        if self._fluorescence_selector(assignment) or native_fluorescence:
            if not native_fluorescence or target.get('resource_kind') != 'local':
                raise ValueError('fluorescence_result_target_conflict')
            from .fluorescence_result_contracts import validate_fluorescence_selector
            return validate_fluorescence_selector(assignment['selector'],
                job=target['assignment']['requested_job']['native_fluorescence'])
        native_nmf = 'native_expression_nmf' in target.get('assignment', {}).get('requested_job', {})
        if self._expression_nmf_selector(assignment) or native_nmf:
            if self.native_expression_nmf_results is None:
                raise ValueError('native_expression_nmf_results_binding_unavailable')
            if not native_nmf or target.get('resource_kind') != 'local':
                raise ValueError('expression_nmf_result_target_conflict')
            from .expression_nmf_result_contracts import validate_expression_nmf_result_selector
            return validate_expression_nmf_result_selector(assignment['selector'],
                job=target['assignment']['requested_job']['native_expression_nmf'])
        native_atac = 'native_atac_differential' in target.get('assignment', {}).get('requested_job', {})
        if self._atac_selector(assignment) or native_atac:
            if self.atac_results is None:
                raise ValueError('native_atac_results_binding_unavailable')
            if not native_atac or target.get('resource_kind') != 'local':
                raise ValueError('atac_result_target_conflict')
            from .atac_differential_execution_information import validate_atac_result_selector
            return validate_atac_result_selector(assignment['selector'],
                request=target['assignment']['requested_job']['native_atac_differential']['request'])
        native_chromatin = 'native_chromatin_interactions' in target.get('assignment', {}).get('requested_job', {})
        if self._chromatin_selector(assignment) or native_chromatin:
            if self.native_chromatin_interaction_results is None:
                raise ValueError('native_chromatin_results_binding_unavailable')
            if not native_chromatin or target.get('resource_kind') != 'local':
                raise ValueError('chromatin_result_target_conflict')
            from .chromatin_interaction_execution_information import validate_chromatin_result_selector
            return validate_chromatin_result_selector(assignment['selector'],
                request=target['assignment']['requested_job']['native_chromatin_interactions']['request'])
        native_overlap = 'native_genomic_overlap' in target.get('assignment', {}).get('requested_job', {})
        if self._genomic_overlap_selector(assignment) or native_overlap:
            if self.native_genomic_overlap_results is None:
                raise ValueError('native_genomic_overlap_results_binding_unavailable')
            if not native_overlap or target.get('resource_kind') != 'local':
                raise ValueError('genomic_overlap_result_target_conflict')
            # Reuse the worker's pure selector/ordered-request validation;
            # this does not open files or execute the worker.
            from .genomic_overlap_result_worker import _selector
            from .genomic_overlap_contracts import validate_genomic_overlap_record
            value = validate_genomic_overlap_record('Selector', assignment['selector'])
            value = _selector(value, mode=value['mode'],
                request=target['assignment']['requested_job']['native_genomic_overlap']['request'])
            if (value['mode'] == 'native_result') != (value['saved_sheet_file'] is None):
                raise ValueError('genomic_overlap_result_saved_sheet_mode_conflict')
            if value['saved_sheet_file'] is not None:
                from .genomic_overlap_return_views import SAVED_SOURCE, validate_genomic_overlap_fact_values
                validate_genomic_overlap_fact_values(SAVED_SOURCE, [value['saved_sheet_file']])
            return value
        if (assignment.get('selector', {}).get('version') == 'protein_structure_result_selector_v1'
                or is_native_protein_structure_target(target)):
            if not is_native_protein_structure_target(target):
                raise ValueError('original_commission_mismatch')
            from .protein_structure_selection import validate_protein_structure_result_selector
            return validate_protein_structure_result_selector(assignment['selector'],
                request=target['assignment']['requested_job']['native_protein_structure']['request'])
        if self._comparison_selector(assignment):
            if self.rna_structure_comparison_results is None:
                raise ValueError('rna_comparison_results_binding_unavailable')
            if not is_native_rna_structure_target(target):
                raise ValueError('rna_comparison_anchor_required')
            from .rna_structure_comparison_contracts import validate_rna_comparison_selector
            return validate_rna_comparison_selector(assignment['selector'])
        if is_native_rna_structure_target(target):
            if self.native_rna_structure_results is None:
                raise ValueError('native_rna_structure_results_binding_unavailable')
            from .rna_structure_result_views import validate_rna_structure_result_selector
            return validate_rna_structure_result_selector(assignment['selector'],
                mode=target['assignment']['requested_job']['native_rna_structure']['mode'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from .native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from .native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from .hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from .hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from .blast_pairwise_result_views import validate_native_blast_result_selector
            return validate_native_blast_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast']['program'])
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from .infernal_native_result_views import validate_native_infernal_result_selector
            return validate_native_infernal_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_infernal']['program'])
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from .infernal_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_infernal_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        value = checked(assignment['selector'], NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
        paths = list(value.get('paths', []))
        if 'path' in value:
            if value['path'] in paths:
                raise ValueError('ambiguous_execution_results_selector')
            paths.append(value['path'])
        if not paths or ('offset' in value or 'limit' in value) and 'path' not in value:
            raise ValueError('execution_results_paths_required')
        for path in paths:
            confined(path, target['assignment']['workspace'])
        return value

    def catalog(self, context):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            from .native_flux_balance_results import operation_catalog as fba_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return fba_result_catalog()
        if self.native_blast_masking_results.applies(context):
            from .native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from .native_blast_utility_results import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        if self.native_fluorescence_results.applies(context):
            from .native_fluorescence_results import operation_catalog as fluorescence_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return fluorescence_result_catalog()
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            from .native_expression_nmf_results import operation_catalog as nmf_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return nmf_result_catalog()
        if self.atac_results is not None and self.atac_results.applies(context):
            from .native_atac_differential_results import operation_catalog as atac_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return atac_result_catalog()
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            from .native_chromatin_interaction_results import operation_catalog as chromatin_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return chromatin_result_catalog()
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            from .native_genomic_overlap_results import operation_catalog as overlap_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return overlap_result_catalog()
        if self.native_protein_structure_results.applies(context):
            from .protein_structure_selection import validate_protein_structure_result_selector
            from .native_protein_structure_results import operation_catalog as protein_result_catalog
            validate_protein_structure_result_selector(plain(context.assignment)['selector'])
            return protein_result_catalog()
        if context.role in ROLE_KINDS:
            practical_context = self._practical_context(context)
            return self._delegate(context).catalog(practical_context)
        if context.role == 'launch':
            return launch_operation_catalog()
        target = self._target(context)
        if is_native_protein_structure_target(target):
            self._selector(plain(context.assignment), target)
        if self._comparison_selector(plain(context.assignment)):
            self._selector(plain(context.assignment), target)
            from .rna_structure_comparison_results import operation_catalog as comparison_catalog
            return comparison_catalog()
        if is_native_rna_structure_target(target):
            self._selector(plain(context.assignment), target)
            from .native_rna_structure_results import operation_catalog as rna_result_catalog
            return rna_result_catalog()
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from .native_blast_standard_database_results import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from .native_blast_database_results import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from .native_hmmer_preparation_results import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from .native_hmmer_results import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from .native_blast_results import operation_catalog as blast_result_catalog
            return blast_result_catalog()
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from .native_infernal_results import operation_catalog as infernal_result_catalog
            return infernal_result_catalog()
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from .native_infernal_preparation_results import operation_catalog as preparation_result_catalog
            return preparation_result_catalog()
        return native_result_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        if context.role in ROLE_KINDS:
            self._check_parent_inputs(context)
            practical_context = self._practical_context(context)
            outcome = await self._delegate(context).execute(
                practical_context, tool_name, arguments, operation_key)
            from .flux_balance_request_binding import is_compact_assignment
            if is_compact_assignment(plain(context.assignment)):
                from .flux_balance_request_binding import practical_outcome_view, read_request_binding
                control = read_request_binding(self.store, context.run_id, context.episode_id)
                outcome = {**outcome, 'result': practical_outcome_view(outcome['result'],
                    assignment=plain(practical_context.assignment), control_version=control['version'])}
                outcome.pop('operation_ref', None)
            from .lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, practical_outcome_view as lumpy_outcome_view
            if is_lumpy_assignment(plain(context.assignment)):
                outcome = {**outcome, 'result': lumpy_outcome_view(outcome['result'])}
                outcome.pop('operation_ref', None)

            from .macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, practical_outcome_view as macs2_outcome_view
            if is_macs2_assignment(plain(context.assignment)):
                outcome = {**outcome, 'result': macs2_outcome_view(outcome['result'])}
                outcome.pop('operation_ref', None)
            return outcome
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            if context.role == 'launch':
                return _outcome(self.initial_decision_context(context))
            target = self._target(context)
            if self.local_file_sources.applies(context):
                return await self.local_file_sources.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_flux_balance_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_blast_masking_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_masking_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_blast_utility_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_utility_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_fluorescence_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_fluorescence_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_expression_nmf_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.atac_results is not None and self.atac_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.atac_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_chromatin_interaction_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_genomic_overlap_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self.native_protein_structure_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_protein_structure_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if self._comparison_selector(plain(context.assignment)):
                return await self.rna_structure_comparison_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if is_native_rna_structure_target(target):
                return await self.native_rna_structure_results.execute(context, target, tool_name, arguments, operation_key)
            if is_standard_blast_database_target(target):
                return await self.native_blast_standard_database_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_database_target(target):
                return await self.native_blast_database_results.execute(context, target, tool_name, arguments, operation_key)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            if is_native_hmmer_preparation_target(target):
                return await self.native_hmmer_preparation_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if is_native_hmmer_target(target):
                return await self.native_hmmer_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_target(target):
                return await self.native_blast_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_target(target):
                return await self.native_infernal_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_preparation_target(target):
                return await self.native_infernal_preparation_results.execute(
                    context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from .native_file_capture import NativeFileCaptureError
            if (isinstance(error, NativeFileCaptureError)
                    and self.local_file_sources.applies(context)
                    and error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                # Keep the selected action pending so its independently
                # committed files remain recoverable under the same key.
                raise
            return _outcome(code=str(error))

    def _result_directory(self, context, *, create=True):
        if type(create) is not bool:
            raise TypeError('execution_results_directory_create_boolean_required')
        directory = self.directory/'execution-results'/digest([context.run_id, context.episode_id])
        manifest = {'run_id': context.run_id, 'episode_id': context.episode_id,
            'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory/'assignment.json', manifest)
        else:
            try:
                existing = _read(directory/'assignment.json')
            except FileNotFoundError as error:
                raise ValueError('execution_results_assignment_control_missing') from error
            if canonical(existing) != canonical(manifest):
                raise ValueError('practical_immutable_record_conflict')
        return directory

    def _windows(self, selector):
        values = {path: (0, None) for path in selector.get('paths', [])}
        if 'path' in selector:
            values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
        return values

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id+':'+episode_id+':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

    async def _execute_native_results(self, context, target, tool_name, arguments, operation_key):
        self._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        selector = self._selector(plain(context.assignment), target)
        requested = self._windows(selector)
        windows = []
        if tool_name == 'execution.results.read':
            if arguments['path'] not in requested:
                raise ValueError('execution_results_selector_conflict')
            start, length = requested[arguments['path']]
            if (arguments['offset'] < start or length is not None
                    and arguments['offset'] + arguments['limit'] > start + length):
                raise ValueError('execution_results_selector_conflict')
            windows = [arguments]
        elif tool_name == 'execution.results.collect':
            windows = [{'path': path, 'offset': start,
                'limit': min(self.log_window_bytes, 1024*1024, length) if length is not None
                    else min(self.log_window_bytes, 1024*1024)}
                for path, (start, length) in requested.items()]
        directory = self._result_directory(context)
        key = digest(operation_key)
        intent = {'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments,
            'target': target, 'assignment': plain(context.assignment)}
        receipt_path = directory/(key+'.receipt.json')
        if receipt_path.exists():
            _immutable(directory/(key+'.intent.json'), intent)
            body = _read(receipt_path)
        else:
            previous = self.store.db.execute('SELECT decision_index FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND result IS NOT NULL ORDER BY decision_index DESC',
                (self.run_id, context.episode_id))
            for row in previous:
                if self._proof_for_action(context, f'{self.run_id}:{context.episode_id}:{row[0]}') is not None:
                    raise ValueError('execution_results_assignment_already_completed')
            _immutable(directory/(key+'.intent.json'), intent)
            observation_path = directory/(key+'.observation.json')
            if not observation_path.exists():
                observed = self.job_progress_provider.targets.observe_target(target,
                    operation_key=operation_key)
                _immutable(observation_path, observed)
            observation = _read(observation_path)
            acquired, failures = [], []
            for index, window in enumerate(windows):
                path = directory/(key+f'.window-{index}.json')
                if not path.exists():
                    try:
                        data = self.job_progress_provider.targets.read_file(target, **window,
                            operation_key=operation_key+f':file:{index}')
                        value = {'window': data, 'failure': None}
                    except (ValueError, OSError) as error:
                        value = {'window': None, 'failure': {'path': window['path'],
                            'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable',
                            'exception_type': type(error).__name__}}
                    _immutable(path, value)
                value = _read(path)
                if value['window'] is not None:
                    acquired.append(value['window'])
                else:
                    failures.append(value['failure'])
            body = {'version': 'execution_result_information_v2', 'run_id': context.run_id,
                'episode_id': context.episode_id, 'scope': plain(context.scope),
                'assignment': plain(context.assignment), 'operation_key': operation_key,
                'tool_name': tool_name, 'arguments': arguments, 'target': target,
                'observation': observation, 'windows': acquired, 'failures': failures,
                'acquisition_origin': deepcopy(NATIVE_RESULT_ORIGIN)}
            _immutable(receipt_path, body)
        reference = self._publish_result(context, body)
        return _outcome(body, references=[reference])

    def _publish_result(self, context, body):
        self._validate_result_body(body, context.scope)
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_'+digest([
            context.run_id, context.episode_id, body['operation_key']]), 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        return self.store.put('source', payload, origin='tool')['id']

    def _validate_result_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key',
            'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
        if (not isinstance(body, dict) or set(body) != fields
                or body['version'] != 'execution_result_information_v2' or body['run_id'] != self.run_id
                or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
            raise ValueError('invalid_execution_result_information')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], scope)
        if canonical(target) != canonical(body['target']):
            raise ValueError('execution_result_original_target_conflict')
        selector = self._selector(body['assignment'], target)
        requested = self._windows(selector)
        row = self._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, body['episode_id'])).fetchone()
        if episode is not None:
            message = json.loads(episode['request'])['message']
            if (message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope']
                    or json.loads(episode['path'])[-1][0] != 'results'):
                raise ValueError('execution_result_original_assignment_conflict')
        for window in body['windows']:
            if window['path'] not in requested:
                raise ValueError('execution_result_selector_conflict')
            raw = base64.b64decode(window['bytes_base64'], validate=True)
            start, length = requested[window['path']]
            if (window['offset'] < start or window['returned_bytes'] != len(raw)
                    or length is not None and window['offset']+len(raw) > start+length
                    or window['size_bytes'] < 0):
                raise ValueError('execution_result_window_conflict')
        # The immutable receiver journal, rather than model assertions or a
        # forged Store artifact, owns this selected acquisition.
        directory = self.directory/'execution-results'/digest([self.run_id, body['episode_id']])
        path = directory/(digest(body['operation_key'])+'.receipt.json')
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
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_'+digest([
            body['run_id'], body['episode_id'], body['operation_key']]), 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': None,
            'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        expected = identity('source', {'origin': 'tool', 'record': payload})
        if (reference != expected or raw != canonical(body).encode()
                or {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != payload):
            raise ValueError('execution_result_source_identity_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if (outcome.get('status') != 'completed' or outcome.get('result') != body
                    or reference not in outcome.get('record_refs', [])):
                raise ValueError('execution_result_saved_outcome_conflict')
        return body

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from .episode_receipts import EpisodeReceipts
            table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
            if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                    (self.run_id, context.episode_id)).fetchone():
                receipts = EpisodeReceipts(self.store, self.run_id)
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(receipts.known(context.episode_id)),
                    'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
            else:
                rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(dict.fromkeys(ref for row in rows
                        for ref in json.loads(row[0]).get('record_refs', []))), 'initial_known_record_refs': []}
        supplied = plain(supplied)
        if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
            raise ValueError('execution_receiver_identity_conflict')
        for key in ('known_record_refs', 'initial_known_record_refs'):
            if not isinstance(supplied.get(key), list) or any(not isinstance(ref, str) or not ref for ref in supplied[key]):
                raise ValueError('execution_receiver_references_required')
        if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
            raise ValueError('execution_initial_references_must_be_known')
        return supplied

    def _context_target(self, context, target):
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding)
        if is_lumpy_launch(plain(context.assignment)) or is_lumpy_assignment(plain(context.assignment)):
            own = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            original = read_lumpy_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])
                    or canonical(target['assignment']) != canonical(original['requests'][0]['assignment'])
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target

        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding)
        if is_macs2_launch(plain(context.assignment)) or is_macs2_assignment(plain(context.assignment)):
            own = read_macs2_binding(self.store, self.run_id, context.episode_id)
            original = read_macs2_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(canonical(row['assignment']) == canonical(target['assignment']) for row in own['requests'])
                    or canonical(target['assignment']) != canonical(original['requests'][0]['assignment'])
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        from .flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if (is_compact_launch(plain(context.assignment)) or is_compact_assignment(plain(context.assignment))):
            own = read_request_binding(self.store, self.run_id, context.episode_id)
            original = read_request_binding(self.store, self.run_id, target['origin_episode_id'])
            if (not any(row['assignment'] == target['assignment'] for row in own['requests'])
                    or target['assignment'] != original['requests'][0]['assignment']
                    or context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        if context.role == 'launch':
            self._match_request(self._launch(plain(context.assignment)), target['assignment'])
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
            handoffs, results = {}, {}
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1',
                            'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
                            'native_protein_structure_bundle_v1',
                            'native_rna_structure_bundle_v1'}:
                        # Original bundle acquisitions have their own exact-row
                        # receipts; they are not current-filesystem byte windows.
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if (source.get('provider') != 'episode.practical_receipt'
                        and not (self.api_execution is not None
                            and self.api_execution.is_handoff_source(reference))):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue  # A preparation/status-only receipt is no handoff.
                try:
                    self._context_target(context, target)
                except ValueError:
                    # An inherited handoff for different work stays valid context,
                    # without becoming this assignment's contribution or endpoint.
                    continue
                if returnable:
                    handoffs[reference] = target
            return selection, handoffs, results

    def _forwards_bvbrc_reports(self, role):
        return (role in {'annotation', 'scientific_process'} and self.api_execution is not None
            and any(service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def _forwards_minhash_reports(self, role):
        return (role in {'annotation', 'scientific_process'} and self.api_execution is not None
            and any(service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

    def received_report_sources(self, role):
        result = {}
        if role in {'annotation', 'scientific_process'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = self.fact_sources('results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if self.native_flux_balance_returns is not None and role in {'annotation', 'scientific_process'}:
            from .flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            if self.native_flux_balance_returns.ordinary_backend is None:
                sources = {name: sources[name] for name in (
                    'flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')}
            result.update(sources)
        if role in {'annotation', 'scientific_process'}:
            from .sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from .blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'scientific_process'}:
            from .uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self._has_enrichr() and role in {'annotation', 'scientific_process'}:
            from .enrichr_contracts import enrichr_fact_sources
            result.update(enrichr_fact_sources())
        if self._has_addgene() and role in {'annotation', 'scientific_process'}:
            from .addgene_sequence_returns import addgene_sequence_fact_sources
            result.update(addgene_sequence_fact_sources())
        if role in {'annotation', 'scientific_process'}:
            from .fluorescence_return_views import fluorescence_fact_sources
            result.update(fluorescence_fact_sources())
        if self.native_expression_nmf_returns is not None and role in {'annotation', 'scientific_process'}:
            from .expression_nmf_return_views import expression_nmf_fact_sources
            result.update(expression_nmf_fact_sources())
        if self.atac_returns is not None and role in {'annotation', 'scientific_process'}:
            from .atac_differential_return_views import atac_fact_sources
            result.update(atac_fact_sources())
        if self.native_chromatin_interaction_returns is not None and role in {'annotation', 'scientific_process'}:
            from .chromatin_interaction_return_views import chromatin_fact_sources
            result.update(chromatin_fact_sources())
        if self.native_genomic_overlap_returns is not None and role in {'annotation', 'scientific_process'}:
            from .genomic_overlap_return_views import genomic_overlap_fact_sources
            result.update(genomic_overlap_fact_sources())
        if role in {'annotation', 'scientific_process'}:
            from .protein_structure_result_views import protein_structure_fact_sources
            result.update(protein_structure_fact_sources())
        if self.rna_structure_comparison_returns is not None and role in {'annotation', 'scientific_process'}:
            from .rna_structure_comparison_views import rna_comparison_fact_sources
            result.update(rna_comparison_fact_sources())
        if self.native_rna_structure_returns is not None and role in {'annotation', 'scientific_process'}:
            from .rna_structure_result_views import rna_structure_fact_sources
            result.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from .native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from .hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_infernal_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from .infernal_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self._has_rfam() and role in {'annotation', 'scientific_process'}:
            from .rfam_batch_returns import rfam_fact_sources
            result.update(rfam_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
            from .blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_returns is not None and role in {'annotation', 'scientific_process'}:
            from .infernal_native_result_views import native_infernal_fact_sources
            result.update(native_infernal_fact_sources())
            result['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._forwards_bvbrc_reports(role):
            from .bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._forwards_minhash_reports(role):
            from .bvbrc_minhash_views import minhash_fact_sources
            result.update(minhash_fact_sources())
        if self._has_appservice() and role in {'annotation', 'scientific_process'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'scientific_process'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if (self.native_flux_balance_returns is not None
                and context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None):
            result.update(self.native_flux_balance_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self._has_enrichr() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.enrichr_returns.facts_for_closure(context, schema))
        if self._has_addgene() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.addgene_returns.received_facts(context, schema))
        if context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None:
            result.update(self.native_fluorescence_returns.facts_for_closure(context, schema))
        if (self.native_expression_nmf_returns is not None
                and context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None):
            result.update(self.native_expression_nmf_returns.facts_for_closure(context, schema))
        if (self.atac_returns is not None and context.role in {'annotation', 'scientific_process'}
                and schema.get('properties') is not None):
            result.update(self.atac_returns.facts_for_closure(context, schema))
        if (self.native_chromatin_interaction_returns is not None
                and context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None):
            result.update(self.native_chromatin_interaction_returns.facts_for_closure(context, schema))
        if (self.native_genomic_overlap_returns is not None
                and context.role in {'annotation', 'scientific_process'} and schema.get('properties') is not None):
            # Runtime freezes this private provenance alongside public facts.
            # Only registered x-sources are projected into the parent form.
            result.update(self.native_genomic_overlap_returns.facts_for_closure(context, schema))
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_protein_structure_returns.received_facts(context, schema))
        if self.rna_structure_comparison_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.rna_structure_comparison_returns.received_facts(context, schema))
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_rna_structure_returns.received_facts(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.rfam_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._forwards_minhash_reports(context.role):
            result.update(self.api_execution.minhash.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
            # Execution roles already supply their own/received support facts
            # through facts(); only the scientific roles need this forwarding.
            if any(node.get('x-source') == 'bvbrc_appservice_support_refs'
                    for node in schema.get('properties', {}).values()):
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
        if context.role not in {'annotation', 'scientific_process'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if self._has_addgene():
            from .addgene_sequence_returns import CLOSURE_PREFIX
            frozen = self.api_execution.addgene_returns.facts_for_closure(context, schema)
            if CLOSURE_PREFIX in frozen:
                result[CLOSURE_PREFIX] = frozen[CLOSURE_PREFIX]
        if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
            result.update(self.native_flux_balance_returns.ordinary_closure_facts(context, schema))
        return result

    def resolve_received_reference(self, context, reference, namespace):
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
            resolved = (self.api_execution.uniprot_returns.resolve_own(context, reference, namespace)
                if context.role == 'results' else
                self.api_execution.uniprot_returns.resolve_received(context, reference, namespace))
            if resolved is not None:
                return resolved
        if self._has_enrichr():
            resolved = (self.api_execution.enrichr_returns.resolve_own(context, reference, namespace)
                if context.role == 'results' else
                self.api_execution.enrichr_returns.resolve_received(context, reference, namespace))
            if resolved is not None:
                return resolved
        if self._has_addgene():
            resolved = (self.api_execution.addgene_returns.resolve_own(context, reference, namespace)
                if context.role == 'results' else
                self.api_execution.addgene_returns.resolve_received(context, reference, namespace))
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
            from .rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
            if namespace in COMPARISON_NAMESPACES:
                return (self.rna_structure_comparison_results.resolve(context, reference, namespace)
                    if context.role == 'results' else
                    self.rna_structure_comparison_returns.resolve_received(context, reference, namespace))
            access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
        if self.native_rna_structure_results is not None:
            # This callback precedes Workflow's generic Store fallback, even
            # for ordinary scientific receivers and old expanded receipts.
            access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if context.role in {'annotation', 'scientific_process'}:
                resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from .bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                # Results owns its publication. The normal role resolver below
                # validates those facts; there is no child return to consult.
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from .bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from .bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
            from .bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
            from .bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            from .bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
            from .bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.application_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_bvbrc_reports(context.role):
            resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_minhash_reports(context.role):
            resolved = self.api_execution.minhash.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        for results in (self.native_hmmer_preparation_results, self.native_infernal_preparation_results):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

    def validate_received_report(self, context, form, schema):
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
        if self._forwards_bvbrc_reports(context.role):
            self.api_execution.bvbrc_data.validate_received_report(context, form, schema)
        if self._forwards_minhash_reports(context.role):
            self.api_execution.minhash.validate_received_report(context, form, schema)

    def fact_sources(self, role):
        from .hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if role == 'results':
            from .local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            for source, schema, meaning in (
                    ('execution_file_source_refs', SOURCE_REFS_SCHEMA,
                     'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'),
                    ('execution_file_capture_outcomes', OUTCOMES_SCHEMA,
                     'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
                values[source] = {'type': 'array', 'meaning': meaning,
                    'report_schema': deepcopy(schema)}
        if self.native_flux_balance_results is not None and role == 'results':
            from .flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            values.update({name: sources[name] for name in (
                'flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')})
        from .sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from .blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        if self._has_uniprot() and role == 'results':
            from .uniprot_return_contracts import uniprot_fact_sources
            values.update(uniprot_fact_sources())
        if self._has_enrichr() and role == 'results':
            from .enrichr_contracts import enrichr_fact_sources
            values.update(enrichr_fact_sources())
        if self._has_addgene() and role == 'results':
            from .addgene_sequence_returns import addgene_sequence_fact_sources
            values.update(addgene_sequence_fact_sources())
        if role == 'results':
            from .fluorescence_return_views import fluorescence_fact_sources
            values.update(fluorescence_fact_sources())
        if self.native_expression_nmf_results is not None and role == 'results':
            from .expression_nmf_return_views import expression_nmf_fact_sources
            values.update(expression_nmf_fact_sources())
        if self.atac_results is not None and role == 'results':
            from .atac_differential_return_views import atac_fact_sources
            values.update(atac_fact_sources())
        if self.native_chromatin_interaction_results is not None and role == 'results':
            from .chromatin_interaction_return_views import chromatin_fact_sources
            values.update(chromatin_fact_sources())
        if self.native_genomic_overlap_results is not None and role == 'results':
            from .genomic_overlap_return_views import genomic_overlap_fact_sources
            values.update(genomic_overlap_fact_sources())
        if role == 'results':
            from .protein_structure_result_views import protein_structure_fact_sources
            values.update(protein_structure_fact_sources())
        if self.rna_structure_comparison_results is not None and role == 'results':
            from .rna_structure_comparison_views import rna_comparison_fact_sources
            values.update(rna_comparison_fact_sources())
        if self.native_rna_structure_results is not None:
            from .rna_structure_result_views import rna_structure_fact_sources
            values.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from .native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from .hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_infernal_preparation_results is not None:
            from .infernal_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self._has_rfam() and role == 'results':
            from .rfam_batch_returns import rfam_fact_sources
            values.update(rfam_fact_sources())
        if self.native_blast_results is not None:
            from .blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_results is not None:
            from .infernal_native_result_views import native_infernal_fact_sources
            values.update(native_infernal_fact_sources())
            values['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from .bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any(service.service == 'bvbrc_minhash'
                for service in self.api_execution.services.values()):
            from .bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            # Definitions are identical across actual practical resources.
            values.update(TerminalExecutionEpisodes.fact_sources(None, role))
        for key, namespace, meaning in (
                ('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database or RNA attempts for partial-output acquisition; failed attempts do not establish a successful native endpoint.'),
                ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER/Infernal/RNA producer bundles retain original attempt outputs matched by digest and requested numerical facts. RNA source delivery alone grants no auxiliary artifacts or unrequested rows.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {
                'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning':
            'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. RNA results mean complete requested original-bundle or retained-sheet delivery, including specific unavailable values; this does not assert native success. Yielding alone is false.'}
        from .native_hmmer_acquisition import ORIGIN as hmmer_origin
        from .native_fluorescence_results import ORIGIN as fluorescence_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin, fluorescence_origin]
        if self.native_flux_balance_results is not None:
            from .native_flux_balance_results import ORIGIN as fba_origin
            origins.append(fba_origin)
        if self.native_expression_nmf_results is not None:
            from .native_expression_nmf_results import ORIGIN as nmf_origin
            origins.append(nmf_origin)
        if self.atac_results is not None:
            from .native_atac_differential_results import ORIGIN as atac_origin, SAVED_ORIGIN as saved_atac_origin
            origins.extend([atac_origin, saved_atac_origin])
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning':
            'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. ATAC records distinguish captured original occurrences from received sheet/table bundles and do not imply native success. No qualified retained data yields null. RNA failed native attempts and saved-sheet recalculations return null even when qualified delivery completes.',
            'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys(
                origin[key] for origin in origins))} for key in NATIVE_RESULT_ORIGIN}),
                'type': ['object', 'null'],
                'x-source': 'execution_result_origin'}}
        from .blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning':
            'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.',
            'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        return values

    def _has_appservice(self):
        return self.api_execution is not None and any(service.service == 'bvbrc_appservice'
            for service in self.api_execution.services.values())

    def _has_rfam(self):
        return self.api_execution is not None and any(service.service == 'rfam_batch'
            for service in self.api_execution.services.values())

    def _has_uniprot(self):
        return self.api_execution is not None and any(service.service == 'uniprot'
            for service in self.api_execution.services.values())

    def _has_enrichr(self):
        return self.api_execution is not None and any(service.service == 'enrichr'
            for service in self.api_execution.services.values())

    def _has_addgene(self):
        return self.api_execution is not None and any(service.service == 'sequence_support'
            for service in self.api_execution.services.values())

    @staticmethod
    def _blast_reference_source():
        return {'type': 'array', 'meaning':
            'Native paired BLAST source, observation and reference records actually returned through this boundary. '
            'References alone do not deliver unrequested numerical rows.',
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                'x-source': 'execution_blast_pairwise_result_refs'}}

    @staticmethod
    def _infernal_reference_source():
        return {'type': 'array', 'meaning':
            'Infernal source, observation and model references actually returned through this episode boundary. '
            'These references alone do not deliver unrequested numerical rows.',
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                'x-source': 'execution_infernal_result_refs'}}

    @staticmethod
    def _appservice_sources():
        from .bvbrc_homology_returns import homology_fact_sources
        from .bvbrc_phylogeny_returns import phylogeny_fact_sources
        from .bvbrc_alignment_returns import alignment_fact_sources
        from .bvbrc_genome_alignment_returns import genome_alignment_fact_sources
        from .bvbrc_proteome_returns import proteome_fact_sources
        from .bvbrc_comparative_systems_returns import comparative_systems_fact_sources
        from .bvbrc_fastqutils_returns import fastqutils_fact_sources
        from .bvbrc_application_returns import application_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **alignment_fact_sources(),
            **genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(),
            **fastqutils_fact_sources(), **application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning':
            'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.',
            'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'},
                'x-source': 'bvbrc_appservice_support_refs'}}}

    def _closed_credit_carrier(self, context):
        """Validate closed runtime metadata without reading scientific payloads."""
        from .episode_return_records import EpisodeReturnRecords
        EpisodeReturnRecords(self.store, self.run_id,
            failure_prefix='execution_closed_credit_').authenticate(context)
        row = self.store.db.execute('SELECT state,completion,archive FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if (context.role not in ROLES or row is None or row['state'] != 'yielded'
                or row['completion'] is None or row['archive'] is None):
            raise ValueError('execution_closed_credit_carrier_conflict')
        completion, archive = json.loads(row['completion']), json.loads(row['archive'])
        if (type(completion) is not dict or set(completion) != {'actions', 'ended_by'}
                or type(completion['actions']) is not int or completion['actions'] < 0
                or type(completion['ended_by']) is not str or not completion['ended_by']
                or type(archive) is not dict or set(archive) != {'file', 'sha256', 'index_sha256'}
                or type(archive['file']) is not str or len(archive['file']) != 69
                or not archive['file'].endswith('.json')
                or any(character not in '0123456789abcdef' for character in archive['file'][:-5])
                or any(type(archive[key]) is not str or len(archive[key]) != 64
                    or any(character not in '0123456789abcdef' for character in archive[key])
                    for key in ('sha256', 'index_sha256'))):
            raise ValueError('execution_closed_credit_carrier_conflict')
        observations = list(self.store.db.execute('SELECT unit_index,observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)))
        if [row['unit_index'] for row in observations] != list(range(completion['actions'])):
            raise ValueError('execution_closed_credit_history_conflict')
        return {'completion': completion, 'archive': archive,
            'history_sha256': digest([list(row) for row in observations])}

    def _closed_credit_receipts(self, context, *, through=None):
        """Pin the original receipt prefix; later delivery never reprices it."""
        from .episode_receipts import EpisodeReceipts
        from .episode_return_records import _same
        db = self.store.db
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name="
                "'runtime_receipt_inheritance'").fetchone() is None or db.execute(
                'SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)).fetchone() is None:
            return None, None, None
        if through is None:
            through = db.execute('SELECT coalesce(max(receipt_index),0) FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()[0]
        if type(through) is not int or through < 0:
            raise ValueError('execution_closed_credit_receipt_conflict')
        own_through, current, seen, manifests, rows = through, context.episode_id, set(), [], []
        while current is not None:
            if current in seen:
                raise ValueError('execution_closed_credit_receipt_conflict')
            seen.add(current)
            manifest = EpisodeReceipts.read_manifest(db, self.run_id, current)
            recorded = db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, current)).fetchone()
            if recorded is None or not _same(json.loads(recorded['request'])['message'].get(
                    'knowledge_inheritance'), manifest):
                raise ValueError('execution_closed_credit_receipt_conflict')
            manifests.append({'episode_id': current, 'manifest': manifest})
            rows.extend(list(row) for row in db.execute('SELECT receipt_index,episode_id,record_ref,receipt_kind,source_index '
                'FROM runtime_record_receipts WHERE run_id=? AND episode_id=? '
                'AND (? IS NULL OR receipt_index<=?) ORDER BY receipt_index',
                (self.run_id, current, through, through)))
            current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
        known = sorted({row[2] for row in rows})
        initial = sorted({row[2] for row in rows if row[1] != context.episode_id or row[3] == 'initial'})
        return {'through_receipt_index': own_through,
            'sha256': digest({'manifests': manifests, 'rows': rows})}, known, initial

    def _closed_credit_value(self, view):
        if (type(view) is not dict or type(view.get('credit')) not in (int, float)
                or not math.isfinite(view['credit'])):
            raise ValueError('execution_closed_credit_view_conflict')

    def _closed_credit_facts(self, context, completion_snapshot):
        """Capture the already projected view once, inside the closing facts."""
        if completion_snapshot is None:
            return {}
        capture = completion_snapshot.get('operational_credit_snapshot')
        completion = completion_snapshot.get('completion')
        if capture is None or completion is None:
            return {}
        # Existing histories are never upgraded or backfilled by a later read.
        if self.store.db.execute('SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)).fetchone() is not None:
            return {}
        if type(capture) is not dict or set(capture) != {'view', 'selection'}:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        capture = json.loads(canonical(plain(capture)))
        carrier = self._closed_credit_carrier(context)
        if (completion.get('ended_by') != carrier['completion']['ended_by']
                or type(completion.get('units_consumed')) is not int
                or completion['units_consumed'] != carrier['completion']['actions']):
            raise ValueError('execution_closed_credit_carrier_conflict')
        selection = self._selection(context, capture['selection'])
        prefix, known, initial = self._closed_credit_receipts(context)
        if prefix is not None and (selection['known_record_refs'] != known
                or selection['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        self._closed_credit_value(capture['view'])
        return {_CLOSED_CREDIT: {'version': _CLOSED_CREDIT,
            'context_sha256': digest(context.as_record()), 'binding_sha256': digest(self.as_record()),
            'selection': selection, 'receipt_prefix': prefix,
            'completion_sha256': digest(carrier['completion']), 'archive_sha256': digest(carrier['archive']),
            'history_sha256': carrier['history_sha256'],
            'view': capture['view'], 'view_sha256': digest(capture['view'])}}

    def _closed_operational_credit_view(self, context, receiver_selection):
        """Return only the original closed view, never another projection."""
        from .episode_return_records import _same
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_forms'").fetchone() is None:
            return None
        row = self.store.db.execute('SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        facts = json.loads(row['facts'])
        if _CLOSED_CREDIT not in facts:
            return None
        value = facts[_CLOSED_CREDIT]
        fields = {'version', 'context_sha256', 'binding_sha256', 'selection', 'receipt_prefix',
            'completion_sha256', 'archive_sha256', 'history_sha256', 'view', 'view_sha256'}
        if row['form'] is None or type(value) is not dict or set(value) != fields or value['version'] != _CLOSED_CREDIT:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        carrier = self._closed_credit_carrier(context)
        if (value['context_sha256'] != digest(context.as_record()) or value['binding_sha256'] != digest(self.as_record())
                or value['completion_sha256'] != digest(carrier['completion'])
                or value['archive_sha256'] != digest(carrier['archive'])
                or value['history_sha256'] != carrier['history_sha256']):
            raise ValueError('execution_closed_credit_carrier_conflict')
        saved = self._selection(context, value['selection'])
        prefix = value['receipt_prefix']
        if prefix is not None and (type(prefix) is not dict or set(prefix) != {'through_receipt_index', 'sha256'}):
            raise ValueError('execution_closed_credit_receipt_conflict')
        actual, known, initial = self._closed_credit_receipts(context,
            through=None if prefix is None else prefix['through_receipt_index'])
        if not _same(actual, prefix) or prefix is not None and (
                saved['known_record_refs'] != known or saved['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        supplied = self._selection(context, receiver_selection)
        if (not set(saved['known_record_refs']) <= set(supplied['known_record_refs'])
                or supplied['initial_known_record_refs'] != saved['initial_known_record_refs']):
            raise ValueError('execution_closed_credit_receipt_conflict')
        if prefix is not None:
            _, current_known, current_initial = self._closed_credit_receipts(context)
            if (set(supplied['known_record_refs']) != set(current_known)
                    or set(supplied['initial_known_record_refs']) != set(current_initial)):
                raise ValueError('execution_closed_credit_receipt_conflict')
        elif supplied['known_record_refs'] != saved['known_record_refs']:
            raise ValueError('execution_closed_credit_receipt_conflict')
        view = json.loads(canonical(value['view']))
        if value['view_sha256'] != digest(view):
            raise ValueError('execution_closed_credit_view_conflict')
        self._closed_credit_value(view)
        if not _same(view['credit'], facts.get('credit')):
            raise ValueError('execution_closed_credit_view_conflict')
        return view

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot),
            **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from .hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        if self.native_flux_balance_results is not None:
            from .flux_balance_return_views import fba_fact_sources
            native_empty.update({source: [] for source in fba_fact_sources()})
            if self.native_flux_balance_results.applies(context):
                return {**native_empty, **self.native_flux_balance_results.facts(context)}
        from .sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from .blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        from .fluorescence_return_views import FACT_SOURCES as FLUORESCENCE_SOURCES
        native_empty.update({source: [] for source in FLUORESCENCE_SOURCES})
        if self.native_fluorescence_results.applies(context):
            return {**native_empty, **self.native_fluorescence_results.facts(context)}
        if self.native_expression_nmf_results is not None:
            from .expression_nmf_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_expression_nmf_results.applies(context):
                return {**native_empty, **self.native_expression_nmf_results.facts(context)}
        if self.atac_results is not None:
            from .atac_differential_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.atac_results.applies(context):
                return {**native_empty, **self.atac_results.facts(context)}
        if self.native_chromatin_interaction_results is not None:
            from .chromatin_interaction_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_chromatin_interaction_results.applies(context):
                return {**native_empty, **self.native_chromatin_interaction_results.facts(context)}
        if self.native_genomic_overlap_results is not None:
            from .genomic_overlap_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_genomic_overlap_results.applies(context):
                return {**native_empty, **self.native_genomic_overlap_results.facts(context)}
        from .protein_structure_result_views import protein_structure_fact_sources
        native_empty.update({source: [] for source in protein_structure_fact_sources()})
        if self.native_protein_structure_results.applies(context):
            return {**native_empty, **self.native_protein_structure_results.facts(context, verify_artifacts=False)}
        if self.rna_structure_comparison_results is not None:
            from .rna_structure_comparison_views import rna_comparison_fact_sources
            native_empty.update({source: [] for source in rna_comparison_fact_sources()})
            if self.rna_structure_comparison_results.applies(context):
                from .rna_structure_result_views import rna_structure_fact_sources
                native_empty.update({source: [] for source in rna_structure_fact_sources()})
                return {**native_empty, **self.rna_structure_comparison_results.facts(context)}
        if self.native_rna_structure_results is not None:
            from .rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
            if self.native_rna_structure_results.applies(context):
                return {**native_empty, **self.native_rna_structure_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from .native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from .native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from .hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_infernal_preparation_results is not None:
            from .infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_infernal_preparation_results.applies(context):
                return {**native_empty, **self.native_infernal_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from .blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_infernal_results is not None:
            from .infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
            if self.native_infernal_results.applies(context):
                return {**native_empty, **self.native_infernal_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return {**native_empty, **self.api_execution.facts(context, completion_snapshot), 'execution_result_origin': None}
        extra = self._delegate(context).facts(self._practical_context(context), completion_snapshot) if context.role in {'launch_local', 'launch_hpc'} else {}
        # Publication above completes before this operation's metadata snapshot.
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            if context.role in {'launch_local', 'launch_hpc'}:
                # Selected receipt publication may precede runtime result storage.
                for reference in extra['practical_receipt_refs']:
                    try:
                        target, _, returnable = read(reference, context.scope)
                        target = self._context_target(context, target)
                        if returnable:
                            handoffs[reference] = target
                    except ValueError:
                        pass
            completed = (extra.get('practical_completed', False) if context.role in ROLE_KINDS else
                any(read(reference, context.scope)[1] for reference in handoffs)
                if context.role == 'launch' else self._native_results_complete(context, list(results.values())))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs),
                    **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)}
                       if self._has_appservice() else {}),
                    'execution_blast_hsps': [],
                    'execution_result_refs': sorted(ref for ref, body in results.items() if body['windows']),
                    'execution_file_source_refs': sorted({row['source_ref'] for body in results.values()
                        for row in body.get('captured_files', []) if row['source_ref'] is not None}),
                    'execution_file_capture_outcomes': (self.local_file_sources.outcomes_for_context(context)
                        if self.local_file_sources.applies(context) else []),
                    'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any(
                        body['windows'] for body in results.values()) else None,
                    'execution_completed': completed}

    def received_form_references(self, context, form, schema, operation_key):
        from .hmmer_native_result_views import FAMILY_SOURCES
        references = []
        native_references = set()
        references.extend(self.local_file_sources.admit_return(context, form, schema, operation_key))
        if self.native_flux_balance_returns is not None:
            references.extend(self.native_flux_balance_returns.record_admission(
                context, form, schema, operation_key))
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
            references.extend(self.native_fluorescence_returns.record_admission(
                context, form, schema, operation_key))
        if self.native_expression_nmf_returns is not None:
            references.extend(self.native_expression_nmf_returns.record_admission(
                context, form, schema, operation_key))
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
            references.extend(self.api_execution.record_bvbrc_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.minhash.record_admission(context, form, schema, operation_key))
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
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs',
                    'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    # This exact native child form was authenticated above.
                    # Reuse only those admitted execution-result references;
                    # other providers and namespaces keep their own resolver.
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and not self.resolve(context, reference, namespace):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))

    def initial_references(self, context):
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding)
        if is_lumpy_launch(plain(context.assignment)) or is_lumpy_assignment(plain(context.assignment)):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            refs = []
            if self._closed_operational_credit_view(context, None) is not None:
                from .native_file_capture import _identity, _metadata
                from .received_native_file_inputs import received_file_context
                known, _ = received_file_context(self.store, context,
                    failure_prefix='lumpy_input_', baseline=True)
                original_initial = {row['record_ref'] for row in self.store.db.execute(
                    "SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=? "
                    "AND receipt_kind='initial'", (self.run_id, context.episode_id))}
                for row in control['requests']:
                    versions = []
                    for supplied in row['input_files']:
                        file = _identity(supplied)
                        reference = file['artifact_ref']
                        version = dict(reference=reference, version=None, content_sha256=file['sha256'])
                        if version not in versions:
                            versions.append(version)
                        if reference not in known or reference not in original_initial:
                            raise ValueError('lumpy_input_original_admission_conflict')
                        if self.resolve_received_reference(context, reference, None) is False:
                            raise ValueError('lumpy_input_protected_reference_denied')
                        metadata = _metadata(self.store, reference)
                        if metadata['sha256'] != file['sha256'] or metadata['size'] != file['size_bytes']:
                            raise ValueError('lumpy_input_file_metadata_conflict')
                        refs.append(reference)
                    if canonical(row['input_versions']) != canonical(versions):
                        raise ValueError('lumpy_input_version_conflict')
                return list(dict.fromkeys(refs))
            for row in control['requests']:
                refs.extend(self._lumpy_inputs(context, row['assignment']))
            return list(dict.fromkeys(refs))
        from .macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding)
        if is_macs2_launch(plain(context.assignment)) or is_macs2_assignment(plain(context.assignment)):
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            refs = []
            if self._closed_operational_credit_view(context, None) is not None:
                from .received_native_file_inputs import received_file_context, received_file_source
                known, receiving_scope = received_file_context(self.store, context,
                    failure_prefix='macs2_peak_input_', baseline=True)
                original_initial = {row['record_ref'] for row in self.store.db.execute(
                    "SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=? "
                    "AND receipt_kind='initial'", (self.run_id, context.episode_id))}
                for row in control['requests']:
                    versions = []
                    for file in row['input_files']:
                        version = dict(reference=file['artifact_ref'], version=None, content_sha256=file['sha256'])
                        if version not in versions:
                            versions.append(version)
                    if canonical(row['input_versions']) != canonical(versions):
                        raise ValueError('macs2_peak_input_version_conflict')
                    reference = row['assignment']['requested_job']['native_macs2_peak']['request']['reference']
                    metadata_refs = [source for value in [reference, *reference['contigs'], *reference['aliases']]
                        for source in value['source_refs']]
                    selected = [file['artifact_ref'] for file in row['input_files']]
                    for reference in [*selected, *metadata_refs]:
                        if reference not in known or reference not in original_initial:
                            raise ValueError('macs2_peak_input_original_admission_conflict')
                        if self.resolve_received_reference(context, reference, None) is False:
                            raise ValueError('macs2_peak_input_protected_reference_denied')
                        if reference in metadata_refs:
                            if reference not in self.store.reference_subset([reference], receiving_scope):
                                raise ValueError('macs2_peak_input_input_outside_scope')
                            received_file_source(self.store, reference, metadata=True, failure_prefix='macs2_peak_input_')
                        refs.append(reference)
                return list(dict.fromkeys(refs))
            for row in control['requests']:
                refs.extend(self._macs2_peak_inputs(context, row['assignment']))
            return list(dict.fromkeys(refs))
        from .flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_assignment(plain(context.assignment)) or is_compact_launch(plain(context.assignment)):
            control = read_request_binding(self.store, self.run_id, context.episode_id)
            return list(dict.fromkeys(version['reference'] for row in control['requests']
                for version in row['input_versions']))
        if self._has_appservice() and (self.api_execution.appservice.owns_context(context)
                or context.role == 'launch' and any(value.get('service') == 'bvbrc_appservice'
                    for value in plain(context.assignment).get('requests', {}).values())):
            return self.api_execution.appservice.initial_references(context)
        if context.role != 'results':
            from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
            from .protein_structure_operands import validate_protein_structure_job_inputs
            assignment = plain(context.assignment)
            requests = (assignment.get('requests', {}).values() if context.role == 'launch' else
                [assignment] if context.role == 'launch_local' else [])
            references = []
            for request in requests:
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
                references.extend(self._fluorescence_inputs(context, request))
                references.extend(self._expression_nmf_inputs(context, request))
                references.extend(self._flux_balance_inputs(context, request))
                references.extend(self._macs2_peak_inputs(context, request))
                references.extend(self._lumpy_inputs(context, request))
                references.extend(self._atac_inputs(context, request))
                references.extend(self._chromatin_inputs(context, request))
                references.extend(self._genomic_overlap_inputs(context, request))
                references.extend(validate_protein_structure_job_inputs(self.store, context, request,
                    returns=self.native_protein_structure_returns))
                references.extend(validate_rna_structure_job_inputs(self.store, context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        selected = [assignment['handoff_ref']]
        target = self._target(context)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        if self.native_fluorescence_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.atac_results is not None and self.atac_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                bundle = selector['saved_sheet_bundle']
                self.atac_returns.authenticate_received_saved_bundle(context, bundle)
                selected.extend([bundle['sheet']['artifact_ref'],
                    *(row['file']['artifact_ref'] for row in bundle['tables'])])
            return list(dict.fromkeys(selected))
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                bundle = selector['saved_sheet_bundle']
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, bundle)
                selected.extend(file['artifact_ref'] for file in [bundle['sheet'], *bundle['tables']])
            return list(dict.fromkeys(selected))
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_genomic_overlap_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self.native_protein_structure_results.applies(context):
            self._selector(assignment, target)
            from .protein_structure_operands import validate_protein_structure_selected_inputs
            return validate_protein_structure_selected_inputs(self.store, context, assignment['selector'],
                handoff_ref=assignment['handoff_ref'], returns=self.native_protein_structure_returns)
        if self._comparison_selector(assignment):
            self._selector(assignment, target)
            from .rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            return validate_rna_comparison_selected_inputs(self.store, context, assignment['selector'],
                anchor_handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns)
        if is_native_rna_structure_target(target):
            from .native_rna_structure_result_publication import validate_rna_structure_selected_inputs
            selected.extend(validate_rna_structure_selected_inputs(self.store, context, assignment['selector'],
                handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        if is_standard_blast_database_target(target):
            from .native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from .native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        from .bvbrc_data_host import is_bvbrc_request
        if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
            # Native input pages retain their result-ownership checks. Supplied
            # metadata was authenticated in the parent and inherits its frozen
            # Source/File receipts; it receives no new initial grant here.
            extra = list(dict.fromkeys(row['source_ref'] for row in assignment['selector']['inputs']))
            for reference in extra:
                self.api_execution.bvbrc_data.possession(context, reference)
            selected.extend(extra)
        if target['resource_kind'] == 'api' and target['assignment'].get('service') == 'bvbrc_minhash':
            extra = self.api_execution.minhash._selected_input_refs(assignment)
            for reference in extra:
                self.api_execution.minhash.possession(context, reference)
            selected.extend(reference for reference in extra if reference not in selected)
        return selected

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
                resolved = (self.api_execution.uniprot_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.api_execution.uniprot_returns.resolve_received(context, reference, namespace))
                if resolved is not None:
                    return resolved
            if self._has_enrichr():
                resolved = (self.api_execution.enrichr_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.api_execution.enrichr_returns.resolve_received(context, reference, namespace))
                if resolved is not None:
                    return resolved
            if self._has_addgene():
                resolved = (self.api_execution.addgene_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.api_execution.addgene_returns.resolve_received(context, reference, namespace))
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
                from .rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
                if namespace in COMPARISON_NAMESPACES:
                    return (self.rna_structure_comparison_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.rna_structure_comparison_returns.resolve_received(context, reference, namespace))
                access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_rna_structure_results is not None:
                access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
                from .rna_structure_result_views import IDENTIFIER_NAMESPACES as RNA_NAMESPACES
                if namespace in RNA_NAMESPACES:
                    return (self.native_rna_structure_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_rna_structure_returns.resolve_received(context, reference, namespace))
                if self.native_rna_structure_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_standard_database_results is not None:
                from .native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return (self.native_blast_standard_database_results.resolve(context, reference, namespace)
                        if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace))
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from .native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return (self.native_blast_database_results.resolve(context, reference, namespace)
                        if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace))
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from .hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return (self.native_hmmer_preparation_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace))
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_preparation_results is not None:
                from .infernal_preparation_result_views import IDENTIFIER_NAMESPACES as PREPARATION_NAMESPACES
                if namespace in PREPARATION_NAMESPACES:
                    return (self.native_infernal_preparation_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_infernal_preparation_returns.resolve_received(context, reference, namespace))
                if self.native_infernal_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_rfam():
                from .rfam_batch_returns import IDENTIFIER_NAMESPACES as RFAM_NAMESPACES
                if namespace in RFAM_NAMESPACES:
                    return (self.api_execution.rfam_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.rfam_returns.resolve_received(context, reference, namespace))
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key',
                        'native_blast_search_pointer'}:
                    return (self.native_blast_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_blast_returns.resolve_received(context, reference, namespace))
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_results is not None:
                from .infernal_native_result_views import IDENTIFIER_NAMESPACES as INFERNAL_NAMESPACES
                if namespace in INFERNAL_NAMESPACES:
                    return (self.native_infernal_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_infernal_returns.resolve_received(context, reference, namespace))
                if self.native_infernal_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from .bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return (self.api_execution.homology_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.homology_returns.resolve_received(context, reference, namespace))
                from .bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return (self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace))
                from .bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return (self.api_execution.alignment_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.alignment_returns.resolve_received(context, reference, namespace))
                from .bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return (self.api_execution.genome_alignment_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace))
                from .bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return (self.api_execution.proteome_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.proteome_returns.resolve_received(context, reference, namespace))
                from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return (self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace))
                from .bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return (self.api_execution.fastqutils_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace))
                from .bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
                if namespace in APPLICATION_NAMESPACES:
                    return (self.api_execution.application_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.application_returns.resolve_received(context, reference, namespace))
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from .bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from .episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(
                    self.services, context, reference, namespace))
            if (context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt'
                    and not reference.startswith('source_')):
                return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
            if self.native_hmmer_results.resolve(context, reference, namespace):
                return True
            source = self.store.get(reference)
            if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
                return namespace in {None, 'source'} and self.local_file_sources.read_source(
                    reference, context.scope) is not None
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1',
                        'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
                        'native_protein_structure_bundle_v1',
                        'native_rna_structure_bundle_v1'}:
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
            if (source.get('provider') == 'episode.practical_receipt'
                    or self.api_execution is not None
                        and self.api_execution.is_handoff_source(reference)):
                return False
            if self.services is not None:
                from .episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (
                namespace in {None, kind} or namespace == 'subject' and
                kind in {'input', 'feature', 'product', 'read_subject'}))
        except (ValueError, KeyError, OSError):
            return False

    def validate_report(self, context, form, original_schema):
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, original_schema)
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from .uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                # Validated successful custody supplies closed historical facts.
                # Generic result discovery would otherwise reopen withdrawn bytes.
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        if self._has_enrichr():
            from .enrichr_returns import OWN_WITNESSES, requested_enrichr_fields
            host = self.api_execution.enrichr_returns
            if requested_enrichr_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if (closed is not None and OWN_WITNESSES in closed['facts']
                    and host._successful_closed(context)):
                # Rebuilding also validates the stripped initial-report schema.
                # Authenticate the original full contract, then retain its facts
                # without asking generic discovery to reopen native payloads.
                full_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
                host.facts_for_closure(context, full_schema)
                frozen_facts = closed['facts']
        if self._has_addgene():
            from .addgene_sequence_returns import OWN_BINDINGS, requested_addgene_fields
            host = self.api_execution.addgene_returns
            if requested_addgene_fields(plain(original_schema)):
                host.validate_received_report(context, form, original_schema)
            closed = host._closed(context)
            if closed is not None and OWN_BINDINGS in closed['facts']:
                # Rebuilding the stripped initial form still authenticates the
                # original full return. Partial yield needs no success gate.
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
        fact_fields = {name: declared['x-source']
            for name, declared in plain(original_schema).get('properties', {}).items()
            if declared.get('x-source') is not None}
        if not fact_fields:
            # Initial interpretation forms request no recorded fact projection.
            # Rebuilding them must not reopen unrequested native payloads.
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return self.native_flux_balance_results.credit_view(context, receiver_selection)
        if self.native_blast_masking_results.applies(context):
            return self.native_blast_masking_results.credit_view(context, receiver_selection)
        if self.native_blast_utility_results.applies(context):
            return self.native_blast_utility_results.credit_view(context, receiver_selection)
        if self.native_fluorescence_results.applies(context):
            return self.native_fluorescence_results.credit_view(context, receiver_selection)
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return self.native_expression_nmf_results.credit_view(context, receiver_selection)
        if self.atac_results is not None and self.atac_results.applies(context):
            return self.atac_results.credit_view(context, receiver_selection)
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return self.native_chromatin_interaction_results.credit_view(context, receiver_selection)
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return self.native_genomic_overlap_results.credit_view(context, receiver_selection)
        if self.native_protein_structure_results.applies(context):
            return self.native_protein_structure_results.credit_view(context, receiver_selection)
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            return self.rna_structure_comparison_results.credit_view(context, receiver_selection)
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return self.native_rna_structure_results.credit_view(context, receiver_selection)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return self.native_blast_standard_database_results.credit_view(context, receiver_selection)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return self.native_blast_database_results.credit_view(context, receiver_selection)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return self.native_hmmer_preparation_results.credit_view(context, receiver_selection)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return self.native_infernal_preparation_results.credit_view(context, receiver_selection)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return self.native_blast_results.credit_view(context, receiver_selection)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return self.native_infernal_results.credit_view(context, receiver_selection)
        if self.native_hmmer_results.applies(context):
            return self.native_hmmer_results.credit_view(context, receiver_selection)
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).credit_view(self._practical_context(context), receiver_selection)
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.credit_view(context, receiver_selection)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items()
            if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        # A Launch assignment names one original request per resource. A new
        # physical execution of that same request remains an observation, but
        # cannot earn the original handoff credit a second time.
        baseline = {target['resource_id'] for ref, target in handoffs.items() if ref in initial}
        identities = {target['resource_id'] for target in handoffs.values()}
        handoff_count = len(identities-baseline) if context.role == 'launch' else 0
        mixed = (self.local_file_sources.acquisition_counts(context, selected, results)
            if context.role == 'results' else None)
        acquired_fraction = (self._generic_result_selector_progress(context, results, initial)
            if context.role == 'results' and mixed is None else 0.)
        acquired_count = int(acquired_fraction > 0)
        credit = self.handoff_unit*handoff_count + self.acquired_record_unit*acquired_fraction
        if mixed is not None:
            acquired_count = sum(mixed)
            credit = self.handoff_unit*handoff_count + self.acquired_record_unit*acquired_count
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count,
            **({'new_file_acquisition_count': mixed[1]} if mixed is not None else {}),
            **({'new_acquired_selector_fraction': acquired_fraction}
               if context.role == 'results' and mixed is None else {}),
            'new_acquired_record_count': acquired_count, 'operational_credit_binding': {
                'version': ('execution_received_selector_coverage_credit_v2'
                    if context.role == 'results' and mixed is None else 'execution_received_records_credit_v1'),
                'handoff_unit': self.handoff_unit,
                'acquired_record_unit': self.acquired_record_unit,
                'qualification': ('original_selector_byte_position_union_current_filesystem_version_unverified'
                    if context.role == 'results' and mixed is None else
                    'original_request_resource_scope_selector_and_actual_received_unique_information')}}

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)

    def _generic_result_selector_progress(self, context, results, initial):
        """Credit saved byte positions once, regardless of read boundaries."""
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        if not requested:
            return 0.

        def covered(windows, start, end):
            intervals = sorted((max(start, window['offset']),
                min(end, window['offset'] + window['returned_bytes']))
                for window in windows if window['offset'] < end
                and window['offset'] + window['returned_bytes'] > start)
            total, right = 0, start
            for left, stop in intervals:
                if stop > right:
                    total += stop - max(left, right)
                    right = stop
            return total

        fractions = []
        for path, (start, length) in requested.items():
            windows = [(reference, window) for reference, body in results.items()
                for window in body['windows'] if window['path'] == path]
            observed_end = max((window['size_bytes'] for _, window in windows), default=start)
            end = start + length if length is not None else max(start, observed_end)
            if end <= start:
                fractions.append(0.)
                continue
            all_bytes = covered((window for _, window in windows), start, end)
            old_bytes = covered((window for reference, window in windows if reference in initial), start, end)
            fractions.append((all_bytes - old_bytes) / (end - start))
        return math.fsum(fractions) / len(fractions)

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return False  # The original requested FBA delivery owns completion.
        if self.native_blast_masking_results.applies(context):
            return False  # Its original selected typed-result receipt owns completion.
        if self.native_blast_utility_results.applies(context):
            return False  # Its original selected typed-result receipt owns completion.
        if self.native_fluorescence_results.applies(context):
            return False  # Its original selected calculation delivery owns completion.
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return False  # The original requested NMF delivery receipt owns completion.
        if self.atac_results is not None and self.atac_results.applies(context):
            return False  # The original ATAC requested-delivery receipt owns this endpoint.
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return False  # The exact original chromatin receipt owns completion.
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return False  # Its original qualified result receipt owns completion.
        if self.native_protein_structure_results.applies(context):
            return False  # Only the completed original protein receipt owns this endpoint.
        if is_native_rna_structure_target(self._target(context)):
            return False  # RNA's original requested qualified delivery owns its endpoint.
        if is_standard_blast_database_target(self._target(context)):
            return False  # Only its original frozen publication proves this endpoint.
        if is_native_blast_database_target(self._target(context)):
            return False  # Only its original frozen publication proves this endpoint.
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed'
                  and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            # A pre-terminal read remains useful partial custody. Completion
            # here establishes requested acquisition alongside a successful
            # exact attempt observation; current files have no verified
            # producing-attempt identity or common atomic version.
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max(window['size_bytes'] for window in windows)
            if length is not None:
                end = min(end, start+length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset']+window['returned_bytes'])
            if cursor < end:
                return False
        return True

    def _proof_for_action(self, context, operation_key):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            proof = self.native_flux_balance_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_fluorescence_results.applies(context):
            proof = self.native_fluorescence_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            proof = self.native_expression_nmf_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.atac_results is not None and self.atac_results.applies(context):
            proof = self.atac_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            proof = self.native_chromatin_interaction_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            proof = self.native_genomic_overlap_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_protein_structure_results.applies(context):
            proof = self.native_protein_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            proof = self.rna_structure_comparison_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            proof = self.native_rna_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        prefix = context.run_id+':'+context.episode_id+':'
        index = operation_key.removeprefix(prefix)
        if (not operation_key.startswith(prefix) or not index.isdecimal()
                or str(int(index)) != index):
            return None
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (context.run_id, context.episode_id, int(index))).fetchone()
        if row is None or row['result'] is None:
            return None
        result = json.loads(row['result'])
        if result.get('status') != 'completed':
            return None
        if context.role == 'launch':
            qualified = []
            for reference in result.get('record_refs', []):
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    self._context_target(context, target)
                    if self.job_progress_provider.targets.usable_handoff(target):
                        qualified.append(reference)
                except (ValueError, KeyError):
                    pass
            complete = bool(qualified)
            keys, endpoint = ['received_usable_handoff'], 'usable_handoff'
        else:
            # Only windows actually returned by this completed own action and
            # preceding received records may establish the acquisition endpoint.
            bodies = []
            rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index<=? AND result IS NOT NULL ORDER BY decision_index',
                (context.run_id, context.episode_id, int(index)))
            for earlier in rows:
                outcome = json.loads(earlier[0])
                if outcome.get('status') != 'completed':
                    continue
                for reference in outcome.get('record_refs', []):
                    body = self._read_result(reference, context.scope)
                    if body is not None and body['assignment'] == plain(context.assignment):
                        bodies.append(body)
            complete = self._native_results_complete(context, bodies)
            keys = ['requested_filesystem_acquisition', 'successful_exact_attempt_observed',
                    'attempt_output_version_unverified']
            if self.local_file_sources.applies(context):
                keys = ['requested_complete_file_sources', 'exact_attempt_terminal_quiescent_observed',
                    'attempt_output_version_unverified']
            endpoint = 'usable_handoff'
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result,
            'endpoint': endpoint, 'validation_keys': keys}
        if context.role == 'results':
            receipt['supporting_receipt_sha256s'] = [digest(body) for body in bodies]
        return {'version': 'practical_completion_v1', 'run_id': context.run_id,
            'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
            'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt),
            'validation_keys': keys}

    def completion_for_action(self, context, operation_key):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            proof = self.native_flux_balance_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_fluorescence_results.applies(context):
            proof = self.native_fluorescence_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            proof = self.native_expression_nmf_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.atac_results is not None and self.atac_results.applies(context):
            proof = self.atac_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            proof = self.native_chromatin_interaction_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            proof = self.native_genomic_overlap_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_protein_structure_results.applies(context):
            proof = self.native_protein_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            proof = self.rna_structure_comparison_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            proof = self.native_rna_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if context.role in ROLE_KINDS:
            return self._delegate(context).completion_for_action(self._practical_context(context), operation_key)
        if context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.completion_for_action(context, operation_key)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            proof = self.native_hmmer_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            proof = self.native_infernal_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            proof = self.native_blast_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            proof = self.native_infernal_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_hmmer_results.applies(context):
            proof = self.native_hmmer_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._proof_for_action(context, operation_key)

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from method_loop.identities import UnitRef
        from .episode_return_records import _same
        from .numerical import NumericBand
        from .practical_yield import ESTIMATOR_VERSION
        from .macs2_peak_request_binding import is_compact_assignment, materialized_assignment
        assignment = (materialized_assignment(self.store, context)
            if is_compact_assignment(plain(context.assignment)) else context.assignment)
        from .lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            materialized_assignment as materialized_lumpy_assignment)
        if is_lumpy_assignment(plain(context.assignment)):
            assignment = materialized_lumpy_assignment(self.store, context)
        matches = 0
        for row in self.store.db.execute('SELECT unit_index,observation FROM runtime_observations '
                'WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)):
            try:
                observed = json.loads(row['observation'])
                supplied = observed['credit']
                if type(supplied) is not dict or not _same(supplied.get('practical_completion'), proof):
                    continue
                index = observed['decision_index']
                unit = UnitRef.from_record(observed['unit_ref'])
                estimate = observed['step']['estimate']
                diagnostics, provenance = estimate['diagnostics'], estimate['provenance']
                if (type(index) is int and index >= 0
                        and type(supplied.get('estimation_action_index')) is int
                        and supplied['estimation_action_index'] == index
                        and unit.episode_id == context.episode_id and unit.unit_index == row['unit_index']
                        and proof['run_id'] == self.run_id and proof['episode_id'] == context.episode_id
                        and proof['assignment_sha256'] == digest(assignment)
                        and proof['operation_key'] == f'{self.run_id}:{context.episode_id}:{index}'
                        and type(estimate['turns']) is int and estimate['turns'] == unit.unit_index + 1
                        and provenance['version'] == ESTIMATOR_VERSION
                        and diagnostics['fitting_scope'] == 'verified_assignment_endpoint'
                        and _same(diagnostics['completion_proof'], proof)
                        and type(diagnostics['completion_action_index']) is int
                        and diagnostics['completion_action_index'] == index
                        and _same(diagnostics['completion_unit_ref'], unit.as_record())
                        and _same(estimate['expected_next_gain'], NumericBand.exact(0).as_record())):
                    matches += 1
            except (ValueError, TypeError, KeyError):
                continue
        return matches == 1

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        historical = self._closed_completion_verdict(context, proof)
        if historical is not None:
            return historical
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return proof == self.native_flux_balance_results.completion(context)
        if self.native_blast_masking_results.applies(context):
            return proof == self.native_blast_masking_results.completion(context)
        if self.native_blast_utility_results.applies(context):
            return proof == self.native_blast_utility_results.completion(context)
        if self.native_fluorescence_results.applies(context):
            return proof == self.native_fluorescence_results.completion(context)
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return proof == self.native_expression_nmf_results.completion(context)
        if self.atac_results is not None and self.atac_results.applies(context):
            return proof == self.atac_results.completion(context)
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return proof == self.native_chromatin_interaction_results.completion(context)
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return proof == self.native_genomic_overlap_results.completion(context)
        if self.native_protein_structure_results.applies(context):
            return proof == self.native_protein_structure_results.completion(context)
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            return proof == self.rna_structure_comparison_results.completion(context)
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return proof == self.native_rna_structure_results.completion(context)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return proof == self.native_blast_standard_database_results.completion(context)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return proof == self.native_blast_database_results.completion(context)
        if context.role in {'launch_local', 'launch_hpc'}:
            return self.state(context).verify_completion(proof)
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.verify_completion(context, proof)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return proof == self.native_hmmer_preparation_results.completion(context)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return proof == self.native_infernal_preparation_results.completion(context)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return proof == self.native_blast_results.completion(context)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return proof == self.native_infernal_results.completion(context)
        if self.native_hmmer_results.applies(context):
            return proof == self.native_hmmer_results.completion(context)
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))

    def practical_estimator(self, context):
        if context.role in {'launch_local', 'launch_hpc'}:
            practical = self._practical_context(context)
            from .flux_balance_request_binding import is_compact_assignment
            if not is_compact_assignment(plain(context.assignment)):
                return self._delegate(context).practical_estimator(practical)
        from .practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))


__all__ = ['ExecutionEpisodes', 'VERSION', 'LAUNCH_VERSION', 'RESULTS_VERSION', 'RESULTS_SCHEMA',
           'launch_operation_catalog', 'native_result_operation_catalog']
