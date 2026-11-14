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

class HomologyResourceAssignment:
    def _selection(self, cpu):
        policy = self.homology.jobs.config['job_limits']
        return {'resource_id': self.resource_id, 'kind': 'local', 'allocation': {'cpu': cpu, **deepcopy(policy)}, 'capability_binding_ref': self.homology.jobs.config['registry_ref']}

    def _verify_selection(self, selected, cpu):
        if selected != self._selection(cpu):
            raise ValueError('resource_selection_conflict')

    def prepare_assignment(self, context, role, launch_assignment, scope, operation_key):
        value = plain(launch_assignment)
        if role == 'results':
            self._selector(value['requested_data_selector'])
            handoff = value['handoff']
            legacy = self._native_handoff(handoff)
            job = self.homology.jobs._row(legacy['job_ref'])
            self.homology._query(self.store, plain(scope), job['query_ref'])
            assigned = {'job_ref': job['job_ref'], 'query_ref': job['query_ref'], 'cpu': job['cpu'], 'handoff': legacy}
            if 'search_modes' in self.homology.jobs.config:
                assigned['search_mode'] = job['search_mode']
            value['adapter_assignment'] = assigned
            return value
        if role != 'launch_local':
            raise ValueError('homology_resource_requires_local_role')
        job = value['job_request']
        if set(job) - {'query_ref', 'cpu', 'search_mode', 'existing_job_ref'}:
            raise ValueError('unsupported_homology_job_operand')
        if 'existing_job_ref' in job:
            row = self.homology.jobs._row(job['existing_job_ref'])
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in job and job[key] != row[key]:
                    raise ValueError('resource_assignment_conflict')
            cpu, query = (row['cpu'], row['query_ref'])
        else:
            cpu, query = (job['cpu'], job['query_ref'])
        self._verify_selection(value['resource_selection'], cpu)
        constraints = value['constraints']
        for key, actual in value['resource_selection']['allocation'].items():
            if key in constraints and constraints[key] != actual:
                raise ValueError('resource_selection_conflict')
        self.homology._query(self.store, plain(scope), query)
        if not self.store.roots(query):
            if self.record_selection is None:
                raise ValueError('reference_query_requires_explicit_received_operand')
            received = self.record_selection(context)
            if received.get('run_id') != context.run_id or received.get('episode_id') != context.episode_id or query not in received['known_record_refs']:
                raise ValueError('reference_query_requires_explicit_received_operand')
        for supplied in value['immutable_input_versions']:
            record = self.store.get(supplied['reference'])
            if not self.store.reference_subset([supplied['reference']], plain(scope)):
                raise ValueError('resource_input_outside_assigned_scope')
            if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
                raise ValueError('resource_input_version_conflict')
            expected = supplied['content_sha256']
            if expected is not None:
                from gene_annotation_episode.materials import artifact_path
                artifact = record['id'] if record['record_type'] == 'artifact' else record.get('sequence_ref')
                if artifact is None or hashlib.sha256(artifact_path(self.store, artifact).read_bytes()).hexdigest() != expected:
                    raise ValueError('resource_input_version_conflict')
        value['adapter_assignment'] = self.homology.implementation_for('job_launch').assign(self.store, 'job_launch', job, plain(scope), operation_key=operation_key)
        return value

    def _legacy(self, context):
        assignment = plain(context.assignment).get('adapter_assignment')
        if assignment is None:
            return None
        role = 'job_results' if context.role == 'results' else 'job_launch'
        return SimpleNamespace(episode_id=context.episode_id, scope=plain(context.scope), path=(*context.path[:-1], (role, context.path[-1][1])), request=SimpleNamespace(message=_Message({'job_assignment': assignment})), workflow=SimpleNamespace(store=self.store, run_id=context.run_id))

    @staticmethod
    def _selector(value):
        """Homology selectors are a zero-based native-row interval.

            An empty selector requests all rows; nullable limit leaves the upper
            bound open. Page acquisition and parser repair remain selected tools.
            """
        schema = {'type': 'object', 'properties': {'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': ['integer', 'null'], 'minimum': 0}}, 'additionalProperties': False}
        try:
            value = _validate(value, schema)
        except ValueError as error:
            raise ValueError('invalid_resource_selector') from error
        return (value.get('offset', 0), value.get('limit'))
