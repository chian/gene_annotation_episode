"""Existing unclaimed provider calls keep original wire context and instructions."""
import asyncio
from copy import deepcopy
import json

import pytest

from .literature_prompt_fixtures import LiteratureWire, INSTRUCTION_TEXT, OUTPUT_SCHEMA


@pytest.mark.parametrize('context', [
    {'unmarked': 'ordinary original inputs', 'qualification': 'unresolved'},
    {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 2, 'exchange_index': 1, 'result': {'status': 'unavailable'}},
])
def test_unclaimed_actual_provider_call_preserves_default_route(tmp_path, context):
    original = deepcopy(context)
    wire = LiteratureWire(tmp_path / 'wire')
    assert asyncio.run(wire.complete('original-unclaimed-episode', 'REASONING',
        INSTRUCTION_TEXT, context, OUTPUT_SCHEMA)) == {'fixture': True}
    turn, = wire.turns_sent()
    assert json.loads(turn['input'][0]['text']) == original
    assert turn['outputSchema'] == OUTPUT_SCHEMA
    developer, = [params['developerInstructions'] for method, params in wire.sent if method == 'thread/start']
    assert developer == INSTRUCTION_TEXT
    saved = json.loads((tmp_path / 'wire/call-00001/request.json').read_text())
    assert saved['context'] == original
    assert 'presentation' not in saved
    assert context == original
