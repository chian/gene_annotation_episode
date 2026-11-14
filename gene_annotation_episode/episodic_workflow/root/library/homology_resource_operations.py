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

class HomologyResourceOperations:
    def capability(self):
        jobs = self.homology.jobs
        files = (jobs.config['executable']['path'], jobs.config['reference_database']['path'])
        availability = 'unavailable'
        if all((Path(path).is_file() for path in files)) and os.access(files[0], os.X_OK):
            try:
                probe = subprocess.run(['systemctl', '--user', 'show-environment'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                availability = 'available' if probe.returncode == 0 else 'unavailable'
            except (OSError, subprocess.SubprocessError):
                availability = 'unknown'
        resources = LocalResources.configured().snapshot()
        policy = jobs.config['job_limits']
        return {'resource_id': self.resource_id, 'kind': 'local', 'availability': availability, 'local_resources': resources, 'allocation_limits': {'cpu': None, **deepcopy(policy)}, 'observed_at': datetime.now(timezone.utc).isoformat(), 'provenance_refs': [jobs.config['registry_ref']], 'knowledge_entry_ids': [], 'tool_names': [tool['name'] for tool in self.homology.implementation_for('job_launch').catalog(SimpleNamespace(path=(('job_launch', self.resource_id),)))]}

    def catalog(self, context):
        source = self._legacy(context)
        return [] if source is None else self.homology.implementation_for(source.path[-1][0]).catalog(source)

    async def execute(self, context, tool_name, arguments, operation_key):
        replay = self.information.selected_handoff(context, tool_name, arguments, operation_key)
        if replay is not None:
            return replay
        source = self._legacy(context)
        if source is None:
            return _outcome(failure=_failure('resource_assignment_conflict'))
        assignment = self.homology.assignment(source)
        try:
            self._verify_selection(plain(context.assignment)['resource_selection'] if context.role != 'results' else plain(context.assignment)['handoff']['resource_selection'], assignment['cpu'])
            row = self.homology.jobs._row(assignment['job_ref'])
            if row['query_ref'] != assignment['query_ref'] or row['cpu'] != assignment['cpu'] or row['search_mode'] != assignment.get('search_mode', 'native_defaults'):
                raise ValueError('resource_assignment_conflict')
            if context.role == 'results' and tool_name == 'homology.extract':
                start, count = self._selector(plain(context.assignment)['requested_data_selector'])
                offset, limit = (arguments.get('offset', 0), arguments['limit'])
                if limit and (offset < start or (count is not None and offset + limit > start + count)):
                    raise ValueError('requested_data_selector_conflict')
        except ValueError as error:
            return _outcome(failure=_failure(str(error), [assignment['job_ref']]))
        outcome = await self.homology.implementation_for(source.path[-1][0]).execute(source, tool_name, plain(arguments), operation_key=operation_key)
        if tool_name == 'homology.check_handoff' and outcome['status'] == 'completed':
            outcome['execution_handoff'] = self._wrap(context, outcome['result'])
        return self.information.publish_handoff(context, tool_name, arguments, outcome, operation_key)

    def check_handoff(self, context, handoff, operation_key):
        replay = self.information.selected_handoff(context, 'resource.check_handoff', {'handoff': handoff}, operation_key)
        if replay is not None:
            return replay
        native = self._native_handoff(handoff)
        assignment = plain(context.assignment)
        if assignment.get('version') == LAUNCH_VERSION and assignment['immutable_input_versions'] != handoff['submitted_input_versions']:
            raise ValueError('resource_assignment_conflict')
        if assignment.get('version') == LAUNCH_VERSION:
            job = self.homology.jobs._row(handoff['execution_handle'])
            selection = handoff['resource_selection']
            if assignment['resource_selection'] is not None and selection != assignment['resource_selection'] or not ResourceEpisodes._permitted(assignment, selection):
                raise ValueError('resource_selection_conflict')
            for key, actual in selection['allocation'].items():
                if key in assignment['constraints'] and assignment['constraints'][key] != actual:
                    raise ValueError('resource_selection_conflict')
            requested = assignment['job_request']
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in requested and requested[key] != job[key]:
                    raise ValueError('resource_assignment_conflict')
            if 'existing_job_ref' in requested and requested['existing_job_ref'] != job['job_ref']:
                raise ValueError('resource_assignment_conflict')
        checked = self.homology.jobs.check_handoff(native)
        value = self._wrap(context, checked)
        outcome = {**_outcome(checked), 'execution_handoff': value}
        return self.information.publish_handoff(context, 'resource.check_handoff', {'handoff': handoff}, outcome, operation_key)
