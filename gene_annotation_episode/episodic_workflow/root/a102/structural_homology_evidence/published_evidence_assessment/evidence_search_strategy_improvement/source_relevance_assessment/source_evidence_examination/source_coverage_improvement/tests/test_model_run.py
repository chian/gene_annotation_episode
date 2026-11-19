"""A real run of this episode with the real model, through the public runner only.

The entry assignment holds a paper source that reports a deposited structure, the mmCIF coordinates and the wwPDB
validation report delivered by an earlier reading of it, and a source of literal witnesses (the experiment's
molecule, construct, system, condition, partner and name). ``link(...).run()`` runs the Episode with the standard
``ModelProvider``; every decision is the model's. The run ends through the yield controller; the journal holds the
model calls and the units; credit and finding are what the episode's own code computes from the held records and
the saved sheets; the return holds exactly the fields ``RETURN_FORM`` admits for the selection; and a resume replays
the recorded answers without starting a model process.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path
RUN_ID = 'real102_leaf'
SETTINGS = {'cost': 0.05, 'parameters': {'uncertainty_alpha': 0.05}}
TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A102', 'kind': 'verified_source_leads',
        'credit_unit': 1.0}
LITERALS = (('molecule', 'glutamate-binding domain GBD1'),
            ('construct', 'GBD1 residues 1-120 with N-terminal His6 tag'),
            ('experimental_system', 'recombinant protein expressed in Escherichia coli BL21(DE3)'),
            ('condition', 'crystallized at pH 7.0, data collected at 100 K'),
            ('partner', 'ligand LIG'),
            ('experiment', 'X-ray crystal structure of GBD1 bound to LIG (PDB 1ABC)'))
PAPER = ('Structure of the GBD1 ligand complex.\n'
         'We determined the X-ray crystal structure of the glutamate-binding domain GBD1 bound to the ligand LIG '
         '(PDB entry 1ABC, deposited coordinates and the wwPDB validation report were obtained with this article). '
         'In the deposited model, the carboxylate oxygens OE1 and OE2 of Glu1 in chain A lie close to atom N1 of '
         'LIG (chain B, residue 2). We propose that this contact holds the ligand. The experimental details '
         '(molecule, construct, expression system, crystallization condition, partner and experiment) are '
         'listed in the methods table that accompanies this article.\n')


def cif():
    fields = ('group_PDB', 'id', 'auth_atom_id', 'auth_comp_id', 'auth_asym_id', 'auth_seq_id',
              'label_alt_id', 'pdbx_PDB_ins_code', 'Cartn_x', 'Cartn_y', 'Cartn_z',
              'occupancy', 'B_iso_or_equiv', 'pdbx_PDB_model_num')
    return ("data_1ABC\n_entry.id 1ABC\n_exptl.method 'X-RAY DIFFRACTION'\n"
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


def source(store, text, provider, parents=(), alias=False):
    artifact = store.artifact(text)
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
                                'artifact_ref': artifact, 'text_ref': artifact if alias else None,
                                'request_ref': None, 'version': None, 'retrieved_at': None,
                                'parent_source_refs': list(parents)}, origin='caller')


def world(directory, paper_text=PAPER):
    """The Store with the problem, the real sources and the proposed annotation (the input binds LIG); the entry
    input passing all of them."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    paper = source(store, paper_text, 'article', alias=True)
    coordinates = source(store, cif(), 'pdb_mmcif', parents=[paper['id']])
    validation = source(store, xml(), 'wwpdb_validation_xml', parents=[paper['id']])
    literal = source(store, '\n'.join(f'{name}: {value}' for name, value in LITERALS) + '\n', 'article_methods_table',
                     parents=[paper['id']], alias=True)
    ligand = store.put('term', {'namespace': 'synthetic', 'accession': 'LIG', 'label': 'ligand LIG',
                                'term_type': 'chemical', 'source_ref': paper['id'], 'anchor': None}, origin='caller')
    proposed = store.put('hypothesis', {'subject_refs': scope['subject_refs'], 'predicate': 'binds',
                                        'value': {'type': 'term_ref', 'ref': ligand['id']}, 'context_refs': []},
                         origin='caller')
    sources = (paper, coordinates, validation, literal)
    held = [*scope['subject_refs'], *(row['id'] for row in sources), *(row['artifact_ref'] for row in sources),
            ligand['id'], proposed['id']]
    page = {'version': 'page_assignment_v1', 'source_ref': paper['id'], 'representation': 'original',
            'artifact_ref': paper['artifact_ref'], 'question_context_refs': [proposed['id'], ligand['id']],
            'prior_delivery_refs': [coordinates['id'], validation['id'], literal['id']]}
    assignment = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': {'source_ref': paper['id'], 'representation': 'original', 'offset': 0,
                                'limit': min(len(paper_text.encode()), 4000)},
                  'literature_task': TASK, 'proposed_annotation_ref': proposed['id'],
                  'scope': scope, 'received_record_refs': list(dict.fromkeys(held))}
    return store, {'assignment': assignment, 'message': {'objective': 'read'}, 'selection': []}


