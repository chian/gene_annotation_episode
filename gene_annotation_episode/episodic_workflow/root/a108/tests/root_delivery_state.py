"""Reuse A108 original contextual-observation presentation inputs; no assessment."""
from copy import deepcopy
from .literature_prompt_fixtures import (snapshot, INSTRUCTION_TEXT, OUTPUT_SCHEMA,
    SOURCE_TEXT, QUALIFICATION, OBSERVATION, LOOKUP_TEXT, assert_task, assert_no_bookkeeping)

def changed_state():
    # Exact original scientific state update from the retained presentation test.
    second=deepcopy(snapshot())
    second['last_local_outcome'] = {'status': 'completed', 'record_refs': [OBSERVATION],
        'changed_record_refs': [], 'result': {'source_ref': 'source_selected',
            'observation_ref': OBSERVATION, 'text': SOURCE_TEXT, 'qualification': QUALIFICATION}}
    second['feedback'] = {'category': 'arguments_or_reference', 'code': 'condition_unresolved', 'field': 'target_context'}
    second['controller']['estimate']['expected_next_gain']['value'] = .25
    return second

def assert_rendered(text, *, changed=False):
    assert_task(text);assert_no_bookkeeping(text)
    assert 'tool/source.read' in text and '-0.25' in text
    if changed:
        assert SOURCE_TEXT in text and QUALIFICATION in text and OBSERVATION in text
        assert 'condition_unresolved' in text and 'target_context' in text
        assert '0.25' in text and 'lower=-0.1; upper=0.9' in text
