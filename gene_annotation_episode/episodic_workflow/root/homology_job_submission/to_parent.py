"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
from copy import deepcopy
import json
import sqlite3
import subprocess
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.library.homology_job_contracts import HANDOFF_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.homology_job_status_contracts import SAMPLE_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import recorded_forecasts, report_source as resource_report_source
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import reference, CHECKED_STATUS_SCHEMA
ROLES = ('job_launch',)

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
    sources['job_checked_status'] = {'type': ['object', 'null'], 'meaning': "The status and timestamp of this child's last successful selected homology.check_handoff action. This is the recorded check-time state, not a fresh closure poll or a monitoring sample. Null if no selected check succeeded. The parent decides what subsequent work this information warrants.", 'report_schema': {**deepcopy(CHECKED_STATUS_SCHEMA), 'type': ['object', 'null'], 'x-source': 'job_checked_status'}}
    if self.has_information_channel(role):
        sources['monitoring_findings'] = self.monitoring_projector.information_report_source()
        sources['monitoring_information_credit'] = {'type': 'number', 'meaning': 'Monitoring information actually obtained by this episode; separate from operational/scientific score and duration estimates. It does not select the controller input.', 'binding': self.monitoring_projector.as_record(), 'report_schema': {'type': 'number', 'x-source': 'monitoring_information_credit'}}
    return sources

def facts(self, source, *, credit_view=None):
    assignment = self.assignment(source)
    try:
        handoff = self.jobs.handoff(assignment['job_ref'])
        self.jobs.check_handoff(handoff)
        failure = None
    except (sqlite3.Error, subprocess.SubprocessError):
        handoff, failure = (None, 'receiving_interface_unavailable')
    except (ValueError, KeyError, OSError, AcquisitionError) as error:
        handoff = None
        try:
            row = self.jobs._row(assignment['job_ref'])
            handle = self.jobs.directory / assignment['job_ref'] / 'native.handle.json'
            unreadable = False
            try:
                prepared = handle.is_file() and json.loads(handle.read_text()).get('stage') == 'prepared'
            except (OSError, ValueError, TypeError, AttributeError):
                prepared, unreadable = (False, True)
            failure = 'receiving_interface_unavailable' if unreadable else 'submission_unconfirmed' if prepared else 'job_not_submitted' if not row['submission_requested'] else 'submission_unconfirmed' if not handle.is_file() else 'native_handle_identity_mismatch' if str(error) == 'native_handle_does_not_describe_registered_job' else 'receiving_interface_unavailable'
        except (sqlite3.Error, ValueError, KeyError):
            failure = 'receiving_interface_unavailable'
    facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'], 'job_handoff': handoff, 'job_handoff_state': 'usable' if handoff else 'unavailable', 'job_handoff_failure': failure, 'job_sample': self.latest_sample(source), 'resource_tool_estimates': recorded_forecasts(source.workflow.store, run_id=source.workflow.run_id, episode_id=source.episode_id)}
    if 'search_modes' in self.jobs.config:
        facts['job_search_mode'] = assignment['search_mode']
    facts['job_checked_status'] = self.latest_checked_status(source)
    if self.has_information_channel(source.path[-1][0]):
        information = self.credit_view(source) if credit_view is None else credit_view
        facts.update(monitoring_information_credit=information['monitoring_information_credit'], monitoring_findings=information['monitoring_findings'])
    return facts

def validate_report(self, value, assignment, *, role, store=None, schema=None):
    """Select the owning job episode's return binding explicitly."""
    bindings = {'job_launch': self._validate_launch_return}
    if role not in bindings:
        raise ValueError('homology_return_role_required')
    bindings[role](value, assignment, store=store, schema=schema)

def _validate_launch_return(self, value, assignment, *, store, schema):
    self._validate_role_return_sources('job_launch', schema)
    self._validate_recorded_return(value, assignment, store=store, schema=schema)

def _validate_role_return_sources(self, role, schema):
    if schema is None:
        return
    allowed = self.fact_sources(role)
    for node in schema.get('properties', {}).values():
        source = node.get('x-source')
        if isinstance(source, str) and source.startswith(('job_', 'monitoring_')) and (source not in allowed):
            raise ReportBoundaryError('Fact does not belong to this job episode', code='homology_return_source_role_conflict')
