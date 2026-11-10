"""Launch-specific pins use the shared document backend without executing work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.launch_instructions import (
    LaunchInstructions, retain_inherited_selection, validate_selection,
)


def source_library(tmp_path):
    source = tmp_path/'source'
    source.mkdir()
    entries = []
    for name, kind in [('aurora', 'hpc'), ('local', 'local'), ('api', 'api')]:
        sections = []
        for section in ('setup', 'results'):
            path = name + '-' + section + '.md'
            (source/path).write_text(name + ' ' + section + '\nExact λ bytes\n', encoding='utf-8')
            sections.append({'section_id': section, 'title': section, 'path': path})
        entries.append({'entry_id': name, 'title': name, 'summary': 'Launch instructions',
            'tags': ['execution'], 'tool_names': [], 'provenance': ['test_fixture'],
            'resource_kinds': [kind], 'sections': sections})
    (source/'index.json').write_text(json.dumps({'version': 'tool_knowledge_v1', 'entries': entries}))
    return source


def test_separate_metadata_search_has_exact_kind_filter_and_never_opens_bodies(tmp_path, monkeypatch):
    source = source_library(tmp_path)
    library = LaunchInstructions.freeze(tmp_path/'frozen', source=source)
    original = Path.open

    def no_body(path, *args, **kwargs):
        assert path.suffix != '.md', 'metadata retrieval opened an instruction body'
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', no_body)
        page = library.search(query='', offset=0, limit=1)
        assert page['entries'][0]['entry_id'] == 'api'
        assert library.search(**page['next_query'])['entries'][0]['entry_id'] == 'aurora'
        hpc = library.search(query='execution', offset=0, limit=1, resource_kind='hpc')
        assert [item['entry_id'] for item in hpc['entries']] == ['aurora']
        assert hpc['next_query'] is None
        assert library.entry('aurora')['entry']['sections'][0]['lines'] == 2


def test_selected_sections_preserve_order_exact_utf8_and_input_immutability(tmp_path):
    library = LaunchInstructions.freeze(tmp_path/'frozen', source=source_library(tmp_path))
    pairs = [{'entry_id': 'api', 'section_id': 'results'},
             {'entry_id': 'local', 'section_id': 'setup'}]
    selection = library.select(pairs)
    saved = deepcopy(selection)
    materialized = library.materialize(selection)
    assert materialized['selection'] == saved
    assert [(item['entry_id'], item['section_id']) for item in materialized['sections']] == [
        ('api', 'results'), ('local', 'setup')]
    for pin, section in zip(saved['sections'], materialized['sections']):
        assert hashlib.sha256(section['text'].encode('utf-8')).hexdigest() == pin['sha256']
        assert section['section_sha256'] == pin['sha256']
        assert section['next_query'] is None
        assert section['coordinate_unit'] == 'zero_based_lines'
    materialized['selection']['sections'].clear()
    pairs.clear()
    assert selection == saved
    assert library.materialize(None) is None


def test_per_assignment_pins_survive_source_changes_and_new_run_gets_new_version(tmp_path):
    source = source_library(tmp_path)
    library = LaunchInstructions.freeze(tmp_path/'first', source=source)
    selection = library.select([{'entry_id': 'aurora', 'section_id': 'setup'}])
    expected = library.materialize(selection)
    (source/'aurora-setup.md').write_text('Future instructions\n')
    assert LaunchInstructions.freeze(tmp_path/'first', source=source).materialize(selection) == expected
    later = LaunchInstructions.freeze(tmp_path/'second', source=source)
    assert later.context()['library_id'] != library.context()['library_id']
    with pytest.raises(ValueError, match='selection_library_mismatch'):
        later.materialize(selection)


def test_changed_frozen_bytes_fail_without_returning_partial_instructions(tmp_path):
    library = LaunchInstructions.freeze(tmp_path/'frozen', source=source_library(tmp_path))
    selection = library.select([{'entry_id': 'aurora', 'section_id': 'setup'}])
    manifest = json.loads((library.directory/'index.json').read_text())
    section = manifest['entries'][0]['sections'][0]
    (library.directory/section['path']).write_text('Changed frozen file\n')
    outcome = library.execute('launch.instructions.read', {
        'entry_id': 'aurora', 'section_id': 'setup', 'offset': 0, 'limit': 10})
    assert outcome['status'] == 'failed'
    assert outcome['feedback']['code'] == 'launch_instruction_section_bytes_changed'
    assert outcome['result'] is None
    with pytest.raises(ValueError, match='section_bytes_changed'):
        library.materialize(selection)


def test_inherited_instructions_can_be_expanded_but_cannot_be_removed_or_replaced(tmp_path):
    library = LaunchInstructions.freeze(tmp_path/'frozen', source=source_library(tmp_path))
    parent = library.select([{'entry_id': 'aurora', 'section_id': 'setup'}])
    child = library.select([{'entry_id': 'aurora', 'section_id': 'setup'},
                            {'entry_id': 'aurora', 'section_id': 'results'}])
    assert retain_inherited_selection(parent, child) == child
    assert retain_inherited_selection(None, child) == child
    assert retain_inherited_selection(None, None) is None
    for replacement in (None, {**child, 'sections': child['sections'][1:]}):
        with pytest.raises(ValueError, match='inheritance_conflict'):
            retain_inherited_selection(parent, replacement)
    altered = deepcopy(child)
    altered['sections'][0]['sha256'] = '0'*64
    with pytest.raises(ValueError, match='inheritance_conflict'):
        retain_inherited_selection(parent, altered)
    assert validate_selection(parent) == parent


@pytest.mark.parametrize('name,arguments,code', [
    ('launch.instructions.run', {}, 'launch_instruction_tool_unknown'),
    ('launch.instructions.select', {'sections': []}, 'launch_instruction_arguments_invalid'),
    ('launch.instructions.search', {'query': '', 'offset': -1, 'limit': 1},
     'launch_instruction_arguments_invalid'),
    ('launch.instructions.read', {'entry_id': 'aurora', 'section_id': 'missing', 'offset': 0, 'limit': 1},
     'launch_instruction_section_unknown'),
])
def test_failed_retrieval_has_no_scientific_or_execution_contribution(tmp_path, name, arguments, code):
    library = LaunchInstructions.freeze(tmp_path/'frozen', source=source_library(tmp_path))
    outcome = library.execute(name, arguments)
    assert outcome['status'] == 'failed'
    assert outcome['feedback']['code'] == code
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert library.execute('launch.instructions.entry', {'entry_id': 'local'})['status'] == 'completed'


def test_default_manuals_use_typed_configuration_without_session_or_note_dependencies(tmp_path, monkeypatch):
    """Exercise the real default corpus, including exact selected body pins."""
    root = Path(__file__).resolve().parents[1]
    source = root / 'gene_annotation_episode/launch_instruction_library'
    original_open = Path.open
    def no_direction_notes(path, *args, **kwargs):
        assert path.name not in {'AGENTS.md', 'AGENT.md', 'GOAL.md', 'MEMORY.md'}
        if path.suffix == '.md':
            resolved = path.resolve()
            assert resolved.is_relative_to(source) or resolved.is_relative_to(tmp_path)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', no_direction_notes)
    library = LaunchInstructions.freeze(tmp_path / 'default-launch-instructions')
    entries = library.search(query='', offset=0, limit=100)['entries']
    assert len(entries) == 7
    for entry in entries:
        assert entry['provenance']
        for value in entry['provenance']:
            if value.startswith('https://'):
                continue
            assert value.startswith('gene_annotation_episode/') and value.endswith('.py')
            assert (root / value).is_file()
    pairs = [dict(entry_id='launch-aurora', section_id=section) for section in
        ('access', 'storage', 'software', 'pbs', 'operations')]
    pairs.append(dict(entry_id='launch-local', section_id='preparation'))
    selection = library.select(pairs)
    materialized = library.materialize(selection)
    assert materialized['selection'] == selection
    assert [(row['entry_id'], row['section_id']) for row in materialized['sections']] == [
        (row['entry_id'], row['section_id']) for row in pairs]
    texts = {row['section_id']: row['text'] for row in materialized['sections']}
    for row, pin in zip(materialized['sections'], selection['sections']):
        assert row['section_sha256'] == pin['sha256'] == hashlib.sha256(row['text'].encode()).hexdigest()
        assert row['next_query'] is None
    assert all(value in texts['access'] for value in ('ssh_argv', 'python_executable', 'workspace', 'account'))
    assert all(value in texts['storage'] for value in ('configuration.account', 'constraints.account',
        'constraints.allowed_accounts', 'workspace', 'cwd', 'environment'))
    assert all(value in texts['software'] for value in ('requested_job', 'initial_context',
        'inventory_snapshot', 'progress_requirements', 'completion_keys'))
    assert all(value in texts['pbs'] for value in ('configuration.account', 'queue', 'resources', 'allowed_queues', 'allocation'))
    assert all(value in texts['preparation'] for value in ('memory_bytes', 'scratch_bytes', 'constraints'))
    for entry in entries:
        detail = library.entry(entry['entry_id'])['entry']
        for section in detail['sections']:
            body = library.read(entry_id=entry['entry_id'], section_id=section['section_id'],
                offset=0, limit=max(1, section['lines']))['text']
            for retired in ('AGENTS.md', 'MEMORY.md', 'GOAL.md', "The user's current requirements",
                    "The project's goal", 'BioReason-Aurora-Test', 'EpiCalib', '/home/chian',
                    'bastion.alcf.anl.gov', 'Gentner', '8953621.aurora'):
                assert retired not in body
    assert LaunchInstructions.freeze(library.directory).materialize(selection) == materialized
