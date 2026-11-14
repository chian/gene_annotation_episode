"""One selected AppService primitive and its original transport receipt.

The existing executor owns selection, its action lock and final observation.
This helper neither chooses another call nor interprets scientific output. The
host decodes retained responses, confirms actual effects and publishes results.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone

from .acquisition import SourceSnapshot
from .bvbrc_appservice_contracts import validate_contract
from .communication import plain
from .execution_contracts import canonical, digest
from .practical_execution_state import _immutable, _read


VERSION = 'selected_api_call_v1'
_PHASES = {'custody', 'prepare', 'transport', 'native_decode', 'association',
           'publication', 'recovery', 'return'}


def _failure(code, *, phase='transport', outcome=None, effects=()):
    return validate_contract('Failure', {'code': code, 'phase': phase,
        'affected_refs': list(effects), 'affected_pointers': [],
        'effect_outcome': outcome, 'valid_record_refs': [], 'requirements': []})


def _effect_rows(journal, reservation):
    if reservation is None:
        return []
    return [journal.read(ref, original_job_owner=reservation['original_job_owner'])
            for ref in reservation['effect_refs']]


def _record_failure(journal, reservation, failure):
    if reservation is None:
        return
    rows = _effect_rows(journal, reservation)
    outcomes = []
    for row in rows:
        if row['state'] in {'confirmed', 'not_sent'}:
            outcomes.append({key: deepcopy(row[key]) for key in (
                'effect_ref', 'state', 'confirmation_source_ref',
                'native_effect_identifiers', 'ancillary_effects', 'failure')})
        else:
            outcomes.append({'effect_ref': row['effect_ref'],
                'state': 'not_sent' if failure['effect_outcome'] == 'not_sent' else 'issued_unknown',
                'confirmation_source_ref': None, 'native_effect_identifiers': {},
                'ancillary_effects': [], 'failure': deepcopy(failure)})
    journal.record_outcome(reservation, outcomes)


async def perform_selected_call(execution, context, service, prepared, *,
                                operation_key, directory, fresh):
    """Return ``{snapshot, failure, effect_receipts}`` for this original action.

    ``snapshot`` is the retained SourceSnapshot or None. The other values are
    detached finite JSON. ``fresh`` comes from the outer immutable action
    intent, never a model argument. A resumed local preparation is pure; all
    remote operations make at most one invocation across recovery.
    """
    prepared = validate_contract('PreparedOperation', prepared)
    if (prepared['execution_contract'] != 'bvbrc_appservice_execution_v1'
            or prepared['bound_inputs']['original_job_owner']['run_id'] != context.run_id
            or context.run_id != execution.run_id
            or prepared['mutates_remote'] != bool(prepared['effects'])):
        raise ValueError('api_selected_call_binding_conflict')
    prefix = f'{context.run_id}:{context.episode_id}:'
    index = operation_key.removeprefix(prefix)
    if (not operation_key.startswith(prefix) or not index.isdecimal()
            or str(int(index)) != index):
        raise ValueError('api_selected_call_action_identity_required')
    local = prepared['native_kind'] == 'local_prepare'
    if local and prepared['effects']:
        raise ValueError('api_selected_local_prepare_cannot_mutate')
    for descriptor in prepared['effects']:
        if (canonical(descriptor['original_job_owner']) != canonical(
                prepared['bound_inputs']['original_job_owner'])
                or descriptor['resource_id'] != prepared['bound_inputs']['resource_id']):
            raise ValueError('api_selected_effect_owner_conflict')

    journal = execution.selected_effects
    intent_path = directory / 'call_intent.json'
    response_path = directory / 'call_response.json'
    issued_path = directory / 'call_issued.json'
    reservation_path = directory / 'effect_reservation.json'
    intent = {'version': VERSION, 'run_id': context.run_id,
        'episode_id': context.episode_id, 'operation_key': operation_key,
        'assignment_sha256': digest(plain(context.assignment)),
        'scope_sha256': digest(plain(context.scope)), 'prepared': prepared}
    first = bool(fresh and not intent_path.exists())
    _immutable(intent_path, intent)

    reservation = None
    if prepared['effects']:
        reservation = journal.reserve(context, operation_key, prepared['effects'])
        _immutable(reservation_path, reservation)
    elif reservation_path.exists():
        raise ValueError('api_selected_unexpected_effect_reservation')

    def retain(snapshot, failure):
        value = {'version': VERSION, 'intent_sha256': digest(intent),
            'snapshot': None if snapshot is None else execution._snapshot(snapshot),
            'failure': failure}
        # Snapshot bytes are retained first. The immutable response associates
        # their metadata and any transport failure in one atomic publication.
        _immutable(response_path, value)
        return value

    def restore(value):
        if (set(value) != {'version', 'intent_sha256', 'snapshot', 'failure'}
                or value['version'] != VERSION or value['intent_sha256'] != digest(intent)):
            raise ValueError('api_selected_response_identity_conflict')
        failure = value['failure']
        if failure is not None:
            failure = validate_contract('Failure', failure)
            _record_failure(journal, reservation, failure)
        snapshot = None if value['snapshot'] is None else execution._load_snapshot(value['snapshot'])
        return {'snapshot': snapshot, 'failure': deepcopy(failure),
            'effect_receipts': _effect_rows(journal, reservation)}

    if response_path.exists():
        return restore(_read(response_path))

    if not first and not local:
        rows = _effect_rows(journal, reservation)
        possible = issued_path.exists() or any(row['state'] != 'prepared_not_issued' for row in rows)
        failure = _failure('issued_effect_unknown' if rows and possible else
            'api_operation_response_unknown' if possible else 'api_operation_not_issued',
            phase='recovery', outcome=('unknown' if possible else 'not_sent') if rows else None,
            effects=() if reservation is None else reservation['effect_refs'])
        return restore(retain(None, failure))

    invoke_arguments = {}
    if prepared['native_kind'] == 'upload':
        # Store uses an owning-thread connection. Only the immutable selected
        # bytes cross into transport; the worker never reads the Store.
        try:
            binding = prepared['native_operands']['call']['content']
            invoke_arguments['upload_content'] = execution.store.get_artifact(binding['artifact_ref'])
        except (ValueError, KeyError, OSError):
            failure = _failure('input_not_possessed', phase='prepare', outcome='not_sent',
                effects=() if reservation is None else reservation['effect_refs'])
            return restore(retain(None, failure))

    if not local:
        if reservation is not None:
            issue = journal.mark_issued(reservation)
            if not issue['first_issue']:
                failure = _failure('issued_effect_unknown', phase='recovery', outcome='unknown',
                    effects=reservation['effect_refs'])
                return restore(retain(None, failure))
        _immutable(issued_path, {'version': VERSION, 'intent_sha256': digest(intent),
            'issued_at': datetime.now(timezone.utc).isoformat()})

    try:
        snapshot = await asyncio.to_thread(service.invoke, prepared, **invoke_arguments)
        if snapshot is not None and not isinstance(snapshot, SourceSnapshot):
            raise ValueError('api_selected_source_snapshot_required')
        if snapshot is None and not local:
            raise ValueError('api_selected_remote_response_required')
    except BaseException as error:
        interruption = isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit))
        snapshot = getattr(error, 'snapshot', None)
        if snapshot is not None and not isinstance(snapshot, SourceSnapshot):
            snapshot = None
        if interruption:
            if snapshot is not None:
                # No invented native failure when only local execution was
                # interrupted after receiving the actual source response.
                retain(snapshot, None)
            raise
        phase = getattr(error, 'phase', 'transport')
        phase = phase if phase in _PHASES else 'transport'
        code = getattr(error, 'code', None)
        if not isinstance(code, str) or not code:
            code = 'api_selected_primitive_failed'
        not_sent = getattr(error, 'submission_outcome', None) == 'not_sent' and snapshot is None
        failure = _failure(code, phase=phase,
            outcome=('not_sent' if not_sent else 'unknown') if reservation is not None else None,
            effects=() if reservation is None else reservation['effect_refs'])
        return restore(retain(snapshot, failure))
    return restore(retain(snapshot, None))


__all__ = ['perform_selected_call']
