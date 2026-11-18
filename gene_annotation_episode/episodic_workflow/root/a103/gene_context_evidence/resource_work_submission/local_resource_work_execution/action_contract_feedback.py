"""Preserve original invalid-selection feedback and rejected-action accounting.

Supplied or restored invalid selections retain all original diagnostic branches;
these diagnostics do not admit a foreign child or execute its scientific work.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import AcquisitionError, ActionFailure, ContractError, ContractInformationError, Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, sqlite3, subprocess, validate_form

class ResourceActionContractFeedback:


    def reject_invalid_action(self, error, selection, schema, index):
        self.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': _live_original_runtime.schema_failure_diagnostic(error) if isinstance(error, _live_original_runtime.ValidationError) else str(error)}
        if isinstance(error, _live_original_runtime.ContractInformationError):
            self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
            if error.code == 'closed_top_level_form_required':
                self.feedback['repair'] = 'schema_json must encode a JSON Schema object with the explicit top-level field "type": "object" and a properties object. Keep the intended properties, declare every field in required, and set additionalProperties to false. A properties object alone does not declare the required outer type.'
            if isinstance(error.__cause__, _live_original_runtime.ReportBoundaryError):
                self.feedback['schema_reason'] = str(error.__cause__)
        if isinstance(error, _live_original_runtime.ContractError) and str(error) == 'component_native_return_channels_required':
            self.feedback['contract_error'] = {'code': str(error), 'field': error.detail['field']}
            self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
            self.feedback['repair'] = error.detail['repair']
        assignment = selection.get('assignment') if isinstance(selection, _live_original_runtime.Mapping) else None
        selector = assignment.get('selector') if isinstance(assignment, _live_original_runtime.Mapping) else None
        if isinstance(error, _live_original_runtime.ContractError) and isinstance(error.detail, _live_original_runtime.Mapping) and isinstance(selection, _live_original_runtime.Mapping) and isinstance(assignment, _live_original_runtime.Mapping) and (selection.get('kind') == 'episode_child') and (selection.get('role') == 'results') and (assignment.get('version') == 'execution_results_assignment_v1') and isinstance(selector, _live_original_runtime.Mapping) and (selector.get('version') == 'bvbrc_minhash_result_selector_v2'):
            affected = {key: _live_original_runtime._plain(error.detail[key]) for key in ('source_ref', 'artifact_ref', 'handoff_ref', 'pair_metadata_index', 'row_index', 'genome_id', 'field', 'record_path') if key in error.detail}
            if affected:
                self.feedback['input_detail'] = affected
        if isinstance(error, _live_original_runtime.ValidationError) and isinstance(selection, _live_original_runtime.Mapping) and (selection.get('kind') == 'tool') and (selection.get('tool') == 'reads.map'):
            from gene_annotation_episode.episodic_workflow.root.a103.read_mapping import parameter_schema_failure
            branches = schema['properties']['selection']['anyOf']
            for branch_error in error.context:
                branch_path = list(branch_error.schema_path)
                if not branch_path or not isinstance(branch_path[0], int):
                    continue
                branch = branches[branch_path[0]]
                if branch.get('properties', {}).get('tool', {}).get('const') != 'reads.map':
                    continue
                feedback = parameter_schema_failure(branch_error, path_prefix=('arguments',))
                if feedback is not None:
                    self.feedback.update(feedback)
                    break
        self.record_effect(index, 'rejected')
        return None
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
