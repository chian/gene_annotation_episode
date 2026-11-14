from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import fcntl
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
RESERVATION_VERSION = 'selected_api_effect_reservation_v1'
INTENT_VERSION = 'selected_api_effect_intent_v1'
STATE_VERSION = 'selected_api_effect_state_v1'
RECEIPT_VERSION = 'selected_api_effect_receipt_v1'
_RESERVATION_FIELDS = {'version', 'reservation_ref', 'run_id', 'episode_id', 'operation_key', 'original_job_owner', 'resource_id', 'effect_refs'}

def _validate(name, value):
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract
    return validate_contract(name, value)

def _same(left, right):
    return canonical(left) == canonical(right)

def _slot(descriptor):
    slot, kind = (descriptor['slot'], descriptor['kind'])
    if slot['kind'] != kind:
        raise ValueError('api_effect_kind_slot_conflict')
    if kind == 'workspace_create':
        path = slot['target_path']
        if not path.startswith('/') or any((char in path for char in '\x00\r\n')):
            raise ValueError('api_effect_workspace_path_invalid')
        target = {'path': re.sub('/+', '/', path).rstrip('/') or '/'}
    elif kind == 'shock_upload':
        target = {'shock_node_id': slot['shock_node_id']}
    elif kind == 'appservice_submit':
        target = {}
    else:
        target = {'object_identity': slot['object_identity'], 'generation': slot['generation']}
    return {'original_job_owner': descriptor['original_job_owner'], 'resource_id': descriptor['resource_id'], 'kind': kind, 'target': target}

def _effect_ref(operation_key, descriptor):
    return 'api_effect_' + digest({'operation_key': operation_key, 'descriptor': descriptor})

