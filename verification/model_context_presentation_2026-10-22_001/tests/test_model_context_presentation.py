"""Isolated finite-JSON presentation fixtures; no scientific workspace or work."""
from copy import deepcopy
import hashlib
import json
from types import MappingProxyType

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode import model_context_presentation as presentation
from method_loop.durable import canonical, content_digest
from method_loop.identities import EpisodeRef, UnitRef


RUN = 'presentation-fixture-run'
EPISODE = EpisodeRef(RUN, (('annotation', 'root'),)).episode_id
BEFORE = 10000
HISTORY = 'own_completed_action_history'
PAGE = 'own_completed_action_history_page'
PAGE_FIELDS = {
    'version', 'run_id', 'episode_id', 'before_decision_index', 'page_size_source',
    'preview_size', 'order', 'total_rows', 'included_rows', 'omitted_rows', 'range',
    'first_unit_index', 'last_unit_index', 'decision_indices', 'identity_fields',
    'included_rows_without_decision_identity', 'included_rows_without_unit_ref',
    'raw_history_sha256', 'included_history_sha256', 'history_is_complete',
    'history_lookup', 'exact_included_records', 'discover_older_decisions',
    'history_result_row_path', 'history_result_step_path', 'calculation_context',
}
CAPTURE_FIELDS = {
    'version', 'definition', 'run_id', 'episode_id', 'before_decision_index',
    'original_context_sha256', 'presented_context_sha256', 'model_input_text_sha256',
    'model_input_char_count', 'model_input_utf8_byte_count', 'context',
}


def fixture_context(count=175, *, version='wait_inputs_v2'):
    inputs = [0, -0.0, 2.5, -3.25, None, {'credit': 0, 'raw': [-2.5, None]}]
    history = []
    for index in range(count):
        unit = 3 * index
        row = {'episode_id': EPISODE, 'unit_index': unit,
            # Completion order differs from decision order; gaps are original.
            'decision_index': 3 * count - 2 * index,
            'controller_input': deepcopy(inputs[index % len(inputs)]),
            'controller_step': {'delta': [-1.5, -0.0, 0, 2.25][index % 4],
                'observed': True, 'estimate': {'lower': None, 'upper': 1.25,
                    'provenance': {'binding': index % 3, 'label': 'fixture β',
                                   'original': {'shape': [1, 1.0, -0.0, None]}}}}}
        if version == 'wait_inputs_v2':
            row.update(unit_ref=UnitRef(EPISODE, unit).as_record(), label=f'own {index}')
        history.append(row)
    return {'tools': [{'name': 'episode.history', 'input_schema': {'fixture': True}},
                      {'name': 'state.query'}],
        'waiting_support': {'version': version, HISTORY: history,
            'duration_expectations': [{'ref': 'fixture-duration', 'data': {'seconds': None}}],
            'progress_records': [{'ref': 'fixture-progress', 'seconds': 2.5}],
            'local_return_history': {'samples': [], 'raw': [-2.0, 0, None]}},
        'controller': {'scores': [1, -0.0, 0, -2.5], 'estimate': None},
        'visible_record_refs': ['fixture-reference'],
        'working_state': {'fixture': 'Unchanged λ', 'nested': {'z': 1.0, 'a': -0.0}},
        'other_history': [{'raw': index} for index in range(30)],
        'visual_evidence': [{'fixture_image': 'unchanged metadata'}]}


def capture(context, size=24, **overrides):
    operands = {'run_id': RUN, 'episode_id': EPISODE,
                'before_decision_index': BEFORE, 'preview_size': size, **overrides}
    return presentation.prepare_model_context_presentation(context, **operands)


def validate(value, original, size=24, **overrides):
    operands = {'run_id': RUN, 'episode_id': EPISODE,
                'before_decision_index': BEFORE, 'preview_size': size, **overrides}
    return presentation.validate_model_context_presentation(value,
        original_context=original, **operands)


def page(value):
    return value['context']['waiting_support'][PAGE]


def assert_conflict(call, *, path=None):
    with pytest.raises(ContractError, match='^model_presentation_contract_conflict$') as error:
        call()
    assert set(error.value.detail) == {'path'}
    assert isinstance(error.value.detail['path'], str)
    if path is not None:
        assert error.value.detail['path'] == path


