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

class HomologyResourceCustody:
    def _wrap(self, context, checked):
        assignment = plain(context.assignment)
        job = self.homology.jobs._row(checked['handoff']['job_ref'])
        versions = assignment['handoff']['submitted_input_versions'] if context.role == 'results' else assignment['immutable_input_versions']
        return {'version': 'execution_handoff_v1', 'execution_handle': job['job_ref'], 'resource_selection': self._selection(job['cpu']), 'submitted_input_versions': versions, 'monitoring': {'provider_id': self.resource_id, 'target_handle': job['job_ref'], 'contract_ref': checked['handoff']['status_interface']}, 'results': {'provider_id': self.resource_id, 'target_handle': job['job_ref'], 'contract_ref': checked['handoff']['results_interface']}, 'checked_at': datetime.fromtimestamp(checked['checked_at_unix_seconds'], timezone.utc).isoformat(), 'check_record_refs': [checked['receipt_ref']], 'state': 'usable', 'failure': None}

    def _native_handoff(self, handoff):
        _validate(handoff, HANDOFF_SCHEMA)
        jobs = self.homology.jobs
        row = jobs._row(handoff['execution_handle'])
        self._verify_selection(handoff['resource_selection'], row['cpu'])
        from gene_annotation_episode.episodic_workflow.root.library.homology_job_contracts import VERSION
        native = {'job_ref': row['job_ref'], 'registry_ref': jobs.config['registry_ref'], 'backend': VERSION, 'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
        expected = {'monitoring': native['status_interface'], 'results': native['results_interface']}
        if handoff['state'] != 'usable' or handoff['failure'] is not None or (not handoff['check_record_refs']):
            raise ValueError('invalid_resource_handoff')
        for key, contract in expected.items():
            receiver = handoff[key]
            if receiver != {'provider_id': self.resource_id, 'target_handle': row['job_ref'], 'contract_ref': contract}:
                raise ValueError('invalid_resource_handoff')
        for reference in handoff['check_record_refs']:
            receipt = jobs.db.execute('SELECT job_ref FROM handoffs WHERE receipt_ref=?', (reference,)).fetchone()
            if receipt is None or receipt[0] != row['job_ref']:
                raise ValueError('invalid_resource_handoff')
        witnesses = self.store.db.execute("SELECT json_extract(result,'$.execution_handoff')\n            FROM runtime_actions WHERE run_id=? AND json_extract(result,'$.status')='completed'\n            AND json_extract(result,'$.execution_handoff.execution_handle')=?", (self.information.run_id, row['job_ref']))
        if not any((json.loads(witness[0]) == handoff for witness in witnesses)):
            matches = [source for source in self.information._sources() if self.information._body(source).get('execution_handoff') == handoff]
            if not matches:
                raise ValueError('invalid_resource_handoff')
            for source in matches:
                body = self.information._body(source)
                self.information.read_handoff_source(source['id'], scope=body['scope'])
        return native

    def execution_handoff(self, context):
        values = self.execution_handoffs(context)
        return values[0] if len(values) == 1 else None

    def execution_handoffs(self, context):
        candidates = []
        callback = self.record_selection
        if callback is not None:
            selected = callback(context)
            if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
                raise ValueError('resource_information_identity_conflict')
            for reference in selected['known_record_refs']:
                source = self.store.get(reference)
                if source.get('provider') != 'episode.resource_handoff':
                    continue
                body = self.information._body(source)
                if body.get('registry_ref') != self.homology.jobs.config['registry_ref']:
                    continue
                body = self.information.read_handoff_source(reference, scope=plain(context.scope))
                try:
                    self.information._validate_assignment(context, body['execution_handoff'], body['job'])
                except ValueError as error:
                    if str(error) != 'resource_information_assignment_conflict':
                        raise
                    continue
                candidates.append((reference, body['execution_handoff']))
        rows = self.store.db.execute("SELECT decision_index,json_extract(result,'$.execution_handoff')\n            FROM runtime_actions WHERE run_id=? AND episode_id=?\n            AND json_extract(result,'$.status')='completed'\n            AND json_type(result,'$.execution_handoff')='object'\n            ORDER BY decision_index", (context.run_id, context.episode_id))
        for row in rows:
            handoff = json.loads(row[1])
            if handoff['resource_selection']['resource_id'] != self.resource_id:
                continue
            self._native_handoff(handoff)
            candidates.append(('legacy:' + str(row[0]), handoff))
        latest = {}
        for source_ref, handoff in candidates:
            from gene_annotation_episode.episodic_workflow.root.library.resource_information import _utc
            identity = (handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle'])
            ordering = (_utc(handoff['checked_at']), source_ref)
            if identity not in latest or ordering > latest[identity][0]:
                latest[identity] = (ordering, handoff)
        return [deepcopy(latest[key][1]) for key in sorted(latest)]

    def received_form_references(self, context, form, schema, operation_key):
        references = []

        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else [] if value is None else [value]
                for handoff in values:
                    if handoff['resource_selection']['resource_id'] == self.resource_id:
                        references.extend(self.information.references_for_form(context, handoff, {'x-source': 'execution_handoff'}))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))

    def initial_references(self, context):
        return self.information.references_for_initial(context)
