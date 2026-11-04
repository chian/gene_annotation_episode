"""Independent launch-library contract checks; no execution or inference.

These exercise immutable instruction identity and actual operation-name metadata.
They do not establish current resource availability or intelligent launch choices.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.launch_instructions import (
    LaunchInstructions, SELECTION_SCHEMA, catalog, validate_selection,
)
from gene_annotation_episode.practical_resource_episodes import operation_catalog
from gene_annotation_episode.homology_episodes import HomologyEpisodes, ROLES as HOMOLOGY_ROLES
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.api_execution import HMMERAPIExecution


def _source(tmp_path):
    directory = tmp_path / 'launch-source'
    directory.mkdir()
    bodies = {
        'prepare.md': 'Prepare first\nUnicode λ is preserved\nLast preparation line\n',
        'results.md': 'Read the requested output\nPreserve the original request\n',
        'service.md': 'A different service instruction\n',
    }
    for name, body in bodies.items():
        (directory / name).write_text(body, encoding='utf-8')
    entries = [
        {'entry_id': 'fixture-local', 'title': 'Fixture local execution',
         'summary': 'Local preparation and result receipt', 'tags': ['fixture', 'launch'],
         'resource_kinds': ['local'], 'tool_names': ['practical.job.start'],
         'provenance': ['synthetic_test_fixture'],
         'sections': [
             {'section_id': 'prepare', 'title': 'Preparation', 'path': 'prepare.md'},
             {'section_id': 'results', 'title': 'Results', 'path': 'results.md'}]},
        {'entry_id': 'fixture-api', 'title': 'Fixture service instructions',
         'summary': 'API service execution', 'tags': ['fixture'],
         'resource_kinds': ['api'], 'tool_names': ['api.hmmer.result'],
         'provenance': ['synthetic_test_fixture'],
         'sections': [{'section_id': 'service', 'title': 'Service', 'path': 'service.md'}]},
    ]
    (directory / 'index.json').write_text(json.dumps({
        'version': 'tool_knowledge_v1', 'entries': entries}), encoding='utf-8')
    return directory


def _library(tmp_path):
    source = _source(tmp_path)
    return LaunchInstructions.freeze(tmp_path / 'frozen-launch', source=source), source


def _selection(library):
    return library.select([
        {'entry_id': 'fixture-local', 'section_id': 'prepare'},
        {'entry_id': 'fixture-api', 'section_id': 'service'},
        {'entry_id': 'fixture-local', 'section_id': 'results'},
    ])


def test_default_collection_has_resource_and_service_entries_with_real_operations(tmp_path):
    library = LaunchInstructions.freeze(tmp_path / 'launch-instructions')
    rows = library.search(query='', offset=0, limit=10)['entries']
    assert {row['entry_id'] for row in rows} == {
        'launch-aurora', 'launch-local', 'launch-api',
        'launch-api-uniprot', 'launch-api-bvbrc', 'launch-api-blast'}
    expected_kinds = {'launch-aurora': ['hpc'], 'launch-local': ['local'],
                      'launch-api': ['api'], 'launch-api-uniprot': ['api'],
                      'launch-api-bvbrc': ['api'], 'launch-api-blast': ['api']}
    with Store(tmp_path / 'catalog-state') as store:
        tools = ToolRegistry(store)
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        api = HMMERAPIExecution(store, run_id='catalog-inspection', directory=tmp_path,
            configuration={'ebi': {'kind': 'hmmer_api'}}, tool_registry=tools,
            handoff_unit=1, acquired_record_unit=1)
        assignment = {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
            'service': 'ebi_hmmer', 'subject_ref': target, 'algorithm': 'phmmer',
            'database': 'swissprot', 'parameters': {}, 'page_size': 10,
            'endpoint': 'usable_handoff', 'constraints': {}}
        context = SimpleNamespace(run_id='catalog-inspection', role='launch_api',
            assignment=assignment, scope={'subject_refs': [target]})
        api_tools = {row['name'] for row in api.catalog(context)}
        # Results catalog needs a qualified actual handoff. Its single bounded
        # operation is checked through the same catalog implementation, with
        # assignment qualification isolated from this metadata-only check.
        original = api._assignment
        api._assignment = lambda context: assignment
        api_tools |= {row['name'] for row in api.catalog(SimpleNamespace(role='results'))}
        api._assignment = original
        from gene_annotation_episode.api_services import build_service
        service_catalogs = {}
        for service, entry_id, request in (
                ('uniprot', 'launch-api-uniprot', {'operation': 'record', 'accession': 'P0AAW1'}),
                ('bvbrc_data', 'launch-api-bvbrc', {'collection': 'genome_feature',
                    'filters': [{'field': 'gene', 'operator': 'eq', 'value': 'ybhP'}]}),
                ('ncbi_blast', 'launch-api-blast', {'subject_ref': target,
                    'program': 'blastp', 'database': 'swissprot'})):
            provider = build_service(service, {'kind': 'api', 'service': service}, tools)
            service_catalogs[entry_id] = {item['name'] for item in
                [*provider.capabilities(), *provider.result_catalog(request, {})]}
    homology = object.__new__(HomologyEpisodes)
    homology_tools = {row['name'] for role in HOMOLOGY_ROLES
        for row in homology.catalog(SimpleNamespace(path=((role, 'catalog-inspection'),)))}
    bound_catalogs = {
        'launch-aurora': {row['name'] for row in operation_catalog('hpc')},
        'launch-local': {row['name'] for row in operation_catalog('local')} | homology_tools,
        'launch-api': api_tools,
        **service_catalogs,
    }
    for row in rows:
        assert row['resource_kinds'] == expected_kinds[row['entry_id']]
        assert row['tool_names']
        assert set(row['tool_names']) <= bound_catalogs[row['entry_id']]
        assert row['provenance']
        entry = library.entry(row['entry_id'])['entry']
        assert entry['sections']
        if row['entry_id'] == 'launch-local':
            assert 'homology' in {section['section_id'] for section in entry['sections']}
            assert homology_tools <= set(row['tool_names'])
        for section in entry['sections']:
            read = library.read(entry_id=row['entry_id'], section_id=section['section_id'],
                                offset=0, limit=max(1, section['lines']))
            assert read['text'].strip()
            assert hashlib.sha256(read['text'].encode()).hexdigest() == section['sha256']
    for kind, entry_id in [('hpc', 'launch-aurora'), ('local', 'launch-local'), ('api', 'launch-api')]:
        matches = library.search(query='', offset=0, limit=10, resource_kind=kind)
        assert {row['entry_id'] for row in matches['entries']} == {
            key for key, values in expected_kinds.items() if kind in values}


def test_discovery_and_section_metadata_never_load_instruction_bodies(tmp_path, monkeypatch):
    library, source = _library(tmp_path)
    original = Path.open

    def reject_instruction_body(path, *args, **kwargs):
        if path.suffix == '.md':
            raise AssertionError('Metadata discovery read a launch instruction body')
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', reject_instruction_body)
        metadata = library.context()
        found = library.search(query='FIXTURE', offset=0, limit=1)
        next_page = library.search(**found['next_query'])
        entry = library.entry('fixture-local')
    assert metadata['library_id'].startswith('launch_instructions_')
    assert metadata['version'] == 'launch_instruction_library_v1'
    assert metadata['entry_count'] == 2
    assert found['total'] == 2
    assert len(found['entries']) == len(next_page['entries']) == 1
    assert next_page['next_query'] is None
    assert 'sections' not in found['entries'][0]
    assert all('path' not in section for section in entry['entry']['sections'])
    combined = json.dumps([metadata, found, next_page, entry])
    assert 'Unicode λ is preserved' not in combined
    assert str(source) not in combined


def test_multiple_entries_and_sections_materialize_exact_ordered_frozen_bytes(tmp_path):
    library, source = _library(tmp_path)
    selection = _selection(library)
    assert validate_selection(selection) == selection
    assert Draft202012Validator(SELECTION_SCHEMA).is_valid(selection)
    selected = library.materialize(selection)
    assert selected['selection'] == selection
    assert [(row['entry_id'], row['section_id']) for row in selected['sections']] == [
        ('fixture-local', 'prepare'), ('fixture-api', 'service'), ('fixture-local', 'results')]
    assert [row['text'] for row in selected['sections']] == [
        (source / name).read_text() for name in ['prepare.md', 'service.md', 'results.md']]
    for identity, body in zip(selection['sections'], selected['sections']):
        assert body['section_sha256'] == identity['sha256']
        assert body['offset'] == 0 and body['next_query'] is None
        assert body['returned_lines'] == body['total_lines']
    first = library.read(entry_id='fixture-local', section_id='prepare', offset=0, limit=1)
    second = library.read(**first['next_query'])
    third = library.read(**second['next_query'])
    assert first['text'] + second['text'] + third['text'] == selected['sections'][0]['text']
    assert third['next_query'] is None


def test_pinned_instruction_text_keeps_original_unicode_and_line_endings(tmp_path):
    source = _source(tmp_path)
    original = 'First λ line\r\nSecond line\r\nNo final newline'.encode('utf-8')
    (source / 'prepare.md').write_bytes(original)
    library = LaunchInstructions.freeze(tmp_path / 'frozen-launch', source=source)
    selection = library.select([{'entry_id': 'fixture-local', 'section_id': 'prepare'}])
    supplied = library.materialize(selection)['sections'][0]
    assert supplied['text'].encode('utf-8') == original
    assert supplied['section_sha256'] == hashlib.sha256(original).hexdigest()
    first = library.read(entry_id='fixture-local', section_id='prepare', offset=0, limit=1)
    assert first['text'] == 'First λ line\r\n'


def test_reopen_keeps_selected_text_while_future_source_edits_change_new_runs(tmp_path):
    library, source = _library(tmp_path)
    selection = _selection(library)
    expected = library.materialize(selection)
    (source / 'prepare.md').write_text('Changed future instructions\n')
    reopened = LaunchInstructions(tmp_path / 'frozen-launch')
    refrozen = LaunchInstructions.freeze(tmp_path / 'frozen-launch', source=source)
    assert reopened.materialize(selection) == expected
    assert refrozen.materialize(selection) == expected
    future = LaunchInstructions.freeze(tmp_path / 'future-launch', source=source)
    assert future.context()['library_id'] != library.context()['library_id']
    with pytest.raises(ValueError, match='launch_instruction_selection_library_mismatch'):
        future.materialize(selection)


def test_corrupted_frozen_bytes_are_rejected_in_reads_and_selected_delivery(tmp_path):
    library, _ = _library(tmp_path)
    selection = _selection(library)
    manifest = json.loads((tmp_path / 'frozen-launch' / 'index.json').read_text())
    entry = next(entry for entry in manifest['entries'] if entry['entry_id'] == 'fixture-local')
    section = next(section for section in entry['sections'] if section['section_id'] == 'prepare')
    (tmp_path / 'frozen-launch' / section['path']).write_text('Changed snapshot bytes\n')
    with pytest.raises(ValueError, match='launch_instruction_section_bytes_changed'):
        library.materialize(selection)
    failed = library.execute('launch.instructions.read', {
        'entry_id': 'fixture-local', 'section_id': 'prepare', 'offset': 0, 'limit': 1})
    assert failed['status'] == 'failed'
    assert failed['feedback']['code'] == 'launch_instruction_section_bytes_changed'
    assert failed['record_refs'] == failed['changed_record_refs'] == []
    # One damaged section does not change a different section's immutable bytes.
    assert library.read(entry_id='fixture-api', section_id='service', offset=0, limit=1)['text'] == (
        'A different service instruction\n')


@pytest.mark.parametrize('mutation', [
    lambda selected: selected.update({'version': 'some_other_version'}),
    lambda selected: selected.update({'library_id': ''}),
    lambda selected: selected.update({'sections': []}),
    lambda selected: selected.update({'instructions': 'arbitrary replacement prose'}),
    lambda selected: selected['sections'][0].update({'sha256': 'A' * 64}),
    lambda selected: selected['sections'][0].update({'sha256': 'a' * 63}),
    lambda selected: selected['sections'][0].update({'text': 'arbitrary replacement prose'}),
    lambda selected: selected['sections'][0].update({'entry_id': ''}),
    lambda selected: selected['sections'].append(deepcopy(selected['sections'][0])),
])
def test_selection_schema_and_pure_validator_reject_unconstrained_or_malformed_values(tmp_path, mutation):
    library, _ = _library(tmp_path)
    selection = _selection(library)
    mutation(selection)
    with pytest.raises(ValueError, match='launch_instruction_selection_'):
        validate_selection(selection)
    # Duplicates are a semantic constraint in addition to the JSON schema.
    if selection['sections'] and selection['sections'][-1] == selection['sections'][0] and len(selection['sections']) > 3:
        return
    assert not Draft202012Validator(SELECTION_SCHEMA).is_valid(selection)


def test_null_selection_remains_valid_without_manufacturing_instruction_text():
    assert validate_selection(None) is None
    assert Draft202012Validator(SELECTION_SCHEMA).is_valid(None)


def test_valid_shaped_references_require_actual_library_sections_and_hashes(tmp_path):
    library, _ = _library(tmp_path)
    selection = _selection(library)
    wrong_library = deepcopy(selection)
    wrong_library['library_id'] = 'launch_instructions_' + '0' * 64
    with pytest.raises(ValueError, match='launch_instruction_selection_library_mismatch'):
        library.materialize(wrong_library)
    wrong_hash = deepcopy(selection)
    wrong_hash['sections'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='launch_instruction_selection_digest_mismatch'):
        library.materialize(wrong_hash)
    unknown_entry = deepcopy(selection)
    unknown_entry['sections'][0]['entry_id'] = 'missing-entry'
    with pytest.raises(ValueError, match='launch_instruction_.*unknown'):
        library.materialize(unknown_entry)
    unknown_section = deepcopy(selection)
    unknown_section['sections'][0]['section_id'] = 'missing-section'
    with pytest.raises(ValueError, match='launch_instruction_.*unknown'):
        library.materialize(unknown_section)


def test_select_tool_preserves_zero_contribution_envelope_and_validates_its_request(tmp_path):
    library, _ = _library(tmp_path)
    definitions = {entry['name']: entry for entry in catalog()}
    assert set(definitions) == {'launch.instructions.search', 'launch.instructions.entry',
                                'launch.instructions.read', 'launch.instructions.select'}
    pairs = [{'entry_id': 'fixture-local', 'section_id': 'prepare'}]
    selected = library.execute('launch.instructions.select', {'sections': pairs})
    assert selected['status'] == 'completed'
    assert selected['result'] == library.select(pairs)
    assert selected['record_refs'] == selected['changed_record_refs'] == []
    invalid_requests = [
        ('launch.instructions.select', {'sections': []}),
        ('launch.instructions.select', {'sections': pairs + pairs}),
        ('launch.instructions.select', {'sections': [{'entry_id': 'fixture-local', 'section_id': 'absent'}]}),
        ('launch.instructions.search', {'query': '', 'offset': -1, 'limit': 1}),
        ('launch.instructions.search', {'query': '', 'offset': 0, 'limit': 1, 'resource_kind': 'guessed-machine'}),
        ('launch.instructions.read', {'entry_id': 'fixture-local', 'section_id': 'prepare',
                                      'offset': 0, 'limit': 1, 'argv': ['invented-execution']}),
        ('launch.instructions.not-a-tool', {}),
    ]
    for name, arguments in invalid_requests:
        failed = library.execute(name, arguments)
        assert failed['status'] == 'failed'
        assert failed['result'] is None
        assert failed['feedback']['code'].startswith('launch_instruction_')
        assert failed['record_refs'] == failed['changed_record_refs'] == []


@pytest.mark.parametrize('duplicate_kind', ['entry', 'section'])
def test_source_identity_collisions_fail_before_creating_ambiguous_snapshot(tmp_path, duplicate_kind):
    source = _source(tmp_path)
    index = json.loads((source / 'index.json').read_text())
    if duplicate_kind == 'entry':
        index['entries'].append(deepcopy(index['entries'][0]))
    else:
        index['entries'][0]['sections'].append(deepcopy(index['entries'][0]['sections'][0]))
    (source / 'index.json').write_text(json.dumps(index))
    with pytest.raises(ValueError, match='duplicate'):
        LaunchInstructions.freeze(tmp_path / 'frozen-launch', source=source)
    assert not (tmp_path / 'frozen-launch' / 'index.json').exists()