def rehash_model_view(value):
    """An attacker can recompute hashes; original raw projection still wins."""
    value['context'] = json.loads(canonical(value['context']))
    value['presented_context_sha256'] = content_digest(value['context'])
    text = json.dumps(value['context'], allow_nan=False)
    value['model_input_text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    value['model_input_char_count'] = len(text)
    value['model_input_utf8_byte_count'] = len(text.encode())


def test_latest_page_preserves_all_raw_numeric_values_and_other_fields():
    original = fixture_context()
    before = canonical(original)
    value = capture(original)
    assert set(value) == CAPTURE_FIELDS
    assert set(page(value)) == PAGE_FIELDS
    assert value['version'] == presentation.VERSION == 'episode_model_presentation_v1'
    assert presentation.MODE == 'bounded_wait_history_v1'
    assert presentation.REQUEST_VERSION == 'runtime_model_call_request_v2'
    assert canonical(original) == before
    assert len(original['waiting_support'][HISTORY]) == 175
    expected = deepcopy(original)
    expected['waiting_support'][HISTORY] = expected['waiting_support'][HISTORY][-24:]
    shown = deepcopy(value['context'])
    del shown['waiting_support'][PAGE]
    assert canonical(shown) == canonical(expected)
    assert canonical(value['context']['waiting_support'][HISTORY]) == canonical(
        original['waiting_support'][HISTORY][-24:])
    assert value['original_context_sha256'] == content_digest(original)
    assert value['presented_context_sha256'] == content_digest(value['context'])
    stored = json.loads(json.dumps(value, ensure_ascii=True, indent=2))
    validated = validate(stored, original)
    assert canonical(validated) == canonical(stored)
    validated['context']['waiting_support'][HISTORY][-1]['controller_step']['delta'] = 99
    assert stored['context']['waiting_support'][HISTORY][-1]['controller_step']['delta'] != 99
    original['waiting_support'][HISTORY][-1]['controller_step']['delta'] = 101
    assert value['context']['waiting_support'][HISTORY][-1]['controller_step']['delta'] != 101


def test_page_counts_ranges_and_actual_decision_indices():
    original = fixture_context(9)
    value = capture(original, 3)
    meta = page(value)
    assert (meta['total_rows'], meta['included_rows'], meta['omitted_rows']) == (9, 3, 6)
    assert meta['range'] == {'start': 6, 'end_exclusive': 9,
                            'unit': 'completed_own_action_history_position'}
    assert (meta['first_unit_index'], meta['last_unit_index']) == (18, 24)
    assert meta['order'] == 'original_unit_index_ascending'
    assert meta['decision_indices'] == [15, 13, 11]
    assert meta['decision_indices'] != [18, 21, 24]
    assert meta['exact_included_records'] == {'tool': 'episode.history', 'arguments': {
        'view': 'records', 'decision_indices': [15, 13, 11]}}
    assert meta['discover_older_decisions'] == {'tool': 'episode.history', 'arguments': {
        'view': 'index', 'offset': 0, 'limit': 3}}
    assert meta['history_result_row_path'] == 'result.records[*].controller_observation'
    assert meta['history_result_step_path'] == 'result.records[*].controller_observation.step'
    assert meta['raw_history_sha256'] == content_digest(original['waiting_support'][HISTORY])
    assert not meta['history_is_complete']
    full = capture(original, 30)
    assert page(full)['history_is_complete'] and page(full)['omitted_rows'] == 0
    assert len(full['context']['waiting_support'][HISTORY]) == 9


@pytest.mark.parametrize('count', [0, 7])
def test_zero_preview_keeps_empty_page_and_positive_lookup(count):
    original = fixture_context(count)
    value = capture(original, 0)
    meta = page(value)
    assert value['context']['waiting_support'][HISTORY] == []
    assert (meta['total_rows'], meta['included_rows'], meta['omitted_rows']) == (count, 0, count)
    assert meta['range']['start'] == meta['range']['end_exclusive'] == count
    assert meta['first_unit_index'] is meta['last_unit_index'] is None
    assert meta['decision_indices'] == [] and meta['exact_included_records'] is None
    assert meta['history_is_complete'] is (count == 0)
    assert meta['discover_older_decisions']['arguments']['limit'] == 1
    assert len(original['waiting_support'][HISTORY]) == count
    validate(value, original, 0)


def test_multiple_provenance_values_stay_complete_in_included_rows():
    original = fixture_context(8)
    value = capture(original, 5)
    rows = value['context']['waiting_support'][HISTORY]
    assert {row['controller_step']['estimate']['provenance']['binding'] for row in rows} == {0, 1, 2}
    assert canonical(rows) == canonical(original['waiting_support'][HISTORY][-5:])
    assert 'provenance_ref' not in canonical(rows)
    assert rows[0]['controller_step']['estimate']['provenance']['original']['shape'] == [1, 1.0, -0.0, None]


@pytest.mark.parametrize('original', [{}, {'waiting_support': {}},
                                    {'waiting_support': {'version': 'wait_inputs_v2'}}])
def test_absent_history_preserves_absence_and_identity_context(original):
    value = capture(original)
    assert canonical(value['context']) == canonical(original)
    assert PAGE not in value['context'].get('waiting_support', {})
    assert value['original_context_sha256'] == value['presented_context_sha256']
    validate(value, original)


def test_absent_history_unknown_identity_and_cross_episode_conflicts():
    original = fixture_context(4, version='wait_inputs_v1')
    rows = original['waiting_support'][HISTORY]
    del rows[0]['decision_index']
    rows[1]['decision_index'] = None
    value = capture(original)
    shown = value['context']['waiting_support'][HISTORY]
    assert 'decision_index' not in shown[0] and shown[1]['decision_index'] is None
    assert all('unit_ref' not in row for row in shown)
    assert page(value)['included_rows_without_decision_identity'] == 2
    assert page(value)['included_rows_without_unit_ref'] == 4
    assert page(value)['decision_indices'] == [8, 6]
    assert page(value)['exact_included_records']['arguments']['decision_indices'] == [8, 6]
    validate(value, original)
    for row in rows:
        row['decision_index'] = None
        row['unit_ref'] = None
    unknown = capture(original)
    assert page(unknown)['exact_included_records'] is None
    assert page(unknown)['included_rows_without_decision_identity'] == 4
    assert unknown['context']['waiting_support'][HISTORY][0]['unit_ref'] is None
    assert_conflict(lambda: capture(original, episode_id='different-episode'))


@pytest.mark.parametrize('catalog,availability,reason', [
    ([{'name': 'episode.history'}], 'available', None),
    ([{'name': 'state.query'}], 'unavailable', 'episode_history_not_in_saved_catalog'),
    ([], 'unavailable', 'episode_history_not_in_saved_catalog'),
    (None, 'unknown', 'saved_tool_catalog_unavailable'),
    ({'episode.history': {}}, 'unknown', 'saved_tool_catalog_unavailable'),
])
def test_history_lookup_reflects_only_actual_saved_tool_map(catalog, availability, reason):
    original = fixture_context(3)
    if catalog is None:
        del original['tools']
    else:
        original['tools'] = catalog
    value = capture(original)
    meta = page(value)
    assert meta['history_lookup'] == {'availability': availability, 'unavailable_reason': reason}
    assert (meta['exact_included_records'] is not None) is (availability == 'available')
    assert (meta['discover_older_decisions'] is not None) is (availability == 'available')
    assert len(value['context']['waiting_support'][HISTORY]) == 3
    validate(value, original)


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(waiting_support=None),
    lambda c: c['waiting_support'].update(own_completed_action_history={}),
    lambda c: c['waiting_support'].update(own_completed_action_history_page={}),
    lambda c: c['waiting_support'][HISTORY].reverse(),
    lambda c: c['waiting_support'][HISTORY].__setitem__(0, None),
    lambda c: c['waiting_support'][HISTORY][0].update(episode_id='foreign'),
    lambda c: c['waiting_support'][HISTORY][1].update(unit_index=0),
    lambda c: c['waiting_support'][HISTORY][0].update(unit_index=-1),
    lambda c: c['waiting_support'][HISTORY][0].update(unit_index=True),
    lambda c: c['waiting_support'][HISTORY][0].update(decision_index=BEFORE),
    lambda c: c['waiting_support'][HISTORY][0].update(decision_index=-1),
    lambda c: c['waiting_support'][HISTORY][0].update(decision_index=False),
    lambda c: c['waiting_support'][HISTORY][1].update(decision_index=9),
    lambda c: c['waiting_support'][HISTORY][0]['unit_ref'].update(unit_id='forged'),
    lambda c: c['waiting_support'][HISTORY][0].update(unit_ref=UnitRef(EPISODE, 3).as_record()),
    lambda c: c['waiting_support'][HISTORY][0].pop('controller_input'),
    lambda c: c['waiting_support'][HISTORY][0].pop('controller_step'),
])
def test_malformed_original_rows_are_rejected_without_sorting_or_repair(mutation):
    original = fixture_context(3)
    mutation(original)
    before = canonical(original)
    assert_conflict(lambda: capture(original))
    assert canonical(original) == before


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf'), object(), {1: 'key'}, '\ud800'])
def test_nonfinite_or_non_json_context_is_a_structured_contract_conflict(bad):
    assert_conflict(lambda: capture({'value': bad}), path='context')
    original = fixture_context(3)
    value = capture(original)
    value['context']['value'] = bad
    assert_conflict(lambda: validate(value, original), path='model_presentation')


