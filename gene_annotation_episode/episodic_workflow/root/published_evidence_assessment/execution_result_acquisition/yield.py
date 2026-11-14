"""Private yield responsibility with original configured behavior."""
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


class ResultAcquisitionYield:
    def yield_controller(self, context, initial_credit, epoch):
        """Choose only this admitted execution task's own yield binding."""
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        self.credit_kind('results')
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        return self._results_yield_controller(context, initial_credit, epoch)

    def _results_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters, estimate_bounded_credit_yield
        from gene_annotation_episode.episodic_workflow.root.practical_yield import PracticalYieldEstimator
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = self._target(context)
        selector = self._selector(assignment, target)
        if target['resource_kind'] != 'api' and 'version' not in selector:
            requested = self._windows(selector)
            if not requested:
                raise ValueError('results_original_selector_has_no_requested_bytes')
            if any((length is None for _, length in requested.values())):
                key = 'native_unbounded_' + target['resource_kind']
                if key not in self.results_yield_profiles:
                    raise ValueError('results_original_task_yield_profile_required:' + key)
                profile = self.results_yield_profiles[key]
                return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']))
            profile = self._task_yield_profile('results:native_finite_' + target['resource_kind'])
            selected, _, results = self._received(context)
            initial = set(selected['initial_known_record_refs'])
            baseline = {ref: body for ref, body in results.items() if ref in initial}
            original_fraction = self._generic_result_selector_progress(context, baseline, set())
            remaining = self.acquired_record_unit * (1.0 - original_fraction)
            if remaining == 0 and initial_credit != 0:
                raise ValueError('results_no_uncredited_bytes_but_nonzero_initial_credit')
            endpoint = PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))

            def finite_result_yield(history, parameters, contexts):
                if contexts and contexts[-1] and (contexts[-1].get('practical_completion') is not None):
                    completed = endpoint(history, parameters, contexts)
                    if completed.diagnostics.get('fitting_scope') == 'verified_assignment_endpoint':
                        return completed
                if remaining == 0:
                    if any((value != 0 for value in history)):
                        raise ValueError('results_credit_without_original_uncredited_bytes')
                    return YieldEstimate(len(history), NumericBand.exact(0), parameters, {'remaining_original_selector_credit': 0.0}, estimator_binding={'version': 'finite_result_selector_exhaustion_v1', 'forecast': 'exact_zero_after_all_requested_byte_positions_credited'})
                return estimate_bounded_credit_yield(history, parameters, contexts=contexts, initial_credit=initial_credit, maximum_credit=remaining)
            return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=finite_result_yield)
        if target['resource_kind'] == 'api':
            service = target.get('service') or target.get('assignment', {}).get('service')
            if not isinstance(service, str) or not service:
                raise ValueError('results_original_api_service_required_for_yield')
            key = 'results:api_' + service + ('_' + selector['version'] if 'version' in selector else '')
        else:
            key = 'results:typed_' + target['resource_kind'] + '_' + selector['version']
        profile = self._task_yield_profile(key)
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
