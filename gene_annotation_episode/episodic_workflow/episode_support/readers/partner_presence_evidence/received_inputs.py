"""The received-input reader of one A107 tool action on ``episode_runtime``.

A tool reads the bytes or metadata of a File/Source only when the acting episode
received it, and only together with the record that produced it:

- **Received.** The reference is one of the ``ActionInvocation.received_record_refs``
  (the records the episode's reasoning views showed it, its own tool outcomes
  returned, or its children returned). A Source must also lie in the episode's
  admitted Store scope.
- **Producer.** Established, in this order, from
  1. this episode's own recorded tool outcomes before the current unit
     (``recorder.recall('a107_state_<i>')`` / ``'a107_outcome_<i>'``): the earliest
     completed or partial tool outcome that returned the reference. The Store's
     saved operation row under the same operation key must hold exactly that
     outcome;
  2. for a Source the episode received in its scope without returning it itself,
     the Store's own record of it (its identity-checked Source record and every
     saved tool operation of the run that published it);
  3. for a File (artifact) not returned by a recorded outcome, a received in-scope
     Source whose original File it is, with that Source's own producer.

  Nothing else establishes a producer; the read fails with
  ``reference_not_received``.
- **Current action.** ``selected_action`` checks the current tool action against
  the decision the episode recorded for this unit (``ActionInvocation.decision_name``).

Results keep the private received-input shapes of
``molecular_sequence_input_contracts``. An authority failure returns a failure
record with no input metadata (the consumers raise on it); a journal record that
is missing or disagrees raises.
"""
from copy import deepcopy
import json

from episode_runtime.journal import same_record

from gene_annotation_episode.episodic_workflow.episode_support.tools.action_invocation import ActionInvocation
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, canonical, identity
from gene_annotation_episode.materials import source_window_selection
from gene_annotation_episode.episodic_workflow.episode_support.forms.molecular_sequence_input_contracts import (
    NAMESPACES, RECEIVED_FILE_VERSION, RECEIVED_SOURCE_VERSION, _file_format, input_record_digest,
    molecular_sequence_input_failure, validate_molecular_sequence_received_file,
    validate_molecular_sequence_received_source)
from gene_annotation_episode.episodic_workflow.episode_support.records.local_execution.partner_presence_evidence.native_file_capture import NativeFileCaptureError, _metadata, retained_native_file

VERSION = 'a107_received_input'
# Store tables in which A107's tool registries save each operation's returned outcome by operation key.
PRODUCING_STATUSES = ('completed', 'partial')
UNIT_KINDS = ('tool', 'reason', 'child')


class _InputFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code):
    if not condition:
        raise _InputFailure(code)


def _selection_text(reference):
    return type(reference) is str and bool(reference) and not any(c in reference for c in '\0\r\n')


