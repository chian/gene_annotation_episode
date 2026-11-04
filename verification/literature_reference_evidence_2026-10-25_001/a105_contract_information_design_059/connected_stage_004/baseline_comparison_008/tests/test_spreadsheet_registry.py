"""Spreadsheet tools publish actual source data/provenance, never annotations."""
import json

import pytest

from gene_annotation_episode import tools as module
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_spreadsheet_tools import ROOT, REAL_SHA, workbook


def register(store, path):
    artifact = store.artifact(path.read_bytes(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return store.put('source', {'provider': 'fixture.retained_workbook_bytes', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
        'version': artifact, 'retrieved_at': None}, origin='external')


def test_actual_study_row_source_lineage_replay_and_caller_limits(tmp_path, monkeypatch):
    path = ROOT/'cases/gene_001/workspace/artifacts'/REAL_SHA[:2]/REAL_SHA
    if not path.is_file():
        pytest.skip('Actual study workbook from investigation_002 is unavailable')
    limits = {'memory_bytes': 256*1024**2, 'scratch_bytes': 8*1024**2}
    with Store(tmp_path/'workspace') as store:
        store.create_problem(ROOT/'cases/gene_001/target.fna', molecule='dna', role='gene')
        original = register(store, path)
        tools = ToolRegistry(store, job_limits=limits)
        sheets = tools.execute('source.xlsx.sheets', {'source_ref': original['id']})
        assert sheets['status'] == 'completed'
        sheet = next(row for row in sheets['result']['sheets'] if row['name'] == 'Average ratio and clustering')
        args = {'source_ref': original['id'], 'sheet_key': sheet['sheet_key'],
            'offset': 0, 'limit': 1, 'header_row': 1,
            'where': {'column': 'B', 'match': 'equals', 'value': 'P0AAW1', 'case_sensitive': True}}
        result = tools.execute('source.xlsx.rows', args, operation_key='actual-target-row')
        assert result['status'] == 'completed'
        body = result['result']
        assert body['rows'][0]['row_number'] == 1324
        source = store.get(body['source_ref'])
        assert source['parent_source_refs'] == [original['id']]
        assert body['xlsx_source_ref'] == original['id']
        assert body['provenance']['input_artifact_ref'] == original['artifact_ref']
        assert body['provenance']['parent_source_ref'] == original['id']
        assert body['provenance']['selection'] == {key: value for key, value in args.items() if key != 'source_ref'}
        saved = json.loads(store.get_artifact(source['artifact_ref']))
        assert saved['rows'] == body['rows'] and saved['sheet']['worksheet_part'] == 'xl/worksheets/sheet2.xml'
        assert body['provenance']['job_limits']['memory_bytes'] == limits['memory_bytes']
        assert tools.catalog()['source.xlsx.rows']['configuration']['job_limits']['scratch_bytes'] == limits['scratch_bytes']
        monkeypatch.setattr(module, 'xlsx_native', lambda *a, **k: pytest.fail('Replay must not launch native parsing'))
        assert tools.execute('source.xlsx.rows', args, operation_key='actual-target-row') == result
        assert project_credit(store).credit == 0
        assert store.count('assessment') == store.count('annotation') == 0


def test_partial_sheet_decode_is_published_with_actionable_feedback(tmp_path):
    path, _ = workbook(tmp_path, bad_string=True)
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='MARGKK', molecule='protein', role='gene')
        source = register(store, path)
        tools = ToolRegistry(store, job_limits={'memory_bytes': 256*1024**2, 'scratch_bytes': 8*1024**2})
        result = tools.execute('source.xlsx.rows', {'source_ref': source['id'],
            'sheet_key': 'selected', 'offset': 0, 'limit': 3, 'where': None, 'header_row': 1})
        assert result['status'] == 'partial'
        assert result['feedback']['cell_error_count'] == 1
        assert result['feedback']['source_ref'] == result['result']['source_ref']
        assert result['result']['rows'][1]['cells'][0]['value'] == 'YBHP'
        assert result['result']['rows'][2]['cells'][1]['value'] == '3'
        assert store.get(result['feedback']['source_ref'])['parent_source_refs'] == [source['id']]
