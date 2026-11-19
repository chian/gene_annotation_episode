"""Instruction retrieval through the real runtime; no model or native job.

Synthetic controllers govern these fixtures only. The tests assert information
delivery, durable recovery and score/form boundaries, not scientific success.
"""
import json
from pathlib import Path

from gene_annotation_episode.tool_knowledge import ToolKnowledge, VERSION


def _source(tmp_path, text='First line\nSecond λ line\nLast line\n'):
    source = tmp_path/'manual-source'
    source.mkdir()
    (source/'manual.md').write_text(text)
    (source/'index.json').write_text(json.dumps({'version': VERSION, 'entries': [{
        'entry_id': 'fixture-manual', 'title': 'Fixture native tool',
        'summary': 'Synthetic launch instructions', 'tags': ['fixture', 'launch'],
        'tool_names': ['fixture.measure'], 'provenance': ['synthetic_test_fixture'],
        'sections': [{'section_id': 'launch', 'title': 'Launch', 'path': 'manual.md'}]}]}))
    return source


def test_metadata_discovery_does_not_open_manuals_and_reads_page_exact_lines(tmp_path, monkeypatch):
    source = _source(tmp_path)
    library = ToolKnowledge.freeze(tmp_path/'saved', source=source)
    original = Path.open

    def metadata_only(path, *args, **kwargs):
        if path.suffix == '.md':
            raise AssertionError('Discovery must not materialize manuals')
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', metadata_only)
        found = library.search(query='FIXTURE launch', offset=0, limit=1)
        assert [entry['entry_id'] for entry in found['entries']] == ['fixture-manual']
        assert 'sections' not in found['entries'][0]
        assert library.entry('fixture-manual')['entry']['sections'][0]['lines'] == 3
    first = library.read(entry_id='fixture-manual', section_id='launch', offset=0, limit=1)
    second = library.read(**first['next_query'])
    third = library.read(**second['next_query'])
    assert first['text']+second['text']+third['text'] == (source/'manual.md').read_text()
    assert second['text'] == 'Second λ line\n'
    assert third['next_query'] is None
    assert first['coordinate_unit'] == 'zero_based_lines'
    assert library.search(query='nonexistent', offset=0, limit=1)['entries'] == []


def test_frozen_run_keeps_instructions_when_source_changes_and_detects_corruption(tmp_path):
    source = _source(tmp_path)
    library = ToolKnowledge.freeze(tmp_path/'saved', source=source)
    expected = library.read(entry_id='fixture-manual', section_id='launch', offset=0, limit=10)
    (source/'manual.md').write_text('Changed instructions\n')
    resumed = ToolKnowledge.freeze(tmp_path/'saved', source=source)
    assert resumed.read(entry_id='fixture-manual', section_id='launch', offset=0, limit=10) == expected
    other = ToolKnowledge.freeze(tmp_path/'later-run', source=source)
    assert other.context()['library_id'] != library.context()['library_id']
    saved = next((tmp_path/'saved').glob('*.md'))
    saved.write_text('Corrupted snapshot\n')
    failed = resumed.execute('knowledge.read', {'entry_id': 'fixture-manual',
        'section_id': 'launch', 'offset': 0, 'limit': 10})
    assert failed['status'] == 'failed'
    assert failed['feedback']['code'] == 'knowledge_section_bytes_changed'
    assert failed['record_refs'] == []


def test_bad_request_is_specific_and_does_not_remove_other_manuals(tmp_path):
    library = ToolKnowledge.freeze(tmp_path/'saved')
    bad = library.execute('knowledge.read', {'entry_id': 'publication-access',
        'section_id': 'missing', 'offset': 0, 'limit': 1})
    assert bad['feedback']['code'] == 'knowledge_section_unknown'
    assert library.execute('knowledge.read', {'entry_id': 'native-phmmer',
        'section_id': 'launch', 'offset': 0, 'limit': 1})['status'] == 'completed'
    assert library.execute('knowledge.search', {'query': '', 'offset': -1, 'limit': 1})['feedback']['code'] == 'knowledge_arguments_invalid'
