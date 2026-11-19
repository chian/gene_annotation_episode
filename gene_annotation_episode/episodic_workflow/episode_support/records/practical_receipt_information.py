"""Scoped immutable Store publications of actual practical action receipts.

Publication follows the selected runtime action and preserves its original
assignment. Reading or admitting a source uses saved records only: it never
rechecks a native process, remote resource, installed environment or output.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import identity
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (canonical, digest, validate_assignment,
    validate_context, validate_receipt, validate_validations)


PROVIDER = 'episode.practical_receipt'
VERSION = 'practical_receipt_information_v1'
ASSIGNMENT_SNAPSHOT_VERSION = 'practical_receipt_assignment_v1'
BODY_FIELDS = {'version', 'run_id', 'episode_id', 'assignment_sha256', 'scope', 'receipt'}
SNAPSHOT_FIELDS = {'version', 'run_id', 'episode_id', 'scope', 'assignment'}


def _object(value, fields, code):
    if not isinstance(value, Mapping):
        raise ValueError(code)
    try:
        value = json.loads(canonical(plain(value)))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(code) from error
    if set(value) != set(fields):
        raise ValueError(code)
    return value


class PracticalReceiptInformation:
    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_practical_receipt_run_required')
        self.store, self.run_id = store, run_id

    def _accession(self, episode_id, operation_key):
        return 'practical_receipt_' + digest([self.run_id, episode_id, operation_key])

    def _sources(self, accession):
        return [row for row in self.store.list('source')
            if row.get('provider') == PROVIDER and row.get('accession') == accession]

    def _original_assignment(self, body, snapshot):
        assignment = validate_assignment(snapshot['assignment'])
        if (snapshot['version'] != ASSIGNMENT_SNAPSHOT_VERSION
                or snapshot['run_id'] != self.run_id or snapshot['episode_id'] != body['episode_id']
                or canonical(snapshot['scope']) != canonical(body['scope'])
                or digest(assignment) != body['assignment_sha256']):
            raise ValueError('practical_receipt_assignment_conflict')
        return assignment

    def _qualify(self, body, snapshot, receiving_scope):
        body = _object(body, BODY_FIELDS, 'invalid_practical_receipt_information')
        snapshot = _object(snapshot, SNAPSHOT_FIELDS, 'invalid_practical_receipt_assignment_snapshot')
        receipt = validate_receipt(body['receipt'])
        if (body['version'] != VERSION or body['run_id'] != self.run_id
                or receipt['run_id'] != self.run_id or receipt['episode_id'] != body['episode_id']
                or receipt['assignment_sha256'] != body['assignment_sha256']):
            raise ValueError('practical_receipt_information_identity_conflict')
        # Ordinary sources are rootless in Store. Explicit containment here
        # preserves original subject/member/segment boundaries across reports.
        try:
            self.store.validate_scope(plain(receiving_scope))
            self.store.validate_scope(body['scope'], parent_scope=plain(receiving_scope))
        except ValueError as error:
            raise ValueError('practical_receipt_outside_receiving_scope') from error
        assignment = self._original_assignment(body, snapshot)
        before = validate_context(receipt['context_before'], workspace=assignment['workspace'])
        after = validate_context(receipt['context_after'], workspace=assignment['workspace'])
        changed = any(before[key] != after[key] for key in ('cwd', 'environment'))
        if after['revision'] != before['revision'] + int(changed):
            raise ValueError('practical_receipt_context_revision_conflict')
        validate_validations(receipt['validations'], assignment, receipt['outcome'], after,
            tool_name=receipt['tool_name'])
        return body

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        metadata = self.store.get(reference)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise ValueError('invalid_practical_receipt_artifact') from error
        sha = hashlib.sha256(raw).hexdigest()
        if (metadata.get('record_type') != 'artifact' or metadata.get('sha256') != sha
                or reference != 'artifact_' + sha or metadata.get('size') != len(raw)
                or raw != canonical(value).encode('utf-8')):
            raise ValueError('practical_receipt_artifact_identity_conflict')
        return value

    def _source_payload(self, body, artifact, request):
        receipt = body['receipt']
        return {'provider': PROVIDER,
            'accession': self._accession(body['episode_id'], receipt['operation_key']),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': VERSION, 'retrieved_at': receipt['finished_at']}

    def publish(self, context, receipt):
        if context.run_id != self.run_id:
            raise ValueError('practical_receipt_publication_context_conflict')
        receipt = validate_receipt(receipt)
        assignment = validate_assignment(plain(context.assignment))
        if (receipt['episode_id'] != context.episode_id
                or receipt['assignment_sha256'] != digest(assignment)
                or context.role != 'launch_' + assignment['resource_kind']):
            raise ValueError('practical_receipt_publication_context_conflict')
        body = {'version': VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'assignment_sha256': digest(assignment), 'scope': plain(context.scope), 'receipt': receipt}
        snapshot = {'version': ASSIGNMENT_SNAPSHOT_VERSION, 'run_id': self.run_id,
            'episode_id': context.episode_id, 'scope': plain(context.scope), 'assignment': assignment}
        self._qualify(body, snapshot, plain(context.scope))
        accession = self._accession(context.episode_id, receipt['operation_key'])
        with self.store.transaction():
            existing = self._sources(accession)
            if existing:
                if len(existing) != 1 or canonical(self.read(existing[0]['id'], context.scope)) != canonical(body):
                    raise ValueError('practical_receipt_publication_identity_conflict')
                return existing[0]['id']
            artifact = self.store.artifact(canonical(body), 'application/json')
            request = self.store.artifact(canonical(snapshot), 'application/json')
            source = self.store.put('source', self._source_payload(body, artifact, request), origin='tool')
            return source['id']

    def read(self, reference, scope):
        source = self.store.get(reference)
        if source.get('record_type') != 'source' or source.get('provider') != PROVIDER:
            raise ValueError('not_a_practical_receipt_source')
        try:
            body = self._artifact_json(source['artifact_ref'])
            snapshot = self._artifact_json(source['request_ref'])
            body = self._qualify(body, snapshot, scope)
            expected = self._source_payload(body, source['artifact_ref'], source['request_ref'])
            actual = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
            if (source.get('origin') != 'tool' or canonical(actual) != canonical(expected)
                    or reference != identity('source', {'origin': 'tool', 'record': expected})):
                raise ValueError('practical_receipt_source_identity_conflict')
            if len(self._sources(expected['accession'])) != 1:
                raise ValueError('practical_receipt_publication_identity_conflict')
            return deepcopy(body)
        except (KeyError, TypeError, OverflowError) as error:
            raise ValueError('invalid_practical_receipt_information') from error

    def resolve(self, context, reference, namespace):
        if context.run_id != self.run_id:
            return False
        if namespace not in {None, 'source', 'practical_receipt'}:
            return False
        try:
            self.read(reference, context.scope)
            return True
        except (ValueError, OSError):
            return False


__all__ = ['PracticalReceiptInformation', 'PROVIDER', 'VERSION']