@pytest.mark.parametrize('bad', [-1, True, 1.0, None, '24'])
def test_preview_operand_is_an_existing_explicit_nonnegative_integer(bad):
    assert_conflict(lambda: capture({}, bad), path='preview_size')
    assert_conflict(lambda: presentation.model_context_presentation_definition(preview_size=bad),
                    path='preview_size')


@pytest.mark.parametrize('operands,path', [
    ({'run_id': ''}, 'run_id'), ({'episode_id': None}, 'episode_id'),
    ({'before_decision_index': True}, 'before_decision_index'),
    ({'before_decision_index': -1}, 'before_decision_index'),
])
def test_capture_requires_actual_owner_and_prior_decision_boundary(operands, path):
    assert_conflict(lambda: capture({}, **operands), path=path)


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(version='unsupported'),
    lambda p: p.update(unknown='extra'),
    lambda p: p['definition'].update(preview_size=False),
    lambda p: p.update(run_id='another-run'),
    lambda p: p.update(original_context_sha256='0' * 64),
    lambda p: p.update(presented_context_sha256='0' * 64),
    lambda p: p.update(model_input_text_sha256='0' * 64),
    lambda p: p.update(model_input_char_count=p['model_input_char_count'] + 1),
    lambda p: page(p).update(total_rows=99),
    lambda p: page(p)['range'].update(start=99),
    lambda p: page(p).update(order='decision_index'),
    lambda p: page(p)['exact_included_records']['arguments'].update(decision_indices=[0]),
    lambda p: page(p)['history_lookup'].update(availability='unavailable'),
    lambda p: page(p).update(history_result_step_path='result.records[*].step'),
    lambda p: p['context']['controller']['scores'].__setitem__(0, True),
    lambda p: p['context']['waiting_support'][HISTORY][0].update(controller_input=0.0),
    lambda p: p['context']['waiting_support'][HISTORY][1].update(controller_input=0.0),
])
def test_tampering_and_type_or_signed_zero_changes_are_rejected(mutation):
    original = fixture_context(3)
    value = capture(original)
    mutation(value)
    assert_conflict(lambda: validate(value, original))


