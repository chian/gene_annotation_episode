"""Pure provider-wire presentation controls using separately pinned392 facts.

Post-result contexts in these tests are explicitly engineering presentation
inputs. The original episodes closed after selecting one action; these controls
neither claim a historical post-result dispatch nor make a new model call.
"""
from copy import deepcopy
import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import apply_state_frame, state_frame
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.molecular_result_facts import frozen_molecular_facts, received_molecular_facts
from gene_annotation_episode.molecular_sequence_result_contracts import validate_ordinary_orf_return
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode import scientific_process_prompt as prompt
from gene_annotation_episode.state import Store


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _forbidden(*args, **kwargs):
    raise AssertionError('presentation attempted provider/scientific work or a scientific File read')


def _guards(monkeypatch):
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    for name in ('complete', '_rpc', '_session'):
        monkeypatch.setattr(_SessionConnection, name, _forbidden)
    for name in ('calculate_orf_components', 'build_orf_sheet'):
        monkeypatch.setattr('gene_annotation_episode.orf_measurements.' + name, _forbidden)
        monkeypatch.setattr('gene_annotation_episode.molecular_sequence_driver.' + name, _forbidden)
    for name in ('prepare_ordinary_orf_attempt', 'run_ordinary_orf_attempt'):
        monkeypatch.setattr('gene_annotation_episode.molecular_sequence_ordinary.' + name, _forbidden)
    monkeypatch.setattr('gene_annotation_episode.materials._verified_artifact_path', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_file_capture._verified_artifact_path', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)


@pytest.fixture
def retained_values(monkeypatch):
    supplied = os.environ.get('HMMER_NATIVE_ORACLE_ORDINARY_ORF_PRESENTATION_PREFIX')
    selected_sha = os.environ.get('HMMER_NATIVE_ORACLE_ORDINARY_ORF_PRESENTATION_SHA256')
    if not supplied or not selected_sha or 'HMMER529_ATTEMPT' not in os.environ:
        pytest.skip('requires the separately pinned successful392 recovery proof and immutable Store')
    proof_path = Path(supplied).resolve(strict=True)
    assert proof_path.name == 'ORF_PUBLIC_SAVED_RECOVERY.json' and _pin(proof_path)['sha256'] == selected_sha
    proof = json.loads(proof_path.read_text())
    assert proof['version'] == 'ordinary_orf_saved_phase_recovery_v1' and proof['passed'] is True
    assert proof['new_native_calls'] == proof['new_calculator_calls'] == proof['retained_recovery_model_dispatches'] == 0
    database = proof['owned_database_file']
    assert _pin(database['path']) == database and not Path(database['path'] + '-wal').exists()
    _guards(monkeypatch)
    store = Store.__new__(Store)
    store.path = Path(database['path']).parent
    store.db = sqlite3.connect(Path(database['path']).as_uri() + '?mode=ro&immutable=1', uri=True)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    try:
        selected = []
        for phase in [*proof['recovered_phases'], proof['derived_read']]:
            run_id = phase['run_id']
            records = EpisodeReturnRecords(store, run_id, failure_prefix='presentation_')
            episodes = list(store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)', (run_id,)))
            parent, child = [records.context(row[0]) for row in episodes]
            operation = store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?', (phase['operation']['operation_key'],)).fetchone()
            assert dict(operation) == phase['operation']
            arguments, outcome = json.loads(operation['arguments']), json.loads(operation['result'])
            action = store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
                (run_id, child.episode_id)).fetchone()
            assert json.loads(action['action']) == dict(kind='tool', tool='annotate_open_reading_frames', arguments=arguments)
            assert operation['scope'] == canonical(plain(child.scope))
            assert operation['id'] == identity('operation', dict(key=operation['operation_key'], name=operation['name'], arguments=arguments))
            assert EpisodeReturnRecords._equal({key: value for key, value in json.loads(action['result']).items()
                if key != 'pending_work_after_action'}, outcome)
            public = validate_ordinary_orf_return(phase['public'])
            assert public == outcome['result']
            source = store.get(public['source_ref'])
            payload = {key: value for key, value in source.items() if key not in ('id', 'origin', 'record_type')}
            assert source['id'] == identity('source', dict(origin=source['origin'], record=payload))
            frozen = frozen_molecular_facts(store, run_id, child, fact_source='orf_measurements')
            assert frozen == received_molecular_facts(store, run_id, parent, fact_source='orf_measurements') == [public]
            _, form, _ = records._attempt(parent, 0)
            assert form == phase['returned'] == {'measurements': [public]}
            calls = [dict(row) for row in store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid', (run_id,))]
            assert len(calls) == 2
            contexts = [json.loads(row['request'])['context'] for row in calls]
            dispatches = phase['scripted_provider_dispatches']
            for row, dispatch in zip(calls, dispatches):
                assert row['episode_id'] == dispatch['episode_id'] and json.loads(row['response']) == dispatch['response']
            assert contexts[0]['goal']['objective'] == contexts[1]['goal']['objective']
            assert contexts[1]['scientific_process']['selection']['evidence_axis']['option_id'] == 'A103'
            assert contexts[1]['scientific_process']['selection']['thought_pattern']['option_id'] == 'P01'
            selected.append(dict(public=public, outcome=outcome, form=form, frozen=frozen,
                parent_context=contexts[0], child_context=contexts[1],
                parent_instructions=dispatches[0]['instructions'], child_instructions=dispatches[1]['instructions']))
        assert store.db.total_changes == 0
        yield selected
        assert store.db.total_changes == 0 and _pin(database['path']) == database
        assert _pin(proof_path)['sha256'] == selected_sha
    finally:
        store.db.close()


def _connection():
    # The actual pure method used by complete() immediately before wire input.
    # No constructor, subprocess, app-server session or transport is created.
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    return connection


def _engineering_state(selected, carrier):
    parent = carrier == 'received'
    base = deepcopy(selected['parent_context' if parent else 'child_context'])
    state = deepcopy(base)
    if carrier == 'own':
        state['last_local_outcome'] = deepcopy(selected['outcome'])
        lookup = deepcopy(selected['outcome'])
    elif carrier == 'received':
        state['child_reports'] = [deepcopy(selected['form'])]
        lookup = dict(status='completed', result=dict(admitted_child_return=deepcopy(selected['form'])))
    else:
        # This is a detached presentation placement of an authenticated frozen
        # form, not a new model report_update or a runtime admission.
        state['current_report_update'] = deepcopy(selected['form'])
        lookup = dict(status='completed', result=dict(frozen_return=deepcopy(selected['form'])))
    return base, state, lookup, selected['parent_instructions' if parent else 'child_instructions']


@pytest.mark.parametrize('phase', [0, 1, 2], ids=['original', 'saved_calculation', 'derived_literal_read'])
@pytest.mark.parametrize('carrier', ['own', 'received', 'frozen'])
@pytest.mark.parametrize('transport', ['full', 'bootstrap', 'update', 'lookup'])
def test_actual_session_renderer_groups_authenticated392_values_without_dispatch(retained_values, phase, carrier, transport):
    selected = retained_values[phase]
    base, state, lookup, instructions = _engineering_state(selected, carrier)
    before = canonical(dict(base=base, state=state, lookup=lookup, selected=selected))
    connection, episode = _connection(), 'engineering-post-result'
    if transport == 'full':
        supplied = state
    elif transport == 'bootstrap':
        supplied = state_frame(state)
        assert apply_state_frame(None, supplied) == state
    else:
        initial = state_frame(base)
        connection._presentation(episode, 'REASONING', instructions, initial)
        supplied = (state_frame(state, base) if transport == 'update' else dict(version='decision_context_v1',
            kind='decision_lookup_result', decision_index=1, exchange_index=0, result=lookup))
        if transport == 'update':
            assert apply_state_frame(base, supplied) == state
    supplied_before = canonical(supplied)
    text, wire_instructions = connection._presentation(episode, 'REASONING', instructions, supplied)
    public = selected['public']
    assert wire_instructions == prompt.text_instructions(instructions)
    assert 'TASK' in text and 'STEERING' in text
    assert text.count(public['source_ref']) == 1
    assert '| ["ATGAAATAA","MK",0,9,"+",1] | stored_value | native_field_units |' in text
    assert '| interval_length_nt | 9 | stored_value | nt | orf_retained_row |' in text
    assert 'native_outcome (original retained components)' in text
    assert 'Original component qualifiers Q1' in text and 'Original component qualifiers Q2' not in text
    assert '| early_ambiguity_termination | false | stored_value |' in text
    assert public['values']['source_kind'] in text
    assert public['file_states']['components'] in text
    assert public['values']['source_sheet_ref'] not in text and public['values']['source_components_ref'] not in text
    assert canonical(supplied) == supplied_before
    assert canonical(dict(base=base, state=state, lookup=lookup, selected=selected)) == before


def test_equal_source_selection_packets_share_one_display_but_distinct_sources_or_selections_do_not(retained_values):
    value = retained_values[1]['public']
    original = canonical(value)
    text = prompt._values(dict(own=value, received=[deepcopy(value)], frozen=deepcopy(value)))
    assert text.count(value['source_ref']) == 1 and text.count('Original component qualifiers Q1') == 1
    other = deepcopy(value); other['source_ref'] = 'source_' + 'f'*24
    text = prompt._values([value, other])
    assert text.count(value['source_ref']) == text.count(other['source_ref']) == 1
    selection = deepcopy(value)
    selection['selection']['rows'][0]['fields'] = ['native_row']
    selection['values']['rows'] = selection['values']['rows'][:1]
    text = prompt._values([value, selection])
    assert text.count(value['source_ref']) == 2
    assert canonical(value) == original


def test_qualifier_factoring_requires_complete_typed_equality_within_one_packet(retained_values):
    value = deepcopy(retained_values[1]['public'])
    value['values']['rows'][1]['scientific_qualifiers']['states']['early_ambiguity_termination']['value'] = True
    validate_ordinary_orf_return(value)
    text = prompt._values(value)
    assert 'Original component qualifiers Q1' in text and 'Original component qualifiers Q2' in text
    assert '| early_ambiguity_termination | false |' in text and '| early_ambiguity_termination | true |' in text


@pytest.mark.parametrize('state', ['stored_value', 'stored_null', 'path_missing', 'invalid_type', 'source_unavailable'])
def test_engineered_zero_null_missing_false_and_unavailable_remain_distinct(retained_values, state):
    value = deepcopy(retained_values[1]['public'])
    cell = value['values']['rows'][1]
    if state == 'source_unavailable':
        value['values']['source_components_ref'] = None
        value['values']['source_states']['components'] = value['file_states']['components'] = 'unavailable'
        for row in value['values']['rows']:
            for item in [row, *row['scientific_qualifiers']['states'].values()]:
                item.update(source_ref=None, source_state='unavailable', value_state='source_unavailable', value=None)
    else:
        cell.update(value_state=state, value=0 if state == 'stored_value' else None)
    validate_ordinary_orf_return(value)
    before = canonical(value)
    text = prompt._values(value)
    assert '| interval_length_nt | ' + ('0' if state == 'stored_value' else 'null') + ' | ' + state + ' | nt |' in text
    if state != 'source_unavailable': assert '| early_ambiguity_termination | false |' in text
    assert canonical(value) == before


def test_engineered_structured_paths_and_scientific_strings_keep_literal_content(retained_values):
    value = deepcopy(retained_values[1]['public'])
    cell = value['values']['rows'][0]
    path = [dict(subject_ref='input_original', start=6, end=9, unit='nt', strand='-'),
        dict(subject_ref='input_original', start=0, end=3, unit='nt', strand='+')]
    value['selection']['rows'][0]['fields'][0] = cell['field'] = 'orf_source_path'
    cell.update(value=path, unit='per_segment_nt_or_symbol', source_pointer='/rows/0/orf_source_path')
    validated = validate_ordinary_orf_return(value)
    text = prompt._values(value)
    assert prompt._molecular_literal(validated['values']['rows'][0]['value']) in text
    literal = next(line.split(' | ')[2] for line in text.splitlines() if ' | orf_source_path | ' in line)
    displayed = json.loads(literal)
    assert EpisodeReturnRecords._equal(displayed, path)
    assert [(part['subject_ref'], part['start'], part['end'], part['unit'], part['strand']) for part in displayed] == [
        ('input_original', 6, 9, 'nt', '-'), ('input_original', 0, 3, 'nt', '+')]
    scientific = deepcopy(retained_values[1]['public'])
    literal = scientific['values']['source_components_ref']
    scientific['values']['rows'][0]['value'][0] = literal
    validate_ordinary_orf_return(scientific)
    assert literal in prompt._values(scientific)  # A value string is not a provenance slot.


def test_engineered_denominator_operands_preserve_typed_zero_units_and_provenance_roles(retained_values):
    value = deepcopy(retained_values[1]['public'])
    cell = deepcopy(value['values']['rows'][1])
    cell.update(row_id={'kind': 'summary'}, field='mean_retained_orf_length_nt', value=None,
        value_state='stored_null', source_pointer='/summary/mean_retained_orf_length_nt',
        unit='nt_symbols_per_row', population_id='orf_retained_strings')
    for name in ('source_definition', 'translation_state', 'early_ambiguity_termination'):
        cell['scientific_qualifiers']['states'].pop(name)
    cell['denominators'] = [dict(value_state='stored_value', value=number,
        source_ref=cell['source_ref'], source_state=cell['source_state'], source_pointer=path,
        kind=kind, unit=unit, unit_sources=[]) for number, path, kind, unit in (
            (0, '/summary/retained_length_sum_nt', 'numerator', 'nt_symbols'),
            (0.0, '/summary/retained_length_denominator_rows', 'denominator', 'rows'))]
    value['selection']['rows'] = [dict(row_id={'kind': 'summary'}, fields=[cell['field']])]
    value['values']['rows'] = [cell]
    validate_ordinary_orf_return(value)
    before = canonical(value)
    text = prompt._values(value)
    assert '"value":0,' in text and '"value":0.0,' in text
    assert '"unit":"nt_symbols"' in text and '"unit":"rows"' in text
    assert '"source_role":"components"' in text and cell['source_ref'] not in text
    assert '| mean_retained_orf_length_nt | null | stored_null | nt_symbols_per_row |' in text
    other = deepcopy(value); other['values']['rows'][0]['denominators'][1]['value'] = 0
    validate_ordinary_orf_return(other)
    assert prompt._values([value, other]).count(value['source_ref']) == 2
    assert canonical(value) == before


def test_unknown_malformed_and_unrelated_values_keep_the_previous_generic_rendering(retained_values):
    malformed = deepcopy(retained_values[1]['public']); malformed.pop('source_ref')
    unknown = dict(version='another_profile', payload=retained_values[1]['public'])
    for value in (malformed, unknown, dict(scientific_string='artifact_' + 'a'*64, false=False, zero=0, missing=None)):
        assert prompt._values(value) == prompt._table(('Field', 'Supplied value'), prompt._rows(value))


@pytest.mark.parametrize('fact_source', ['itc_binding_parameters', 'liftover_point_mappings',
    'circular_dichroism_summaries', 'orf_measurements'])
def test_registered_molecular_receiver_starts_with_actual_empty_initial_values(retained_values, fact_source):
    selected = retained_values[0]
    state = deepcopy(selected['parent_context'])
    state['available_report_facts'] = {fact_source: state['available_report_facts'][fact_source]}
    assert state['child_reports'] == [] and state['last_local_outcome'] is None and state['current_report_update'] == {}
    assert 'received_rna_structure_values' not in state and 'received_rna_comparison_values' not in state
    assert prompt.has_molecular_receiver_context(state)
    before = canonical(state)
    connection, episode = _connection(), 'engineering-empty-molecular-receiver'
    frame = state_frame(state)
    text, instructions = connection._presentation(episode, 'REASONING', selected['parent_instructions'], frame)
    assert text.startswith('TASK\n') and 'STEERING' in text and 'Selected molecular result' not in text
    assert instructions == prompt.text_instructions(selected['parent_instructions'])
    assert connection.scientific_prompt_states[(episode, 'REASONING')] == state
    assert canonical(state) == before and apply_state_frame(None, frame) == state


@pytest.mark.parametrize('declaration', ['absent', 'empty', 'name_only', 'wrong_type', 'wrong_schema',
    'changed_meaning', 'unregistered', 'not_object'])
def test_absent_or_malformed_molecular_declaration_preserves_prior_raw_routing(retained_values, declaration):
    selected = retained_values[0]
    state = deepcopy(selected['parent_context'])
    registered = deepcopy(state['available_report_facts']['orf_measurements'])
    molecular = {'itc_binding_parameters', 'liftover_point_mappings', 'circular_dichroism_summaries', 'orf_measurements'}
    state['available_report_facts'] = {key: value for key, value in state['available_report_facts'].items() if key not in molecular}
    if declaration == 'absent':
        state.pop('available_report_facts')
    elif declaration == 'empty':
        state['available_report_facts'] = {}
    elif declaration == 'name_only':
        state['available_report_facts']['orf_measurements'] = {'type': 'array'}
    elif declaration == 'wrong_type':
        registered['type'] = 'object'; state['available_report_facts']['orf_measurements'] = registered
    elif declaration == 'wrong_schema':
        registered['report_schema'] = {'type': 'array', 'items': {'type': 'number'}}
        state['available_report_facts']['orf_measurements'] = registered
    elif declaration == 'changed_meaning':
        registered['meaning'] = 'unregistered meaning'; state['available_report_facts']['orf_measurements'] = registered
    elif declaration == 'unregistered':
        state['available_report_facts']['unregistered_molecular_values'] = registered
    else:
        state['available_report_facts'] = []
    assert not prompt.has_molecular_receiver_context(state)
    before = canonical(state)
    connection = _connection()
    text, instructions = connection._presentation('engineering-unregistered-receiver', 'REASONING',
        selected['parent_instructions'], state)
    assert text == json.dumps(state, allow_nan=False) and instructions == selected['parent_instructions']
    assert connection.scientific_prompt_states == {} and canonical(state) == before


def test_published_scientific_renderer_keeps_precedence_over_molecular_receiver_capability(retained_values):
    selected = retained_values[0]
    state = deepcopy(selected['child_context'])
    assert prompt.has_molecular_receiver_context(state) and prompt.is_published_scientific_context(state)
    text, instructions = _connection()._presentation('engineering-existing-published-task', 'REASONING',
        selected['child_instructions'], state)
    assert text == prompt.render_scientific_process_prompt(state, selected['child_instructions'])
    assert instructions == prompt.text_instructions(selected['child_instructions'])


def test_task_and_steering_keep_pre_n_registration_text():
    source = Path(prompt.__file__).read_text()
    tree = ast.parse(source)
    # Exact pre-N-registration units, independently checked against retained469.
    # This guard establishes unchanged text, not new approval of its wording.
    pins = dict(_task='fdffd84c9f19fa8705f55b74153e35288d319c524344458dd3f1126ebaa8c0bc',
        _steering='286cc38ec22fe2a7f2c1bd3c05c0a3ddf5a332c4f127407b630ae3fb97c1f9f1')
    for name, expected in pins.items():
        unit = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert hashlib.sha256(ast.get_source_segment(source, unit).encode()).hexdigest() == expected
