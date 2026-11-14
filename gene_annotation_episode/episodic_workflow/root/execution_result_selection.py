"""Complete original execution result selection responsibility."""
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

class ExecutionResultSelection:
    @classmethod
    def retained_protein_structure_reader(cls, store, *, run_id, directory):
        """Construct only this owner's unchanged legacy protein read authority.

            No resource, client, progress, registry or execution state is created.
            The caller supplies metadata sealed from the actual original owner;
            original receipts and typed delivery remain authoritative on every read.
            """
        from gene_annotation_episode.state import Store
        if not isinstance(store, Store) or type(run_id) is not str or (not run_id) or (not isinstance(directory, (str, Path))):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        value = str(directory)
        path = Path(value)
        if not value or '\x00' in value or (not path.is_absolute()) or ('..' in path.parts) or (value != str(path)):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        if store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None:
            raise ValueError('protein_structure_retained_reader_run_missing')
        owner = cls.__new__(cls)
        owner.store, owner.run_id, owner.directory = (store, run_id, path)
        from gene_annotation_episode.episodic_workflow.root.native_protein_structure_results import NativeProteinStructureResults
        from gene_annotation_episode.episodic_workflow.root.native_protein_structure_returns import NativeProteinStructureReturns
        owner.native_protein_structure_results = NativeProteinStructureResults(owner)
        owner.native_protein_structure_returns = NativeProteinStructureReturns(owner)
        return owner.native_protein_structure_returns

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
        from gene_annotation_episode.execution_contracts import validate_target
        from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import same
        from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import validate_protein_structure_result_selector
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
            from gene_annotation_episode.episodic_workflow.root.library.flux_balance_result_selection import validate_flux_balance_result_selector
            selector = validate_flux_balance_result_selector(assignment['selector'])
            return validate_flux_balance_result_selector(selector, job=target['assignment']['requested_job']) if selector['mode'] == 'native_result' else selector
        if self._masking_selector(assignment) or is_native_blast_masking_target(target):
            if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.sequence_masking_result_views import validate_masking_result_selector
            return validate_masking_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
        if self._utility_selector(assignment) or is_native_blast_utility_target(target):
            if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.blast_utility_result_views import validate_blast_utility_result_selector
            return validate_blast_utility_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
        native_fluorescence = 'native_fluorescence' in target.get('assignment', {}).get('requested_job', {})
        if self._fluorescence_selector(assignment) or native_fluorescence:
            if not native_fluorescence or target.get('resource_kind') != 'local':
                raise ValueError('fluorescence_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_contracts import validate_fluorescence_selector
            return validate_fluorescence_selector(assignment['selector'], job=target['assignment']['requested_job']['native_fluorescence'])
        native_nmf = 'native_expression_nmf' in target.get('assignment', {}).get('requested_job', {})
        if self._expression_nmf_selector(assignment) or native_nmf:
            if self.native_expression_nmf_results is None:
                raise ValueError('native_expression_nmf_results_binding_unavailable')
            if not native_nmf or target.get('resource_kind') != 'local':
                raise ValueError('expression_nmf_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_result_contracts import validate_expression_nmf_result_selector
            return validate_expression_nmf_result_selector(assignment['selector'], job=target['assignment']['requested_job']['native_expression_nmf'])
        native_atac = 'native_atac_differential' in target.get('assignment', {}).get('requested_job', {})
        if self._atac_selector(assignment) or native_atac:
            if self.atac_results is None:
                raise ValueError('native_atac_results_binding_unavailable')
            if not native_atac or target.get('resource_kind') != 'local':
                raise ValueError('atac_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.atac_differential_execution_information import validate_atac_result_selector
            return validate_atac_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_atac_differential']['request'])
        native_chromatin = 'native_chromatin_interactions' in target.get('assignment', {}).get('requested_job', {})
        if self._chromatin_selector(assignment) or native_chromatin:
            if self.native_chromatin_interaction_results is None:
                raise ValueError('native_chromatin_results_binding_unavailable')
            if not native_chromatin or target.get('resource_kind') != 'local':
                raise ValueError('chromatin_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_execution_information import validate_chromatin_result_selector
            return validate_chromatin_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_chromatin_interactions']['request'])
        native_overlap = 'native_genomic_overlap' in target.get('assignment', {}).get('requested_job', {})
        if self._genomic_overlap_selector(assignment) or native_overlap:
            if self.native_genomic_overlap_results is None:
                raise ValueError('native_genomic_overlap_results_binding_unavailable')
            if not native_overlap or target.get('resource_kind') != 'local':
                raise ValueError('genomic_overlap_result_target_conflict')
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_result_worker import _selector
            from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts import validate_genomic_overlap_record
            value = validate_genomic_overlap_record('Selector', assignment['selector'])
            value = _selector(value, mode=value['mode'], request=target['assignment']['requested_job']['native_genomic_overlap']['request'])
            if (value['mode'] == 'native_result') != (value['saved_sheet_file'] is None):
                raise ValueError('genomic_overlap_result_saved_sheet_mode_conflict')
            if value['saved_sheet_file'] is not None:
                from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_return_views import SAVED_SOURCE, validate_genomic_overlap_fact_values
                validate_genomic_overlap_fact_values(SAVED_SOURCE, [value['saved_sheet_file']])
            return value
        if assignment.get('selector', {}).get('version') == 'protein_structure_result_selector_v1' or is_native_protein_structure_target(target):
            if not is_native_protein_structure_target(target):
                raise ValueError('original_commission_mismatch')
            from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import validate_protein_structure_result_selector
            return validate_protein_structure_result_selector(assignment['selector'], request=target['assignment']['requested_job']['native_protein_structure']['request'])
        if self._comparison_selector(assignment):
            if self.rna_structure_comparison_results is None:
                raise ValueError('rna_comparison_results_binding_unavailable')
            if not is_native_rna_structure_target(target):
                raise ValueError('rna_comparison_anchor_required')
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_contracts import validate_rna_comparison_selector
            return validate_rna_comparison_selector(assignment['selector'])
        if is_native_rna_structure_target(target):
            if self.native_rna_structure_results is None:
                raise ValueError('native_rna_structure_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import validate_rna_structure_result_selector
            return validate_rna_structure_result_selector(assignment['selector'], mode=target['assignment']['requested_job']['native_rna_structure']['mode'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.library.hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.blast_pairwise_result_views import validate_native_blast_result_selector
            return validate_native_blast_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast']['program'])
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import validate_native_infernal_result_selector
            return validate_native_infernal_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_infernal']['program'])
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_result_views import validate_preparation_result_selector
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