def test_recomputed_model_hashes_do_not_allow_changed_rows_or_omitted_raw_inputs():
    original = fixture_context(6)
    value = capture(original, 2)
    rows = value['context']['waiting_support'][HISTORY]
    rows[0]['controller_step']['delta'] = 123
    page(value)['included_history_sha256'] = content_digest(rows)
    rehash_model_view(value)
    assert_conflict(lambda: validate(value, original, 2))
    unchanged_view = capture(original, 2)
    original['waiting_support'][HISTORY][0]['controller_step']['delta'] = 456
    assert_conflict(lambda: validate(unchanged_view, original, 2))


def test_exact_provider_text_is_canonical_ordered_on_first_capture_and_replay(monkeypatch):
    original = fixture_context(5)
    original['z'] = {'z': 'β', 'a': -0.0}
    first = capture(original, 2)
    text = json.dumps(first['context'], allow_nan=False)
    expected_order = json.loads(canonical(first['context']))
    assert text == json.dumps(expected_order, allow_nan=False)
    assert first['model_input_text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert first['model_input_char_count'] == len(text)
    assert first['model_input_utf8_byte_count'] == len(text.encode())
    assert '\\u03b2' in text
    stored_request = canonical({'version': presentation.REQUEST_VERSION,
        'context': original, 'schema': {}, 'model_presentation': first})
    stored = json.loads(stored_request)['model_presentation']
    monkeypatch.setattr(presentation, 'prepare_model_context_presentation',
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError('Do not recapture')))
    replay = validate(stored, original, 2)
    assert json.dumps(replay['context'], allow_nan=False).encode() == text.encode()


def test_metadata_size_does_not_embed_omitted_rows():
    small = capture(fixture_context(10), 2)
    large = capture(fixture_context(1000), 2)
    assert len(large['context']['waiting_support'][HISTORY]) == 2
    assert len(page(large)['decision_indices']) == 2
    assert set(page(large)) == set(page(small)) == PAGE_FIELDS
    assert len(canonical(page(large))) - len(canonical(page(small))) < 100
    assert page(large)['omitted_rows'] == 998
    assert 'controller_input' not in canonical(page(large))
    assert 'controller_step' not in canonical(page(large))


def test_frozen_mapping_inputs_are_copied_as_independent_json():
    original = fixture_context(2)
    value = capture(MappingProxyType(original))
    validate(MappingProxyType(value), MappingProxyType(original))
    definition = presentation.model_context_presentation_definition(preview_size=24)
    definition['preview_size'] = 0
    assert value['definition']['preview_size'] == 24
