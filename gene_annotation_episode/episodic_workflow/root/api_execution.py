"""Bounded HMMER operations inside the shared execution episode.

This adapter contains no polling, retry, model or episode loop. API targets use
``digest(original API assignment)`` as request_sha256; the HTTP request, submitted
FASTA bytes and parsed sequence each retain their own distinct frozen identities.
Native monitoring has independent observation custody and never changes launch
receipts, completion proofs or its closed controller history.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import uuid

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.library.provider_jobs import HMMER_IDENTITY_VERSION, validate_remote_identity

from gene_annotation_episode.episodic_workflow.root.api_hmmer_protocol import (PROVIDER, VERSION, HANDOFF_VERSION, RESULT_DESCRIPTION,
    _now, _object, hmmer_operation_catalog, _envelope, _native_status)
from gene_annotation_episode.episodic_workflow.root.api_hmmer_operations import HMMERAPIOperations
from gene_annotation_episode.episodic_workflow.root.api_hmmer_handoff_records import HMMERHandoffRecords
from gene_annotation_episode.episodic_workflow.root.api_hmmer_result_records import HMMERResultRecords
from gene_annotation_episode.episodic_workflow.root.api_hmmer_progress import HMMERAPIProgress


class HMMERAPIExecution(HMMERAPIOperations, HMMERHandoffRecords,
                       HMMERResultRecords, HMMERAPIProgress):
    def __init__(self, store, *, run_id, directory, configuration, tool_registry,
                 handoff_unit, acquired_record_unit):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for value in (handoff_unit, acquired_record_unit):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.configuration = json.loads(canonical(configuration))
        if (not isinstance(self.configuration, dict) or not self.configuration or
                any(not isinstance(key, str) or not key or not isinstance(value, dict)
                    or value.get('kind') != 'hmmer_api' or set(value) - {'kind', 'service'}
                    or value.get('service', 'ebi_hmmer') != 'ebi_hmmer'
                    for key, value in self.configuration.items())):
            raise ValueError('explicit_api_resources_required')
        if tool_registry.store is not store or not callable(getattr(tool_registry, 'publish_hmmer_result', None)):
            raise ValueError('actual_tool_registry_required_for_api_execution')
        self.tools, self.clients = tool_registry, tool_registry.clients
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        store.db.executescript('''
            CREATE TABLE IF NOT EXISTS api_execution_episodes (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, assignment TEXT NOT NULL,
                scope TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS api_execution_preparations (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, request TEXT NOT NULL,
                fasta_ref TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS api_execution_actions (
                operation_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                name TEXT NOT NULL, arguments TEXT NOT NULL, intent TEXT NOT NULL,
                snapshot TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS api_execution_observations (
                operation_key TEXT PRIMARY KEY, target TEXT NOT NULL, observation TEXT);
        ''')

    def _constraints(self, assignment):
        constraints = assignment['constraints']
        for key, value in constraints.items():
            if key == 'allowed_resource_ids':
                if not isinstance(value, list) or assignment['resource_id'] not in value:
                    raise ValueError('api_resource_constraint_conflict')
            elif key == 'allowed_kinds':
                if not isinstance(value, list) or 'api' not in value:
                    raise ValueError('api_kind_constraint_conflict')
            elif key == 'kind':
                if value not in {'api', 'hmmer_api'}:
                    raise ValueError('api_kind_constraint_conflict')
            elif key in {'service', 'resource_id', 'subject_ref', 'algorithm', 'database', 'parameters', 'page_size'}:
                if value != assignment[key]:
                    raise ValueError('api_request_constraint_conflict')
            else:
                raise ValueError('unsupported_api_execution_constraint:'+key)

    def _assignment(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role == 'results':
            raw = plain(context.assignment)
            if (set(raw) != {'version', 'handoff_ref', 'selector'}
                    or raw['version'] != 'execution_results_assignment_v1'
                    or not isinstance(raw['selector'], dict)):
                raise ValueError('invalid_api_results_assignment')
            selector = raw['selector']
            if (set(selector) - {'page', 'page_size'} or 'page' not in selector
                    or any(type(value) is not int or value <= 0 for value in selector.values())):
                raise ValueError('invalid_api_results_selector')
            assignment = self.read_target(raw['handoff_ref'], context.scope)['assignment']
            if ('page_size' in assignment['constraints'] and
                    selector.get('page_size', assignment['page_size']) != assignment['constraints']['page_size']):
                raise ValueError('api_result_page_size_constraint_conflict')
            return assignment
        if context.role != 'launch_api':
            raise ValueError('api_execution_role_required')
        assignment = validate_api_assignment(plain(context.assignment))
        self._constraints(assignment)
        if assignment['resource_id'] not in self.configuration:
            raise ValueError('api_resource_not_bound')
        self.tools._check_sequence_operand(assignment['subject_ref'], plain(context.scope))
        return assignment

    def initialize(self, context):
        self._assignment(context)
        assignment, scope = canonical(context.assignment), canonical(context.scope)
        with self.store.transaction():
            row = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
                'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
            if row is not None:
                if row['assignment'] != assignment or row['scope'] != scope:
                    raise ValueError('api_original_assignment_conflict')
            else:
                self.store.db.execute('INSERT INTO api_execution_episodes VALUES(?,?,?,?)',
                    (self.run_id, context.episode_id, assignment, scope))
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def catalog(self, context):
        self._assignment(context)
        return hmmer_operation_catalog(context.role)



__all__ = ['HMMERAPIExecution', 'PROVIDER', 'VERSION']
