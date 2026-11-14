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


class ExecutionSubmissionYield:
    def yield_controller(self, context, initial_credit, epoch):
        """Choose only this admitted execution task's own yield binding."""
        if context.role != 'launch' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        self.credit_kind('launch')
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        return self._launch_yield_controller(context, initial_credit, epoch)

    def _launch_yield_controller(self, context, initial_credit, epoch):
        """Cap one next handoff by original request slots still uncredited."""
        from gene_annotation_episode.episodic_workflow.root.numerical import BoundedYieldController, NumericBand, YieldController, YieldEstimate, YieldParameters
        assignment = plain(context.assignment)
        if 'requests' not in assignment:
            raise ValueError('launch_original_request_map_required')
        original = self._launch(assignment, scope=context.scope)
        eligible = {resource_id for resource_id in original['requests'] if self._permitted(original, resource_id)}
        selected, handoffs, _ = self._received(context)
        initial = set(selected['initial_known_record_refs'])
        already_received = {target['resource_id'] for reference, target in handoffs.items() if reference in initial and self.job_progress_provider.targets.usable_handoff(target)}
        remaining = len(eligible - already_received) * self.handoff_unit
        if remaining:
            classes = sorted((self._request_yield_class(original['requests'][resource_id]) for resource_id in eligible))
            profile = self._task_yield_profile('launch:' + '+'.join(classes))
            return BoundedYieldController(epoch, initial_credit, profile['cutoff'], remaining, YieldParameters(**profile['parameters']))
        if initial_credit != 0:
            raise ValueError('launch_no_uncredited_requests_but_nonzero_initial_credit')

        def no_remaining_requests(history, parameters, contexts):
            if any((value != 0 for value in history)):
                raise ValueError('launch_credit_without_original_uncredited_request')
            return YieldEstimate(len(history), NumericBand.exact(0), parameters, {'remaining_original_request_credit': 0.0, 'original_request_count': len(eligible)}, estimator_binding={'version': 'launch_original_request_exhaustion_v1', 'forecast': 'exact_zero_when_every_eligible_original_request_was_in_initial_handoffs'})
        return YieldController(epoch, initial_credit, 0.0, YieldParameters(), estimate_with_context=no_remaining_requests)

    def practical_estimator(self, context):
        if context.role != 'launch' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
