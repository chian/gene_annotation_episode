"""A108 task/steering delivery through own real provider and private task port."""
import asyncio
from copy import deepcopy
import json

from ..decision_context import state_frame
from .literature_prompt_fixtures import (LiteratureWire, snapshot, complete, assert_task,
    assert_no_bookkeeping, SOURCE_TEXT, QUALIFICATION, OBSERVATION, LOOKUP_TEXT,
    OUTPUT_SCHEMA, INSTRUCTION_TEXT)


def test_native_turns_repeat_full_a108_task_after_delta_and_same_decision_lookup(tmp_path):
    wire = LiteratureWire(tmp_path / 'wire')
    first = snapshot()
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'record_refs': [OBSERVATION],
        'changed_record_refs': [], 'result': {'source_ref': 'source_selected',
            'observation_ref': OBSERVATION, 'text': SOURCE_TEXT, 'qualification': QUALIFICATION}}
    second['feedback'] = {'category': 'arguments_or_reference', 'code': 'condition_unresolved', 'field': 'target_context'}
    second['controller']['estimate']['expected_next_gain']['value'] = .25
    delta = state_frame(second, first)
    assert 'literature_experimental_work' not in delta['fields']
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
              'decision_index': 8, 'exchange_index': 2, 'result': {'status': 'completed', 'text': LOOKUP_TEXT}}
    original = deepcopy((first, second, delta, lookup))
    async def exercise():
        assert await complete(wire, state_frame(first)) == {'fixture': True}
        await complete(wire, delta)
        await complete(wire, lookup)
    asyncio.run(exercise())
    turns = wire.turns_sent()
    assert len(turns) == 3
    tasks = []
    for turn in turns:
        text = turn['input'][0]['text']
        tasks.append(assert_task(text))
        assert_no_bookkeeping(text)
        assert 'tool/source.read' in text and '-0.25' in text
        assert turn['outputSchema'] == OUTPUT_SCHEMA
    assert tasks[0] == tasks[1] == tasks[2]
    assert SOURCE_TEXT not in turns[0]['input'][0]['text']
    for turn in turns[1:]:
        text = turn['input'][0]['text']
        assert SOURCE_TEXT in text and QUALIFICATION in text and OBSERVATION in text
        assert 'condition_unresolved' in text and 'target_context' in text
        assert '0.25' in text and 'lower=-0.1; upper=0.9' in text
    assert LOOKUP_TEXT in turns[2]['input'][0]['text']
    assert (first, second, delta, lookup) == original
    developer = next(params['developerInstructions'] for method, params in wire.sent if method == 'thread/start')
    assert 'decision_bootstrap supplies' not in developer
    assert 'request_context' in developer and 'select_action' in developer
    saved = json.loads((tmp_path / 'wire/call-00002/request.json').read_text())
    assert saved['context'] == delta and saved['instructions'] == INSTRUCTION_TEXT
    assert saved['input'] == turns[1]['input']


def test_restart_bootstrap_repeats_a108_task_and_only_answered_lookup(tmp_path):
    state = snapshot()
    frame = state_frame(state)
    frame.update(restored_pending_decision_index=9, restored_public_exchanges=[{
        'exchange_index': 3, 'response': {'response': {'response_type': 'request_context',
            'lookup': {'view': 'own_history', 'decision_index': 1}, 'private_extra': 'DO_NOT_RENDER_RESPONSE_TRANSCRIPT'}},
        'lookup_result': {'status': 'completed', 'text': LOOKUP_TEXT}}])
    original = deepcopy(frame)
    first = LiteratureWire(tmp_path / 'first-process')
    restarted = LiteratureWire(tmp_path / 'restarted-process')
    asyncio.run(complete(first, state_frame(state)))
    asyncio.run(complete(restarted, frame))
    before = first.turns_sent()[0]['input'][0]['text']
    after = restarted.turns_sent()[0]['input'][0]['text']
    assert assert_task(before) == assert_task(after)
    assert LOOKUP_TEXT in after
    assert_no_bookkeeping(after)
    assert restarted.turns_sent()[0]['outputSchema'] == OUTPUT_SCHEMA
    assert frame == original
