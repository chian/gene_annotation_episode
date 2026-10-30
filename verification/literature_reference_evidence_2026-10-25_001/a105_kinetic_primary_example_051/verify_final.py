"""Read-only artifact audit of the successful bounded-nomination generation."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3

OUT = Path(__file__).resolve().parent
RUN = OUT / 'controlled_005'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    terminal = json.loads((RUN / 'TERMINAL_RECEIPT.json').read_bytes())
    assert terminal['exit_code'] == 0 and terminal['pin_unchanged']
    pin = json.loads((RUN / 'PIN_MANIFEST.json').read_bytes())
    assert digest(RUN / 'PIN_MANIFEST.json') == terminal['pin_manifest_sha256']
    for relative, entry in pin['files'].items():
        path = RUN / 'pin' / relative
        assert path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256']
    for name in ('run_example.py', 'launch_example.py'):
        assert digest(OUT / name) == digest(RUN / 'pin' / name)
    source = OUT.parent / 'a105_specificity_case_038'
    custody = json.loads((RUN / 'SOURCE_CUSTODY.json').read_bytes())
    assert {p.relative_to(source).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()} == custody['original_sources']
    form = json.loads((RUN / 'TYPED_PARENT_RETURN.json').read_bytes())
    primary = (source / 'source/PMC2711008.bioc.xml').read_bytes()
    assert form['count_source_ref'] == custody['primary']['id']
    assert primary[form['count_source_start']:form['count_source_end']].decode() == form['count_source_expression'] == 'three'
    assert primary[form['count_source_end']:].startswith(b' independent experiments')
    assert form['count_extraction_status'] == 'reported_in_words_reader_unimplemented'
    rows = form['numbers']
    context_checks, sheets = [], []
    database = (RUN / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(database, uri=True) as db:
        db.row_factory = sqlite3.Row
        before = '\n'.join(db.iterdump())
        def record(ref):
            return json.loads(db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()[0])
        for alternative, denominator_spread in (('IMP', .0015), ('FBP', .001)):
            saved = json.loads((RUN / ('SHEET_' + alternative + '.json')).read_bytes())
            matching = [r for r in rows if r['sheet_ref'] == next(r['sheet_ref'] for r in rows
                if record(r['denominator']['context']['substrate'])['label'] == alternative)]
            assert len(matching) == 5
            cells = {r['component']: r for r in matching}
            for role, spread in (('numerator', 8), ('denominator', denominator_spread)):
                raw = cells[role + '_parameter'][role]
                assert raw['uncertainty_values']['delivery_status'] == 'requested'
                assert math.isclose(raw['uncertainty_values']['magnitude'], spread)
                assert raw['uncertainty_values']['count'] is None
                assert raw['uncertainty']['statistic'] == 'unspecified'
                assert raw['uncertainty']['estimate_basis'] == 'unknown'
                assert raw['uncertainty']['repetition_basis'] == 'unspecified'
                for name in ('parameter_difference', 'parameter_ratio', 'log_parameter_contrast'):
                    values = cells[name][role]['uncertainty_values']
                    assert values == {'delivery_status': 'not_requested', 'magnitude': None,
                                      'interval': None, 'confidence_level': None, 'count': None}
                timing = record(raw['context']['experiment'])['label']
                assert ('After 4 min at 30 °C' in timing if role == 'numerator' else '15 min thereafter' in timing)
                assert raw['context']['preparation'] is None
                context_checks.append({'alternative': alternative, 'role': role,
                    'timing_witness': timing, 'source_spread': spread,
                    'known_word_count_delivered_separately_from_native_numeric_count': True})
            assert saved['calculation']['model'] is None
            sheets.append({'alternative': alternative, 'cells': saved['cells'],
                'numerator_measurement_id': saved['calculation']['inputs']['numerator']['measurement_id'],
                'numerator_physical_summary_id': saved['calculation']['inputs']['numerator']['physical_measurement_id']})
        assert sheets[0]['numerator_measurement_id'] == sheets[1]['numerator_measurement_id']
        assert sheets[0]['numerator_physical_summary_id'] == sheets[1]['numerator_physical_summary_id']
        assert '\n'.join(db.iterdump()) == before
    attempts = {}
    for name in ('controlled_001', 'controlled_002', 'controlled_003', 'controlled_004', 'controlled_005'):
        path = OUT / name
        receipt = json.loads((path / 'TERMINAL_RECEIPT.json').read_bytes())
        with sqlite3.connect((path / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0] if table in tables else None for table in
                      ('runtime_actions', 'runtime_observations', 'literature_kinetic_operations')}
        attempts[name] = {'exit_code': receipt['exit_code'], **counts,
                          'null_table_counts_mean_table_not_initialized': True}
    result = {'status': 'passed', 'successful_generation': 'controlled_005',
        'pin_files_verified': len(pin['files']), 'both_harness_files_match_executed_pin': True,
        'original038_files_exact': True, 'finite_count_source_span_matches_exact_primary_bytes': True,
        'source_uncertainty_and_per_arm_timing_verified': context_checks,
        'shared_PAP_summary_identity_verified': True, 'sheets': sheets,
        'separate_attempts_not_additive_scientific_evidence': attempts,
        'configured_model_run': False, 'whole_A105_complete': False}
    with (OUT / 'FINAL_ARTIFACT_REVIEW_001.json').open('x') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'status': 'passed', 'pin_files_verified': len(pin['files']), 'attempts': attempts}))


if __name__ == '__main__':
    main()
