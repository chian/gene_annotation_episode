"""Original session/parser consumes actual controlled wire bytes exactly once."""
import asyncio
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.boundary_validation import ModelOutputError
from gene_annotation_episode.episodic_workflow.root.provider_errors import ModelCallError
from gene_annotation_episode.episodic_workflow.root.tests.model_transport_support import (
    ControlledConnection, actual_session, assert_exited, configuration, observed, requests)


@pytest.mark.parametrize('wire,context,expected,stream_whitespace', [
    ('{"controlled":true}', {}, {'controlled': True}, False),
    ('null', {'version': 'decision_context_v1'}, None, False),
    ('[1,false,"retained"]', {'version': 'decision_context_v1'}, [1, False, 'retained'], False),
    (' ' * 5000 + '{"after_whitespace":true}', {}, {'after_whitespace': True}, True),
], ids=['object', 'finite-null', 'finite-array', 'past-original-whitespace-threshold'])
def test_finite_wire_response_is_returned_and_journaled(tmp_path, wire, context, expected, stream_whitespace):
    async def exercise():
        async with actual_session(tmp_path, text=wire,
                whitespace_delta=' ' * 5000 if stream_whitespace else None) as (session, control):
            ready = await observed(control / 'ready.json')
            value = await session.complete('controlled-episode', 'REASONING', 'Controlled protocol only',
                                           context, {'type': 'object'})
            assert value == expected and type(value) is type(expected)
        assert_exited(session, ready)
        directory = session.directory / 'call-00001'
        assert (directory / 'response.txt').read_text() == wire
        assert json.loads((directory / 'response.json').read_text()) == expected
        assert not (directory / 'error.json').exists()
        saved = json.loads((directory / 'request.json').read_text())
        assert saved['context'] == context
        assert saved['input'] == [{'type': 'text', 'text': 'Controlled transport bytes; no scientific interpretation.'}]
        assert sum(r['method'] == 'turn/start' for r in requests(control)) == 1
        assert not any(r['method'] == 'turn/interrupt' for r in requests(control))
        if stream_whitespace:
            events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
            assert events[0]['method'] == 'item/started'
            assert events[0]['params']['item'] == {'id': 'answer', 'type': 'agentMessage', 'phase': 'final_answer'}
            assert events[1]['method'] == 'item/agentMessage/delta'
            assert events[1]['params']['itemId'] == 'answer' and events[1]['params']['delta'] == ' ' * 5000
        assert not list(directory.glob('turn-02*'))
    asyncio.run(exercise())


@pytest.mark.parametrize('wire,context,category', [
    ('null', {}, 'non_object_json'),
    ('[]', {}, 'non_object_json'),
    ('{', {'version': 'decision_context_v1'}, 'malformed_json'),
    ('{"a":1,"a":2}', {'version': 'decision_context_v1'}, 'duplicate_json_key'),
    ('NaN', {'version': 'decision_context_v1'}, 'nonfinite_json_number'),
    ('1e9999', {'version': 'decision_context_v1'}, 'nonfinite_json_number'),
], ids=['legacy-null', 'legacy-array', 'malformed', 'duplicate-key', 'nan', 'overflow'])
def test_invalid_wire_response_preserves_parser_failure_without_retry(tmp_path, wire, context, category):
    async def exercise():
        async with actual_session(tmp_path, text=wire) as (session, control):
            ready = await observed(control / 'ready.json')
            with pytest.raises(ModelOutputError) as caught:
                await session.complete('controlled-episode', 'REASONING', 'Controlled protocol only', context, {})
            assert type(caught.value) is ModelOutputError
            assert caught.value.raw_response == wire and caught.value.diagnostic['category'] == category
        assert_exited(session, ready)
        directory = session.directory / 'call-00001'
        assert (directory / 'response.txt').read_text() == wire
        assert not (directory / 'response.json').exists()
        failure = json.loads((directory / 'error.json').read_text())
        assert failure['error'] == 'ModelOutputError'
        assert failure['thread_id'] == 'controlled-thread' and failure['turn_id'] == 'controlled-turn'
        assert sum(r['method'] == 'turn/start' for r in requests(control)) == 1
        assert not list(directory.glob('turn-02*'))
    asyncio.run(exercise())


@pytest.mark.parametrize('settings,message,interrupted', [
    ({'turn_status': 'failed'}, 'Model turn failed', False),
    ({'undeclared_tool': True}, 'Model attempted commandExecution', True),
], ids=['returned-provider-failure', 'undeclared-tool'])
def test_actual_protocol_failure_retains_canonical_error(tmp_path, settings, message, interrupted):
    async def exercise():
        async with actual_session(tmp_path, **settings) as (session, control):
            ready = await observed(control / 'ready.json')
            with pytest.raises(ModelCallError, match=message) as caught:
                await session.complete('controlled-episode', 'REASONING', 'Controlled protocol only', {}, {})
            assert type(caught.value) is ModelCallError
        assert_exited(session, ready)
        methods = [row['method'] for row in requests(control)]
        assert methods.count('turn/start') == 1
        assert ('turn/interrupt' in methods) is interrupted
        failure = json.loads((session.directory / 'call-00001/error.json').read_text())
        assert failure['error'] == 'ModelCallError'
        assert not (session.directory / 'call-00001/response.json').exists()
    asyncio.run(exercise())


@pytest.mark.parametrize('wire,failed', [('{"controlled":true}', False), ('{', True)], ids=['success', 'parser-failure'])
def test_connection_retires_original_state_after_return_or_parser_failure(tmp_path, wire, failed):
    async def exercise():
        control = tmp_path / 'control'
        connection = ControlledConnection(configuration(control, text=wire), tmp_path / 'connection', tmp_path)
        try:
            if failed:
                with pytest.raises(ModelOutputError):
                    await connection.complete('controlled-episode', 'REASONING', 'Controlled only', {}, {})
            else:
                assert await connection.complete('controlled-episode', 'REASONING', 'Controlled only', {}, {}) == {'controlled': True}
            ready = await observed(control / 'ready.json')
            assert not connection.workers and not connection.worker_lock.locked()
            receipt = json.loads((connection.directory / 'retired-sessions/retired-00001.json').read_text())
            assert receipt['provider_process'] == ready['pid'] and receipt['provider_exit_code'] == 0
            assert receipt['local_session_removed'] is True and receipt['remaining_active_workers'] == 0
            from gene_annotation_episode.episodic_workflow.root.model_transport_resources import owned_process_group_running
            assert not owned_process_group_running(ready['pgid'])
            assert sum(r['method'] == 'turn/start' for r in requests(control)) == 1
        finally:
            await connection.__aexit__(asyncio.CancelledError, None, None)
    asyncio.run(exercise())
