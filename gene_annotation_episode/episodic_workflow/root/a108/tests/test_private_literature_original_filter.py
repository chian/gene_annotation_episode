"""Original tracking filter over A108 context, without hiding scientific identity."""
from copy import deepcopy

import pytest

from ..library import literature_experimental_prompt as prompt
from .literature_prompt_fixtures import snapshot, INSTRUCTION_TEXT, OBSERVATION, QUALIFICATION


@pytest.mark.parametrize('tracking', ['episode_id', 'private_receipt_locator', 'worker_source_sha256'])
def test_original_tracking_controls_do_not_reach_a108_steering(tracking):
    state = snapshot()
    state['last_local_outcome'] = {'status': 'partial', 'record_refs': [OBSERVATION],
        'result': {'observation_ref': OBSERVATION, 'qualification': QUALIFICATION,
                   'context': {'temperature': {'value': 38, 'unit': 'C'}}, tracking: 'PRIVATE_CONTROL_SENTINEL'}}
    original = deepcopy(state)
    rendered = prompt.render_literature_experimental_prompt(state, INSTRUCTION_TEXT)
    assert 'PRIVATE_CONTROL_SENTINEL' not in rendered
    assert OBSERVATION in rendered and QUALIFICATION in rendered
    assert '38' in rendered and 'temperature' in rendered
    assert state == original


def test_current_byte_payload_filter_stays_private_with_original_tracking_rules():
    value = {'observation_ref': OBSERVATION, 'qualification': QUALIFICATION,
             'raw': {'body': 'PRIVATE_BYTES', 'content': 'PRIVATE_BYTES', 'bytes': 'PRIVATE_BYTES',
                     'base64': 'PRIVATE_BYTES', 'stdout': 'PRIVATE_BYTES', 'stderr': 'PRIVATE_BYTES'}}
    original = deepcopy(value)
    assert prompt._safe(value) == {'observation_ref': OBSERVATION, 'qualification': QUALIFICATION, 'raw': {}}
    assert value == original
