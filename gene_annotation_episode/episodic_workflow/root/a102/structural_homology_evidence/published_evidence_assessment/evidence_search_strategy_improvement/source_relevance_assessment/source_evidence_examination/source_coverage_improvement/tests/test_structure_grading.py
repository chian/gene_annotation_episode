"""The A102 literature structure grading of this episode, run through the real runner on a real Store.

The run is linked with the real runner, journal and Store and stepped through the runner's two calls.
``EpisodeRun.next_decision()`` enters the Episode as ``run()`` enters it (its yield controller is built from
``credit`` of the initial summary) and returns what the episode's own ``decide`` returns first. The model is not
asked: the next step of a real run is the model call, which needs a model provider and is not made here.
``EpisodeRun.run_unit(ToolCall(...))`` then runs the populate tool as a real tool unit of that Episode (journaled
attempt, custody receipts of what it wrote, ``credit`` and a controller step), on real held records: a paper
source, an mmCIF coordinate source, a wwPDB validation report and a source of literal witnesses (the fixtures of
the old ``test_literature_structure_storage.py`` at ``97308b94c``). ``EpisodeRun.view`` is the Episode's view
after those units. Nothing is faked and no runner internal is touched."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_structure_prompt import (
    STRUCTURE_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    FEATURES, EVIDENCE_TYPE)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.structural_homology_evidence.literature_structure_storage import (
    CELLS, COMPONENTS, PROVIDER, LiteratureStructureRepository)

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
TASK = importlib.import_module(PACKAGE + '.task')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'tool_registry': {}}
LEADS_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A102', 'kind': 'verified_source_leads',
              'credit_unit': 1.0}
LITERALS = ('molecule', 'construct', 'experimental_system', 'condition', 'partner', 'experiment')


def cif():
    fields = ('group_PDB', 'id', 'auth_atom_id', 'auth_comp_id', 'auth_asym_id', 'auth_seq_id',
              'label_alt_id', 'pdbx_PDB_ins_code', 'Cartn_x', 'Cartn_y', 'Cartn_z',
              'occupancy', 'B_iso_or_equiv', 'pdbx_PDB_model_num')
    return ("data_synthetic\n_entry.id 1ABC\n_exptl.method 'X-RAY DIFFRACTION'\n"
            '_pdbx_audit_revision_history.ordinal 2\n'
            '_pdbx_audit_revision_history.revision_date 2026-01-02\nloop_\n'
            + '\n'.join('_atom_site.' + field for field in fields) + '\n'
            'ATOM 1 OE1 GLU A 1 . ? 0 0 0 0.5 20 1\n'
            'ATOM 2 OE2 GLU A 1 . ? 0 1 0 0.5 21 1\n'
            'HETATM 3 N1 LIG B 2 . ? 3 0 0 1 12 1\n')


def xml():
    return ('<wwPDB-validation-information><Entry pdbid="1ABC" PDB-revision-number="2" '
            'PDB-revision-date="2026-01-02" XMLcreationDate="2026-01-03"/><ModelledSubgroup model="1" chain="A" '
            'resnum="1" icode=" " altcode=" " resname="GLU" rscc="0.8"/><ModelledSubgroup model="1" chain="B" '
            'resnum="2" icode=" " altcode=" " resname="LIG" rscc="0.9"/></wwPDB-validation-information>')


def selector(chain='A', residue='1', comp='GLU'):
    return {'auth_chain': chain, 'auth_seq_id': residue, 'comp_id': comp, 'insertion_code': '', 'alt_id': '.'}


def source(store, text, parents=(), alias=False):
    artifact = store.artifact(text)
    return store.put('source', {'provider': 'synthetic_structure_fixture', 'accession': None, 'uri': None,
                                'artifact_ref': artifact, 'text_ref': artifact if alias else None,
                                'request_ref': None, 'version': None, 'retrieved_at': None,
                                'parent_source_refs': list(parents)}, origin='caller')


def held_world(directory):
    """The Store with the problem, the sources and their artifacts; the entry input passing all of them."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    provenance = source(store, 'Synthetic provenance, never directly read.')
    paper = source(store, 'Synthetic structural experiment.', parents=[provenance['id']])
    coordinates = source(store, cif(), parents=[paper['id']])
    validation = source(store, xml(), parents=[paper['id']])
    text = 'Molecule|Construct|System|Condition|Partner|Experiment'
    literal = source(store, text, parents=[paper['id']], alias=True)
    witnesses, offset = {}, 0
    for field, quote in zip(LITERALS, text.split('|')):
        witnesses[field] = {'source_ref': literal['id'], 'representation': 'original', 'start': offset,
                            'end': offset + len(quote)}
        offset += len(quote) + 1
    sources = (provenance, paper, coordinates, validation, literal)
    held = [*scope['subject_refs'], *(row['id'] for row in sources), *(row['artifact_ref'] for row in sources)]
    page = {'version': 'page_assignment_v1', 'source_ref': paper['id'], 'representation': 'original',
            'artifact_ref': paper['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': []}
    assignment = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': {'source_ref': paper['id'], 'representation': 'original', 'offset': 0, 'limit': 10},
                  'literature_task': LEADS_TASK, 'proposed_annotation_ref': 'hypothesis_not_passed',
                  'scope': scope, 'received_record_refs': list(dict.fromkeys(held))}
    # What the model selects: literal witnesses as source locations (the host reads the quotations).
    selection = {'source_ref': paper['id'], 'coordinate_source_ref': coordinates['id'],
                 'validation_source_ref': validation['id'], 'source_kind': 'synthetic_fixture', 'model_number': 1,
                 'literals': witnesses,
                 'geometry_panel': [{'endpoint_a': {**selector(), 'atom_names': ['OE1', 'OE2']},
                                     'endpoint_b': {**selector('B', '2', 'LIG'), 'atom_names': ['N1']},
                                     'positive_max_A': 3.5, 'incompatible_min_A': 4.5}],
                 'local_panel': [selector(), selector('B', '2', 'LIG')],
                 'evaluation_scope': 'conditional_deposited_model_geometry'}
    return store, {'assignment': assignment, 'message': {'objective': 'read'}, 'selection': []}, selection, paper


