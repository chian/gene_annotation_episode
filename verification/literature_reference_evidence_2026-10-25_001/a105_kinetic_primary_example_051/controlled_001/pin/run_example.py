"""Owner-interpreted primary operands, actual selected Workflow, controlled choices.

No external model, new scientific TASK, target correspondence or credit policy.
Expected numerical answers appear only in assertions, never in source selections.
"""
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, COMPONENTS, kinetic_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


class LiteralSources:
    """Exact selectors over the original BioC and verbatim embedded table bytes."""
    def __init__(self, main_ref, table_ref, main_raw, table_raw):
        self.main_ref, self.table_ref = main_ref, table_ref
        self.bytes = {main_ref: main_raw, table_ref: table_raw}
        self.main, self.table = main_raw.decode(), table_raw.decode()
        self.passages = list(re.finditer(r'<passage>(.*?)</passage>', self.main, re.S))
        self.rows = {}
        for match in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', self.table, re.S):
            cells = list(re.finditer(r'<td\b[^>]*>(.*?)</td>', match[1], re.S))
            if cells:
                self.rows[cells[0][1]] = [(match.start(1) + cell.start(1), cell[1]) for cell in cells]

    def at(self, reference, first, quote):
        text = self.bytes[reference].decode()
        start = len(text[:first].encode())
        assert self.bytes[reference][start:start + len(quote.encode())] == quote.encode()
        return {'source_ref': reference, 'representation': 'original',
                'start': start, 'end': start + len(quote.encode()), 'quote': quote}

    def passage(self, index, literal=None):
        passage = self.passages[index]
        body = re.search(r'<text>(.*?)</text>', passage[1], re.S)
        quote = body[1] if literal is None else literal
        at = body[1].index(quote)
        return self.at(self.main_ref, passage.start(1) + body.start(1) + at, quote)

    def table_witness(self, quote):
        return self.at(self.table_ref, self.table.index(quote), quote)

    def cell(self, substrate):
        first, expression = self.rows[substrate][3]
        return self.at(self.table_ref, first, expression)

    def number(self, witness, start, end):
        return {'witness': deepcopy(witness), 'number_start': start, 'number_end': end}

    def selection(self, alternative):
        unit = self.table_witness('µM<sup>−1</sup> min<sup>−1</sup>')
        kind = self.table_witness('<italic>k</italic><sub>cat</sub>/<italic>K</italic><sub>m</sub>')
        footnote = self.passage(64)
        def meaning(value, witnesses=()):
            return {'value': value, 'witnesses': deepcopy(list(witnesses))}
        def operand(substrate):
            cell = self.cell(substrate)
            match = re.fullmatch(r'\s*(\S+)\s*±\s*(\S+)\s*', cell['quote'])
            assert match
            methods = self.passage(32 if substrate == 'PAP' else 34)
            return {
                'parameter_kind': meaning('catalytic_efficiency', [kind]),
                'subject': {
                    'organism': self.passage(0, 'Mycobacterium tuberculosis'),
                    'genotype': self.passage(14, 'Mtb H37Rv'),
                    'molecule': self.passage(14, 'Rv2131c'),
                    'construct': self.passage(14, 'ligated into a similarly digested and CIP-treated pET28b vector with an N-terminal His6 tag'),
                },
                'context': {
                    'substrate': self.at(self.table_ref, self.rows[substrate][0][0], substrate),
                    'preparation': None,
                    'experiment': self.passage(62),
                    'experimental_system': self.passage(18, 'pET28b_2131c was transformed into E. coli strain BL21(DE3).'),
                    'conditions': methods,
                    'endpoint': self.passage(32, 'calculated AMP concentration') if substrate == 'PAP' else self.passage(34, 'amount of inorganic phosphate'),
                    'normalization': self.passage(19, 'Protein concentration was determined by UV absorption at 280 nm using a calculated extinction coefficient of 46350 M−1 cm−1.'),
                },
                'measurement_identity': deepcopy(cell),
                'measurement': {'number': self.number(cell, *match.span(1)), 'unit': deepcopy(unit)},
                'qualification': meaning('reported_point', [cell]),
                'uncertainty': {
                    'statistic': meaning('unspecified', [cell, footnote]),
                    'magnitude': self.number(cell, *match.span(2)), 'interval': None,
                    'unit': None, 'unit_relationship': meaning('same_as_parameter', [unit]),
                    'confidence_level': None, 'count': None,
                    'repetition_basis': meaning('unspecified', [footnote]),
                    'estimate_basis': meaning('unknown', [footnote]),
                },
            }
        return {'version': 'a105_kinetic_source_selection_v1', 'source_ref': self.main_ref,
            'source_kind': 'primary_source', 'numerator': operand('PAP'), 'denominator': operand(alternative),
            'comparison': {
                'subject_relationship': meaning('same_molecule_and_construct', [self.passage(14), self.passage(23), self.passage(34)]),
                'parameter_definition_relationship': meaning('same', [kind, footnote]),
                'substrate_arrangement': meaning('separate_assays', [self.passage(32), self.passage(34)]),
                'comparison_scope': meaning('reported_protocols', [footnote]),
                'nonintended_conditions_relationship': meaning('different', [footnote]),
            }}


