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
    assert requests[0]['context']['tools'] == []
    child_tool = next(entry for entry in requests[1]['context']['tools']
                      if entry['name'] == 'fixture.measure')
    assert child_tool['knowledge_entry_ids'] == ['fixture-manual']


def test_interrupted_read_recovery_preserves_outcome_and_supplied_library_version(tmp_path, monkeypatch):
    store, tools = setup(tmp_path)
    tools.knowledge_library_directory = source = _source(tmp_path)
    form = obj({'changed': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                          'x-source': 'changed_record_refs'}})
    read = _action('knowledge.read', {'entry_id': 'fixture-manual',
        'section_id': 'launch', 'offset': 1, 'limit': 1})
    interrupted = ScriptedProvider([commission(form, {}), read, KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, interrupted, tmp_path/'run')
    assert interrupted.contexts[0]['tools'] == []
    child = store.db.execute('SELECT episode_id,path FROM runtime_episodes '
        'WHERE json_array_length(path)=2').fetchone()
    child_id = child['episode_id']
    assert json.loads(child['path'])[-1] == ['improvement', 'child_0']
    library_directory = tmp_path/'run/tool-knowledge'

    def original_read_snapshot():
        return {
            'action': dict(store.db.execute('SELECT * FROM runtime_actions '
                'WHERE episode_id=? AND decision_index=0', (child_id,)).fetchone()),
            'observation': dict(store.db.execute('SELECT * FROM runtime_observations '
                'WHERE episode_id=? AND unit_index=0', (child_id,)).fetchone()),
            'model_call': dict(store.db.execute('SELECT * FROM runtime_model_calls '
                'WHERE episode_id=? AND call_index=0', (child_id,)).fetchone()),
            'identities': [dict(row) for row in store.db.execute(
                'SELECT episode_id,path,request,initial_credit FROM runtime_episodes ORDER BY episode_id')],
            'frozen_bytes': {path.name: path.read_bytes().hex()
                             for path in library_directory.iterdir() if path.is_file()},
        }

    before = original_read_snapshot()
    (tmp_path/'recovery_before.json').write_text(json.dumps(before, indent=2) + '\n')
    assert json.loads(before['action']['action']) == read['selection']
    outcome = json.loads(before['action']['result'])
    assert outcome['status'] == 'completed' and before['action']['credit'] == 0
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert outcome['result']['text'] == 'Second λ line\n'
    assert outcome['result']['version'] == VERSION
    manifest = json.loads(bytes.fromhex(before['frozen_bytes']['index.json']))
    section = manifest['entries'][0]['sections'][0]
    assert outcome['result']['library_id'] == manifest['library_id']
    assert outcome['result']['section_sha256'] == section['sha256']
    assert bytes.fromhex(before['frozen_bytes'][section['path']]) == (source/'manual.md').read_bytes()
    assert json.loads(before['observation']['observation'])['step']['delta'] == 0
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
    assert store.db.execute('SELECT count(*) FROM synthetic_operations').fetchone()[0] == 0
    pending = store.db.execute('SELECT request FROM runtime_model_calls '
        'WHERE episode_id=? AND response IS NULL', (child_id,)).fetchone()
    pending_context = json.loads(pending['request'])['context']
    assert pending_context == interrupted.contexts[-1]
    (source/'manual.md').write_text('Future revision\n')

    def replacement_read_forbidden(*args, **kwargs):
        raise AssertionError('Recovery must reuse the completed child-owned read')

    monkeypatch.setattr(ToolKnowledge, 'read', replacement_read_forbidden)

    def recovered(context):
        assert context == pending_context
        assert context['last_local_outcome']['result']['text'] == 'Second λ line\n'
        assert context['last_local_outcome'] == outcome
        assert context['current_credit'] == 0
        return _action('knowledge.entry', {'entry_id': 'fixture-manual'})

    def parent_after_child(context):
        assert context['tools'] == []
        assert context['child_reports'] == [{'changed': []}]
        assert context['current_credit'] == 0
        return reason(1)

    resumed = ScriptedProvider([recovered, parent_after_child])
    result = run(store, tools, resumed, None, resume=True)
    after = original_read_snapshot()
    (tmp_path/'recovery_after.json').write_text(json.dumps(after, indent=2) + '\n')
    assert after == before
    assert (source/'manual.md').read_text() == 'Future revision\n'
    assert len(resumed.contexts) == 2 and tools.executions == 0
    read_actions = [dict(row) for row in store.db.execute('SELECT * FROM runtime_actions '
        "WHERE json_extract(action,'$.tool')='knowledge.read'")]
    assert read_actions == [before['action']]
    observations = [dict(row) for row in store.db.execute(
        'SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    assert len(observations) == 4
    assert sum(row['episode_id'] == child_id for row in observations) == 2
    assert sorted(json.loads(row['observation'])['step']['delta'] for row in observations) == [0, 0, 0, 1]
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