def _initial(intent):
    return [{'version': RECEIPT_VERSION, 'effect_ref': reference, 'descriptor': deepcopy(descriptor), 'operation_key': intent['reservation']['operation_key'], 'state': 'prepared_not_issued', 'issued_at': None, 'confirmation_source_ref': None, 'native_effect_identifiers': {}, 'ancillary_effects': [], 'failure': None} for reference, descriptor in zip(intent['reservation']['effect_refs'], intent['descriptors'])]

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

    @staticmethod
    def _action_owner(reservation):
        return {'version': 'selected_api_effect_action_owner_v1', 'operation_key': reservation['operation_key'], 'original_job_owner': deepcopy(reservation['original_job_owner']), 'reservation_ref': reservation['reservation_ref']}

    def _intent(self, directory):
        value = _read(directory / 'intent.json')
        if set(value) != {'version', 'reservation', 'descriptors'} or value['version'] != INTENT_VERSION:
            raise ValueError('api_effect_intent_invalid')
        reservation = value['reservation']
        if set(reservation) != _RESERVATION_FIELDS or reservation['version'] != RESERVATION_VERSION or reservation['run_id'] != self.run_id or (directory.name != digest(reservation['operation_key'])):
            raise ValueError('api_effect_reservation_identity_conflict')
        owner = _validate('OriginalJobOwner', reservation['original_job_owner'])
        if directory.parent.parent != self._job(owner):
            raise ValueError('api_effect_owner_directory_conflict')
        descriptors = [_validate('EffectDescriptor', row) for row in value['descriptors']]
        if not descriptors or not _same(descriptors, value['descriptors']):
            raise ValueError('api_effect_descriptors_invalid')
        for descriptor in descriptors:
            if not _same(descriptor['original_job_owner'], owner) or descriptor['resource_id'] != reservation['resource_id']:
                raise ValueError('api_effect_reservation_descriptor_conflict')
            _slot(descriptor)
        refs = [_effect_ref(reservation['operation_key'], descriptor) for descriptor in descriptors]
        body = {key: deepcopy(item) for key, item in reservation.items() if key != 'reservation_ref'}
        if reservation['effect_refs'] != refs or len(set(refs)) != len(refs) or len({digest(_slot(row)) for row in descriptors}) != len(descriptors) or (reservation['reservation_ref'] != 'api_effect_reservation_' + digest(body)):
            raise ValueError('api_effect_reservation_digest_conflict')
        self._operation_key(reservation['episode_id'], reservation['operation_key'])
        action_owner = self.directory / 'selected-actions' / digest(reservation['operation_key']) / 'owner.json'
        if not _same(_read(action_owner), self._action_owner(reservation)):
            raise ValueError('api_effect_selected_action_owner_conflict')
        return value

    def _operation_key(self, episode_id, key):
        if not isinstance(episode_id, str) or not episode_id or (not isinstance(key, str)):
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
            if set(value) != {'version', 'reservation_ref', 'ordinal', 'previous_sha256', 'effects'} or value['version'] != STATE_VERSION or value['ordinal'] != count or (type(value['ordinal']) is not int) or (value['previous_sha256'] != previous) or (value['reservation_ref'] != intent['reservation']['reservation_ref']) or (path.name != f'{count:08d}-{digest(value)}.json'):
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
            receipts, previous = (rows, digest(value))
        return (receipts, count, previous)

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
                if row['issued_at'] is not None or row['confirmation_source_ref'] is not None or row['native_effect_identifiers'] or row['ancillary_effects'] or (not isinstance(row['failure'], dict)) or (row['failure']['effect_outcome'] != 'not_sent'):
                    raise ValueError('api_effect_definitive_not_sent_required')
                return
            expected = {**old, 'state': 'issued_unknown', 'issued_at': row['issued_at']}
            if row['state'] != 'issued_unknown' or not isinstance(row['issued_at'], str) or (not row['issued_at']) or (not _same(row, expected)):
                raise ValueError('api_effect_issue_transition_required')
            return
        if old['state'] != 'issued_unknown' or row['issued_at'] != old['issued_at']:
            raise ValueError('api_effect_outcome_transition_invalid')
        if row['state'] not in {'issued_unknown', 'confirmed', 'not_sent'}:
            raise ValueError('api_effect_outcome_state_invalid')
        if row['state'] == 'confirmed' and (not row['confirmation_source_ref']):
            raise ValueError('api_effect_confirmation_source_required')
        if row['state'] == 'not_sent':
            if row['confirmation_source_ref'] is not None or row['native_effect_identifiers'] or row['ancillary_effects'] or (not isinstance(row['failure'], dict)) or (row['failure']['effect_outcome'] != 'not_sent'):
                raise ValueError('api_effect_definitive_not_sent_required')
        if row['state'] == 'issued_unknown' and row['confirmation_source_ref'] is not None:
            raise ValueError('api_effect_unknown_confirmation_conflict')

    def _all(self, job):
        for path in sorted((job / 'actions').glob('*/intent.json')):
            intent = self._intent(path.parent)
            receipts, _, _ = self._state(path.parent, intent)
            yield (intent, receipts)

    def read(self, effect_ref, *, original_job_owner):
        if not isinstance(effect_ref, str) or not effect_ref:
            raise ValueError('api_effect_reference_required')
        with self._locked(original_job_owner) as job:
            for _, receipts in self._all(job):
                for row in receipts:
                    if row['effect_ref'] == effect_ref:
                        return deepcopy(row)
        raise ValueError('api_effect_not_owned_or_recorded')

    def read_completed(self, effect_ref, *, original_job_owner):
        """Read a closed effect outcome without creating or locking controls.

        The original intent, action owner and full state chain use the same
        validators as ordinary reads. A confirmed/not-sent effect cannot change
        under those transition rules. Its state describes that selected effect,
        not completion of the remote scientific task or the whole original job.
        """
        if not isinstance(effect_ref, str) or not effect_ref:
            raise ValueError('api_effect_reference_required')
        job = self._job(original_job_owner)
        for _, receipts in self._all(job):
            for row in receipts:
                if row['effect_ref'] == effect_ref:
                    if row['state'] not in {'confirmed', 'not_sent'}:
                        raise ValueError('api_effect_completed_outcome_required')
                    return deepcopy(row)
        raise ValueError('api_effect_not_owned_or_recorded')