def source_record(store, raw, provider, *, uri=None, parents=()):
    artifact = store.artifact(raw, 'application/xml')
    value = {'provider': provider, 'accession': None, 'uri': uri, 'artifact_ref': artifact,
             'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}
    if parents:
        value['parent_source_refs'] = list(parents)
    return store.put('source', value, origin='caller')


def run_example(root, run):
    original = root / 'verification/literature_reference_evidence_2026-10-25_001/a105_specificity_case_038'
    original_hashes = {p.relative_to(original).as_posix(): digest(p.read_bytes())
                       for p in original.rglob('*') if p.is_file()}
    main_raw = (original / 'source/PMC2711008.bioc.xml').read_bytes()
    assert digest(main_raw) == '53be249a7cfc6df40d85fdb5dfc39b156d1c260fdb810951102eeaa4070a3f9e'
    document = ET.fromstring(main_raw)
    passages = document.findall('.//document/passage')
    assert len(passages) == 123
    table_raw = passages[63].find("infon[@key='xml']").text.encode()
    assert table_raw == (original / 'source/Table1.decoded.xml').read_bytes()
    assert digest(table_raw) == '5530074b03823a0c8ff1a86026fbdd7bcd5d269977cc37419adf1c0a8dfb0546'
    store = Store(run / 'state')
    try:
        store.create_problem(root / 'cases/gene_001/target.fna', molecule='dna', format='fasta')
        main = source_record(store, main_raw, 'retained_primary_bioc', uri='https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/')
        table = source_record(store, table_raw, 'primary_bioc_embedded_table', parents=(main['id'],))
        literals = LiteralSources(main['id'], table['id'], main_raw, table_raw)
        selections = {name: literals.selection(name) for name in ('IMP', 'FBP')}
        save(run / 'SOURCE_SELECTIONS.json', selections)
        save(run / 'SOURCE_CUSTODY.json', {
            'primary': main, 'decoded_primary_table': table,
            'recipe': "ElementTree.fromstring(primary).findall('.//document/passage')[63].find(infon[@key=xml]).text.encode(utf-8)",
            'decoded_table_equals_retained_table_bytes': True,
            'original_sources': original_hashes,
            'main_sha256': digest(main_raw), 'table_sha256': digest(table_raw),
            'coverage_limit': 'BioC prose/table representation; no rendered equations, images, supplement or raw fit data',
            'target_scope': 'Existing gene_001 material is host scope only; assayed reference remains separate; no correspondence/target finding',
        })
        # Controlled negative contract probe, outside the episode demonstration:
        # the source uses a written count, which this decimal-only reader lacks.
        bad = deepcopy(selections['IMP'])
        count_witness = literals.passage(64, 'three independent experiments')
        bad['numerator']['uncertainty']['count'] = literals.number(count_witness, 0, len('three'))
        def source_bytes(reference, representation):
            assert representation == 'original' and reference in literals.bytes
            record = store.get(reference)
            return {'artifact_ref': record['artifact_ref'], 'content': literals.bytes[reference]}
        try:
            read_kinetic_inputs(bad, read_source=source_bytes)
        except ExperimentalContractError as error:
            assert error.code == 'literal_source_number_required'
            count_failure = {'code': error.code, 'field': error.field}
        else:
            raise AssertionError('Word count unexpectedly acquired a native numerical value')
        save(run / 'SOURCE_LIMITATIONS.json', {
            'word_count_reader_unimplemented': {'source_witness': count_witness, 'negative_probe': count_failure,
                'source_count_is_reported': True, 'native_numeric_count': None},
            'uncertainty_statistic': 'unspecified', 'independent_preparation_count': None,
            'estimate_basis': 'unknown', 'model_source_reader': 'unimplemented',
            'comparison_scope': 'reported_protocols', 'condition_response_mapping': None,
            'negative_probe_is_not_an_episode_action_or_scientific_credit': True,
        })
        form = obj({'numbers': kinetic_cells_schema()})
        assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
            'source_refs': [main['id'], table['id']], 'requested_kinetic_components': list(COMPONENTS)}
        received, controllers = [], []
        def work(alternative):
            return {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
                                  'arguments': selections[alternative]}, 'report_update': {}}
        def receive(inputs):
            report, = inputs['child_reports']
            received.append(deepcopy(report))
            commit = {key: [] for key in store.reasoning_schema()['required']}
            witness = literals.passage(14, 'Rv2131c')
            commit['source_subjects'] = [{'alias': 'assayed_reference', 'reference_type': 'assay',
                'source_ref': main['id'], 'label': witness['quote'],
                'anchor': {**{k: witness[k] for k in ('source_ref', 'start', 'end', 'quote')},
                           'artifact_ref': main['artifact_ref']}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        provider = ScriptedProvider([
            {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
                'goal': 'Determine the reported PAP catalytic-efficiency contrasts against separately assayed IMP and FBP',
                'scope': plain(store.validate_scope()),
                'purpose': 'Return requested native kinetic components preserving the reference molecule, protocol differences and uncertainty meanings',
                'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}},
            work('IMP'), work('FBP'), receive,
        ])
        def controller(path, initial):
            item = FixtureController(str(path), initial, 2)
            controllers.append(item)
            return item
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=run / 'workflow', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[main['id'], table['id']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[main['id'], table['id']]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1
        rows = received[0]['numbers']
        assert len(rows) == 10
        repo = LiteratureKineticRepository(store, summary['run_id'])
        operations = [dict(row) for row in store.db.execute('SELECT * FROM literature_kinetic_operations ORDER BY rowid')]
        assert len(operations) == 2
        saved, outcomes = [], []
        expected = ((0.0027, 41.9973, 15555.5555555556, 9.652173124255),
                    (0.025, 41.975, 1680, 7.426549072397))
        for operation, expectation in zip(operations, expected):
            outcome = json.loads(operation['outcome'])
            value = repo.read(outcome['result']['sheet_ref'])
            outcomes.append(outcome)
            saved.append(value)
            actual = {r['component']: r for r in rows if r['sheet_ref'] == outcome['result']['sheet_ref']}
            assert list(actual) == list(COMPONENTS)
            for component, answer in zip(COMPONENTS, (42, *expectation)):
                assert math.isclose(actual[component]['value'], answer, rel_tol=1e-11)
            for row in actual.values():
                assert row['comparison']['comparison_scope']['value'] == 'reported_protocols'
                assert row['comparison']['nonintended_conditions_relationship']['value'] == 'different'
                assert row['model_reader_capability'] == 'unimplemented'
                assert row['numerator']['context']['preparation'] is None
                assert row['numerator']['uncertainty']['statistic'] == 'unspecified'
                assert row['numerator']['uncertainty']['repetition_basis'] == 'unspecified'
                for role in ('numerator', 'denominator'):
                    assert row[role]['uncertainty_values']['count'] is None
            assert value['calculation']['independent_preparation_count'] is None
            assert all(value['calculation']['cells'][name]['value'] is None for name in (
                'log_contrast_variance', 'log_contrast_standard_uncertainty',
                'source_profile_log_ratio', 'source_signed_index'))
        first, second = (s['calculation']['inputs']['numerator'] for s in saved)
        assert first == second
        assert first['measurement_id'] == second['measurement_id']
        assert first['physical_measurement_id'] == second['physical_measurement_id']
        assert saved[0]['calculation']['inputs']['denominator']['physical_measurement_id'] != saved[1]['calculation']['inputs']['denominator']['physical_measurement_id']
        for outcome, value in zip(outcomes, saved):
            save(run / ('SHEET_' + ('IMP' if value is saved[0] else 'FBP') + '.json'), value)
        save(run / 'TYPED_PARENT_RETURN.json', received[0])
        admissions = [dict(r) for r in store.db.execute('SELECT * FROM literature_kinetic_received')]
        assert len(admissions) == 1
        admission = admissions[0]
        assert json.loads(admission['cells']) == rows
        parent = BindingContext(summary['run_id'], admission['episode_id'], 'annotation',
            (('annotation', 'root'),), store.validate_scope(), {}, {}, tuple(dict.fromkeys(
                [main['id'], table['id'], *(ref for o in outcomes for ref in o['record_refs'])])))
        assert repo.received_cells(parent) == rows
        observations = [dict(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        actions = [dict(r) for r in store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid')]
        action_categories = Counter(json.loads(row['action']).get('kind') for row in actions)
        assert len(observations) == len(actions) == 4
        assert action_categories == {'episode_child': 1, 'tool': 2, 'reason': 1}
        assert len(provider.contexts) == 4
        assert not store.list('observation') and not store.list('assessment')
        save(run / 'RUNTIME_RECEIPT.json', {'summary': summary, 'controller_scores': [c.scores for c in controllers],
            'actions': actions, 'observations': observations, 'typed_admissions': admissions,
            'action_categories': dict(action_categories), 'selected_population_operations': len(operations),
            'ordinary_observations': len(observations), 'internal_synthetic_observations': 0,
            'actual_credit': summary['credit'], 'configured_model_run': False,
            'provider': 'ScriptedProvider controlled choices over owner-interpreted primary operands',
            'controller': 'FixtureController verification seam; no production continuation claim'})
        before = list(store.db.iterdump())
        source_artifacts = {main['artifact_ref'], table['artifact_ref']}
        store.close()
        import gene_annotation_episode.literature_kinetic_storage as storage_module
        old_reader, old_calculator = storage_module.read_kinetic_inputs, storage_module.populate_kinetic_contrast
        def forbidden(*_args, **_kwargs):
            raise AssertionError('Saved reconstruction must not read primary source or rerun scientific interpretation/calculation')
        storage_module.read_kinetic_inputs = storage_module.populate_kinetic_contrast = forbidden
        try:
            with Store(run / 'state') as reopened:
                restored = LiteratureKineticRepository(reopened, summary['run_id'])
                get_artifact = reopened.get_artifact
                reopened.get_artifact = lambda ref: forbidden() if ref in source_artifacts else get_artifact(ref)
                reopened.db.close()
                reopened.db = sqlite3.connect((run / 'state/state.sqlite3').as_uri() + '?mode=ro', uri=True, isolation_level=None)
                reopened.db.row_factory = sqlite3.Row
                assert [restored.read(o['result']['sheet_ref']) for o in outcomes] == saved
                assert restored.received_cells(parent) == rows
                host = SimpleNamespace(store=reopened, run_id=summary['run_id'], tools=ToolRegistry(reopened))
                binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
                host.episode_bindings = EpisodeBindingRegistry((binding,))
                assert binding.received_report_facts(parent)['literature_kinetic_cells'] == rows
                assert list(reopened.db.iterdump()) == before
                assert reopened.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == len(observations)
        finally:
            storage_module.read_kinetic_inputs, storage_module.populate_kinetic_contrast = old_reader, old_calculator
        assert {p.relative_to(original).as_posix(): digest(p.read_bytes())
                for p in original.rglob('*') if p.is_file()} == original_hashes
        save(run / 'RECONSTRUCTION_RECEIPT.json', {'actual_sqlite_mode_ro': True,
            'primary_source_artifacts_forbidden': True, 'kinetic_reader_calculator_forbidden': True,
            'both_saved_sheets_exact': True, 'admitted_typed_parent_rows_exact': True,
            'whole_sql_unchanged': True, 'new_observations': 0, 'original038_files_unchanged': True})
        save(run / 'RESULT.json', {'status': 'passed', 'run_id': summary['run_id'],
            'source_reported_efficiencies': [42, .0027, .025],
            'reported_protocol_ratios': [saved[0]['cells']['parameter_ratio']['value'], saved[1]['cells']['parameter_ratio']['value']],
            'typed_rows': len(rows), 'actual_observations': len(observations), 'actual_credit': summary['credit'],
            'configured_model_execution': False, 'word_count_reader_unimplemented': True,
            'model_source_reader_unimplemented': True, 'complete_A105': False})
        print(json.dumps({'status': 'passed', 'run_id': summary['run_id'], 'typed_rows': len(rows),
            'actual_observations': len(observations), 'actual_credit': summary['credit']}))
    finally:
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--run-directory', type=Path, required=True)
    arguments = parser.parse_args()
    run_example(arguments.repository_root.resolve(), arguments.run_directory.resolve())
