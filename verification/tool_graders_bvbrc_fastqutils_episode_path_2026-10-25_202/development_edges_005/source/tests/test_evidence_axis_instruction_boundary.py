"""Historical sheets remain inspectable but never become investigation prompts.

These are engineering checks with real retained definitions and synthetic
assignments. They do not run a model, an experiment or an annotation workflow.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import (
    apply_state_frame, instructional_model_context, model_snapshot, state_frame)
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_scientific_process_episodes import ContractServices, INVOCATION, SCHEMA, SCOPE


PUBLICATION = Path(__file__).resolve().parents[1] / 'research/slotted_process_library/publications/2026-10-23-002'
SHEET_FIELDS = {'scoring_rubric', 'judgment_criteria', 'qualitative_grading',
                'native_measurements', 'transfer_chain', 'grade_scores', 'bands',
                'axis_judgment_contract'}


def assert_instructions(view):
    assert not SHEET_FIELDS.intersection(view)
    text = view['investigation_instructions']
    assert 'supplied' in text and 'sequence, selected file contents or snippets' in text
    assert 'An initial candidate annotation or publicly searchable name is not required' in text
    assert 'Missing information remains unknown' in text
    assert view['instruction_status'] == 'limited_existing_measurement_guidance'
    for forbidden in ('ordinal_evidence_level', 'grade_scores', 'molecular_activity_assurance',
                      'highest fully warranted nested level', 'reader bindings'):
        assert forbidden not in text


@pytest.fixture
def library(tmp_path):
    # The retained draft publication has no assembled production index. Build
    # only an ephemeral engineering catalog around its unmodified entry bytes.
    source = tmp_path / 'synthetic-library-source'
    (source / 'entries').mkdir(parents=True)
    paths = [*sorted((PUBLICATION / 'entries').glob('A*.json')),
             PUBLICATION.parent / '2026-10-21-001/entries/P01.json']
    entries, rows = [], []
    for path in paths:
        original = path.read_bytes()
        body = json.loads(original)
        relative = 'entries/' + body['id'] + '.json'
        (source / relative).write_bytes(original)
        source_ids = [f"E-{body['id']}-{index:04d}" for index in range(len(body['evidence']))]
        entries.append({key: body[key] for key in ('id', 'slot', 'name', 'description')} | {
            'detail_path': relative, 'source_evidence_ids': source_ids})
        rows.extend({'evidence_id': reference, 'option_id': body['id'], **row}
                    for reference, row in zip(source_ids, body['evidence']))
    index = {'format': 'research_three_slot_options_v1',
        'status': 'Synthetic catalog for withdrawal verification; no production publication.',
        'slots': [{'slot': slot, 'catalog': slot + '.json',
                   'count': sum(row['slot'] == slot for row in entries)}
                  for slot in ('evidence_axis', 'thought_pattern')], 'entries': entries}
    (source / 'index.json').write_text(json.dumps(index))
    (source / 'option_sources.json').write_text(json.dumps({
        'meaning': 'Retained instruction provenance in a synthetic verification catalog.', 'rows': rows}))
    return ScientificProcessLibrary.freeze(tmp_path / 'library', source=source)


def test_all_retained_axes_have_limited_measurement_guidance_without_scoring_recipes(library):
    for header in library.headers():
        if header['option_ref']['slot'] != 'evidence_axis':
            continue
        axis_id = header['option_ref']['option_id']
        original = (PUBLICATION / 'entries' / (axis_id + '.json')).read_bytes()
        before = hashlib.sha256(original).hexdigest()
        raw = library.resolve(header['option_ref'])
        assert raw == json.loads(original)
        outcome = library.execute('process.entry', {'option_id': axis_id})
        assert outcome['status'] == 'completed'
        assert outcome['record_refs'] == outcome['changed_record_refs'] == []
        view = outcome['result']['entry']
        assert_instructions(view)
        assert all(metric['name'] in view['investigation_instructions']
                   for metric in raw['native_measurements'])
        assert library.resolve(header['option_ref']) == raw
        assert hashlib.sha256((PUBLICATION / 'entries' / (axis_id + '.json')).read_bytes()).hexdigest() == before
        assert (library.directory / 'entries' / (axis_id + '.json')).read_bytes() == original
        assert library.sources(option_ref=header['option_ref'], offset=0, limit=100)['rows']


def test_scientific_measurement_limits_survive_the_instruction_projection(library):
    text = library.entry('A105')['entry']['investigation_instructions']
    assert 'Identify the actual assayed protein, preparation or organism' in text
    assert 'binding is distinct from productive chemistry, transport and native responsibility' in text
    assert 'retain bounds, approximation and uncertainty exactly as recorded' in text
    assert 'No ordinary Store metric' not in text
    assert 'JSON pointer' not in text


def test_actual_child_construction_uses_instructions_and_preserves_parent_form(library, tmp_path):
    services = ContractServices()
    services.available = []
    tools = ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=[], tool_info=True)
    binding = ScientificProcessEpisodes(services, library=library, tool_library=tools,
                                        child_roles=('scientific_process',))
    assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A105'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': []}, 'evidence_refs': [], 'constraints': {},
        'context': {'supplied_sequence': 'MACDEFGH'}}
    prepared = binding.prepare_invocation(SimpleNamespace(role='annotation'), 'scientific_process',
        assignment, SCOPE, 'synthetic-instruction-check', invocation=INVOCATION)
    path = (('annotation', 'root'), ('scientific_process', 'child_0'))
    context = BindingContext('synthetic-run', 'synthetic-child', 'scientific_process', path,
        SCOPE, prepared['assignment'], {'goal': {'objective': INVOCATION['objective']},
            'report_contract': {'decision': INVOCATION['purpose'], 'measurements': {'schema': SCHEMA}},
            'message': {'scope': SCOPE, 'episode_assignment': prepared['assignment'],
                'scientific_process': prepared['scientific_process'],
                'scientific_invocation_ref': scientific_invocation_ref('synthetic-run', path),
                'initial_report': INVOCATION['initial_report']}})
    frame = binding.decision_context(context, {})['scientific_process']
    assert_instructions(frame['evidence_axis'])
    assert 'axis_judgment_contract' not in frame
    assert frame['thought_pattern']['decision_guidance']
    assert frame['assignment']['context'] == assignment['context']
    assert plain(context.request)['report_contract']['measurements']['schema'] == SCHEMA
    assert frame['selection']['evidence_axis'] == library.reference('A105')
    assert services.calls == []


def test_lookup_and_restored_presentation_copies_do_not_reexpose_historical_sheets(library):
    raw = library.resolve(library.reference('A105'))
    partial = {key: raw[key] for key in ('id', 'name', 'description', 'native_measurements',
                                        'judgment_criteria', 'qualitative_grading', 'transfer_chain')}
    context = {'last_outcome': {'result': {'entry': raw}},
        'scientific_process': {'evidence_axis': partial, 'axis_judgment_contract': {'old': 'descriptor'}},
        'restored_public_exchanges': [{'lookup_result': {'result': {'entry': raw}}}],
        'requested_form': deepcopy(SCHEMA),
        'native_observation': {'value': 12.5, 'unit': 'nmol/min', 'bound': 'less_than'},
        'controller': {'scores': [1, 2], 'estimate': {'next_gain': .5}}}
    original = deepcopy(context)
    presented = instructional_model_context(context)
    assert presented['requested_form'] == original['requested_form']
    assert presented['native_observation'] == original['native_observation']
    assert presented['controller'] == original['controller']
    assert_instructions(presented['last_outcome']['result']['entry'])
    assert_instructions(presented['scientific_process']['evidence_axis'])
    assert_instructions(presented['restored_public_exchanges'][0]['lookup_result']['result']['entry'])
    assert 'axis_judgment_contract' not in presented['scientific_process']
    assert context == original
    assert instructional_model_context(presented) == presented
    snapshot = model_snapshot(context, {'rows': []})
    assert snapshot['last_outcome'] == presented['last_outcome']
    assert snapshot['controller'] == {'estimate': {'next_gain': .5}}
    assert context == original


def test_projection_before_frame_hashing_preserves_bootstrap_and_update_identity(library):
    raw = library.resolve(library.reference('A105'))
    historical_snapshot = {'last_outcome': {'result': {'entry': raw}},
                           'controller': {'estimate': {'next_gain': .5}}}
    before = deepcopy(historical_snapshot)
    snapshot = instructional_model_context(historical_snapshot)
    frame = state_frame(snapshot)
    frame['restored_public_exchanges'] = [{'lookup_result': {'result': {'entry': raw}}}]
    frame['restored_pending_decision_index'] = 2
    actual_dispatch = instructional_model_context(frame)
    assert apply_state_frame(None, actual_dispatch) == snapshot
    following = instructional_model_context({**historical_snapshot,
        'controller': {'estimate': {'next_gain': .25}}})
    update = instructional_model_context(state_frame(following, snapshot))
    assert apply_state_frame(snapshot, update) == following
    assert historical_snapshot == before
