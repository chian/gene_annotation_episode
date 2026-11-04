"""Passive, append-only reservations for explicitly selected API effects.

The execution host proves commission ownership and supplies actual outcomes.
This module makes no request, schedules no work and projects no credit. An
issued marker records uncertainty before transport; it is not an idempotency
guarantee supplied by a remote service.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import re

from .execution_contracts import canonical, digest
from .practical_execution_state import _immutable, _read


RESERVATION_VERSION = 'selected_api_effect_reservation_v1'
INTENT_VERSION = 'selected_api_effect_intent_v1'
STATE_VERSION = 'selected_api_effect_state_v1'
RECEIPT_VERSION = 'selected_api_effect_receipt_v1'
_RESERVATION_FIELDS = {'version', 'reservation_ref', 'run_id', 'episode_id',
    'operation_key', 'original_job_owner', 'resource_id', 'effect_refs'}
_OUTCOME_FIELDS = {'effect_ref', 'state', 'confirmation_source_ref',
    'native_effect_identifiers', 'ancillary_effects', 'failure'}


class EffectConflict(ValueError):
    """Specific local conflict retaining the original affected effect handles."""

    def __init__(self, code, *, effect_refs=()):
        self.code = code
        self.effect_refs = tuple(effect_refs)
        super().__init__(code)


def _validate(name, value):
    from .bvbrc_appservice_contracts import validate_contract
    return validate_contract(name, value)


def _same(left, right):
    return canonical(left) == canonical(right)


def _slot(descriptor):
    slot, kind = descriptor['slot'], descriptor['kind']
    if slot['kind'] != kind:
        raise ValueError('api_effect_kind_slot_conflict')
    if kind == 'workspace_create':
        path = slot['target_path']
        if not path.startswith('/') or any(char in path for char in '\x00\r\n'):
            raise ValueError('api_effect_workspace_path_invalid')
        # Only the equivalence already established by the native Workspace
        # contract. Do not invent relative-path, UUID or symlink equivalence.
        target = {'path': re.sub(r'/+', '/', path).rstrip('/') or '/'}
    elif kind == 'shock_upload':
        target = {'shock_node_id': slot['shock_node_id']}
    elif kind == 'appservice_submit':
        target = {}
    else:
        target = {'object_identity': slot['object_identity'], 'generation': slot['generation']}
    return {'original_job_owner': descriptor['original_job_owner'],
        'resource_id': descriptor['resource_id'], 'kind': kind, 'target': target}


def _effect_ref(operation_key, descriptor):
    return 'api_effect_' + digest({'operation_key': operation_key, 'descriptor': descriptor})


def _initial(intent):
    return [{
        'version': RECEIPT_VERSION,
        'effect_ref': reference,
        'descriptor': deepcopy(descriptor),
        'operation_key': intent['reservation']['operation_key'],
        'state': 'prepared_not_issued', 'issued_at': None,
        'confirmation_source_ref': None, 'native_effect_identifiers': {},
        'ancillary_effects': [], 'failure': None,
    } for reference, descriptor in zip(intent['reservation']['effect_refs'], intent['descriptors'])]


class SelectedAPIEffects:
    def __init__(self, directory, *, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_effect_run_required')
        self.run_id = run_id
        self.directory = Path(directory) / 'selected-api-effects' / digest(run_id)

    def _job(self, owner):
        owner = _validate('OriginalJobOwner', owner)
        if owner['run_id'] != self.run_id:
            raise ValueError('api_effect_original_owner_run_conflict')
        return self.directory / 'jobs' / digest(owner)

    @contextmanager
    def _locked(self, owner):
        directory = self._job(owner)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield directory
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    @contextmanager
    def _action_locked(self, operation_key):
        directory = self.directory / 'selected-actions' / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield directory / 'owner.json'
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    @staticmethod
    def _action_owner(reservation):
        return {'version': 'selected_api_effect_action_owner_v1',
            'operation_key': reservation['operation_key'],
            'original_job_owner': deepcopy(reservation['original_job_owner']),
            'reservation_ref': reservation['reservation_ref']}

    def _intent(self, directory):
        value = _read(directory / 'intent.json')
        if set(value) != {'version', 'reservation', 'descriptors'} or value['version'] != INTENT_VERSION:
            raise ValueError('api_effect_intent_invalid')
        reservation = value['reservation']
        if (set(reservation) != _RESERVATION_FIELDS or reservation['version'] != RESERVATION_VERSION
                or reservation['run_id'] != self.run_id
                or directory.name != digest(reservation['operation_key'])):
            raise ValueError('api_effect_reservation_identity_conflict')
        owner = _validate('OriginalJobOwner', reservation['original_job_owner'])
        if directory.parent.parent != self._job(owner):
            raise ValueError('api_effect_owner_directory_conflict')
        descriptors = [_validate('EffectDescriptor', row) for row in value['descriptors']]
        if not descriptors or not _same(descriptors, value['descriptors']):
            raise ValueError('api_effect_descriptors_invalid')
        for descriptor in descriptors:
            if (not _same(descriptor['original_job_owner'], owner)
                    or descriptor['resource_id'] != reservation['resource_id']):
                raise ValueError('api_effect_reservation_descriptor_conflict')
            _slot(descriptor)
        refs = [_effect_ref(reservation['operation_key'], descriptor) for descriptor in descriptors]
        body = {key: deepcopy(item) for key, item in reservation.items() if key != 'reservation_ref'}
        if (reservation['effect_refs'] != refs or len(set(refs)) != len(refs)
                or len({digest(_slot(row)) for row in descriptors}) != len(descriptors)
                or reservation['reservation_ref'] != 'api_effect_reservation_' + digest(body)):
            raise ValueError('api_effect_reservation_digest_conflict')
        self._operation_key(reservation['episode_id'], reservation['operation_key'])
        action_owner = self.directory / 'selected-actions' / digest(reservation['operation_key']) / 'owner.json'
        if not _same(_read(action_owner), self._action_owner(reservation)):
            raise ValueError('api_effect_selected_action_owner_conflict')
        return value

    def _operation_key(self, episode_id, key):
        if not isinstance(episode_id, str) or not episode_id or not isinstance(key, str):
            raise ValueError('api_effect_selected_action_identity_required')
        prefix = self.run_id + ':' + episode_id + ':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('api_effect_selected_action_identity_required')

    def _state(self, directory, intent):
        receipts = _initial(intent)
        previous = digest(intent)
        count = 0
        for path in sorted((directory / 'states').glob('*.json')):
            count += 1
            value = _read(path)
            if (set(value) != {'version', 'reservation_ref', 'ordinal', 'previous_sha256', 'effects'}
                    or value['version'] != STATE_VERSION or value['ordinal'] != count
                    or type(value['ordinal']) is not int
                    or value['previous_sha256'] != previous
                    or value['reservation_ref'] != intent['reservation']['reservation_ref']
                    or path.name != f'{count:08d}-{digest(value)}.json'):
                raise ValueError('api_effect_state_chain_conflict')
            rows = value['effects']
            if not isinstance(rows, list) or len(rows) != len(receipts):
                raise ValueError('api_effect_state_members_conflict')
            changed = False
            for old, row in zip(receipts, rows):
                _validate('EffectReceipt', row)
                self._transition(old, row)
                changed |= not _same(old, row)
            if not changed:
                raise ValueError('api_effect_empty_state_transition')
            receipts, previous = rows, digest(value)
        return receipts, count, previous

    @staticmethod
    def _transition(old, row):
        for field in ('version', 'effect_ref', 'descriptor', 'operation_key'):
            if not _same(old[field], row[field]):
                raise ValueError('api_effect_immutable_identity_conflict')
        if _same(old, row):
            return
        if old['state'] in {'confirmed', 'not_sent'}:
            raise ValueError('api_effect_closed_outcome_conflict')
        if old['state'] == 'prepared_not_issued':
            if row['state'] == 'not_sent':
                if (row['issued_at'] is not None or row['confirmation_source_ref'] is not None
                        or row['native_effect_identifiers'] or row['ancillary_effects']
                        or not isinstance(row['failure'], dict)
                        or row['failure']['effect_outcome'] != 'not_sent'):
                    raise ValueError('api_effect_definitive_not_sent_required')
                return
            expected = {**old, 'state': 'issued_unknown', 'issued_at': row['issued_at']}
            if (row['state'] != 'issued_unknown' or not isinstance(row['issued_at'], str)
                    or not row['issued_at'] or not _same(row, expected)):
                raise ValueError('api_effect_issue_transition_required')
            return
        if old['state'] != 'issued_unknown' or row['issued_at'] != old['issued_at']:
            raise ValueError('api_effect_outcome_transition_invalid')
        if row['state'] not in {'issued_unknown', 'confirmed', 'not_sent'}:
            raise ValueError('api_effect_outcome_state_invalid')
        if row['state'] == 'confirmed' and not row['confirmation_source_ref']:
            raise ValueError('api_effect_confirmation_source_required')
        if row['state'] == 'not_sent':
            if (row['confirmation_source_ref'] is not None or row['native_effect_identifiers']
                    or row['ancillary_effects'] or not isinstance(row['failure'], dict)
                    or row['failure']['effect_outcome'] != 'not_sent'):
                raise ValueError('api_effect_definitive_not_sent_required')
        if row['state'] == 'issued_unknown' and row['confirmation_source_ref'] is not None:
            raise ValueError('api_effect_unknown_confirmation_conflict')

    def _append(self, directory, intent, receipts, count, previous):
        value = {'version': STATE_VERSION, 'reservation_ref': intent['reservation']['reservation_ref'],
            'ordinal': count + 1, 'previous_sha256': previous, 'effects': receipts}
        states = directory / 'states'
        states.mkdir(exist_ok=True)
        _immutable(states / f'{count + 1:08d}-{digest(value)}.json', value)

    def _all(self, job):
        for path in sorted((job / 'actions').glob('*/intent.json')):
            intent = self._intent(path.parent)
            receipts, _, _ = self._state(path.parent, intent)
            yield intent, receipts

    def _aliases(self, job, resource_id):
        """Reconstruct only recorded target aliases; no reference discovery."""
        groups = []
        for path in sorted((job / 'object-identities').glob('*.json')):
            row = _read(path)
            if (set(row) != {'version', 'original_job_owner', 'resource_id', 'aliases',
                            'identity', 'merged_identities', 'evidence_refs'}
                    or row['version'] != 'selected_api_object_identity_v1'
                    or path.stem != digest(row) or self._job(row['original_job_owner']) != job):
                raise ValueError('api_effect_object_alias_record_conflict')
            aliases = self._object_aliases(**row['aliases'])
            if not _same(aliases, row['aliases']):
                raise ValueError('api_effect_object_alias_normalization_conflict')
            if (not isinstance(row['identity'], str) or not row['identity'].startswith('api_workspace_object_')
                    or not isinstance(row['merged_identities'], list)
                    or not row['merged_identities']
                    or any(not isinstance(item, str) or not item.startswith('api_workspace_object_')
                           for item in row['merged_identities'])
                    or row['identity'] != min(row['merged_identities'])
                    or row['merged_identities'] != sorted(set(row['merged_identities']))
                    or not isinstance(row['evidence_refs'], list) or not row['evidence_refs']
                    or any(not isinstance(item, str) or not item for item in row['evidence_refs'])):
                raise ValueError('api_effect_object_alias_evidence_invalid')
            if row['resource_id'] != resource_id:
                continue
            nodes = {('identity', item) for item in row['merged_identities']}
            nodes.update((kind, item) for kind, item in aliases.items() if item is not None)
            joined = [group for group in groups if group & nodes]
            for group in joined:
                nodes |= group
                groups.remove(group)
            groups.append(nodes)
        aliases, identities = {}, {}
        for group in groups:
            identity = min(value for kind, value in group if kind == 'identity')
            for kind, value in group:
                if kind == 'identity':
                    identities[value] = identity
                else:
                    aliases[(kind, value)] = identity
        return aliases, identities

    @staticmethod
    def _object_aliases(*, path, uuid):
        if path is None and uuid is None:
            raise ValueError('api_effect_object_identity_required')
        if path is not None:
            if (not isinstance(path, str) or not path.startswith('/')
                    or any(char in path for char in '\x00\r\n')):
                raise ValueError('api_effect_workspace_path_invalid')
            path = re.sub(r'/+', '/', path).rstrip('/') or '/'
        if uuid is not None:
            if (not isinstance(uuid, str) or re.fullmatch(
                    r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}', uuid) is None):
                raise ValueError('api_effect_workspace_uuid_invalid')
            uuid = uuid.lower()
        return {'path': path, 'uuid': uuid}

    def resolve_object_identity(self, original_job_owner, resource_id, *, path, uuid, evidence_refs):
        """Record caller-authenticated aliases for a capability mutation target.

        A path is a mutable Workspace target, not proof of immutable bytes.
        The host owns source custody and the actual path/UUID relationship.
        Original effect descriptors remain unchanged when more aliases arrive.
        """
        aliases = self._object_aliases(path=path, uuid=uuid)
        if (not isinstance(resource_id, str) or not resource_id
                or not isinstance(evidence_refs, list) or not evidence_refs
                or any(not isinstance(item, str) or not item for item in evidence_refs)):
            raise ValueError('api_effect_object_alias_evidence_required')
        with self._locked(original_job_owner) as job:
            known, _ = self._aliases(job, resource_id)
            found = sorted({known[(kind, value)] for kind, value in aliases.items()
                if value is not None and (kind, value) in known})
            identity = (found[0] if found else 'api_workspace_object_' + digest({
                'owner': original_job_owner, 'resource_id': resource_id, 'aliases': aliases}))
            row = {'version': 'selected_api_object_identity_v1',
                'original_job_owner': deepcopy(original_job_owner), 'resource_id': resource_id,
                'aliases': aliases, 'identity': identity,
                'merged_identities': found or [identity], 'evidence_refs': sorted(set(evidence_refs))}
            directory = job / 'object-identities'
            directory.mkdir(exist_ok=True)
            _immutable(directory / (digest(row) + '.json'), row)
            return identity

    @staticmethod
    def _effective_slot(descriptor, identities):
        value = _slot(descriptor)
        if descriptor['kind'] == 'download_capability':
            original = value['target']['object_identity']
            value['target']['object_identity'] = identities.get(original, original)
        return value

    def _reservation(self, reservation, job):
        if (not isinstance(reservation, dict) or set(reservation) != _RESERVATION_FIELDS
                or not isinstance(reservation.get('operation_key'), str)):
            raise ValueError('api_effect_reservation_required')
        directory = job / 'actions' / digest(reservation['operation_key'])
        intent = self._intent(directory)
        if not _same(reservation, intent['reservation']):
            raise ValueError('api_effect_original_reservation_conflict')
        return directory, intent

    def reserve(self, context, operation_key, effects):
        if context.run_id != self.run_id:
            raise ValueError('api_effect_context_run_conflict')
        self._operation_key(context.episode_id, operation_key)
        if not isinstance(effects, list) or not effects:
            raise ValueError('api_effect_nonempty_batch_required')
        descriptors = [_validate('EffectDescriptor', row) for row in effects]
        owner, resource = descriptors[0]['original_job_owner'], descriptors[0]['resource_id']
        if any(not _same(row['original_job_owner'], owner) or row['resource_id'] != resource
               for row in descriptors):
            raise ValueError('api_effect_single_original_job_resource_required')
        slots = [digest(_slot(row)) for row in descriptors]
        if len(set(slots)) != len(slots):
            raise ValueError('api_effect_duplicate_target_in_batch')
        reservation = {'version': RESERVATION_VERSION, 'run_id': self.run_id,
            'episode_id': context.episode_id, 'operation_key': operation_key,
            'original_job_owner': deepcopy(owner), 'resource_id': resource,
            'effect_refs': [_effect_ref(operation_key, row) for row in descriptors]}
        reservation['reservation_ref'] = 'api_effect_reservation_' + digest(reservation)
        intent = {'version': INTENT_VERSION, 'reservation': reservation, 'descriptors': descriptors}
        # Global action identity first, then original-job slots. Network work
        # holds neither lock. A failed local publication can resume this same
        # selection, but cannot reassign its key to another original job.
        with self._action_locked(operation_key) as action_owner, self._locked(owner) as job:
            _, identities = self._aliases(job, resource)
            slots = [digest(self._effective_slot(row, identities)) for row in descriptors]
            if len(set(slots)) != len(slots):
                raise EffectConflict('api_effect_duplicate_target_in_batch')
            owner_record = self._action_owner(reservation)
            if action_owner.exists() and not _same(_read(action_owner), owner_record):
                raise EffectConflict('api_effect_action_reused_for_different_work')
            directory = job / 'actions' / digest(operation_key)
            if (directory / 'intent.json').exists():
                if not _same(self._intent(directory), intent):
                    raise EffectConflict('api_effect_action_reused_for_different_work')
                return deepcopy(reservation)
            prior = [row for _, rows in self._all(job) for row in rows]
            for descriptor, slot in zip(descriptors, slots):
                occupied = [row for row in prior if digest(self._effective_slot(row['descriptor'], identities)) == slot
                            and row['state'] != 'not_sent']
                if occupied:
                    code = ('api_effect_payload_conflict' if any(
                        row['descriptor']['payload_sha256'] != descriptor['payload_sha256'] for row in occupied)
                        else 'api_effect_already_reserved_or_issued')
                    raise EffectConflict(code, effect_refs=[row['effect_ref'] for row in occupied])
                if descriptor['kind'] == 'download_capability':
                    generation = descriptor['slot']['generation']
                    predecessor_refs = descriptor['predecessor_evidence_refs']
                    if generation:
                        predecessor = [row for row in prior
                            if row['descriptor']['kind'] == 'download_capability'
                            and row['descriptor']['resource_id'] == resource
                            and identities.get(row['descriptor']['slot']['object_identity'],
                                row['descriptor']['slot']['object_identity']) == identities.get(
                                descriptor['slot']['object_identity'], descriptor['slot']['object_identity'])
                            and row['descriptor']['slot']['generation'] == generation - 1
                            and row['state'] in {'issued_unknown', 'confirmed'}
                            and row['effect_ref'] in predecessor_refs]
                        if len(predecessor) != 1:
                            raise EffectConflict('api_effect_capability_predecessor_required')
            directory.mkdir(parents=True, exist_ok=True)
            # One atomic publication reserves every member together. A crash
            # cannot reserve only the first target of a selected native batch.
            _immutable(action_owner, owner_record)
            _immutable(directory / 'intent.json', intent)
            return deepcopy(reservation)

    def mark_issued(self, reservation):
        with self._locked(reservation['original_job_owner']) as job:
            directory, intent = self._reservation(reservation, job)
            receipts, count, previous = self._state(directory, intent)
            first = all(row['state'] == 'prepared_not_issued' for row in receipts)
            if first:
                _, identities = self._aliases(job, reservation['resource_id'])
                own_slots = {digest(self._effective_slot(row['descriptor'], identities)) for row in receipts}
                conflicts = [row['effect_ref'] for prior, rows in self._all(job)
                    if prior['reservation']['operation_key'] != reservation['operation_key']
                    for row in rows if row['state'] != 'not_sent'
                    and digest(self._effective_slot(row['descriptor'], identities)) in own_slots]
                if conflicts:
                    raise EffectConflict('api_effect_alias_reservation_conflict', effect_refs=conflicts)
                stamp = datetime.now(timezone.utc).isoformat()
                updated = [{**row, 'state': 'issued_unknown', 'issued_at': stamp} for row in receipts]
                for old, row in zip(receipts, updated):
                    self._transition(old, row)
                self._append(directory, intent, updated, count, previous)
                receipts = updated
            return {'reservation': deepcopy(reservation), 'first_issue': first, 'effects': deepcopy(receipts)}

    def record_outcome(self, reservation, outcomes):
        if (not isinstance(outcomes, list) or any(not isinstance(row, dict)
                or set(row) != _OUTCOME_FIELDS
                or row['state'] not in {'confirmed', 'not_sent', 'issued_unknown'} for row in outcomes)):
            raise ValueError('api_effect_outcome_rows_required')
        with self._locked(reservation['original_job_owner']) as job:
            directory, intent = self._reservation(reservation, job)
            receipts, count, previous = self._state(directory, intent)
            refs = [row['effect_ref'] for row in outcomes]
            if (len(refs) != len(set(refs)) or set(refs) != set(reservation['effect_refs'])):
                raise ValueError('api_effect_complete_batch_outcomes_required')
            by_ref = {row['effect_ref']: row for row in outcomes}
            updated = []
            for old in receipts:
                row = _validate('EffectReceipt', {**old, **deepcopy(by_ref[old['effect_ref']])})
                self._transition(old, row)
                updated.append(row)
            if not _same(receipts, updated):
                self._append(directory, intent, updated, count, previous)
            return deepcopy(updated)

    def read(self, effect_ref, *, original_job_owner):
        if not isinstance(effect_ref, str) or not effect_ref:
            raise ValueError('api_effect_reference_required')
        with self._locked(original_job_owner) as job:
            for _, receipts in self._all(job):
                for row in receipts:
                    if row['effect_ref'] == effect_ref:
                        return deepcopy(row)
        raise ValueError('api_effect_not_owned_or_recorded')


__all__ = ['SelectedAPIEffects', 'EffectConflict']