def linked_run(directory, entry):
    store = entry['store']
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                    directory),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, entry['input'], run_id='pilot102-structure',
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_next_decision_offers_the_structure_grader_and_its_instructions(tmp_path):
    store, entry, _, _ = held_world(tmp_path)
    linked = linked_run(tmp_path, {'store': store, 'input': entry})
    request = asyncio.run(linked.next_decision())
    view = linked.view
    assert view.units_consumed == 0 and view.controller_state.stop is False
    summary = EPISODE.internal_summary(view)
    assert summary['structure_sheets'] == [] and EPISODE.credit(summary, view.records) == 0
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert 'structure_populate' in tools and 'report' not in tools
    assert tools['structure_populate']['input_schema'] == TASK.population_input_schema()
    assert STRUCTURE_TASK in request.instructions
    assert 'What does an experimentally determined model establish' in request.instructions
    assert '"structure_populate"' in json.dumps(request.output_schema)
    assert request.context['structure_sheets'] == []
    store.close()


def populate(linked, envelope, arguments):
    """Run the populate tool as the Episode's next unit; the unit's outcome."""
    return asyncio.run(linked.run_unit(ToolCall('structure_populate', {**envelope, 'arguments': arguments})))


def test_the_populate_tool_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    store, entry, selection, paper = held_world(tmp_path)
    linked = linked_run(tmp_path, {'store': store, 'input': entry})
    envelope = {'scope': entry['assignment']['scope'], 'page_source_ref': paper['id']}
    first = populate(linked, envelope, selection)
    assert first['outcome']['status'] == 'completed', first['outcome']
    sheet_ref = first['outcome']['result']['sheet_ref']
    reader = linked.view.records
    assert reader.holds(sheet_ref) and reader.receipt(sheet_ref)['how'] == 'produced'
    assert reader.get(sheet_ref)['provider'] == PROVIDER
    saved = LiteratureStructureRepository(reader).read(sheet_ref)
    assert saved['sheet']['native_geometry'][0]['distance_A'] == 3
    assert saved['sheet']['cells']['source_geometry_positive']['value'] == pytest.approx(.64)
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert set(cells) == set(COMPONENTS)
    experiment_ref = saved['experimental_bindings']['experiment_ref']
    assert reader.get(experiment_ref)['label'] == 'Experiment'

    # A second sheet for the same experiment with an assessment, then its revision (corrected local panel).
    assessment = {'experiment_ref': experiment_ref, 'experiment_type': 'structural_feature_geometry',
                  'assessment_key': 'ligand_contact', 'scientific_question': 'Is the ligand in contact?',
                  'conclusion': 'Within the positive criterion.', 'limitations': ['one fitted dataset'],
                  'revision_reason': None, 'revises_sheet_ref': None}
    assessed = {**selection, 'local_panel': [selector()], 'experiment_assessment': assessment}
    second = populate(linked, envelope, assessed)
    assert second['outcome']['status'] == 'completed', second['outcome']
    assessed_ref = second['outcome']['result']['sheet_ref']
    stale = {**selection, 'local_panel': [selector('B', '2', 'LIG')], 'experiment_assessment': assessment}
    refused = populate(linked, envelope, stale)
    assert refused['outcome']['status'] == 'invalid'
    assert refused['outcome']['feedback']['code'] == 'experimental_assessment_revision_required'
    revision = {**assessment, 'revision_reason': 'corrected local panel', 'revises_sheet_ref': assessed_ref}
    revised = {**selection, 'local_panel': [selector('B', '2', 'LIG')], 'experiment_assessment': revision}
    third = populate(linked, envelope, revised)
    assert third['outcome']['status'] == 'completed', third['outcome']
    revised_ref = third['outcome']['result']['sheet_ref']

    # The Episode after its four units, as the system holds it: its view, the summary and its controller's credit.
    view = linked.view
    assert view.units_consumed == 4 and view.controller_state.stop is False
    summary = EPISODE.internal_summary(view)
    sheets = summary['structure_sheets']
    assert [features['sheet_refs'] for features in sheets] == [[sheet_ref], [revised_ref]]
    first_features, revised_features = sheets
    assert set(first_features) == set(FEATURES)
    assert first_features['evidence_type'] == EVIDENCE_TYPE
    assert first_features['source_geometry_positive_status'] == 'populated'
    assert first_features['source_geometry_positive_lower'] == cells['source_geometry_positive']['lower']
    assert first_features['local_fit_index_unavailable_reason'] == 'none'
    assert (first_features['geometry_member_count'], first_features['geometry_measured_count']) == (1, 1)
    assert (first_features['local_member_count'], first_features['local_measured_count']) == (2, 2)
    assert first_features['validation_binding'] == 'matching_entry_revision'
    assert first_features['operand_source_kind'] == 'synthetic_fixture'
    assert first_features['experiment_assessed'] is False and revised_features['experiment_assessed'] is True
    assert revised_features['local_member_count'] == 1

    completion = {'ended_by': 'yield_stop', 'units_consumed': view.units_consumed,
                  'credit': view.controller_state.current_credit}
    result = EPISODE.final_to_parent(summary, completion, ())
    assert set(result) == {'credit', 'finding'} and set(result['finding']) == {'structure_sheets'}
    admitted = EPISODE.return_form.select(()).admit(result, 'return')
    assert admitted == result
    assert set(EPISODE.return_form.select(()).record_refs(admitted)) == {sheet_ref, revised_ref}
    text_fields = [name for name, spec in FINAL.SHEET_FORM.fields.items() if spec.type == 'text']
    assert all(hasattr(FINAL.SHEET_FORM.fields[name], 'options') for name in text_fields)
    json.dumps(result, allow_nan=False)
    store.close()
