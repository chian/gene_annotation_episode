"""Spreadsheet tools publish actual source data/provenance, never annotations."""
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from test_spreadsheet_tools import workbook


def register(store, path):
    artifact = store.artifact(path.read_bytes(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return store.put('source', {'provider': 'fixture.retained_workbook_bytes', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
        'version': artifact, 'retrieved_at': None}, origin='external')


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
