"""Human views of fixed HOMER returns, using retained native bytes.

Engineered Source identities exercise pure presentation only. Runtime custody
and requested-return evidence belong to the ordinary Workflow verification.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3

import pytest

from gene_annotation_episode import homer_motif_measurements as measurements
from gene_annotation_episode.scientific_process_prompt import _values
from test_homer_motif_measurements import complete_sheet, retained, selection, series_for, SOURCE


def _forbidden(*args, **kwargs):
    raise AssertionError('HOMER presentation must only consume fixed return values')


def test_retained_homer_display_keeps_native_precision_and_distinct_populations(complete_sheet, monkeypatch):
    known = series_for(complete_sheet, 'known_results')
    ordinal = 0
    assert known['observations'][ordinal]['name'].startswith('NF1')
    components = measurements.calculate_homer_components(complete_sheet,
        selector=selection(known, offset=ordinal, limit=1))
    packet = measurements.project_homer_return(components, source_ref=SOURCE)
    original = deepcopy(packet)
    monkeypatch.setattr(measurements, 'calculate_homer_components', _forbidden)
    monkeypatch.setattr(measurements, 'parse_homer_motif_sheet', _forbidden)
    text = _values({'result': packet, 'status': 'completed', 'record_refs': [SOURCE],
        'changed_record_refs': [SOURCE], 'same_fixed_result': deepcopy(packet)})
    assert text.count('Callable operand') == 1
    assert text.count(SOURCE) == 1 and text.count(known['series_id']) == 1
    assert all(text.count(series['series_id']) == 1 for series in packet['available_series'])
    assert 'Retained series available for saved selection' in text
    assert '1e-78' in text and '-1.800e+02' in text and '-180.016288' in text
    assert '6.734334' in text and '0.0000' in text and 'fixed_4' in text
    assert 'unique_joined_background_members | 1000' in text
    assert '| background | 956 | 956 | available |' in text
    assert 'Effective native motif denominators remain separate' in text
    assert 'not_provided' in text and 'known_table' in text and 'native_pwm' in text
    assert 'homer_occurrence_' not in text and 'homer_input_population_' not in text
    assert packet == original


def test_retained_homer_display_preserves_pwm_order_and_auxiliary_meanings(complete_sheet, monkeypatch):
    series = series_for(complete_sheet, 'denovo_pwm', 'homerMotifs.motifs8')
    components = measurements.calculate_homer_components(complete_sheet,
        selector=selection(series, limit=1))
    packet = measurements.project_homer_return(components, source_ref=SOURCE)
    original = deepcopy(packet)
    monkeypatch.setattr(measurements, 'calculate_homer_components', _forbidden)
    text = _values(packet)
    assert 'TTGCCAAG' in text and '1e-202' in text and '-466.553334' in text
    assert 'native column order A, C, G, T' in text
    representation = packet['selected_series'][0]['observations'][0]['representations'][0]
    cursor = 0
    for row in representation['pwm_rows']:
        tokens = json.dumps(row['raw_fields'], separators=(',', ':'))
        cursor = text.index('| ' + str(row['ordinal_0based']) + ' | ' + tokens, cursor) + 1
    for auxiliary in representation['native_auxiliary_measurements']:
        assert auxiliary['raw_field'] in text and auxiliary['definition'] in text
        assert auxiliary['population'] in text and auxiliary['denominator'] in text
        assert auxiliary['coordinate_origin'] in text
    assert packet == original


def test_homer_display_does_not_merge_distinct_source_or_selection_views(complete_sheet):
    known = series_for(complete_sheet, 'known_results')
    first = measurements.project_homer_return(measurements.calculate_homer_components(
        complete_sheet, selector=selection(known, limit=1)), source_ref=SOURCE)
    second = deepcopy(first)
    second['source_ref'] = 'source_' + 'b' * 24
    third = measurements.project_homer_return(measurements.calculate_homer_components(
        complete_sheet, selector=selection(known, offset=1, limit=1)), source_ref=SOURCE)
    text = _values([first, second, third, deepcopy(first)])
    assert text.count('Callable operand') == 3
    assert text.count(SOURCE) == 2 and text.count(second['source_ref']) == 1


def test_actual_retained_homer_post_read_context_reaches_provider_text(tmp_path, monkeypatch):
    """Render the exact recorded post-read decision; no new scientific work."""
    from gene_annotation_episode import acquisition, homer_motif_tools as host
    from gene_annotation_episode import native_homer_execution as native
    from gene_annotation_episode import native_homer_worker, native_lifecycle
    from gene_annotation_episode.providers import _SessionConnection
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_homer_motif_workflow import QUESTION

    environment = 'HMMER_NATIVE_ORACLE_HOMER_PRESENTATION'
    selected = os.environ.get(environment + '_PROOF')
    if not selected:
        pytest.skip('requires an explicitly pinned passed retained HOMER Workflow')

    def pin(path):
        path = Path(path).resolve(strict=True)
        raw = path.read_bytes()
        return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    prefix = Path(selected).resolve(strict=True)
    prefix_pin = pin(prefix)
    assert prefix_pin['sha256'] == os.environ[environment + '_PROOF_SHA256']
    proof = json.loads(prefix.read_bytes())
    assert proof['version'] == 'ordinary_homer_saved_workflow_v1'
    assert proof['phase'] == 'verified' and proof['passed'] is True
    assert all(proof[name] is True for name in ('original_prefix_authenticated',
        'original_parent_literal_read_verified', 'literal_read_verified',
        'public_unselected_series_selection_verified', 'saved_calculation_verified',
        'exact_repeat_verified', 'derived_read_verified', 'typed_parent_delivery_verified',
        'closed_replay_verified', 'originals_unchanged'))
    assert proof['native_attempts'] == proof['payload_read_attempts'] == []
    assert len(proof['worker_requests']) == len(proof['worker_handles']) == 1
    database = Path(proof['owned_database']['path']).resolve(strict=True)
    assert pin(database) == proof['owned_database']
    assert all(not Path(str(database) + suffix).exists() for suffix in ('-wal', '-shm'))
    copied = tmp_path / 'retained-closed-state.sqlite3'
    shutil.copyfile(database, copied)
    copied_before = pin(copied)
    assert {key: copied_before[key] for key in ('sha256', 'size_bytes')} == {
        key: proof['owned_database'][key] for key in ('sha256', 'size_bytes')}
    run_id = proof['configuration']['run_id']
    connection = sqlite3.connect(copied.as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        # Authenticate the pinned proof's complete saved history against the
        # actual closed database, without constructing another Store/episode.
        history = {}
        for table in proof['saved_run_history']:
            if table == 'tool_operations':
                rows = connection.execute('SELECT * FROM tool_operations WHERE '
                    'substr(operation_key,1,?)=? ORDER BY rowid', (len(run_id) + 1, run_id + ':'))
            else:
                rows = connection.execute('SELECT * FROM ' + table + ' WHERE run_id=? ORDER BY rowid', (run_id,))
            history[table] = [dict(row) for row in rows]
        assert history == proof['saved_run_history'] == proof['actual_histories'][run_id]
        assert len(history['runtime_model_calls']) == len(history['runtime_actions']) == 5
        assert len(history['tool_operations']) == 4
        assert all(row['state'] == 'yielded' for row in history['runtime_episodes'])
        call, = [item for item in proof['calls'] if item['grain'] == 'scientific_process' and item['turn'] == 2]
        episode_id = call['episode_id']
        episode, = [row for row in history['runtime_episodes'] if row['episode_id'] == episode_id]
        assert json.loads(episode['path'])[-1][0] == 'scientific_process'
        recorded, = [row for row in history['runtime_model_calls']
            if row['episode_id'] == episode_id and row['call_index'] == 1]
        assert recorded['purpose'] == 'decision'
        request = json.loads(recorded['request'])
        assert request['context'] == call['context']
        assert json.loads(recorded['response']) == call['response']
        schema_before = deepcopy(request['schema'])
        context = request['context']
        context_before = deepcopy(context)
        assert context['goal']['objective'] == QUESTION == proof['configuration']['question']
        literal, = [row for row in history['tool_operations'] if json.loads(row['arguments']) ==
            dict(mode='read_stored', result_ref=proof['original_value']['source_ref'])]
        literal_outcome = json.loads(literal['result'])
        public = literal_outcome['result']
        assert public == proof['original_value'] == context['last_local_outcome']['result']
        assert literal_outcome['changed_record_refs'] == []
        source_row, = connection.execute('SELECT data FROM records WHERE id=?', (public['source_ref'],))
        source = json.loads(source_row['data'])
        assert source == proof['original_source']
        capture_row, = connection.execute('SELECT data FROM records WHERE id=?', (source['parent_source_refs'][0],))
        capture = json.loads(capture_row['data'])
        assert capture['accession'] in {row['id'] for row in connection.execute('SELECT id FROM tool_operations')}
        selected_tool, = [tool for tool in context['scientific_process']['child_tool_info']
            if tool['name'] == host.TOOL]
        assert selected_tool['description'] == host.DESCRIPTION
        assert selected_tool['instructions'] == host.INSTRUCTIONS
        candidate, = [series for series in public['available_series'] if series['role'] == 'denovo_pwm'
            and series['requested_motif_length_bp'] == 10 and series['capture_state'] == 'complete']
        assert candidate == proof['original_series_candidate']
        assert candidate['series_id'] not in public['selector']['series_ids']

        # This is the real provider's pure text entry, with exactly the same
        # recorded context/instructions that precede model dispatch. Its state
        # is the same empty presentation state established by its constructor.
        provider = object.__new__(_SessionConnection)
        provider.scientific_prompt_states = {}
        with monkeypatch.context() as guard:
            for name in ('parse_homer_motif_sheet', 'calculate_homer_components', 'project_homer_return'):
                guard.setattr(measurements, name, _forbidden)
            for name in ('prepare_ordinary_homer_attempt', 'run_ordinary_homer_attempt'):
                guard.setattr(native, name, _forbidden)
            for name in ('run_native_homer', 'run_homer_motif_job'):
                guard.setattr(native_homer_worker, name, _forbidden)
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
                guard.setattr(native_lifecycle, name, _forbidden)
            for name in ('complete', '_rpc', '_session'):
                guard.setattr(_SessionConnection, name, _forbidden)
            guard.setattr(acquisition.PublicClients, '_http', _forbidden)
            guard.setattr(socket, 'create_connection', _forbidden)
            guard.setattr(Store, '__init__', _forbidden)
            guard.setattr(ToolRegistry, '_source', _forbidden)
            text, instructions = provider._presentation(episode_id, 'REASONING', call['instructions'], context)
        assert text.startswith('TASK\n') and '\n\nSTEERING\n' in text
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert QUESTION in task and host.DESCRIPTION in task and host.INSTRUCTIONS in task
        assert 'Operands for ' + host.TOOL in task and 'Parent return form' in task
        assert 'calculate_saved' in task and 'result_ref' in task and 'series_ids' in task
        assert 'Last own action outcome' in steering
        assert '| p_value | provided | 1e-78 | 1e-78 | available | finite | probability | integer_exponent |' in steering
        assert '| ln_p_value | provided | -1.800e+02 | -180.0 | available | finite | natural_log_probability | scientific_3 |' in steering
        assert '| q_value | provided | 0.0000 | 0.0 | available | finite | probability | fixed_4 |' in steering
        assert '| site_threshold | not_provided | null | null | not_provided | not_provided | native_site_detection_score | not_provided |' in steering
        assert '| background_weight | provided | 158.8 | 158.8 | available | finite | relative_weight | fixed_1 |' in steering
        assert '| background_percentage | provided | 16.61 | 16.61 | available | finite | percent | fixed_2 |' in steering
        assert 'unique_joined_background_members | 1000' in steering
        assert '| background | 956 | 956 | available |' in steering
        assert 'Effective native motif denominators remain separate' in steering
        assert '| known_outcome | unknown |' in steering and '| denovo_outcome | unknown |' in steering
        catalog_index = public['available_series'].index(candidate) + 1
        row = '| Series ' + str(catalog_index) + ' | ' + candidate['series_id'] + ' | denovo_pwm | 10 | complete | unknown |'
        assert row in steering and steering.count(candidate['series_id']) == 1
        assert 'Retained series available for saved selection' in steering
        assert '"available_series":' not in text and '"selected_series":' not in text
        assert not text.lstrip().startswith('{')

        private = {capture['id'], capture['artifact_ref'], capture['request_ref'], *capture['auxiliary_artifact_refs'],
            source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']}
        private.update(reference[9:] for reference in tuple(private) if reference.startswith('artifact_'))
        def private_metadata(value):
            if type(value) is dict:
                for key, item in value.items():
                    if type(item) is str and (item.startswith('/') or key.endswith('sha256')):
                        private.add(item)
                    else:
                        private_metadata(item)
            elif type(value) is list:
                for item in value: private_metadata(item)
            elif type(value) is str and value.startswith('/'):
                private.add(value)
        for value in (proof['original_native_handle'], proof['worker_control'], proof['configuration']['factory']):
            private_metadata(value)
        private.add(str(database.parent))
        private.add(context['scientific_process']['initial_selection_sha256'])
        assert all(value not in text for value in private if value)
        assert public['source_ref'] in steering
        assert context == context_before and request['schema'] == schema_before
        assert provider.scientific_prompt_states[(episode_id, 'REASONING')] == context_before
        assert type(instructions) is str and instructions
        assert connection.execute('SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? '
            'AND call_index=1', (run_id, episode_id)).fetchone()[0] == recorded['request']
    finally:
        connection.close()
    assert pin(copied) == copied_before
    assert pin(database) == proof['owned_database'] and pin(prefix) == prefix_pin
    assert all(not Path(str(database) + suffix).exists() for suffix in ('-wal', '-shm'))
