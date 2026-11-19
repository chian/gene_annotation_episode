"""The received-file reader of one A103 head tool action on ``episode_runtime``.

A103's native genomic tools (``context.bind_locus`` and the other ``a103_tools``
operations) read a supplied file only through this reader, which the head's
decision source opens for exactly one tool action (``ToolRegistry.current_invocation``).
It returns the file only when the acting episode received it, together with the
record that produced it:

- **Received.** The reference is one of the ``A103Invocation.received_record_refs``
  (the records this episode was handed, its own outcomes returned, or its children
  returned) and lies in the episode's admitted Store scope. A Source's stored
  identity must match its content.
- **Producer.** Established, in this order, from
  1. this episode's own recorded tool outcomes before the current unit
     (``recorder.recall('outcome.<i>')``): the earliest completed or partial tool
     outcome whose tool result returned the reference. The Store's saved
     operation under the same operation key must hold exactly that tool result;
  2. the Store's own record of the Source (its origin, provider and every saved
     tool operation of the run that published it).
- **Bytes.** The Source's original artifact, identity-verified against its
  retained digest; the read returns that file's path.

An authority or byte failure is returned as a ``failure`` with no input (the
consumer raises on it). A recorded outcome or saved operation that disagrees
raises.
"""
from __future__ import annotations

import hashlib
import json

from episode_runtime.journal import same_record

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical, identity
from gene_annotation_episode.episodic_workflow.episode_support.records.documents.gene_context_evidence.materials import _verified_artifact_path, source_window_selection

VERSION = 'a103_received_file_v1'
NAMESPACES = ('source',)
# Store tables in which A103's tool registries save each operation's returned tool result by operation key.
PRODUCING_STATUSES = ('completed', 'partial')
_FAILURE_STAGES = {'invalid_context': 'authority', 'reference_not_received': 'authority',
                   'reference_unavailable': 'authority', 'reference_type_conflict': 'authority',
                   'scope_denied': 'authority', 'source_identity_conflict': 'identity',
                   'artifact_unavailable': 'bytes', 'artifact_identity_conflict': 'bytes'}


class _InputFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code):
    if not condition:
        raise _InputFailure(code)


def _digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class ReceivedFiles:
    """Reads Source files the acting A103 episode received, with their producing records.

    ``recorder`` is the acting Episode's ``EpisodeRecorder``; ``position`` is the
    current unit, whose earlier units' recorded outcomes establish producers.
    """

    def __init__(self, store, invocation, recorder, position):
        if type(position) is not int or position < 0:
            raise ContractError('a103_received_files_require_unit_position')
        self.store, self.invocation, self.recorder, self.position = store, invocation, recorder, position

    def producer(self, reference, record):
        """The record that produced a received Source ``reference`` (see module docstring)."""
        context = self.invocation
        for position in range(self.position):
            outcome = self.recorder.recall('outcome.' + str(position))
            if not isinstance(outcome, dict) or outcome.get('kind') != 'tool':
                continue
            result = outcome.get('result')
            if (isinstance(result, dict) and result.get('status') in PRODUCING_STATUSES
                    and reference in (result.get('record_refs') or ())):
                operation_key = context.run_id + ':' + context.episode_id + ':' + str(position)
                return {'kind': 'recorded_tool_outcome', 'run_id': context.run_id,
                        'episode_id': context.episode_id, 'position': position,
                        'operation_key': operation_key, 'operation_ref': result.get('operation_ref'),
                        'status': result['status']}
        return {'kind': 'store_record', 'record_type': 'source', 'origin': record['origin'],
                'provider': record.get('provider'), 'record_sha256': _digest(record)}

    def _source(self, context, reference):
        _require(context is self.invocation, 'invalid_context')
        try:
            scope = self.store.validate_scope(plain(context.scope))
        except ContractError as error:
            raise _InputFailure('scope_denied') from error
        _require(reference in context.received_record_refs, 'reference_not_received')
        try:
            _require(bool(self.store.reference_subset([reference], scope)), 'scope_denied')
            record = self.store.get(reference)
        except ContractError as error:
            raise _InputFailure('reference_unavailable') from error
        _require(record.get('id') == reference and record.get('record_type') == 'source', 'reference_type_conflict')
        payload = {key: value for key, value in record.items() if key not in ('id', 'record_type', 'origin')}
        _require(record.get('origin') is not None
                 and identity('source', dict(origin=record['origin'], record=payload)) == reference,
                 'source_identity_conflict')
        return scope, record

    def __call__(self, context, reference, namespace, *, file_format):
        """``(delivery, path)``: the received Source's original file and its producer, or a failure and ``None``."""
        if (type(reference) is not str or not reference or namespace not in NAMESPACES
                or type(file_format) is not str or not file_format):
            raise ValueError('a103_received_file_invalid_selection')
        delivery = {'version': VERSION, 'selection': {'reference': reference, 'namespace': namespace,
                                                      'file_format': file_format},
                    'input': None, 'failure': None}
        path = None
        try:
            with self.store.read_snapshot():
                scope, record = self._source(context, reference)
                artifact_ref, representation, _ = source_window_selection(record, 'original')
                _require(representation == 'original' and type(artifact_ref) is str, 'artifact_unavailable')
                try:
                    artifact = self.store.get(artifact_ref)
                    path = _verified_artifact_path(self.store, artifact_ref)
                except ContractError as error:
                    code = ('artifact_identity_conflict' if str(error).startswith('artifact_digest_mismatch')
                            else 'artifact_unavailable')
                    raise _InputFailure(code) from error
                except OSError as error:
                    raise _InputFailure('artifact_unavailable') from error
                delivery['input'] = {
                    'receiver': {'run_id': context.run_id, 'episode_id': context.episode_id,
                                 'position': self.position},
                    'scope': scope,
                    'received_record_refs_sha256': _digest(list(context.received_record_refs)),
                    'producer': self.producer(reference, record),
                    'witness': {'reference': reference, 'namespace': namespace, 'record_sha256': _digest(record)},
                    'file': {'artifact_ref': artifact_ref, 'sha256': artifact['sha256'],
                             'size_bytes': artifact['size'], 'format': file_format}}
        except _InputFailure as error:
            delivery['input'], path = None, None
            delivery['failure'] = {'stage': _FAILURE_STAGES[error.code], 'code': error.code}
        return delivery, path


__all__ = ['NAMESPACES', 'ReceivedFiles', 'VERSION']