def collaborators(store, directory, cache):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': {PATH: {**SETTINGS, 'tool_registry': {'minimap2_cache_dir': str(cache)}}},
            'services': {}}


def saved_sheet_features(store, sheet_ref, cells):
    """What the finding of one sheet must be: its cells as the populate unit returned them and the counts and
    bindings of the sheet's saved artifact in the Store."""
    saved = json.loads(store.get_artifact(store.get(sheet_ref)['artifact_ref']))
    geometry, local = saved['sheet']['native_geometry'], saved['extraction']['native_local']
    features = {'evidence_type': 'experimental_structure_geometry', 'sheet_refs': [sheet_ref],
                'geometry_member_count': len(geometry),
                'geometry_measured_count': sum(row['distance_A'] is not None for row in geometry),
                'local_member_count': len(local), 'local_measured_count': sum(item['rscc'] is not None for item in local),
                'validation_binding': saved['extraction']['calculation_inputs']['validation_binding'],
                'operand_source_kind': saved['extraction']['source_kind'],
                'experiment_assessed': 'experiment_assessment' in saved}
    for name, cell in cells.items():
        features.update({name + '_lower': cell['lower'], name + '_upper': cell['upper'], name + '_status': cell['status'],
                         name + '_unavailable_reason': cell['unavailable_reason'] or 'none'})
    return features


def run_leaf(directory):
    store, entry = world(directory)
    journal = RunJournal(directory / 'journal.sqlite3')
    registry = BindingRegistry([EPISODE()])
    first = asyncio.run(link(registry, PATH, entry, run_id=RUN_ID, journal=journal,
                             collaborators=collaborators(store, directory, directory / 'minimap2')).run())
    return store, entry, journal, registry, first['result'].as_record()


@pytest.mark.model_run
def test_the_model_reads_and_grades_the_source_and_the_run_ends_by_its_yield_controller(tmp_path):
    store, entry, journal, registry, result = run_leaf(tmp_path)
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes(RUN_ID)
    path = episode['path']
    calls, units = journal.model_calls(RUN_ID, path), journal.units(RUN_ID, path)
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    assert calls and units and asked == len(calls)
    print('UNITS', json.dumps([(unit[2]['tool'], unit[2]['outcome']['status'],
                                (unit[2]['outcome'].get('feedback') or {}).get('code')) for unit in units]))
    # The return: exactly the required fields (nothing selected), admitted by the episode's own form.
    assert set(result) == {'credit', 'finding'} == set(FINAL.RETURN_FORM.select(()).fields)
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    # Credit: what the controller stopped on, which is credit_unit per validated relevant lead (one per source).
    assert result['credit'] == episode['completion']['credit'] == units[-1][1]['credit']
    leads = {unit[2]['outcome']['literature_source_lead']['source_ref'] for unit in units
             if unit[2]['tool'] == 'reason' and 'literature_source_lead' in unit[2]['outcome']
             and unit[2]['outcome']['literature_source_lead']['disposition'] == 'relevant'}
    assert result['credit'] == TASK['credit_unit'] * len(leads)
    # Finding: one entry per current sheet, read from the saved sheet.
    # A sheet is current when it is the latest of its family (its arguments without the assessment) and no
    # assessment revision superseded it.
    current, superseded = {}, set()
    for unit in units:
        if unit[2]['tool'] == 'structure_populate' and unit[2]['outcome']['status'] == 'completed':
            arguments = unit[2]['arguments']['arguments']
            assessment = arguments.get('experiment_assessment') or {}
            if assessment.get('revises_sheet_ref'):
                superseded.add(assessment['revises_sheet_ref'])
            family = json.dumps({key: value for key, value in arguments.items() if key != 'experiment_assessment'},
                                sort_keys=True)
            current[family] = unit[2]['outcome']['result']
    expected = [saved_sheet_features(store, sheet['sheet_ref'], sheet['cells']) for sheet in current.values()
                if sheet['sheet_ref'] not in superseded]
    assert result['finding']['structure_sheets'] == expected
    # Resume replays the recorded run: the episode's own code rebuilds the same result; no model process starts.
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators(store, tmp_path / 'resume', tmp_path / 'minimap2')).run())
    assert resumed['result'].as_record() == result
    assert journal.model_calls(RUN_ID, path) == calls
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    store.close()
