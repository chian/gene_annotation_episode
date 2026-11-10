"""Selected waiting on original, parent-owned in-process child returns.

The existing Context scheduler waits and chooses the ready owned return. This
adapter neither dispatches work nor receives a report or assigns credit.
"""
from datetime import datetime, timezone
import hashlib

from method_loop.durable import EventTargetError


PREFIX = 'pending_child_'


def public_child_handle(parent_episode_id, invocation_handle):
    return PREFIX + hashlib.sha256(
        (parent_episode_id + ':' + invocation_handle).encode()).hexdigest()


def selected_owned_children(workflow, source, condition):
    """Distinguish original owned returns from external event-provider targets."""
    events = condition['events']
    local = [event for event in events if event['handle'].startswith(PREFIX)]
    if not local:
        return None
    context = getattr(source, '_execution_context', None)
    owned = ({public_child_handle(source.episode_id, item.handle): item
        for item in context._pending_children(source.path)}
        if workflow.execution_binding is None and context is not None else {})
    missing = [event['handle'] for event in local if event['handle'] not in owned]
    if missing:
        raise EventTargetError('wait_target_unavailable', affected_refs=missing,
            detail='selected_inprocess_child_is_not_an_outstanding_owned_return')
    if len(local) != len(events):
        raise EventTargetError('unsupported_wait_event',
            affected_refs=[event['handle'] for event in events],
            detail='select_owned_child_collection_or_external_event_wait_separately')
    unsupported = [event['handle'] for event in local
        if event['event'] != 'returned' or event['after_cursor'] != 0]
    if unsupported or condition['reconsider_at'] is not None:
        raise EventTargetError('unsupported_wait_event',
            affected_refs=unsupported or [event['handle'] for event in local],
            detail='owned_child_collection_uses_returned_after_cursor_zero_without_a_timer')
    return {event['handle']: owned[event['handle']] for event in local}


async def await_owned_return(workflow, source, condition):
    selected = selected_owned_children(workflow, source, condition)
    if selected is None:
        raise ValueError('original_owned_child_wait_required')
    context = source._execution_context
    # This existing scheduler also gives an earlier ready sibling priority.
    # It manages suspension and observer cleanup without cancelling children.
    ready = await context._next_owned_child(source.path)
    if ready is None:
        raise EventTargetError('wait_target_unavailable', affected_refs=list(selected),
            detail='original_owned_returns_no_longer_outstanding')
    return {'version': 'owned_child_return_readiness_v1',
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'selected_condition': condition,
        'ready_handle': public_child_handle(source.episode_id, ready.handle),
        'ready_state': ready.status()['state'],
        'selected_return_available': any(item._task.done() for item in selected.values()),
        'receipt_status': 'awaiting_original_scheduler_collection',
        'meaning': 'operational_readiness_only; original_child_action_owns_report_and_credit'}
