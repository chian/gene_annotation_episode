"""An existing admission precondition must be known before action selection."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt


RECORDED = json.loads((Path(__file__).parent / 'fixtures/reasoning/'
    'a11033-empty-reason-admission.json').read_text())


def source_frame(*, common_reason=True, specialist=None):
    workflow = SimpleNamespace(
        is_job_source=lambda source: False,
        specialist=lambda source: specialist,
        binding_context=lambda source: None,
        permits_common_action=lambda source, kind: common_reason and kind == 'reason',
        native_event_information=None, decision_protocol=None,
        store=SimpleNamespace(reasoning_schema=lambda: deepcopy(
            RECORDED['original_reason_schema']['properties']['commit'])))
    return workflow, SimpleNamespace(workflow=workflow, path=(('annotation', 'root'),))


def test_original_trace_has_three_empty_selections_and_explicit_rejections():
    assert [row['decision_index'] for row in RECORDED['attempts']] == [64, 75, 80]
    for row, feedback in zip(RECORDED['attempts'], RECORDED['rejection_feedback']):
        assert row['response']['selection']['kind'] == 'reason'
        assert all(value == [] for value in row['response']['selection']['commit'].values())
        assert feedback == {'category': 'action_contract',
            'detail': 'empty_reasoning_commit', 'status': 'invalid'}


def test_admission_requirement_reaches_actual_scientific_text_before_feedback():
    workflow, source = source_frame()
    state = deepcopy(RECORDED['state'])
    before = deepcopy(state)
    instructions = DecisionSource.instructions(source, {})
    text = render_scientific_process_prompt(state, instructions)
    assert 'every commit section empty' in text
    assert 'rejected before acquisition' in text
    assert 'return-form update' in text
    assert 'no_applicable_evidence' in text
    assert 'feedback' not in state
    assert state == before


@pytest.mark.parametrize('specialized', [False, True])
def test_schema_describes_requirement_without_changing_its_scientific_payload(specialized):
    original = deepcopy(RECORDED['original_reason_schema'])
    original['description'] = 'Original specialist interpretation requirements.'
    before = deepcopy(original)
    specialist = SimpleNamespace(reasoning_action_schema=lambda context, commit: original)
    workflow, source = source_frame(specialist=specialist if specialized else None)
    schema = Workflow.reasoning_action_schema(workflow, source)
    assert 'every commit section empty' in schema['description']
    assert 'no_applicable_evidence' in schema['description']
    assert schema['properties']['commit'] == original['properties']['commit']
    if specialized:
        assert schema['description'].startswith(original['description'])
    assert original == before


def test_unavailable_common_reason_does_not_receive_its_admission_instructions():
    _workflow, source = source_frame(common_reason=False)
    assert 'every commit section empty' not in DecisionSource.instructions(source, {})
