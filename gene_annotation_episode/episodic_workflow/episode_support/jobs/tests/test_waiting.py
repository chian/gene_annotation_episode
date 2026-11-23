"""A selected wait over a real native event ledger: native event wake, reconsideration and target errors."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger import EventTargetError, NativeEventLedger, native_target_handle
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait, wait_target_feedback

RECEIPT = b'service exit receipt'


def _registered(store):
    identity = {'kind': 'systemd_user_service', 'unit': 'job.service', 'request_sha256': 'a' * 64}
    handle = native_target_handle(identity)
    store.register_native_target({'version': 'native_event_registration', 'handle': handle, 'run_id': 'run',
                                  'owner_episode_id': 'episode', 'job_ref': 'job:1', 'registry_ref': 'registry:1',
                                  'resource_id': 'local', 'native_identity': identity})
    return handle


def _publish(store, handle):
    digest = hashlib.sha256(RECEIPT).hexdigest()
    return store.publish_native_event(handle, {
        'version': 'native_event_publication', 'event': 'state_changed', 'cause': 'service_exit_receipt_committed',
        'record_ref': 'native_event_record_' + digest[:24], 'receipt_sha256': digest,
        'occurred_at': datetime.now(timezone.utc).isoformat()}, receipt_bytes=RECEIPT)


def _condition(handle, event='state_changed', after_cursor=0, reconsider_at=None):
    return {'version': 'event_condition', 'reconsider_at': reconsider_at,
            'events': [{'handle': handle, 'event': event, 'after_cursor': after_cursor}]}


def test_wait_wakes_on_the_published_native_event(tmp_path):
    store = NativeEventLedger(tmp_path / 'executions')
    handle = _registered(store)

    async def run():
        waiting = asyncio.create_task(selected_wait(store, _condition(handle)))
        await asyncio.sleep(0.2)
        assert not waiting.done()
        published = _publish(store, handle)
        return published, await waiting
    published, outcome = asyncio.run(run())
    assert outcome['status'] == 'completed' and outcome['record_refs'] == []
    assert outcome['result']['reason'] == 'state_changed'
    assert outcome['result']['events'][0]['cursor'] == published['cursor']


def test_wait_returns_at_its_reconsideration_time_without_events(tmp_path):
    store = NativeEventLedger(tmp_path / 'executions')
    handle = _registered(store)
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    cursor = _publish(store, handle)['cursor']
    outcome = asyncio.run(selected_wait(store, _condition(handle, after_cursor=cursor, reconsider_at=past)))
    assert outcome['status'] == 'completed' and outcome['result']['reason'] == 'reconsideration'


@pytest.mark.parametrize('event, code', [('returned', 'unsupported_wait_event'), (None, 'unknown_wait_target')])
def test_unusable_target_is_a_failed_wait_outcome_with_feedback(tmp_path, event, code):
    store = NativeEventLedger(tmp_path / 'executions')
    handle = _registered(store) if event else 'pending_child_episode_3'
    outcome = asyncio.run(selected_wait(store, _condition(handle, event=event or 'returned')))
    assert outcome['status'] == 'failed' and outcome['result'] is None
    assert outcome['feedback']['status'] == 'failed' and outcome['feedback']['code'] == code
    assert outcome['feedback']['affected_refs'] == [handle]


def test_feedback_requires_an_event_target_error_and_a_known_status():
    error = EventTargetError('wait_target_not_visible', affected_refs=['handle:1'])
    assert wait_target_feedback(error, status='invalid') == {
        'status': 'invalid', 'category': 'wait_target', 'code': 'wait_target_not_visible',
        'affected_refs': ['handle:1'], 'detail': 'wait_target_not_visible'}
    with pytest.raises(ValueError, match='invalid_or_failed'):
        wait_target_feedback(error, status='rejected')
    with pytest.raises(TypeError):
        wait_target_feedback(ValueError('x'), status='failed')
