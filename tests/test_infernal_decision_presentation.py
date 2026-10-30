"""Infernal receiving-model boundaries, using retained native-run contexts.

No scientific program, network, or model is run. Native contexts are immutable
fixtures; root variants and pending journal setup are explicitly synthetic.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import runtime
from gene_annotation_episode.decision_context import (
    INSTRUCTIONS, apply_state_frame, model_snapshot, state_frame,
)
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_decision_provider_frames import ConversationWire
from test_runtime import FixtureController, obj, reason
from test_scientific_process_prompt_delivery import ScientificWire, OUTPUT_SCHEMA


FIXTURES = Path(__file__).parent / 'fixtures' / 'native_infernal_episode'
TABLE = {'version': 'own_decision_yield_table_v1', 'rows': []}
METRICS = (
    'bitscore', 'evalue', 'bias_bits', 'gc_fraction', 'model_span_length',
    'model_span_fraction', 'sequence_span_length', 'sequence_span_fraction',
    'consensus_length', 'sequence_length',
)


def saved_context(index=6, *, receiver='scientific'):
    saved = json.loads((FIXTURES / f'scientific-decision-{index}.json').read_text())
    if receiver == 'root':
        # A labelled root presentation variant, not a claim that this is a
        # retained annotation-root call from the native run.
        saved['context'].pop('scientific_process')
        saved['context']['goal']['objective'] = 'Synthetic root receiving the retained Infernal return.'
        saved['instructions'] = 'Synthetic root presentation verification.\n' + INSTRUCTIONS
    return saved


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def without_automatic_observations(context):
    expected = deepcopy(context)
    expected['working_state']['observations'] = []
    return expected


def steering(text):
    return text.split('\n\nSTEERING\n', 1)[1]


def assert_requested_text(text, *, evalue=False):
    content = steering(text)
    assert '| [1].rows[0].measurements[0].name | bitscore |' in content
    assert '| [1].rows[0].measurements[0].value | 71.4 |' in content
    if evalue:
        assert '| [2].rows[0].measurements[0].name | evalue |' in content
        assert '| [2].rows[0].measurements[0].value | 3.6e-22 |' in content
    else:
        assert '| evalue |' not in content
        assert '3.6e-22' not in content
    for metric in METRICS[2:]:
        assert f'| {metric} |' not in content
    assert 'native_infernal.' not in content


def test_retained_native_contexts_keep_their_original_bytes_and_separate_requested_quantities():
    provenance = json.loads((FIXTURES / 'provenance.json').read_text())
    for row in provenance['records']:
        path = FIXTURES / Path(row['path']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
    first, second = (saved_context(index)['context'] for index in (6, 8))
    assert first['working_state']['observations'] == second['working_state']['observations']
    observed = first['working_state']['observations'][0]['measurements']
    assert [row['name'] for row in observed] == list(METRICS)
    assert first['child_reports'][1]['rows'][0]['measurements'] == [{'name': 'bitscore', 'value': 71.4}]
    assert second['child_reports'][2]['rows'][0]['measurements'] == [{'name': 'evalue', 'value': 3.6e-22}]


@pytest.mark.parametrize('receiver', ['scientific', 'root'])
def test_snapshot_bootstrap_and_update_project_before_hashing_without_changing_saved_operands(receiver):
    raw = [saved_context(index, receiver=receiver)['context'] for index in (6, 8)]
    before = encode(raw)
    views = [model_snapshot(context, TABLE) for context in raw]
    bootstrap = state_frame(views[0])
    update = state_frame(views[1], views[0])
    assert apply_state_frame(None, bootstrap) == views[0]
    assert apply_state_frame(views[0], update) == views[1]
    assert update['base_revision'] == bootstrap['revision']
    assert 'working_state' not in update['fields']
    assert update['fields']['child_reports'] == raw[1]['child_reports']
    for original, view in zip(raw, views):
        assert view['working_state'] == without_automatic_observations(original)['working_state']
        assert view['child_reports'] == original['child_reports']
        assert view['last_local_outcome'] == original['last_local_outcome']
        assert view['requested_form'] == original['requested_form']
        assert view['current_report_basis_refs'] == original['current_report_basis_refs']
        assert view['current_credit'] == original['current_credit']
        assert view['waiting_support']['duration_expectations'] == original['waiting_support']['duration_expectations']
    views[0]['child_reports'][1]['rows'][0]['measurements'][0]['value'] = -999
    assert encode(raw) == before


@pytest.mark.parametrize('protocol', ['legacy', 'framed'])
def test_actual_scientific_provider_preserves_task_and_only_requested_native_numbers(tmp_path, protocol):
    saved = [saved_context(index) for index in (6, 8)]
    before = encode(saved)
    wire = ScientificWire(tmp_path / 'wire')
    views = [model_snapshot(row['context'], TABLE) for row in saved]
    contexts = ([row['context'] for row in saved] if protocol == 'legacy' else
        [state_frame(views[0]), state_frame(views[1], views[0])])

    async def exercise():
        for context in contexts:
            await wire.complete('scientific', 'REASONING', saved[0]['instructions'], context, OUTPUT_SCHEMA)
    asyncio.run(exercise())
    turns = wire.turns_sent()
    texts = [turn['input'][0]['text'] for turn in turns]
    assert_requested_text(texts[0])
    assert_requested_text(texts[1], evalue=True)
    assert texts[0].split('\n\nSTEERING\n')[0] == texts[1].split('\n\nSTEERING\n')[0]
    assert saved[0]['context']['scientific_process']['evidence_axis']['investigation_instructions'] in texts[0]
    for index, turn in enumerate(turns):
        request = json.loads((tmp_path / f'wire/call-{index + 1:05}/request.json').read_text())
        assert request['context'] == contexts[index]
        assert request['input'] == turn['input']
        assert turn['outputSchema'] == OUTPUT_SCHEMA
    if protocol == 'framed':
        assert wire.scientific_prompt_states[('scientific', 'REASONING')] == views[1]
    assert encode(saved) == before


def test_public_scientific_renderer_filters_the_full_saved_context_without_a_provider():
    saved = saved_context()
    before = encode(saved)
    rendered = render_scientific_process_prompt(saved['context'], saved['instructions'])
    assert_requested_text(rendered)
    assert encode(saved) == before


@pytest.mark.parametrize('protocol', ['legacy', 'framed'])
def test_actual_root_provider_serializes_exact_projected_returns_and_valid_frames(tmp_path, protocol):
    saved = [saved_context(index, receiver='root') for index in (6, 8)]
    before = encode(saved)
    wire = ConversationWire(tmp_path / 'wire')
    views = [model_snapshot(row['context'], TABLE) for row in saved]
    contexts = ([row['context'] for row in saved] if protocol == 'legacy' else
        [state_frame(views[0]), state_frame(views[1], views[0])])

    async def exercise():
        for context in contexts:
            await wire.complete('root', 'REASONING', saved[0]['instructions'], context, OUTPUT_SCHEMA)
    asyncio.run(exercise())
    turns = [params for method, params in wire.sent if method == 'turn/start']
    received = None
    for index, turn in enumerate(turns):
        payload = json.loads(turn['input'][0]['text'])
        if protocol == 'framed':
            assert payload == contexts[index]  # no post-hash mutation in provider
            received = apply_state_frame(received, payload)
            assert received == views[index]
        else:
            received = payload
            assert received == without_automatic_observations(saved[index]['context'])
        assert received['child_reports'] == saved[index]['context']['child_reports']
        assert received['working_state']['observations'] == []
        request = json.loads((tmp_path / f'wire/call-{index + 1:05}/request.json').read_text())
        assert request['context'] == contexts[index]
        assert request['input'] == turn['input']
        assert turn['outputSchema'] == OUTPUT_SCHEMA
    assert encode(saved) == before


@pytest.mark.parametrize('receiver', ['scientific', 'root'])
@pytest.mark.parametrize('protocol', ['legacy', 'framed'])
def test_reference_only_return_never_automatically_expands_native_measurements(tmp_path, receiver, protocol):
    saved = saved_context(receiver=receiver)
    context = saved['context']
    observation = context['working_state']['observations'][0]
    reference = observation['id']
    context['child_reports'] = [{'completed': True, 'references': [reference, observation['source_ref']]}]
    context['current_report_basis_refs'] = [reference]
    context['last_local_outcome'] = {'status': 'completed', 'record_refs': [reference]}
    before = encode(context)
    snapshot = model_snapshot(context, TABLE)
    supplied = state_frame(snapshot) if protocol == 'framed' else context
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(wire.complete(receiver, 'REASONING', saved['instructions'], supplied, OUTPUT_SCHEMA))
    text = wire.turns_sent()[0]['input'][0]['text']
    if receiver == 'scientific':
        content = steering(text)
        assert reference in content
        for metric in METRICS:
            assert f'| {metric} |' not in content
        assert '71.4' not in content and '3.6e-22' not in content
    else:
        payload = json.loads(text)
        received = apply_state_frame(None, payload) if protocol == 'framed' else payload
        assert received['working_state']['observations'] == []
        assert received['child_reports'] == context['child_reports']
    assert encode(context) == before


@pytest.mark.parametrize('receiver', ['scientific', 'root'])
def test_explicit_own_outcome_and_lookup_remain_available_at_actual_model_boundary(tmp_path, receiver):
    saved = saved_context(receiver=receiver)
    raw = saved['context']
    observation = deepcopy(raw['working_state']['observations'][0])
    raw['last_local_outcome'] = {'status': 'completed', 'result': {'selected_record': observation}}
    before = encode(raw)
    snapshot = model_snapshot(raw, TABLE)
    assert snapshot['working_state']['observations'] == []
    assert snapshot['last_local_outcome'] == raw['last_local_outcome']
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'result': {'status': 'completed', 'result': {'selected_record': observation}}}
    wire = ScientificWire(tmp_path / 'wire')

    async def exercise():
        await wire.complete(receiver, 'REASONING', saved['instructions'], state_frame(snapshot), OUTPUT_SCHEMA)
        await wire.complete(receiver, 'REASONING', saved['instructions'], lookup, OUTPUT_SCHEMA)
    asyncio.run(exercise())
    texts = [turn['input'][0]['text'] for turn in wire.turns_sent()]
    if receiver == 'scientific':
        own = steering(texts[0]).split('Last own action outcome\n', 1)[1]
        looked_up = steering(texts[1]).split('Requested information; continue the same decision\n', 1)[1]
        for text in (own, looked_up):
            assert 'selected_record.measurements[1].name | evalue' in text
            assert 'selected_record.measurements[1].value.value | 3.6e-22' in text
    else:
        received = apply_state_frame(None, json.loads(texts[0]))
        assert received['last_local_outcome'] == raw['last_local_outcome']
        assert json.loads(texts[1]) == lookup
    assert encode(raw) == before


@pytest.mark.parametrize('receiver', ['scientific', 'root'])
def test_runtime_restores_old_pending_snapshot_without_rereading_or_rewriting_answered_lookup(
        tmp_path, monkeypatch, receiver):
    """Exercise DecisionSource.call -> exchange_decision with real durable rows.

    The pre-fix pending snapshot and interrupted second dispatch are seeded using
    the ordinary immutable journal API. The selected response is not executed;
    this check concerns decision restoration, not a new scientific investigation.
    """
    saved = saved_context(receiver=receiver)
    raw = saved['context']
    raw_before = encode(raw)
    wire = ConversationWire(tmp_path / 'wire')
    wire.reply = {'response': {'response_type': 'select_action', **reason(0)}}
    schema = obj({'selection': obj({'kind': {'const': 'reason'},
        'commit': obj({'fixture_value': {'type': 'number'}})}), 'report_update': obj({})})
    with Store(tmp_path / 'state') as store:
        subject = store.create_problem(raw_sequence='ACGU', molecule='rna')['subject_refs'][0]
        workflow = runtime.Workflow(store, ToolRegistry(store), wire, tmp_path / 'run',
            'synthetic-infernal-pending-restoration',
            lambda path, initial: FixtureController(str(path), initial, 1), lambda *_: 0,
            episode_binding_factories=(), execution_binding={'fixture': True},
            decision_protocol='decision_exchange_v1')
        source = workflow.build('annotation', 'root', 'Synthetic pending snapshot restoration',
            store.validate_scope({'subject_refs': [subject]})).source
        source.calls = index = 9
        output_schema = runtime._action_generation_schema(source.exchange_schema(schema))
        # A previous selected (unexecuted) reason supplies real own-input detail
        # through the ordinary history reader, before its answer is frozen.
        workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
            'call_index': 4, 'purpose': 'decision', 'request': runtime._json({
                'context': {}, 'schema': schema, 'decision_protocol': 'decision_exchange_v1'}),
            'response': runtime._json(reason(0.125))})
        logical = {'context': raw, 'schema': schema, 'decision_protocol': 'decision_exchange_v1'}
        workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
            'call_index': index, 'purpose': 'decision', 'request': runtime._json(logical), 'response': None})
        old_snapshot = model_snapshot(raw, TABLE)
        old_snapshot['working_state']['observations'] = deepcopy(raw['working_state']['observations'])
        frozen_frame = state_frame(old_snapshot)
        request = {'context': frozen_frame, 'instructions': saved['instructions'],
            'output_schema': output_schema, 'restoration': {'snapshot': old_snapshot,
                'pending_public_exchanges': []}, 'conversation_key': None}
        exchanges = workflow.decision_exchanges
        exchanges.prepare(source.episode_id, index, 0, request)
        query = {'response': {'response_type': 'request_context', 'lookup': {
            'view': 'own_attempt_detail', 'decision_index': 4,
            'pointer': '/commit/fixture_value', 'offset': 0, 'limit': 1}}}
        answer = runtime.lookup_attempts(workflow.journal, source.episode_id,
            before=index, query=query['response']['lookup'])
        assert answer['values'] == 0.125 and answer['slice_unit'] == 'scalar_values'
        exchanges.respond(source.episode_id, index, 0, query)
        exchanges.resolve_lookup(source.episode_id, index, 0, answer)
        public = [{'exchange_index': 0, 'response': query, 'lookup_result': answer}]
        exchanges.prepare(source.episode_id, index, 1, {**request,
            'context': {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
                'decision_index': index, 'exchange_index': 0, 'result': answer},
            'restoration': {'snapshot': old_snapshot, 'pending_public_exchanges': public}})
        prior = exchanges.rows(source.episode_id, index)
        original_request = workflow.journal.row('runtime_model_calls', source.episode_id, index)['request']

        def no_acquisition(*args, **kwargs):
            raise AssertionError('Restoration must reuse its answered lookup and saved inputs')
        monkeypatch.setattr(runtime, 'lookup_attempts', no_acquisition)
        monkeypatch.setattr(runtime, 'yield_table', no_acquisition)
        monkeypatch.setattr(workflow, 'execute', no_acquisition)
        monkeypatch.setattr(workflow.tools, 'execute', no_acquisition)
        response, returned_index, interpreted, returned_schema = asyncio.run(source.call({}, {}))
        rows = exchanges.rows(source.episode_id, index)
        assert rows[:2] == prior
        assert len(rows) == 3
        retry = rows[2]['request']
        assert retry['retry_of_exchange_index'] == 1
        frame = retry['context']
        restored = apply_state_frame(None, frame)
        assert restored == model_snapshot(raw, TABLE)
        assert frame['kind'] == 'decision_bootstrap'
        assert frame['restored_pending_decision_index'] == index
        assert frame['restored_public_exchanges'] == public
        assert restored['child_reports'] == raw['child_reports']
        assert restored['working_state']['observations'] == []
        assert prior[0]['request']['context'] == frozen_frame
        assert apply_state_frame(None, frozen_frame) == old_snapshot
        assert response == reason(0) and returned_index == index and returned_schema == schema
        assert interpreted['working_state']['observations'] == raw['working_state']['observations']
        assert workflow.journal.row('runtime_model_calls', source.episode_id, index)['request'] == original_request
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        turns = [params for method, params in wire.sent if method == 'turn/start']
        assert len(turns) == 1
        text = turns[0]['input'][0]['text']
        if receiver == 'scientific':
            assert_requested_text(text)
            assert '/commit/fixture_value' in text and '| values | 0.125 |' in text
        else:
            assert json.loads(text) == frame
        assert turns[0]['outputSchema'] == output_schema
        model_request = json.loads((tmp_path / 'wire/call-00001/request.json').read_text())
        assert model_request['context'] == frame
        assert model_request['input'] == turns[0]['input']
    assert encode(raw) == raw_before
