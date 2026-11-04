"""Instruction retrieval through the real runtime; no model or native job.

Synthetic controllers govern these fixtures only. The tests assert information
delivery, durable recovery and score/form boundaries, not scientific success.
"""
import asyncio
import json
from pathlib import Path

import pytest

from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tool_knowledge import ToolKnowledge, VERSION
from test_runtime import (FixtureController, ScriptedProvider, commission,
                          fixture_credit, obj, reason, run, setup)


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


def _action(name, args):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': args}, 'report_update': {}}


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


def test_parent_and_child_get_reads_without_scientific_credit_or_manual_prose_in_form(tmp_path):
    store, tools = setup(tmp_path)
    tools.knowledge_library_directory = _source(tmp_path)
    form = obj({'changed': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                          'x-source': 'changed_record_refs'}})
    read = _action('knowledge.read', {'entry_id': 'fixture-manual',
        'section_id': 'launch', 'offset': 0, 'limit': 1})

    def after_read(context):
        assert context['last_local_outcome']['result']['text'] == 'First line\n'
        assert context['current_credit'] == 0
        assert context['tool_knowledge']['entry_count'] == 1
        return _action('knowledge.entry', {'entry_id': 'fixture-manual'})

    provider = ScriptedProvider([commission(form, {}), read, after_read, reason(2)])
    summary = run(store, tools, provider, tmp_path/'run')
    assert summary['credit'] == 2
    assert tools.executions == 0
    reports = [json.loads(row[0]) for row in store.db.execute('SELECT form FROM runtime_report_attempts')]
    assert reports == [{'changed': []}]
    rows = store.db.execute('SELECT observation FROM runtime_observations').fetchall()
    assert sorted(json.loads(row[0])['step']['delta'] for row in rows) == [0, 0, 0, 2]
    requests = [json.loads(row[0]) for row in store.db.execute('SELECT request FROM runtime_model_calls')]
    assert all('text' not in request['context']['tool_knowledge'] for request in requests)
    assert requests[0]['context']['tools'][0]['knowledge_entry_ids'] == ['fixture-manual']


def test_interrupted_read_recovery_preserves_outcome_and_supplied_library_version(tmp_path):
    store, tools = setup(tmp_path)
    tools.knowledge_library_directory = source = _source(tmp_path)
    read = _action('knowledge.read', {'entry_id': 'fixture-manual',
        'section_id': 'launch', 'offset': 1, 'limit': 1})
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([read, KeyboardInterrupt()]), tmp_path/'run')
    before = store.db.execute('SELECT result,credit FROM runtime_actions').fetchone()
    observation = store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0]
    (source/'manual.md').write_text('Future revision\n')

    def recovered(context):
        assert context['last_local_outcome']['result']['text'] == 'Second λ line\n'
        assert context['current_credit'] == 0
        return reason(1)

    result = run(store, tools, ScriptedProvider([recovered]), None, resume=True)
    after = store.db.execute('SELECT result,credit FROM runtime_actions ORDER BY decision_index LIMIT 1').fetchone()
    assert tuple(after) == tuple(before)
    assert store.db.execute('SELECT observation FROM runtime_observations ORDER BY unit_index LIMIT 1').fetchone()[0] == observation
    assert result['credit'] == 1 and result['completed_actions'] == 2


def test_every_job_role_can_read_knowledge_without_executing_a_job(tmp_path):
    from types import SimpleNamespace
    from gene_annotation_episode.homology_episodes import HomologyEpisodes, ROLES
    store, tools = setup(tmp_path)
    binding = object.__new__(HomologyEpisodes)
    binding.roles = ROLES
    binding.recover_statistics = lambda: {}
    workflow = Workflow(store, tools, ScriptedProvider([]), tmp_path/'run', 'knowledge-fixture',
        lambda path, initial: FixtureController(str(path), initial, 2), fixture_credit,
        job_episodes=binding)
    for role in ROLES:
        source = SimpleNamespace(path=((role, 'fixture'),), scope={'subject_refs': ['subject_A']})
        catalog = workflow.catalog(source.scope, source=source)
        assert {'knowledge.search', 'knowledge.entry', 'knowledge.read'} <= {entry['name'] for entry in catalog}
        selected = next(entry for entry in catalog if entry['name'].startswith('homology.'))
        assert selected['knowledge_entry_ids'] == ['native-phmmer']
        result = asyncio.run(workflow.execute(source, 'knowledge.read',
            {'entry_id': 'native-phmmer', 'section_id': 'launch', 'offset': 0, 'limit': 1},
            decision_index=0, operation_key=role))
        assert result['status'] == 'completed'
        assert result['record_refs'] == result['changed_record_refs'] == []
    assert tools.executions == 0
    assert store.db.execute('SELECT count(*) FROM synthetic_operations').fetchone()[0] == 0


def test_bad_request_is_specific_and_does_not_remove_other_manuals(tmp_path):
    library = ToolKnowledge.freeze(tmp_path/'saved')
    bad = library.execute('knowledge.read', {'entry_id': 'publication-access',
        'section_id': 'missing', 'offset': 0, 'limit': 1})
    assert bad['feedback']['code'] == 'knowledge_section_unknown'
    assert library.execute('knowledge.read', {'entry_id': 'native-phmmer',
        'section_id': 'launch', 'offset': 0, 'limit': 1})['status'] == 'completed'
    assert library.execute('knowledge.search', {'query': '', 'offset': -1, 'limit': 1})['feedback']['code'] == 'knowledge_arguments_invalid'
