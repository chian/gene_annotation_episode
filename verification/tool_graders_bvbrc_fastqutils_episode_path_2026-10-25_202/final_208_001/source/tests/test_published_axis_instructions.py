"""Instruction-only publication contracts; fixtures are not scientific findings."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import (
    INSTRUCTIONS, TEXT_INSTRUCTIONS, apply_state_frame, instructional_model_context,
    model_snapshot, state_frame)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import reopen_scientific_binding
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.evidence_axis_instructions import (
    VERSION, instruction_view, validate_instruction_entry)
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import (
    ScientificProcessLibrary, instruction_entry)
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


PUBLICATIONS = Path(__file__).resolve().parents[1] / 'research/slotted_process_library/publications'
SOURCE_ROW = {'case_group': 'synthetic_instruction_fixture', 'case_id': 'synthetic_case',
    'source_url': 'https://example.org/synthetic-instruction', 'source_locator': 'Synthetic fixture',
    'observation': 'Invented instruction provenance for an engineering check.',
    'limit': 'Not a scientific finding or a scoring sheet.'}
ENTRY = {'entry_version': VERSION, 'id': 'A101', 'slot': 'evidence_axis',
    'name': 'Synthetic investigation instructions',
    'description': 'Exercise supplied-material instruction delivery without scientific conclusions.',
    'investigation_instructions': 'Start from the supplied sequence, selected file contents or snippets. '
        'Retain their boundaries and completeness. Examine the recorded measurements and controls; '
        'possible functions may emerge from this investigation. Missing measurements remain unknown.',
    'evidence': [SOURCE_ROW]}
VIEW_FIELDS = {'id', 'name', 'instruction_status', 'investigation_instructions'}


def write_source(directory, *, axes=None):
    """An ephemeral engineering catalog, with the unchanged published P01 body."""
    directory.mkdir(parents=True)
    (directory / 'entries').mkdir()
    thought_bytes = (PUBLICATIONS / '2026-10-21-001/entries/P01.json').read_bytes()
    thought = json.loads(thought_bytes)
    axes = [deepcopy(ENTRY)] if axes is None else deepcopy(axes)
    headers, rows = [], []
    for body in [*axes, thought]:
        path = 'entries/' + body['id'] + '.json'
        raw = thought_bytes if body['id'] == 'P01' else (json.dumps(body, indent=2) + '\n').encode()
        (directory / path).write_bytes(raw)
        refs = [f"E-{body['id']}-{index:04d}" for index in range(len(body['evidence']))]
        headers.append({key: body[key] for key in ('id', 'slot', 'name', 'description')} | {
            'detail_path': path, 'source_evidence_ids': refs})
        rows.extend({'evidence_id': reference, 'option_id': body['id'], **evidence}
                    for reference, evidence in zip(refs, body['evidence']))
    slots = ('evidence_axis', 'thought_pattern')
    index = {'format': 'research_three_slot_options_v1', 'status': 'Synthetic engineering catalog',
        'slots': [{'slot': slot, 'catalog': slot + '.json',
                   'count': sum(header['slot'] == slot for header in headers)} for slot in slots],
        'entries': headers}
    (directory / 'index.json').write_text(json.dumps(index))
    (directory / 'option_sources.json').write_text(json.dumps({
        'meaning': 'Synthetic instruction provenance only; not target evidence.', 'rows': rows}))
    return directory


@pytest.fixture
def frozen(tmp_path):
    source = write_source(tmp_path / 'synthetic-source')
    library = ScientificProcessLibrary.freeze(tmp_path / 'run/scientific-process-library', source=source)
    return source, library


def test_closed_instruction_record_detaches_provenance_and_projects_only_task():
    entry = validate_instruction_entry(ENTRY)
    assert entry == ENTRY and entry is not ENTRY
    entry['evidence'][0]['observation'] = 'Changed detached copy'
    assert entry != ENTRY
    view = instruction_view(ENTRY)
    assert set(view) == VIEW_FIELDS
    assert view['instruction_status'] == 'published_investigation_instructions'
    assert view['investigation_instructions'] == ENTRY['investigation_instructions']
    assert instruction_entry(ENTRY) == view
    assert 'synthetic_instruction_fixture' not in json.dumps(view)


@pytest.mark.parametrize('change', [
    {'entry_version': 'evidence_axis_entry_v1'}, {'slot': 'annotation_distinction'},
    {'id': 'A101\n'}, {'name': ' '}, {'description': ''}, {'investigation_instructions': []},
    {'investigation_instructions': '\n\t'}, {'evidence': []}, {'evidence': [SOURCE_ROW | {'score': 1}]},
    {'evidence': [SOURCE_ROW | {'limit': ''}]}, {'scoring_rubric': {}}, {'grade_scores': {}},
    {'reader_bindings': {}}, {'extra': float('nan')},
])
def test_instruction_record_rejects_malformed_text_and_noninstruction_fields(change):
    with pytest.raises(ValueError, match='evidence_axis_instruction_invalid'):
        validate_instruction_entry(deepcopy(ENTRY) | change)


def test_freeze_lookup_sources_and_reopen_preserve_original_instruction_bytes(frozen):
    source, library = frozen
    original = (source / 'entries/A101.json').read_bytes()
    reference = library.reference('A101')
    descriptor = library.as_record()
    outcome = library.execute('process.entry', {'option_id': 'A101'})
    assert outcome['status'] == 'completed'
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert outcome['result']['entry'] == instruction_view(ENTRY)
    assert library.resolve(reference) == ENTRY
    rows = library.sources(option_ref=reference, offset=0, limit=5)['rows']
    assert rows == [{'evidence_id': 'E-A101-0000', 'option_id': 'A101', **SOURCE_ROW}]
    assert library.search(slot='evidence_axis', query='supplied-material', offset=0, limit=5)[
        'entries'][0]['option_ref'] == reference
    (source / 'entries/A101.json').write_text('{}')
    shutil.rmtree(source)
    reopened = ScientificProcessLibrary.freeze(library.directory, source=source)
    assert reopened.as_record() == descriptor
    assert reopened.resolve(reference) == ENTRY
    assert (library.directory / 'entries/A101.json').read_bytes() == original
    assert reopened.entry('P01')['entry'] == json.loads(
        (PUBLICATIONS / '2026-10-21-001/entries/P01.json').read_bytes())


def test_publication_source_rows_must_match_retained_entry_provenance(tmp_path):
    source = write_source(tmp_path / 'synthetic-source')
    path = source / 'option_sources.json'
    table = json.loads(path.read_text())
    table['rows'][0]['observation'] = 'A different instruction source assertion'
    path.write_text(json.dumps(table))
    with pytest.raises(ValueError, match='scientific_process_source_entry_mismatch'):
        ScientificProcessLibrary.freeze(tmp_path / 'invalid', source=source)


@pytest.mark.parametrize('relative', ['entries/A101.json', 'sources/A101.json'])
def test_snapshot_byte_changes_reject_lookup_and_reconstruction(frozen, relative):
    _, library = frozen
    path = library.directory / relative
    path.write_bytes(path.read_bytes() + b'\n')
    assert library.execute('process.entry', {'option_id': 'A101'})['status'] == 'failed'
    with pytest.raises(ValueError, match='scientific_process_(entry|sources)_changed'):
        ScientificProcessLibrary(library.directory)


def child_context(binding, target, *, axis='A101'):
    scope = {'subject_refs': [target]}
    schema = obj({'status': {'type': 'string', 'enum': ['unresolved', 'qualified']}})
    invocation = {'objective': 'Investigate the supplied protein sequence',
        'purpose': 'Return the constrained state of this investigation',
        'report_schema': schema, 'initial_report': {'status': 'unresolved'}}
    assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': binding.library.reference(axis),
        'thought_pattern': binding.library.reference('P01'),
        'child_tool_info': [{'name': 'sequence.inspect', 'resources': 'local'}]},
        'evidence_refs': [target], 'constraints': {'preserve_sequence_boundaries': True},
        'context': {'supplied_sequence': 'MACDEFGH', 'completeness': 'complete'}}
    prepared = binding.prepare_invocation(SimpleNamespace(role='annotation'), 'scientific_process',
        assignment, scope, 'synthetic-commission', invocation=invocation)
    path = (('annotation', 'root'), ('scientific_process', 'selected'))
    request = {'goal': {'objective': invocation['objective']},
        'report_contract': {'decision': invocation['purpose'], 'measurements': {'schema': schema}},
        'message': {'scope': scope, 'initial_report': invocation['initial_report'],
            'episode_assignment': prepared['assignment'], 'scientific_process': prepared['scientific_process'],
            'scientific_invocation_ref': scientific_invocation_ref('synthetic-run', path)}}
    return BindingContext('synthetic-run', 'synthetic-child', 'scientific_process', path,
                          scope, prepared['assignment'], request), assignment


def test_child_uses_published_task_actual_tool_and_original_form_after_reconstruction(frozen, tmp_path):
    source, library = frozen
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        tools = ToolRegistry(store)
        tool_library = ScientificToolLibrary.freeze(library.directory.parent / 'scientific-tool-library',
            catalog=tools.catalog(), tool_info=True)
        services = WorkflowServices(SimpleNamespace(store=store, tools=tools, run_id='synthetic-run'))
        def forbidden_routes(*args, **kwargs):
            pytest.fail('Instruction-only entries declare no scoring-route dispatch')
        services.scientific_support_routes = forbidden_routes
        binding = ScientificProcessEpisodes(services, library=library, tool_library=tool_library,
            child_roles=('scientific_process',))
        child, supplied = child_context(binding, target)
        original = plain(child.request)
        assert binding.replaces_default_instructions
        frame = binding.decision_context(child, {})['scientific_process']
        assert frame['evidence_axis'] == instruction_view(ENTRY)
        assert 'annotation_support_routes' not in frame and 'axis_judgment_contract' not in frame
        assert frame['assignment']['context'] == supplied['context']
        assert frame['assignment']['constraints'] == supplied['constraints']
        assert frame['assignment']['evidence_refs'] == [target]
        assert frame['thought_pattern']['decision_guidance']
        info, = frame['child_tool_info']
        assert set(info) == {'name', 'description', 'resources', 'instructions'}
        assert info['description'] == tools.catalog()['sequence.inspect']['description']
        assert info == tool_library.resolve_tool_info(supplied['selection']['child_tool_info'])[0]
        assert [row['name'] for row in binding.catalog(child)] == ['sequence.inspect', 'process.revise']
        instructions = binding.instructions(child)
        assert 'No initial candidate annotation or publicly searchable name is required' in instructions
        assert 'annotation_support_routes' not in instructions and 'scoring' not in instructions
        outcome = asyncio.run(binding.execute(child, 'sequence.inspect', {'subject_ref': target},
                                             'synthetic-selected-inspection'))
        assert outcome['status'] == 'completed' and outcome['result']['length'] == 8
        assert store.count('annotation') == 0
        binding.validate_report(child, {'status': 'qualified'}, original['report_contract']['measurements']['schema'])
        descriptor = binding.as_record()
        shutil.rmtree(source)
        reopened = reopen_scientific_binding(services, descriptor=descriptor, directory=library.directory.parent)
        reopened.validate_context(child)
        assert reopened.replaces_default_instructions
        assert reopened.decision_context(child, {})['scientific_process'] == frame
        assert reopened.instructions(child) == instructions
        assert plain(child.request) == original


def test_legacy_and_mixed_publications_keep_default_instruction_composition(tmp_path):
    historical = json.loads((PUBLICATIONS / '2026-10-23-002/entries/A105.json').read_bytes())
    for label, axes in [('legacy', [historical]), ('mixed', [ENTRY, historical]), ('no-axes', [])]:
        source = write_source(tmp_path / label / 'source', axes=axes)
        library = ScientificProcessLibrary.freeze(tmp_path / label / 'library', source=source)
        tools = ScientificToolLibrary.freeze(tmp_path / label / 'tools', catalog=[], tool_info=True)
        binding = ScientificProcessEpisodes(None, library=library, tool_library=tools,
            child_roles=('scientific_process',))
        assert not binding.replaces_default_instructions
        if axes:
            assert library.resolve(library.reference('A105')) == historical
            assert library.entry('A105')['entry']['instruction_status'] == 'limited_existing_measurement_guidance'


def test_raw_lookup_and_restored_records_project_without_mutating_frames_or_parent_form():
    schema = obj({'status': {'type': 'string', 'enum': ['unknown']}})
    raw = {'scientific_process': {'evidence_axis': deepcopy(ENTRY)},
        'last_outcome': {'result': {'entry': deepcopy(ENTRY)}}, 'requested_form': schema,
        'controller': {'scores': [2, 3], 'estimate': {'next_gain': .5}}}
    original = deepcopy(raw)
    snapshot = model_snapshot(raw, {'rows': []})
    assert snapshot['scientific_process']['evidence_axis'] == instruction_view(ENTRY)
    assert snapshot['last_outcome']['result']['entry'] == instruction_view(ENTRY)
    frame = state_frame(snapshot)
    frame['restored_public_exchanges'] = [{'lookup_result': {'entry': deepcopy(ENTRY)}}]
    frame['restored_pending_decision_index'] = 1
    presented = instructional_model_context(frame)
    assert presented['restored_public_exchanges'][0]['lookup_result']['entry'] == instruction_view(ENTRY)
    assert apply_state_frame(None, presented) == snapshot
    next_state = {**snapshot, 'controller': {'estimate': {'next_gain': .25}}}
    assert apply_state_frame(snapshot, state_frame(next_state, snapshot)) == next_state
    assert snapshot['requested_form'] == schema and raw == original
    assert 'decision_bootstrap supplies' in INSTRUCTIONS
    assert 'decision_bootstrap' not in TEXT_INSTRUCTIONS and 'base_revision' not in TEXT_INSTRUCTIONS
    assert 'request_context' in TEXT_INSTRUCTIONS and 'select_action' in TEXT_INSTRUCTIONS
    assert 'OWN completed action categories' in TEXT_INSTRUCTIONS
