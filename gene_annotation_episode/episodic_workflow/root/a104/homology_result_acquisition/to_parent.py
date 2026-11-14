"""Actual private job_results to_parent."""
from __future__ import annotations
from .message_contracts import AcquisitionError, CHECKED_STATUS_SCHEMA, ContractError, EXECUTION_OBSERVATION_SCHEMA, HANDOFF_SCHEMA, Mapping, REFERENCE_FORMATS, RESULT_PROGRESS_SCHEMA, ROLES, ReportBoundaryError, SAMPLE_SCHEMA, _result_progress, deepcopy, json, recorded_coverage, recorded_estimate, recorded_forecasts, reference, resource_report_source, sqlite3, subprocess, validate_recorded_estimates
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_fact_readers import read_facts_for_role

from .internal_summary import read_facts

class HomologyAcquisitionToParent:

    def fact_sources(self, role):
        if role not in ROLES:
            return {}
        handoff = {**deepcopy(HANDOFF_SCHEMA), 'type': ['object', 'null']}
        sample = {**deepcopy(SAMPLE_SCHEMA), 'type': ['object', 'null']}
        values = {'job_ref': (reference('homology_job'), 'The immutable assigned job, not an episode identity.'), 'job_cpu': ({'type': 'integer', 'minimum': 1}, 'Assigned CPU threads selected by the parent and retained in the job; not measured consumption.'), 'job_handoff': (handoff, 'A freshly functionally checked receiving-interface handoff, or null when unavailable.'), 'job_handoff_state': ({'type': 'string', 'enum': ['usable', 'unavailable']}, 'Whether this closure established a usable receiving-interface handoff; no scientific completion claim.'), 'job_handoff_failure': ({'type': ['string', 'null'], 'enum': [None, 'job_not_submitted', 'submission_unconfirmed', 'native_handle_identity_mismatch', 'receiving_interface_unavailable']}, 'The basic reason no usable handoff could be returned; null after a successful receiving-interface check.'), 'job_sample': (sample, 'The last actual sample selected by this child, unchanged on replay; null if it selected none.')}
        if 'search_modes' in self.jobs.config:
            values['job_search_mode'] = ({'type': 'string', 'enum': list(self.jobs.search_modes)}, 'The immutable parent-selected search mode. Maximum sensitivity disables heuristic filters; it is not evidence of a specific function or a stronger significance threshold.')
        sources = {key: {'type': schema['type'], 'meaning': meaning, 'report_schema': {**schema, 'x-source': key}} for key, (schema, meaning) in values.items()}
        sources['resource_tool_estimates'] = resource_report_source()
        if self.has_information_channel(role):
            sources['monitoring_findings'] = self.monitoring_projector.information_report_source()
            sources['monitoring_information_credit'] = {'type': 'number', 'meaning': 'Monitoring information actually obtained by this episode; separate from operational/scientific score and duration estimates. It does not select the controller input.', 'binding': self.monitoring_projector.as_record(), 'report_schema': {'type': 'number', 'x-source': 'monitoring_information_credit'}}
        sources['job_result_progress'] = {'type': ['object', 'null'], 'meaning': 'Recorded acquisition coverage for the last native snapshot selected by this child. Includes snapshot identity, native/parse completion, parsed/acquired row counts, all_parsed_rows_acquired and explicit parse errors. A complete native result with a finished error-free parser and zero parsed/acquired rows is a completed empty search in the selected database, not evidence of a biological function. Native ordinals are one-based; intervals are half-open. Acquiring a partial parsed prefix is distinct from a complete native result. This is not scientific credit or completion. Null when no snapshot was selected or its coverage could not be read.', 'report_schema': {**deepcopy(RESULT_PROGRESS_SCHEMA), 'type': ['object', 'null'], 'x-source': 'job_result_progress'}}
        sources['job_result_progress_failure'] = {'type': ['string', 'null'], 'meaning': 'Basic coverage-read failure; null when no read failed. Native parse failures remain separate coverage facts.', 'report_schema': {'type': ['string', 'null'], 'enum': [None, 'invalid_snapshot_or_scope', 'storage_failure', 'coverage_read_failed'], 'x-source': 'job_result_progress_failure'}}
        return sources
