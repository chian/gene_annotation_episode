"""Durable practical action intents, factual receipts and working context.

There is deliberately no executor here. An unfinished intent records uncertain
work for the caller to reconcile; reading or replaying it never repeats a side
effect. The append-only hashed records recover context without a fragile mutable
pointer or a second source of truth for progress.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile

from .practical_execution_credit import project_practical_credit
from .practical_execution_records import (ASSIGNMENT_VERSION, COMPLETION_VERSION,
    RECEIPT_VERSION, _object, _text, assess_validations, canonical, digest, timestamp, validate_assignment,
    validate_completion_proof, validate_context, validate_outcome, validate_receipt,
    validate_validations)


INTENT_VERSION = 'practical_action_intent_v1'
MANIFEST_VERSION = 'practical_state_v1'
INTENT_FIELDS = {'version', 'run_id', 'episode_id', 'assignment_sha256', 'operation_key',
    'tool_name', 'arguments', 'context_before', 'ordinal', 'started_at'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read(path):
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if raw != (canonical(value) + '\n').encode('utf-8'):
            raise ValueError('practical_record_bytes_changed')
        return value
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError('invalid_practical_state_record') from error


def _immutable(path, value):
    """Publish fully written bytes once, without ever replacing a receipt."""
    payload = (canonical(value) + '\n').encode('utf-8')
    descriptor, temporary = tempfile.mkstemp(prefix='.practical-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError('practical_immutable_record_conflict')
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def _transition(before, after, workspace):
    after = validate_context(after, workspace=workspace)
    changed = any(before[key] != after[key] for key in ('cwd', 'environment'))
    if after['revision'] != before['revision'] + int(changed):
        raise ValueError('practical_context_revision_conflict')
    return after


class PracticalState:
    def __init__(self, directory, run_id, episode_id, assignment, *,
                 initial_validations=None, initial_outcome=None):
        if not _text(run_id) or not _text(episode_id):
            raise ValueError('explicit_practical_episode_identity_required')
        self.directory = Path(directory).expanduser().resolve()
        self.run_id, self.episode_id = run_id, episode_id
        self.assignment = validate_assignment(assignment)
        self.assignment_sha256 = digest(self.assignment)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.directory / 'assignment.json'
        self._intents_path = self.directory / 'intents'
        self._receipts_path = self.directory / 'receipts'
        with self._locked():
            if self._manifest_path.exists():
                if initial_validations is not None or initial_outcome is not None:
                    raise ValueError('practical_initial_baseline_already_frozen')
            else:
                # An existing record set cannot be relabelled as a fresh state.
                if (self._intents_path.exists() and any(self._intents_path.iterdir())
                        or self._receipts_path.exists() and any(self._receipts_path.iterdir())):
                    raise ValueError('practical_initial_manifest_missing')
                outcome = validate_outcome(initial_outcome or {'facts': {}})
                if 'requested_job' in outcome['facts']:
                    raise ValueError('practical_baseline_cannot_complete_requested_job')
                supplied = (assess_validations(self.assignment, outcome, self.assignment['initial_context'])
                    if initial_validations is None else initial_validations)
                validations = validate_validations(supplied, self.assignment,
                    outcome, self.assignment['initial_context'])
                manifest = {'version': MANIFEST_VERSION, 'run_id': run_id, 'episode_id': episode_id,
                    'assignment': self.assignment, 'assignment_sha256': self.assignment_sha256,
                    'initial_validations': validations, 'initial_outcome': outcome, 'created_at': _now()}
                _immutable(self._manifest_path, manifest)
            self._intents_path.mkdir(exist_ok=True)
            self._receipts_path.mkdir(exist_ok=True)
            self._load()

    @contextmanager
    def _locked(self):
        with (self.directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _load(self):
        manifest = _object(_read(self._manifest_path), {'version', 'run_id', 'episode_id',
            'assignment', 'assignment_sha256', 'initial_validations', 'initial_outcome', 'created_at'},
            code='invalid_practical_state_manifest')
        if (manifest['version'] != MANIFEST_VERSION or manifest['run_id'] != self.run_id
                or manifest['episode_id'] != self.episode_id
                or manifest['assignment_sha256'] != self.assignment_sha256
                or canonical(manifest['assignment']) != canonical(self.assignment)):
            raise ValueError('practical_assignment_identity_conflict')
        timestamp(manifest['created_at'])
        baseline_outcome = validate_outcome(manifest['initial_outcome'])
        if 'requested_job' in baseline_outcome['facts']:
            raise ValueError('practical_baseline_cannot_complete_requested_job')
        validate_validations(manifest['initial_validations'], self.assignment,
            baseline_outcome, self.assignment['initial_context'])
        receipts_by_operation = {}
        for path in self._receipts_path.glob('*.json'):
            receipt = validate_receipt(_read(path))
            if path.stem != digest(receipt) or receipt['operation_key'] in receipts_by_operation:
                raise ValueError('practical_receipt_identity_conflict')
            receipts_by_operation[receipt['operation_key']] = receipt
        context = deepcopy(self.assignment['initial_context'])
        intents, receipts, pending, seen = [], [], None, set()
        for ordinal, path in enumerate(sorted(self._intents_path.glob('*.json'))):
            intent = _object(_read(path), INTENT_FIELDS, code='invalid_practical_action_intent')
            if (intent['version'] != INTENT_VERSION or intent['ordinal'] != ordinal
                    or type(intent['ordinal']) is not int
                    or path.name != f'{ordinal:012d}-{digest(intent)}.json'
                    or intent['operation_key'] in seen or pending is not None
                    or intent['run_id'] != self.run_id or intent['episode_id'] != self.episode_id
                    or intent['assignment_sha256'] != self.assignment_sha256
                    or canonical(intent['context_before']) != canonical(context)
                    or not _text(intent['operation_key']) or not _text(intent['tool_name'])):
                raise ValueError('practical_intent_identity_conflict')
            _object(intent['arguments'])
            timestamp(intent['started_at'])
            seen.add(intent['operation_key'])
            intents.append(intent)
            receipt = receipts_by_operation.pop(intent['operation_key'], None)
            if receipt is None:
                pending = intent
                continue
            expected = {key: intent[key] for key in ('run_id', 'episode_id', 'assignment_sha256',
                'operation_key', 'tool_name', 'arguments', 'context_before', 'started_at')}
            if any(canonical(receipt[key]) != canonical(value) for key, value in expected.items()):
                raise ValueError('practical_receipt_intent_conflict')
            context = _transition(context, receipt['context_after'], self.assignment['workspace'])
            validate_validations(receipt['validations'], self.assignment, receipt['outcome'],
                context, tool_name=intent['tool_name'])
            receipts.append(receipt)
        if receipts_by_operation:
            raise ValueError('practical_receipt_without_selected_intent')
        return manifest, intents, receipts, context, pending

    def context(self):
        with self._locked():
            return deepcopy(self._load()[3])

    def receipts(self):
        with self._locked():
            return deepcopy(self._load()[2])

    def begin(self, operation_key, tool_name, arguments):
        if not _text(operation_key) or not _text(tool_name):
            raise ValueError('explicit_practical_operation_identity_required')
        arguments = _object(arguments, code='invalid_practical_action_arguments')
        with self._locked():
            manifest, intents, receipts, context, pending = self._load()
            original = next((item for item in intents if item['operation_key'] == operation_key), None)
            if original is not None:
                if original['tool_name'] != tool_name or canonical(original['arguments']) != canonical(arguments):
                    raise ValueError('practical_operation_identity_conflict')
                receipt = next((item for item in receipts if item['operation_key'] == operation_key), None)
                return {'state': 'completed' if receipt is not None else 'pending',
                    'intent': deepcopy(original), 'receipt': deepcopy(receipt)}
            if pending is not None:
                raise ValueError('practical_unfinished_intent_requires_reconciliation')
            if self._completion(manifest, receipts, pending) is not None:
                raise ValueError('practical_assignment_already_completed')
            intent = {'version': INTENT_VERSION, 'run_id': self.run_id, 'episode_id': self.episode_id,
                'assignment_sha256': self.assignment_sha256, 'operation_key': operation_key,
                'tool_name': tool_name, 'arguments': arguments, 'context_before': context,
                'ordinal': len(intents), 'started_at': _now()}
            _immutable(self._intents_path / f'{len(intents):012d}-{digest(intent)}.json', intent)
            return {'state': 'new', 'intent': deepcopy(intent), 'receipt': None}

    def finish(self, operation_key, outcome, validations, context_after=None):
        outcome = validate_outcome(outcome)
        with self._locked():
            _, intents, receipts, context, _ = self._load()
            intent = next((item for item in intents if item['operation_key'] == operation_key), None)
            if intent is None:
                raise ValueError('practical_action_intent_missing')
            original = next((item for item in receipts if item['operation_key'] == operation_key), None)
            after = _transition(intent['context_before'],
                intent['context_before'] if context_after is None else context_after,
                self.assignment['workspace'])
            validations = validate_validations(validations, self.assignment, outcome, after,
                tool_name=intent['tool_name'])
            if original is not None:
                expected = {'outcome': outcome, 'validations': validations, 'context_after': after}
                if any(canonical(original[key]) != canonical(value) for key, value in expected.items()):
                    raise ValueError('practical_action_receipt_conflict')
                return deepcopy(original)
            if canonical(context) != canonical(intent['context_before']):
                raise ValueError('practical_context_revision_conflict')
            receipt = validate_receipt({'version': RECEIPT_VERSION, 'run_id': self.run_id,
                'episode_id': self.episode_id, 'assignment_sha256': self.assignment_sha256,
                'operation_key': operation_key, 'tool_name': intent['tool_name'],
                'arguments': intent['arguments'], 'context_before': intent['context_before'],
                'context_after': after, 'outcome': outcome, 'validations': validations,
                'started_at': intent['started_at'], 'finished_at': _now()})
            _immutable(self._receipts_path / (digest(receipt) + '.json'), receipt)
            return deepcopy(receipt)

    def credit_view(self):
        with self._locked():
            manifest, _, receipts, _, _ = self._load()
            return project_practical_credit(self.assignment, manifest['initial_validations'], receipts)

    def _completion(self, manifest, receipts, pending):
        if not receipts or pending is not None:
            return None
        satisfied = set(project_practical_credit(self.assignment,
            manifest['initial_validations'], receipts)['satisfied_keys'])
        keys = set(self.assignment['completion_keys'])
        if not keys <= satisfied:
            return None
        endpoint_kind = ('requested_job_handoff' if self.assignment['endpoint'] == 'usable_handoff'
            else 'requested_job_outputs')
        last = receipts[-1]
        if not any(item['key'] in keys and item['satisfied']
                and item['predicate']['kind'] == endpoint_kind for item in last['validations']):
            return None
        return {'version': COMPLETION_VERSION, 'run_id': self.run_id, 'episode_id': self.episode_id,
            'assignment_sha256': self.assignment_sha256, 'endpoint': self.assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}

    def completion_proof(self):
        with self._locked():
            manifest, _, receipts, _, pending = self._load()
            return self._completion(manifest, receipts, pending)

    def verify_completion(self, proof):
        if proof is None:
            return False
        try:
            proof = validate_completion_proof(proof)
        except (ValueError, TypeError):
            return False
        with self._locked():
            manifest, _, receipts, _, pending = self._load()
            actual = self._completion(manifest, receipts, pending)
            return actual is not None and canonical(proof) == canonical(actual)


__all__ = ['PracticalState']
