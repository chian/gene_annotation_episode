"""Original primary nominations, preserved controlled runtime, accepted054 display.

Reuse the immutable successful005 verification machinery, replacing only its
bounded nominations with the byte-identical original001 source selections.
No new paper, scientific interpretation, decision loop or credit rule.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
import gene_annotation_episode.literature_kinetic_storage as storage


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main(root, run):
    pin = Path(__file__).resolve().parent
    assert Path(storage.__file__).resolve() == pin / 'gene_annotation_episode/literature_kinetic_storage.py'
    assert hashlib.sha256(Path(storage.__file__).read_bytes()).hexdigest() == '599606c6e40f00e587934b0a7fcd1c550b46253974dd5b123cfdde228245759e'
    baseline_path = pin / 'baseline_worker_005.py'
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == '8426e1cf2e2e607811223bed9b3cbc932e226fcc3a826ce81130be19ea5caefb'
    spec = importlib.util.spec_from_file_location('controlled_051_frozen005_worker', baseline_path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    original = load(pin / 'original_source_selections_001.json')
    assert len(original['IMP']['numerator']['context']['conditions']['quote']) == 1003
    class OriginalNominations(baseline.LiteralSources):
        def selection(self, alternative):
            selected = deepcopy(original[alternative])
            assert selected['source_ref'] == self.main_ref
            return selected
    baseline.LiteralSources = OriginalNominations
    baseline.run_example(root, run)
    assert load(run / 'SOURCE_SELECTIONS.json') == original
    result, custody = load(run / 'RESULT.json'), load(run / 'SOURCE_CUSTODY.json')
    typed = load(run / 'TYPED_PARENT_RETURN.json')
    primary_dir = root / 'verification/literature_reference_evidence_2026-10-25_001/a105_specificity_case_038/source'
    sources = {
        custody['primary']['id']: (custody['primary']['artifact_ref'], (primary_dir / 'PMC2711008.bioc.xml').read_bytes()),
        custody['decoded_primary_table']['id']: (custody['decoded_primary_table']['artifact_ref'], (primary_dir / 'Table1.decoded.xml').read_bytes()),
    }
    def source_bytes(reference, representation):
        assert representation == 'original'
        artifact, raw = sources[reference]
        return {'artifact_ref': artifact, 'content': raw}
    sheets = [load(run / ('SHEET_' + alternative + '.json')) for alternative in ('IMP', 'FBP')]
    original_contract_checks = []
    for alternative, saved in zip(('IMP', 'FBP'), sheets):
        # A pure deterministic verification of original001 interpretations;
        # it creates no runtime work, observation, new interpretation or credit.
        expected_extraction = read_kinetic_inputs(original[alternative], read_source=source_bytes)
        expected_calculation = populate_kinetic_contrast(expected_extraction['calculation_inputs'])
        assert saved['selection'] == original[alternative]
        assert saved['extraction'] == expected_extraction
        assert saved['calculation'] == expected_calculation
        bounded = load(run.parent / 'controlled_005' / ('SHEET_' + alternative + '.json'))
        assert saved['cells'] == bounded['cells']
        assert saved['calculation']['physical_measurement_ids'] == bounded['calculation']['physical_measurement_ids']
        for role in ('numerator', 'denominator'):
            new_operand = saved['calculation']['inputs'][role]
            old_operand = bounded['calculation']['inputs'][role]
            for field in ('parameter_kind', 'unit', 'value', 'status', 'relation', 'approximate',
                          'origin', 'measurement_id', 'physical_measurement_id', 'subject', 'uncertainty', 'source'):
                assert new_operand[field] == old_operand[field], field
        original_contract_checks.append({'alternative': alternative, 'original001_selection_exact': True,
            'extraction_and_calculation_equal_frozen045046_original_interpretations': True,
            'all_nine_cells_preserved': True, 'native_values_units_uncertainty_and_physical_ids_equal005': True,
            'context_witness_difference_from005': 'Original full Methods and original experiment-title witnesses; no new scientific interpretation'})
    # Direct read facade: actual mode=ro BEFORE any reconstructed repository
    # read, no writable Store initializer and no scientific-state prewarming.
    store = Store.__new__(Store)
    store.path, store._savepoint = run / 'state', 0
    store.db = sqlite3.connect((store.path / 'state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    before = list(store.db.iterdump())
    forbidden_calls = []
    def forbidden(*_args, **_kwargs):
        forbidden_calls.append(True)
        raise AssertionError('No primary source artifacts, scientific reader/calculator, population or receipt during reconstruction')
    get_artifact = store.get_artifact
    primary_artifacts = {artifact for artifact, _raw in sources.values()}
    store.get_artifact = lambda ref: forbidden() if ref in primary_artifacts else get_artifact(ref)
    storage.read_kinetic_inputs = storage.populate_kinetic_contrast = forbidden
    try:
        repo = storage.LiteratureKineticRepository(store, result['run_id'])
        repo.populate = repo.receive_cells = forbidden
        outcomes = [json.loads(r['outcome']) for r in store.db.execute('SELECT outcome FROM literature_kinetic_operations ORDER BY rowid')]
        assert len(outcomes) == 2
        assert [repo.read(o['result']['sheet_ref']) for o in outcomes] == sheets
        admission, = list(store.db.execute('SELECT * FROM literature_kinetic_received'))
        assert json.loads(admission['cells']) == typed['numbers']
        parent = BindingContext(result['run_id'], admission['episode_id'], 'annotation',
            (('annotation', 'root'),), store.validate_scope(), {}, {}, tuple(dict.fromkeys(
                [custody['primary']['id'], custody['decoded_primary_table']['id'],
                 *(ref for outcome in outcomes for ref in outcome['record_refs'])])))
        assert repo.received_cells(parent) == typed['numbers']
        host = SimpleNamespace(store=store, run_id=result['run_id'], tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        assert binding.received_report_facts(parent)['literature_kinetic_cells'] == typed['numbers']
        preview_checks = []
        for alternative, sheet, outcome in zip(('IMP', 'FBP'), sheets, outcomes):
            row = next(r for r in typed['numbers'] if r['sheet_ref'] == outcome['result']['sheet_ref'])
            for role in ('numerator', 'denominator'):
                reference = row[role]['context']['conditions']
                actual = store.get(reference)
                witness = original[alternative][role]['context']['conditions']
                assert actual['anchor']['quote'] == witness['quote']
                assert actual['anchor']['start'] == witness['start'] and actual['anchor']['end'] == witness['end']
                assert len(actual['anchor']['quote']) > 512
                assert len(actual['label']) <= 512 and actual['label'].startswith('[source witness preview] ')
                assert '\n' not in actual['label'] and '\r' not in actual['label']
                raw = sources[witness['source_ref']][1]
                assert raw[witness['start']:witness['end']].decode() == actual['anchor']['quote']
                assert sheet['calculation']['inputs'][role]['context']['conditions'] == witness['quote']
                preview_checks.append({'alternative': alternative, 'role': role, 'reference': reference,
                    'original_anchor_characters': len(witness['quote']),
                    'original_anchor_utf8_bytes': len(witness['quote'].encode()),
                    'preview_label': actual['label'], 'preview_label_characters': len(actual['label']),
                    'full_original_anchor_exact': True, 'full_canonical_context_exact': True})
        observation_count = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        action_count = store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
        assert observation_count == action_count == result['actual_observations'] == 4
        assert list(store.db.iterdump()) == before and not forbidden_calls
    finally:
        store.close()
    save(run / 'LONG_WITNESS_VERIFICATION.json', {'status': 'passed', 'original001_nominations_exact': True,
        'original_contract_checks': original_contract_checks, 'long_anchor_preview_checks': preview_checks,
        'direct_mode_ro_before_any_repository_read': True, 'primary_artifacts_reader_calculator_receive_forbidden': True,
        'full_sql_unchanged': True, 'forbidden_calls': len(forbidden_calls),
        'actual_observations': observation_count, 'actual_credit': result['actual_credit'],
        'finite_count_interpretation': {k: v for k, v in typed.items() if k != 'numbers'},
        'numeric_count_and_model_reader_unimplemented': True,
        'configured_model_run': False, 'scope': 'Same-case publication repair verification only; no new scientific evidence or A105 completion'})
    print(json.dumps({'long_witness_verification': 'passed', 'original_anchor_lengths': [p['original_anchor_characters'] for p in preview_checks],
        'actual_observations': observation_count, 'actual_credit': result['actual_credit']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--run-directory', type=Path, required=True)
    args = parser.parse_args()
    main(args.repository_root.resolve(), args.run_directory.resolve())
