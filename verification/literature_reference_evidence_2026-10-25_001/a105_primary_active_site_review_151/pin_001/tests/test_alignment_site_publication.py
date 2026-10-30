"""Selected real retained-result reads and numerical custody; no remote calls."""
import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from test_blast_result_views import published
from test_tool_grading_publication import numerical


@pytest.mark.parametrize('molecule,sequence', [('dna', 'ACGTTGCA'),
    ('rna', 'ACGUUGCA'), ('protein', 'MACDEFGH')])
def test_actual_alignment_selected_positions_publish_exact_distinct_population(tmp_path, molecule, sequence):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)['subject_refs']
        tools = ToolRegistry(store)
        aligned = tools.execute('sequence.align', {'query_ref': target, 'reference_ref': target,
            'molecule': molecule, 'mode': 'global'}, operation_key='align')
        assert aligned['status'] == 'completed', aligned
        arguments = {'alignment_ref': aligned['result']['observation_ref'], 'positions': [2, 0, 2]}
        result = tools.execute('sequence.sites', arguments, operation_key='sites')
        assert result['status'] == 'completed', result
        grading, = source_tool_gradings(store, result['result']['source_ref'])
        sheet, summary = grading['sheet'], grading['scores']['summary']
        assert sheet['selection'] == {'kind': 'reference_positions', 'positions': [2, 0, 2]}
        assert [row['reference_position'] for row in sheet['sites']] == [2, 0, 2]
        assert summary['requested_position_count'] == 3
        assert summary['unique_requested_position_count'] == 2
        assert summary['duplicate_requested_position_count'] == 1
        assert summary['paired_positions'] == summary['identical_positions'] == 2
        assert summary['selected_query_paired_coverage'] == summary['selected_reference_paired_coverage'] == .25
        assert grading['scores']['ratios']['selected_paired_identity'] == {
            'numerator': 2, 'denominator': 2, 'value': 1.}
        assert numerical(store.get(result['result']['observation_ref']))['paired_positions'] == 2
        assert len(result['result']['sites']) == 3 and store.count('observation') == 2
        assert 'native_input' not in result['result'] and 'sheet' not in result['result']
        assert tools.execute('sequence.sites', arguments, operation_key='sites') == result
        assert store.count('observation') == 2 and store.count('annotation') == 0


def test_known_no_alignment_preserves_zero_coverage_and_unknown_identity(tmp_path):
    path = tmp_path / 'pair.fa'
    path.write_text('>query\nAAAA\n>reference\nTTTT\n')
    with Store(tmp_path / 'state') as store:
        query, reference = store.create_problem(path, molecule='dna')['subject_refs']
        tools = ToolRegistry(store)
        aligned = tools.execute('sequence.align', {'query_ref': query, 'reference_ref': reference,
            'molecule': 'dna', 'mode': 'local'}, operation_key='align')
        assert aligned['status'] == 'completed', aligned
        result = tools.execute('sequence.sites', {'alignment_ref': aligned['result']['observation_ref'],
            'window': {'start': 0, 'end': 4}}, operation_key='sites')
        assert result['status'] == 'completed', result
        grading, = source_tool_gradings(store, result['result']['source_ref'])
        assert grading['sheet']['status'] == 'no_alignment'
        assert grading['scores']['summary']['outside_alignment_positions'] == 4
        assert grading['scores']['summary']['selected_query_paired_coverage'] == 0
        assert grading['scores']['summary']['selected_paired_identity'] is None


@pytest.mark.parametrize('alignment,offset,expected_rows', [(True, 2, 4), (True, 8, 0), (False, 0, None)])
def test_blast_column_grading_is_retained_without_another_scientific_record(tmp_path, alignment, offset, expected_rows):
    store, tools, target, hsp, _ = published(tmp_path, alignment=alignment)
    with store:
        counts = store.count('source'), store.count('observation'), store.count('annotation')
        args = {'observation_ref': hsp, 'column_offset': offset, 'column_limit': 4}
        result = tools.execute('result.blast.hsp', args, operation_key='selected-columns',
            permitted_record_refs=[hsp])
        assert result['status'] == 'completed', result
        assert result['record_refs'] == []
        body = result['result']
        retained = json.loads(store.get_artifact(body['site_grading_artifact_ref']))
        sheet, scores = retained['grading']['sheet'], retained['grading']['scores']
        assert sheet['source']['alignment_ref'] == hsp
        assert sheet['source']['native_locator'] == {'report_ordinal': 0, 'hit_ordinal': 0, 'hsp_ordinal': 0}
        assert sheet['requested_window'] == {'column_offset': offset, 'column_limit': 4}
        assert body['column_correspondence_count'] == expected_rows
        if offset == 2:
            assert [row['query_interval'] for row in sheet['columns']] == [[4, 5], None, [5, 6], [6, 7]]
            assert [row['reference_interval'] for row in sheet['columns']] == [[8, 9], [7, 8], None, [6, 7]]
            assert scores['summary']['paired_columns'] == scores['summary']['identical_pairs'] == 2
            assert scores['summary']['alignment_identity'] == .5
            assert scores['summary']['query_paired_coverage'] == 2 / 12
            assert scores['summary']['reference_paired_coverage'] == 2 / 18
            assert sheet['original_mapping_inputs']['reference'] is None
        elif alignment:
            assert sheet['columns'] == [] and scores['summary']['paired_columns'] == 0
            assert scores['summary']['paired_identity'] is None
        else:
            assert sheet['realized_window'] is None
            assert scores['summary']['paired_columns'] is None
        assert (store.count('source'), store.count('observation'), store.count('annotation')) == counts
        assert tools.execute('result.blast.hsp', args, operation_key='selected-columns',
            permitted_record_refs=[hsp]) == result
        denied = tools.execute('result.blast.hsp', args, operation_key='selected-columns', permitted_record_refs=[])
        assert denied['status'] == 'invalid'


def test_site_grading_failure_keeps_existing_native_source_and_typed_partial(tmp_path, monkeypatch):
    import gene_annotation_episode.alignment_site_inputs as inputs
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ACGTTGCA', molecule='dna')['subject_refs']
        tools = ToolRegistry(store)
        aligned = tools.execute('sequence.align', {'query_ref': target, 'reference_ref': target,
            'molecule': 'dna', 'mode': 'global'}, operation_key='align')
        def fail(*args, **kwargs):
            raise ValueError('injected_selected_site_grading_failure')
        monkeypatch.setattr(inputs, 'extract_biopython_reference_sites', fail)
        result = tools.execute('sequence.sites', {'alignment_ref': aligned['result']['observation_ref'],
            'positions': [2]}, operation_key='failed-grading')
        assert result['status'] == 'partial', result
        assert result['result']['sites'] is None and result['result']['data_status'] == 'unavailable'
        grading, = source_tool_gradings(store, result['result']['source_ref'])
        assert grading['sheet'] is None and grading['scores'] is None
        assert grading['failure']['code'] == 'injected_selected_site_grading_failure'
        assert numerical(store.get(result['result']['observation_ref'])) == {}