class ReceivedInputs:
    """Reads Files/Sources the acting A107 episode received, with their producing records."""

    def __init__(self, store, invocation, name, arguments):
        if type(invocation) is not ActionInvocation or type(name) is not str or not name:
            raise ContractError('a107_received_inputs_require_action_invocation')
        self.store, self.invocation, self.name, self.arguments = store, invocation, name, deepcopy(arguments)
        self._outcomes = None

    # -- the acting action and its recorded predecessors -------------------------------

    def selected_action(self):
        """The recorded decision of this unit, which must select exactly this tool action."""
        invocation = self.invocation
        response = invocation.recorder.recall(invocation.decision_name)
        selection = response.get('selection') if isinstance(response, dict) else None
        try:
            arguments = json.loads(selection['arguments_json'])
        except (TypeError, KeyError, ValueError) as error:
            raise ContractError('a107_received_input_selected_action_conflict') from error
        if (not invocation.decision_name.startswith('a107_decision_' + str(invocation.position) + '_')
                or selection.get('kind') != 'tool' or selection.get('tool') != self.name
                or canonical(arguments) != canonical(self.arguments)):
            raise ContractError('a107_received_input_selected_action_conflict')
        return {'kind': 'tool', 'tool': self.name, 'arguments': deepcopy(self.arguments),
                'run_id': invocation.run_id, 'episode_id': invocation.episode_id,
                'position': invocation.position, 'decision_name': invocation.decision_name,
                'operation_key': invocation.operation_key}

    def recorded_tool_outcomes(self):
        """``(position, executed)`` for every tool unit this episode recorded before the current one."""
        if self._outcomes is None:
            recorder, outcomes = self.invocation.recorder, []
            for position in range(self.invocation.position):
                state = recorder.recall('a107_state_' + str(position))
                last = state.get('last_outcome') if isinstance(state, dict) else None
                if not isinstance(last, dict) or last.get('kind') not in UNIT_KINDS:
                    raise ContractError('a107_recorded_unit_state_invalid:' + str(position))
                if last['kind'] != 'tool':
                    continue
                executed = recorder.recall('a107_outcome_' + str(position))
                if not same_record(canonical(executed), last) or not isinstance(executed.get('outcome'), dict):
                    raise ContractError('a107_recorded_tool_outcome_differs_from_state:' + str(position))
                outcomes.append((position, executed))
            self._outcomes = outcomes
        return self._outcomes

    def producer(self, reference, namespace, scope):
        """The record that produced a received ``reference`` (see module docstring)."""
        invocation = self.invocation
        for position, executed in self.recorded_tool_outcomes():
            outcome = executed['outcome']
            if outcome.get('status') in PRODUCING_STATUSES and reference in outcome.get('record_refs', ()):
                operation_key = invocation.run_id + ':' + invocation.episode_id + ':' + str(position)
                return {'kind': 'recorded_tool_outcome', 'run_id': invocation.run_id,
                        'episode_id': invocation.episode_id, 'position': position,
                        'operation_key': operation_key, 'tool': executed['tool'],
                        'arguments': deepcopy(executed['arguments']), 'status': outcome['status']}
        if namespace == 'source':
            record = self.store.get(reference)
            return {'kind': 'store_record', 'record_type': 'source', 'origin': record['origin'],
                    'provider': record.get('provider'), 'record_sha256': input_record_digest(record)}
        if namespace == 'artifact':
            for candidate in invocation.received_record_refs:
                if candidate == reference:
                    continue
                row = self.store.get(candidate)
                if row.get('record_type') == 'source' and row.get('artifact_ref') == reference:
                    self._received_source(candidate, scope)
                    return {'kind': 'received_source_original', 'source_ref': candidate,
                            'source_producer': self.producer(candidate, 'source', scope)}
        raise _InputFailure('reference_not_received')

    # -- received records ----------------------------------------------------------------

    def _scope(self, context):
        _require(context is self.invocation, 'invalid_context')
        try:
            return self.store.validate_scope(plain(context.scope))
        except ContractError as error:
            raise _InputFailure('scope_denied') from error

    def _received_source(self, reference, scope):
        try:
            _require(bool(self.store.reference_subset([reference], scope)), 'scope_denied')
        except ContractError as error:
            raise _InputFailure('scope_denied') from error
        record = self.store.get(reference)
        payload = {key: value for key, value in record.items() if key not in ('id', 'record_type', 'origin')}
        _require(record.get('origin') is not None
                 and identity('source', dict(origin=record['origin'], record=payload)) == reference,
                 'source_identity_conflict')
        return record

    def _record_item(self, context, reference, namespace):
        scope = self._scope(context)
        _require(reference in context.received_record_refs, 'reference_not_received')
        try:
            record = self.store.get(reference)
        except ContractError as error:
            raise _InputFailure('reference_unavailable') from error
        _require(record.get('id') == reference and record.get('record_type') == namespace, 'reference_type_conflict')
        if namespace == 'source':
            self._received_source(reference, scope)
        manifest = {'version': VERSION,
                    'received_record_refs_sha256': input_record_digest(list(context.received_record_refs)),
                    'position': context.position, 'producer': self.producer(reference, namespace, scope)}
        return dict(receiver=dict(run_id=context.run_id, episode_id=context.episode_id,
                                  request_sha256=input_record_digest(context.request),
                                  assignment_sha256=input_record_digest(context.assignment)),
                    scope=scope, inheritance_manifest=manifest,
                    witness=dict(reference=reference, namespace=namespace, record=deepcopy(record),
                                 record_sha256=input_record_digest(record), record_revision=record.get('revision'),
                                 source_version=record.get('version') if namespace == 'source' else None))

    def _file_item(self, context, reference, namespace, *, file_format):
        item = self._record_item(context, reference, namespace)
        record = item['witness']['record']
        if namespace == 'source':
            artifact_ref, representation, _ = source_window_selection(record, 'original')
            _require(representation == 'original' and type(artifact_ref) is str, 'artifact_unavailable')
        else:
            artifact_ref = reference
        try:
            artifact = _metadata(self.store, artifact_ref)
        except NativeFileCaptureError as error:
            raise _InputFailure('artifact_identity_conflict' if error.code == 'retained_artifact_mismatch'
                                else 'artifact_unavailable') from error
        item.update(file=dict(artifact_ref=artifact_ref, sha256=artifact['sha256'], size_bytes=artifact['size'],
                              format=file_format),
                    artifact_record=artifact, byte_verification='unavailable')
        return item

    # -- readers ---------------------------------------------------------------------------

    def read_received_source(self, context, reference):
        """Received Source metadata only; its artifact references confer no File access."""
        if not _selection_text(reference):
            raise ValueError('molecular_sequence_input_invalid_selection')
        result = dict(version=RECEIVED_SOURCE_VERSION, selection=dict(reference=reference, namespace='source'),
                      input=None, failure=None)
        try:
            with self.store.read_snapshot():
                result['input'] = self._record_item(context, reference, 'source')
        except _InputFailure as error:
            result['input'], result['failure'] = None, molecular_sequence_input_failure(error.code)
        return validate_molecular_sequence_received_source(result)

    def read_received_file_metadata(self, context, reference, namespace, *, file_format):
        """Received File metadata without opening its bytes; raises ``ValueError`` on an authority failure."""
        if not _selection_text(reference) or namespace not in NAMESPACES or not _file_format(file_format):
            raise ValueError('molecular_sequence_input_invalid_selection')
        try:
            with self.store.read_snapshot():
                return self._file_item(context, reference, namespace, file_format=file_format)
        except _InputFailure as error:
            raise ValueError('molecular_sequence_input_' + error.code) from error

    def read_received_file(self, context, reference, namespace, *, file_format):
        """Received File metadata and its identity-verified Store path (``None`` on failure)."""
        if not _selection_text(reference) or namespace not in NAMESPACES or not _file_format(file_format):
            raise ValueError('molecular_sequence_input_invalid_selection')
        result = dict(version=RECEIVED_FILE_VERSION, selection=dict(reference=reference, namespace=namespace),
                      input=None, failure=None)
        path = None
        try:
            with self.store.read_snapshot():
                item = self._file_item(context, reference, namespace, file_format=file_format)
                result['input'] = item
                try:
                    path = retained_native_file(self.store, item['file'])
                except NativeFileCaptureError as error:
                    code = ('artifact_identity_conflict' if error.code == 'retained_artifact_mismatch'
                            else 'artifact_bytes_unavailable')
                    result['failure'] = molecular_sequence_input_failure(code)
                    item['byte_verification'] = 'identity_conflict' if code == 'artifact_identity_conflict' else 'unavailable'
                else:
                    item['byte_verification'] = 'verified'
        except _InputFailure as error:
            result['input'], result['failure'] = None, molecular_sequence_input_failure(error.code)
        return validate_molecular_sequence_received_file(result), path

    def __call__(self, context, reference, namespace, *, file_format=None, source_metadata_only=False):
        """The reader A107's tools call: Source metadata only, or one File in a selected format."""
        if type(source_metadata_only) is not bool or (file_format is None) == (not source_metadata_only) \
                or (source_metadata_only and namespace != 'source'):
            raise ValueError('molecular_sequence_input_invalid_selection')
        if source_metadata_only:
            return self.read_received_source(context, reference)
        return self.read_received_file(context, reference, namespace, file_format=file_format)


__all__ = ['ReceivedInputs', 'VERSION']
