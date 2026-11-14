"""Real root completion methods with controlled lifecycle/RPC ports only.

No provider process, private scientific renderer, publication or workflow is
constructed. The controlled process identifier is deliberately not an OS PID.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.boundary_validation import ModelOutputError
from gene_annotation_episode.episodic_workflow.root.model_session import _SessionConnection
from gene_annotation_episode.episodic_workflow.root.provider_errors import ModelCallError
from gene_annotation_episode.episodic_workflow.root.providers import ModelConnection


def configuration():
    role = {'model': 'controlled-no-process', 'reasoning_effort': 'controlled'}
    return {'connection': {'command': ['controlled-command-never-executed']},
            'FAST': dict(role), 'REASONING': dict(role), 'routing': {}}


class ControlledSession(_SessionConnection):
    """Only lifecycle/RPC collection and legacy presentation are controlled.

    __init__ and complete are inherited. Release belongs to ModelConnection;
    OS process cleanup belongs to the separate original transport tests.
    """
    async def __aenter__(self):
        self.process = SimpleNamespace(pid=-1, returncode=None)
        self.trace['entered'] = True
        return self

    async def __aexit__(self, exception_type, exception, traceback):
        self.trace.setdefault('exits', []).append(exception_type)
        self.process.returncode = -1 if exception_type is asyncio.CancelledError else 0

    def _presentation(self, episode_id, role, instructions, context):
        self.trace['legacy_presentation'] = (episode_id, role, instructions, context)
        return 'controlled legacy text', instructions

    async def _session(self, episode_id, role, instructions):
        self.trace['session'] = (episode_id, role, instructions)
        self.sessions[(episode_id, role)] = ('controlled-thread', instructions)
        self.compaction_epochs[(episode_id, role)] = 1
        self.pending.append({'controlled': 'retained until real release'})
        return 'controlled-thread'

    async def _rpc(self, method, parameters):
        self.trace.setdefault('rpc', []).append((method, parameters))
        if self.trace.get('rpc_error') is not None:
            raise self.trace['rpc_error']
        assert method == 'turn/start'
        return {'turn': {'id': 'controlled-turn'}}

    async def _collect_turn(self, thread, turn_id, directory, episode_id, role):
        self.trace['collect'] = (thread, turn_id, directory, episode_id, role)
        if self.trace.get('started') is not None:
            self.trace['started'].set()
            await self.trace['release'].wait()
        return self.trace.get('wire', '{"controlled":true}')


class LegacyFiveArgumentSession(ControlledSession):
    async def complete(self, episode_id, role, instructions, context, schema):
        self.trace.setdefault('legacy_calls', []).append(
            (episode_id, role, instructions, context, schema))
        return self.trace['legacy_result']


def connection_at(tmp_path, *, session_type=ControlledSession, image_resolver=None, **settings):
    connection = ModelConnection(configuration(), tmp_path / 'connection', tmp_path,
                                 image_resolver=image_resolver)
    sessions = []

    def selected_session(config, directory, cwd, *, image_resolver):
        assert config is connection.config and cwd == connection.cwd
        assert image_resolver is connection.image_resolver
        session = session_type(config, directory, cwd, image_resolver=image_resolver)
        session.trace = dict(settings)
        sessions.append(session)
        return session

    connection.session_type = selected_session
    return connection, sessions


def controlled_renderer(state, instructions, *, lookup_results):
    assert lookup_results == []
    return 'controlled selected text: ' + state['label']


def controlled_declared_presenter(session, episode_id, role, instructions, context, renderer):
    session.trace['declared'] = (session, episode_id, role, instructions, context, renderer)
    session.scientific_prompt_states[(episode_id, role)] = context
    return renderer(context, instructions, lookup_results=[]), instructions + ' / declared'


def controlled_full_presenter(session, episode_id, role, instructions, context):
    session.trace['full'] = (session, episode_id, role, instructions, context)
    session.scientific_prompt_states[(episode_id, role)] = context
    return 'controlled full text: ' + context['label'], instructions + ' / full'


controlled_full_presenter.presentation_protocol = 'episode_context_presentation_v1'


def forbidden_declared_presenter(*args):
    raise AssertionError('Marked full callback must not use the declared-presenter port')


def read_call(session, name):
    return json.loads((session.directory / 'call-00001' / name).read_text())


def assert_retired(connection, session, index=1, cancelled=False):
    assert connection.workers == {} and not connection.worker_lock.locked()
    assert session.sessions == {} and session.compaction_epochs == {}
    assert session.scientific_prompt_states == {} and not session.pending
    assert session.trace['exits'] == [asyncio.CancelledError if cancelled else None]
    saved = json.loads((connection.directory / 'retired-sessions' /
                        f'retired-{index:05}.json').read_text())
    assert saved == {'episode_id': 'engineering-episode', 'role': 'REASONING',
        'provider_process': -1, 'provider_exit_code': -1 if cancelled else 0,
        'local_session_removed': True, 'remaining_active_workers': 0,
        'maximum_active_workers': 1}


async def selected_call(connection, context, schema, *, renderer=controlled_renderer,
                        presenter=controlled_declared_presenter):
    return await connection.complete_with_presentation(
        'engineering-episode', 'REASONING', 'original instructions', context, schema,
        prompt_renderer=renderer, declared_presenter=presenter)


def test_default_complete_preserves_five_argument_custom_session(tmp_path):
    async def exercise():
        expected = object()
        connection, sessions = connection_at(tmp_path, session_type=LegacyFiveArgumentSession,
                                             legacy_result=expected)
        context, schema = {'label': 'legacy'}, {'type': 'object'}
        result = await connection.complete('engineering-episode', 'REASONING',
                                           'original instructions', context, schema)
        assert result is expected
        call, = sessions[0].trace['legacy_calls']
        assert call[:3] == ('engineering-episode', 'REASONING', 'original instructions')
        assert call[3] is context and call[4] is schema
        assert_retired(connection, sessions[0])
    asyncio.run(exercise())


def test_explicit_hook_does_not_retry_incompatible_custom_session(tmp_path):
    async def exercise():
        connection, sessions = connection_at(tmp_path, session_type=LegacyFiveArgumentSession,
                                             legacy_result=object())
        with pytest.raises(TypeError, match='prompt_renderer'):
            await selected_call(connection, {'label': 'selected'}, {})
        assert len(sessions) == 1 and 'legacy_calls' not in sessions[0].trace
        assert_retired(connection, sessions[0])
    asyncio.run(exercise())


@pytest.mark.parametrize('mode', ['ordinary', 'full'])
def test_selected_owners_identities_and_actual_model_input_are_recorded(tmp_path, mode):
    async def exercise():
        connection, sessions = connection_at(tmp_path)
        context, schema = {'label': 'selected', 'kept': [1, False]}, {'type': 'object'}
        renderer = controlled_renderer if mode == 'ordinary' else controlled_full_presenter
        presenter = controlled_declared_presenter if mode == 'ordinary' else forbidden_declared_presenter
        assert await selected_call(connection, context, schema, renderer=renderer,
                                   presenter=presenter) == {'controlled': True}
        session, = sessions
        assert 'legacy_presentation' not in session.trace
        seen = session.trace['declared' if mode == 'ordinary' else 'full']
        assert seen[0] is session and seen[4] is context
        assert seen[1:4] == ('engineering-episode', 'REASONING', 'original instructions')
        if mode == 'ordinary':
            assert seen[5] is renderer
        method, rpc = session.trace['rpc'][0]
        assert method == 'turn/start' and rpc['outputSchema'] is schema
        suffix = 'declared' if mode == 'ordinary' else 'full'
        text = ('controlled selected text: ' if mode == 'ordinary' else 'controlled full text: ') + 'selected'
        saved = read_call(session, 'request.json')
        assert saved['context'] == context and saved['output_schema'] == schema
        assert saved['instructions'] == 'original instructions'
        assert saved['model_instructions'] == 'original instructions / ' + suffix
        assert saved['input'] == rpc['input'] == [{'type': 'text', 'text': text}]
        expected = {'module': renderer.__module__, 'qualname': renderer.__qualname__}
        if mode == 'ordinary':
            expected['declared_presenter'] = {'module': presenter.__module__, 'qualname': presenter.__qualname__}
        else:
            expected['protocol'] = 'episode_context_presentation_v1'
        assert saved['presentation'] == expected
        assert read_call(session, 'turn-01.request.json') == rpc
        assert read_call(session, 'response.json') == {'controlled': True}
        assert session.trace['session'][2] == saved['model_instructions']
        assert context == {'label': 'selected', 'kept': [1, False]}
        assert_retired(connection, session)
    asyncio.run(exercise())


def test_real_session_default_path_has_no_presentation_metadata(tmp_path):
    async def exercise():
        connection, sessions = connection_at(tmp_path)
        context = {'label': 'legacy'}
        assert await connection.complete('engineering-episode', 'REASONING',
            'original instructions', context, {}) == {'controlled': True}
        session, = sessions
        assert session.trace['legacy_presentation'][3] is context
        saved = read_call(session, 'request.json')
        assert 'presentation' not in saved and 'model_instructions' not in saved
        assert saved['input'] == [{'type': 'text', 'text': 'controlled legacy text'}]
        assert_retired(connection, session)
    asyncio.run(exercise())


@pytest.mark.parametrize('kind,expected_images', [
    ('decision_bootstrap', 1), ('decision_update', 1), ('decision_lookup_result', 0),
    ('legacy', 1)], ids=['bootstrap', 'update', 'lookup', 'legacy'])
def test_selected_presentation_retains_original_image_frame_selection(tmp_path, kind, expected_images):
    async def exercise():
        image = {'controlled_image_operand': 'only supplied view'}
        resolved = {'type': 'image', 'url': 'controlled:resolved-image'}
        observed = []
        def resolve(value):
            observed.append(value)
            return resolved
        connection, sessions = connection_at(tmp_path, image_resolver=resolve)
        context = {'label': 'images', 'visual_evidence': [image]} if kind == 'legacy' else {
            'label': 'images', 'version': 'decision_context_v1', 'kind': kind,
            'fields': {'visual_evidence': [image]}}
        await selected_call(connection, context, {})
        session, = sessions
        assert len(observed) == expected_images
        if expected_images:
            assert observed[0] is image and session.trace['rpc'][0][1]['input'][1] is resolved
        assert len(read_call(session, 'request.json')['input']) == 1 + expected_images
        assert_retired(connection, session)
    asyncio.run(exercise())


def test_missing_image_resolver_preserves_failure_before_rpc(tmp_path):
    async def exercise():
        connection, sessions = connection_at(tmp_path)
        context = {'label': 'missing-resolver', 'visual_evidence': [{'selected': 'image'}]}
        with pytest.raises(ModelCallError, match='Selected image has no bound artifact resolver'):
            await selected_call(connection, context, {})
        session, = sessions
        assert 'rpc' not in session.trace and 'session' not in session.trace
        saved = read_call(session, 'error.json')
        assert saved['error'] == 'ModelCallError'
        assert saved['thread_id'] is None and saved['turn_id'] is None
        assert read_call(session, 'request.json')['context'] == context
        assert_retired(connection, session)
    asyncio.run(exercise())


@pytest.mark.parametrize('wire,context,expected', [
    ('null', {'version': 'decision_context_v1'}, None),
    ('[1,false]', {'version': 'decision_context_v1'}, [1, False]),
    ('"finite-invalid-envelope"', {'version': 'decision_context_v1'}, 'finite-invalid-envelope'),
    ('{"legacy":true}', {}, {'legacy': True})], ids=['finite-null', 'finite-array', 'finite-scalar', 'legacy-object'])
def test_selected_route_preserves_original_finite_response_parser(tmp_path, wire, context, expected):
    async def exercise():
        connection, sessions = connection_at(tmp_path, wire=wire)
        context['label'] = 'parser'
        result = await selected_call(connection, context, {})
        assert result == expected and type(result) is type(expected)
        session, = sessions
        assert read_call(session, 'response.json') == expected
        assert (session.directory / 'call-00001/response.txt').read_text() == wire
        assert len(session.trace['rpc']) == 1
        assert_retired(connection, session)
    asyncio.run(exercise())


@pytest.mark.parametrize('wire,framed,category', [
    ('null', False, 'non_object_json'), ('[]', False, 'non_object_json'),
    ('{', True, 'malformed_json'), ('{"a":1,"a":2}', True, 'duplicate_json_key'),
    ('NaN', True, 'nonfinite_json_number'), ('1e9999', True, 'nonfinite_json_number')],
    ids=['legacy-null', 'legacy-array', 'malformed', 'duplicate-key', 'nan', 'overflow'])
def test_selected_route_preserves_original_parser_errors_and_retirement(tmp_path, wire, framed, category):
    async def exercise():
        connection, sessions = connection_at(tmp_path, wire=wire)
        context = {'label': 'bad-json', **({'version': 'decision_context_v1'} if framed else {})}
        with pytest.raises(ModelOutputError) as caught:
            await selected_call(connection, context, {})
        assert type(caught.value) is ModelOutputError
        assert caught.value.raw_response == wire and caught.value.diagnostic['category'] == category
        session, = sessions
        saved = read_call(session, 'error.json')
        assert saved['error'] == 'ModelOutputError'
        assert (saved['thread_id'], saved['turn_id']) == ('controlled-thread', 'controlled-turn')
        assert len(session.trace['rpc']) == 1 and not (session.directory / 'call-00001/response.json').exists()
        assert_retired(connection, session)
    asyncio.run(exercise())


@pytest.mark.parametrize('where', ['renderer', 'declared', 'full'])
def test_presentation_exception_identity_is_saved_without_dispatch_or_retry(tmp_path, where):
    async def exercise():
        failure = ValueError('controlled selected presentation failure')
        def broken_renderer(*args, **kwargs):
            raise failure
        def broken_presenter(*args, **kwargs):
            raise failure
        def broken_full(*args, **kwargs):
            raise failure
        broken_full.presentation_protocol = 'episode_context_presentation_v1'
        renderer = broken_full if where == 'full' else broken_renderer if where == 'renderer' else controlled_renderer
        presenter = broken_presenter if where == 'declared' else controlled_declared_presenter
        connection, sessions = connection_at(tmp_path)
        with pytest.raises(ValueError) as caught:
            await selected_call(connection, {'label': 'failure'}, {}, renderer=renderer, presenter=presenter)
        assert caught.value is failure
        session, = sessions
        assert 'rpc' not in session.trace and 'legacy_presentation' not in session.trace
        assert 'presentation' in read_call(session, 'request.json')
        assert read_call(session, 'error.json') == {'error': 'ValueError', 'message': str(failure),
                                                  'thread_id': None, 'turn_id': None}
        assert_retired(connection, session)
    asyncio.run(exercise())


def test_rpc_failure_preserves_original_exception_and_partial_identifiers(tmp_path):
    async def exercise():
        failure = ModelCallError('controlled RPC failure')
        connection, sessions = connection_at(tmp_path, rpc_error=failure)
        with pytest.raises(ModelCallError) as caught:
            await selected_call(connection, {'label': 'rpc'}, {})
        assert caught.value is failure
        session, = sessions
        saved = read_call(session, 'error.json')
        assert saved == {'error': 'ModelCallError', 'message': str(failure),
                         'thread_id': 'controlled-thread', 'turn_id': None}
        assert len(session.trace['rpc']) == 1 and 'collect' not in session.trace
        assert_retired(connection, session)
    asyncio.run(exercise())


def test_cancel_selected_completion_saves_failure_and_forces_original_retirement(tmp_path):
    async def exercise():
        started, release = asyncio.Event(), asyncio.Event()
        connection, sessions = connection_at(tmp_path, started=started, release=release)
        calling = asyncio.create_task(selected_call(connection, {'label': 'cancel'}, {}))
        observing = asyncio.create_task(started.wait())
        try:
            await asyncio.wait((calling, observing), return_when=asyncio.FIRST_COMPLETED)
            if calling.done():
                calling.result()
                raise AssertionError('Completion exited before the controlled collection barrier')
            assert started.is_set() and connection.worker_lock.locked()
            calling.cancel()
            with pytest.raises(asyncio.CancelledError):
                await calling
            session, = sessions
            saved = read_call(session, 'error.json')
            assert saved['error'] == 'CancelledError'
            assert (saved['thread_id'], saved['turn_id']) == ('controlled-thread', 'controlled-turn')
            assert len(session.trace['rpc']) == 1
            assert_retired(connection, session, cancelled=True)
        finally:
            if not calling.done():
                calling.cancel()
            if not observing.done():
                observing.cancel()
            await asyncio.gather(calling, observing, return_exceptions=True)
            await connection.__aexit__(asyncio.CancelledError, None, None)
    asyncio.run(exercise())


def test_repeated_selected_calls_use_fresh_sessions_and_clear_presentation_state(tmp_path):
    async def exercise():
        connection, sessions = connection_at(tmp_path)
        for index, label in enumerate(('first', 'second'), 1):
            await selected_call(connection, {'label': label}, {})
            assert len(sessions) == index
            assert_retired(connection, sessions[-1], index=index)
        assert sessions[0] is not sessions[1]
        assert sessions[0].directory != sessions[1].directory
        assert read_call(sessions[0], 'request.json')['context'] == {'label': 'first'}
        assert read_call(sessions[1], 'request.json')['context'] == {'label': 'second'}
    asyncio.run(exercise())
