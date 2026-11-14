"""Own original Resource action-contract diagnostics and rejected accounting.

Malformed supplied actions retain their typed repair details, including reads.map
feedback, before a unit is acquired. This does not filter returned invalid work.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.runtime import AcquisitionError, ActionFailure, ContractError, ContractInformationError, Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, sqlite3, subprocess, validate_form

class ResourceActionContractFeedback:


    def action_contract_feedback(self, error, selection, schema, index):
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
        if isinstance(error, _live_original_runtime.ValidationError) and isinstance(selection, _live_original_runtime.Mapping) and (selection.get('kind') == 'tool') and (selection.get('tool') == 'reads.map'):
            from gene_annotation_episode.episodic_workflow.root.a102.read_mapping import parameter_schema_failure
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
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
