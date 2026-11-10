"""Own source reuse has exact scope and no scientific or controller side effects."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.component_axis_inspection import inspection_index
from gene_annotation_episode.state import Store
from test_state import source


def add(store, index, tool, args, result, *, run='run', episode='owner', status='completed'):
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
        (run, episode, index, json.dumps({'kind': 'tool', 'tool': tool, 'arguments': args}),
         None if result is None else json.dumps({'status': status, 'result': result})))


def setup(store):
    store.create_problem(raw_sequence='MACD', molecule='protein')
    store.db.execute('CREATE TABLE runtime_actions '
        '(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
    return source(store, 'The source reports a ratio of 1:1. Another passage follows.')


def test_read_coverage_reuses_only_actual_own_received_artifact_frames(tmp_path):
    with Store(tmp_path / 'state') as store:
        src = setup(store)
        args = {'source_ref': src['id']}
        result = {'source_ref': src['id'], 'artifact_ref': src['artifact_ref'],
                  'representation': 'original', 'start': 0, 'end': 10}
        add(store, 0, 'source.read', args, result)
        add(store, 1, 'source.read', args, {**result, 'start': 5, 'end': 15})
        add(store, 2, 'source.read', args, {**result, 'start': 0, 'end': 10,
            'representation': 'text'})
        add(store, 3, 'source.read', args, {**result, 'start': 20, 'end': 25})
        # A different byte artifact must retain a separate coordinate frame.
        other_artifact = store.artifact('A different representation.')
        add(store, 4, 'source.read', args, {**result, 'artifact_ref': other_artifact})
        add(store, 5, 'source.read', args, {**result, 'end': 50}, episode='child')
        add(store, 6, 'source.read', args, {**result, 'end': 50}, run='other')
        hidden = source(store, 'A source not received by this episode.')
        add(store, 7, 'source.read', {'source_ref': hidden['id']},
            {**result, 'source_ref': hidden['id'], 'end': 50})
        add(store, 8, 'source.read', args, {**result, 'end': 50}, status='failed')
        add(store, 9, 'source.read', args, None)
        before = store.db.total_changes
        index = inspection_index(store, run_id='run', episode_id='owner',
                                 known_source_refs={src['id']})
        first, second = index['read_sources']
        assert first['inspected_ranges'] == [{'start': 0, 'end': 15}, {'start': 20, 'end': 25}]
        assert first['decision_indices'] == [0, 1, 2, 3]
        assert first['representations'] == ['original', 'text']
        assert second['artifact_ref'] == other_artifact
        assert second['inspected_ranges'] == [{'start': 0, 'end': 10}]
        assert index['credit_change'] is index['permission_change'] is False
        assert store.db.total_changes == before
        assert inspection_index(store, run_id='run', episode_id='owner',
            known_source_refs={src['id']}) == index


def test_exact_search_witness_and_context_survive_later_reads_without_reexecution(tmp_path):
    with Store(tmp_path / 'state') as store:
        src = setup(store)
        text = store.get_artifact(src['artifact_ref']).decode()
        start = text.index('1:1')
        witness = {'source_ref': src['id'], 'representation': 'text',
                   'start': start, 'end': start + 3, 'quote': '1:1'}
        context = {'artifact_ref': src['artifact_ref'], 'start': 0,
                   'end': len(text.encode()), 'text': text}
        match = {'artifact_ref': src['artifact_ref'], 'witness': witness, 'context': context}
        result = {'source_ref': src['id'], 'artifact_ref': src['artifact_ref'],
            'matches': [match], 'scanned_range': {'start': 0, 'end': len(text.encode())},
            'has_more': False, 'next_query': None}
        original = deepcopy(result)
        for index in (9, 15, 19, 21):
            add(store, index, 'source.locate', {'source_ref': src['id'],
                'representation': 'text', 'needle': '1:1'}, result)
        add(store, 22, 'source.read', {'source_ref': src['id']},
            {'source_ref': src['id'], 'artifact_ref': src['artifact_ref'],
             'representation': 'original', 'start': 0, 'end': 10})
        before = store.db.total_changes
        shown = inspection_index(store, run_id='run', episode_id='owner',
                                 known_source_refs={src['id']})
        search, = shown['located_passages']
        assert search['decision_indices'] == [9, 15, 19, 21]
        assert search['matches'] == [match]
        assert search['scanned_ranges'] == [{'start': 0, 'end': len(text.encode())}]
        assert search['last_query_has_more'] is False
        assert result == original and store.db.total_changes == before


@pytest.mark.parametrize('assessment', [None, {'scientific_question': 'What ratio was reported?'}])
def test_saved_partial_components_remain_available_without_filling_unknowns_or_new_credit(tmp_path, assessment):
    with Store(tmp_path / 'state') as store:
        src = setup(store)
        cells = {'ratio_mean': {'value': 1.0, 'status': 'populated', 'unit': 'mol_per_mol'},
                 'claim_mean_squared_error': {'value': None, 'status': 'unavailable',
                    'unavailable_reason': 'claim_unreported', 'unit': 'squared_ratio'}}
        saved = {'sheet_ref': 'source_' + 'a' * 24, 'cells': cells, 'independent_n': None,
            'assay_interpretation': {'molecule': None},
            'experiment_assessment': assessment}
        add(store, 24, 'literature.reaction.source.populate', {'source_ref': src['id']}, saved)
        add(store, 25, 'literature.reaction.source.populate', {'source_ref': src['id']}, saved)
        add(store, 26, 'source.read', {'source_ref': src['id']}, {'source_ref': src['id'],
            'artifact_ref': src['artifact_ref'], 'start': 0, 'end': 10})
        before = store.db.total_changes
        shown = inspection_index(store, run_id='run', episode_id='owner',
                                 known_source_refs={src['id']})
        result, = shown['saved_component_results']
        assert result['cells'] == cells and result['independent_n'] is None
        assert result['assay_interpretation']['molecule'] is None
        assert result['experiment_assessment'] == assessment
        assert result['decision_indices'] == [24, 25]
        assert store.db.total_changes == before


def test_explicit_own_revision_marks_prior_result_without_erasing_original_numbers(tmp_path):
    with Store(tmp_path / 'state') as store:
        src = setup(store)
        first = 'source_' + 'a' * 24
        second = 'source_' + 'b' * 24
        original_cells = {'ratio_mean': {'value': 1.0, 'status': 'populated'}}
        add(store, 1, 'literature.reaction.source.populate', {'source_ref': src['id']},
            {'sheet_ref': first, 'cells': original_cells, 'experiment_assessment': {
                'scientific_question': 'Reported ratio', 'revises_sheet_ref': None}})
        add(store, 2, 'literature.reaction.source.populate', {'source_ref': src['id']},
            {'sheet_ref': second, 'cells': original_cells, 'experiment_assessment': {
                'scientific_question': 'Reported ratio', 'revises_sheet_ref': first}})
        before = store.db.total_changes
        shown = inspection_index(store, run_id='run', episode_id='owner',
                                 known_source_refs={src['id']})
        old, new = shown['saved_component_results']
        assert old['superseded_by_own_result_refs'] == [second]
        assert old['cells'] == new['cells'] == original_cells
        assert new['experiment_assessment']['revises_sheet_ref'] == first
        assert store.db.total_changes == before
