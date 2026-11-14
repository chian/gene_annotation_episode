from __future__ import annotations

from collections.abc import Mapping

from copy import deepcopy

from datetime import datetime, timezone

import hashlib

import inspect

import json

import os

from pathlib import Path

import sqlite3

import subprocess

from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, plain

from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context

from gene_annotation_episode.episodic_workflow.root.library.homology_result_coverage import recorded_coverage

from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import recorded_forecasts

from gene_annotation_episode.episodic_workflow.root.resource_records import ROLES, RESOURCE_ROLES, LAUNCH_VERSION, RESULTS_VERSION, FAILURE_CODES, ALLOCATION_SCHEMA, SELECTION_SCHEMA, INPUT_VERSION_SCHEMA, CAPABILITY_SCHEMA, FAILURE_SCHEMA, RECEIVER_SCHEMA, HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA, _string, _reference, _array, _nullable, _validate

from gene_annotation_episode.episodic_workflow.root.library.resource_information import ResourceInformation

from gene_annotation_episode.launch_instructions import validate_selection

from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.episodic_workflow.root.resource_records import obj
from gene_annotation_episode.episodic_workflow.root.library.resource_outcomes import _failure, _outcome, _availability_failure
from gene_annotation_episode.episodic_workflow.root.library.resource_message import _Message
from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _result_progress

class HomologyResourceReturns:
    def fact_sources(self, role):
        values = self.homology.implementation_for('job_results' if role == 'results' else 'job_launch').fact_sources('job_results' if role == 'results' else 'job_launch') if role != 'launch' else {}
        if values:
            values['job_handoff']['meaning'] = 'The original recorded usable receiving handoff available to this episode; no new receiving check occurs at closure.'
            values['job_handoff_state']['meaning'] = 'Whether an original usable checked handoff is available in the assigned or received records; no scientific completion claim.'
        return values

    def facts(self, context, completion_snapshot):
        source = self._legacy(context)
        handoffs = self.execution_handoffs(context)
        handoff = handoffs[0] if len(handoffs) == 1 else None
        facts = {}
        if source is not None:
            assignment = self.homology.assignment(source)
            native = self._native_handoff(handoff) if handoff is not None else assignment.get('handoff')
            facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'], 'job_handoff': native, 'job_handoff_state': 'usable' if native is not None else 'unavailable', 'job_handoff_failure': None if native is not None else 'receiving_interface_unavailable', 'job_sample': self.homology.latest_sample(source), 'resource_tool_estimates': recorded_forecasts(self.store, run_id=context.run_id, episode_id=context.episode_id)}
            if 'search_modes' in self.homology.jobs.config:
                facts['job_search_mode'] = assignment['search_mode']
            legacy_role = source.path[-1][0]
            if legacy_role == 'job_launch':
                facts['job_checked_status'] = self.homology.latest_checked_status(source)
            if self.homology.implementation_for(legacy_role).has_information_channel(legacy_role):
                information = self.homology.implementation_for(source.path[-1][0]).credit_view(source)
                facts.update(monitoring_information_credit=information['monitoring_information_credit'], monitoring_findings=information['monitoring_findings'])
            if legacy_role == 'job_results':
                facts.update(job_result_progress=None, job_result_progress_failure=None)
                selected = self.store.db.execute("SELECT json_extract(result,'$.result.snapshot_ref')\n                    FROM runtime_actions WHERE run_id=? AND episode_id=?\n                    AND json_extract(action,'$.tool') IN ('homology.extract','homology.coverage')\n                    AND json_type(result,'$.result.snapshot_ref')='text'\n                    ORDER BY decision_index DESC LIMIT 1", (context.run_id, context.episode_id)).fetchone()
                if selected is not None:
                    from gene_annotation_episode.domain import ContractError
                    try:
                        coverage = recorded_coverage(self.store, selected[0], query_ref=assignment['query_ref'], scope=plain(context.scope), execution_context={'job_ref': assignment['job_ref'], 'registry_ref': self.homology.jobs.config['registry_ref']})
                        facts['job_result_progress'] = _result_progress(coverage)
                    except ContractError:
                        facts['job_result_progress_failure'] = 'invalid_snapshot_or_scope'
                    except (OSError, sqlite3.Error):
                        facts['job_result_progress_failure'] = 'storage_failure'
                    except (ValueError, KeyError, TypeError):
                        facts['job_result_progress_failure'] = 'coverage_read_failed'
        facts['execution_handoff'] = handoff
        facts['execution_handoffs'] = handoffs
        return facts

    def resolve(self, context, reference, namespace):
        source = self._legacy(context)
        assignment = self.homology.assignment(source) if source else None
        if namespace == 'resource_binding':
            return reference == self.resource_id
        if namespace == 'resource_interface':
            return reference in {'homology.status.v1', 'homology.results.v1'}
        if namespace == 'resource_execution':
            namespace = 'homology_job'
        if namespace in {'resource_input_version', 'resource_input_digest', 'resource_check_timestamp'}:
            handoffs = self.execution_handoffs(context)
            if not handoffs and context.role == 'results':
                handoffs = [plain(context.assignment)['handoff']]
            if namespace == 'resource_check_timestamp':
                return any((reference == handoff['checked_at'] for handoff in handoffs))
            field = 'version' if namespace == 'resource_input_version' else 'content_sha256'
            return any((reference == item[field] for handoff in handoffs for item in handoff['submitted_input_versions']))
        return self.homology.resolve(self.store, plain(context.scope), reference, namespace, assignment=assignment)

    def validate_report(self, context, form, original_schema):
        source = self._legacy(context)
        if source is not None:
            self.homology.implementation_for(source.path[-1][0]).validate_report(form, self.homology.assignment(source), store=self.store, schema=plain(original_schema), role=source.path[-1][0])
