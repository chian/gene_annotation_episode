"""Independent actual SQL/artifact audit, with no production imports."""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata

BASE = Path(__file__).resolve().parent
PIN = BASE / 'partner_defined_verification_pin_018'
EXAMPLES = BASE / 'partner_defined_examples_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit_native(payload, record, artifact):
    """Check actual selected bytes and arithmetic without production readers."""
    extraction = payload['extraction']
    assert extraction['version'] == 'literature_partner_inputs_extraction_v3'
    assert extraction['arguments']['input_mode'] == 'native_source_spans'
    witness_count = 0
    number_count = 0

    def visit(value):
        nonlocal witness_count, number_count
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if {'source_ref', 'representation', 'start', 'end', 'quote'} <= set(value):
                source = record(value['source_ref'])
                reference = source['artifact_ref'] if value['representation'] == 'original' else source['text_ref']
                if 'artifact_ref' in value:
                    assert value['artifact_ref'] == reference
                content = artifact(reference)
                assert content[value['start']:value['end']].decode('utf-8') == value['quote']
                witness_count += 1
            if {'selector', 'raw_number', 'value', 'relation'} == set(value):
                selection = value['selector']
                quote = selection['witness']['quote']
                assert quote[selection['number_start']:selection['number_end']] == value['raw_number']
                assert float(Fraction(value['raw_number'].replace('−', '-'))) == value['value']
                number_count += 1
            for child in value.values():
                visit(child)

    visit(extraction['arguments'])
    visit(extraction['native_evidence'])
    native_rates = {}
    unit_scales = {
        'pmol min-1 mg-1': ('pmol/min/mg', 1),
        'pmol/min/mg': ('pmol/min/mg', 1),
        'nmol/min/mg': ('pmol/min/mg', 1000),
    }
    for role, arm in extraction['native_evidence'].items():
        if arm is None or arm['rate'] is None:
            continue
        rate = arm['rate']

        def convert(number, unit):
            if 'definition' in unit:
                definition = unit['definition']
                normalize = lambda value: ' '.join(unicodedata.normalize('NFKC', value).split())
                amount_unit = normalize(definition['amount_unit']['quote']).replace('μ', 'u').replace('µ', 'u')
                time_unit = normalize(definition['time_unit']['quote'])
                scale = (Fraction(definition['amount']['raw_number'])
                         * {'pmol': 1, 'nmol': 1000, 'umol': 1000000}[amount_unit]
                         * {'min': 1, 'minute': 1, 's': 60, 'second': 60}[time_unit])
                canonical = 'pmol/min/mg'
                assert unit['raw_unit'] == 'U/mg'
                assert definition['endpoint'] == arm['endpoint']
                assert normalize(definition['endpoint_entity']['quote']) == normalize(definition['definition_entity']['quote'])
            else:
                canonical, scale = unit_scales[unit['raw_unit']]
            assert (unit['canonical_unit'], unit['multiplier']) == (canonical, float(scale))
            return float(Fraction(number['raw_number'].replace('−', '-')) * scale)

        value = convert(rate['value'], rate['unit'])
        assert value == rate['canonical_value']
        spread = rate['spread']
        magnitude = spread['magnitude']
        expected_spread = None if magnitude is None else convert(magnitude, spread['unit'] or rate['unit'])
        assert expected_spread == rate['canonical_spread']
        core = extraction['recipe']['inputs']['arms'][role]
        assert core['measurement']['spread'] == {'kind': spread['kind'], 'magnitude': expected_spread}
        assert core['unit'] == rate['unit']['canonical_unit']
        if rate['value']['relation'] == 'point':
            assert core['measurement']['status'] == 'observed'
            assert core['measurement']['value'] == value
        else:
            assert rate['value']['relation'] in ('lt', 'le')
            assert core['measurement']['status'] == 'upper_bound'
            assert core['measurement']['value'] == value
        assert (core['measurement']['measurement_id'] is None) == (arm['measurement_identity'] is None)
        native_rates[role] = {'raw_number': rate['value']['raw_number'],
            'relation': rate['value']['relation'], 'canonical_value': value,
            'spread_kind': spread['kind'], 'canonical_spread': expected_spread}
    return {'witnesses_checked': witness_count, 'numbers_checked': number_count, 'rates': native_rates}


def audit_case(replay):
    name = replay['case']
    directory = EXAMPLES / name
    original = read(directory/'RECEIPT.json')
    delivered, = read(directory/'DELIVERED_BINDINGS_AND_FACTORS.json')
    db = sqlite3.connect((directory/'state/state.sqlite3').as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')

    def record(ref):
        return json.loads(db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()[0])

    def artifact(ref):
        digest, = db.execute('SELECT sha256 FROM artifacts WHERE id=?', (ref,)).fetchone()
        path = directory/'state/artifacts'/digest[:2]/digest
        assert sha(path) == digest
        return path.read_bytes()

    try:
        expected_sql = read(directory/'SQL_SNAPSHOT.json')
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert names == set(expected_sql)
        for table, rows in expected_sql.items():
            assert [dict(row) for row in db.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY rowid')] == rows, (name, table)
        operation, = db.execute('SELECT * FROM literature_partner_operations').fetchall()
        outcome = json.loads(operation['outcome'])
        assert outcome == original['outcome'] and outcome['status'] == 'completed'
        assert operation['run_id'] == original['run_id']
        sheet = record(outcome['result']['sheet_ref'])
        assert sheet['version'] == 'literature_partner_record_v1'
        assert sheet['provider'] == 'literature.experimental.partner'
        payload = json.loads(artifact(sheet['artifact_ref']))
        assert payload == original['saved_payload']
        native = audit_native(payload, record, artifact)
        assert len(payload['input_source_refs']) == 1
        source = record(payload['data_source_ref'])
        assert source['artifact_ref'] != source['text_ref']
        assert hashlib.sha256(artifact(source['artifact_ref'])).hexdigest() == '91c0ed6ce15d330e4359a231fe593039ebd72459d1ba1f585482f67fa7f66821'
        assert hashlib.sha256(artifact(source['text_ref'])).hexdigest() == '7944c5568b1ee0f8ff343be2a7f57c1b28e2e71d4e480fd984ac668136e0357f'
        assert native['rates']['reference']['canonical_value'] == (7000000 if name == 'nadh' else 5000000)
        assert native['rates']['omitted']['canonical_value'] == (100000 if name == 'nadh' else 10000)
        assert native['rates']['omitted']['relation'] == ('point' if name == 'nadh' else 'lt')
        assert all(arm is None or arm['measurement_identity'] is None
                   for arm in payload['extraction']['native_evidence'].values())
        assert sheet['parent_source_refs'] == payload['input_source_refs']
        assert payload['sheet']['cells'] == payload['extraction']['cells'] == payload['extraction']['calculation']['cells']
        admission, = db.execute('SELECT * FROM literature_partner_received').fetchall()
        attempt, = db.execute('SELECT * FROM runtime_report_attempts').fetchall()
        assert attempt['failure'] is None and attempt['child_episode_id'] == operation['episode_id']
        assert admission['episode_id'] == attempt['parent_episode_id']
        form = json.loads(attempt['form'])
        cells = json.loads(admission['cells'])
        assert form == original['actual_frozen_child_form']
        assert cells == form['measurements'] == original['actual_admitted_parent_subset']
        assert len(cells) == 8
        assert all(row['value'] is None for row in cells[2:])
        assert json.loads(attempt['contract'])['measurements']['schema'] == original['parent_form_schema']
        for row in cells:
            assert all(row[key] == value for key, value in payload['sheet']['cells'][row['component']].items())
            assert row['partner_necessity'] == 'not_inferred'
            assert row['target_correspondence'] == row['statistical_uncertainty'] == 'not_evaluated'
            assert row['arm_metadata'] == delivered['arm_metadata']
            for pair, check in payload['extraction']['calculation']['comparison_checks'].items():
                assert row['comparison_checks'][pair] == {'status': check['status'],
                    'unavailable_reason': check['unavailable_reason'],
                    'differing_factor_refs': [payload['factor_bindings'][n] for n in check['differing_factors']]}
        for field, ref in payload['experimental_bindings'].items():
            assert cells[0][field] == ref
            if ref is not None:
                actual = record(ref)
                anchor = actual['anchor']
                assert artifact(anchor['artifact_ref'])[anchor['start']:anchor['end']].decode() == anchor['quote']
        for field, value in delivered['bindings'].items():
            assert value == record(cells[0][field])
        for term in delivered['factor_terms']:
            assert term == record(payload['factor_bindings'][term['label']])
            assert term['source_ref'] == payload['data_source_ref'] and term['anchor'] is None
        for ref, item in original['sources_and_lineage'].items():
            assert record(ref) == item['record']
            assert hashlib.sha256(artifact(item['record']['artifact_ref'])).hexdigest() == item['sha256']
            for field, digest in item['original_and_text_sha256'].items():
                assert hashlib.sha256(artifact(item['record'][field])).hexdigest() == digest
        for item in original['original_setup_asset_origins']:
            assert sha(directory/item['retained_path']) == item['sha256']
        assert db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        selected_tools = [json.loads(row[0]) for row in db.execute('SELECT action FROM runtime_actions')]
        selected_tools = [row for row in selected_tools if row['kind'] == 'tool']
        assert len(selected_tools) == 1 and selected_tools[0]['tool'] == 'literature.partner.source.populate'
        assert selected_tools[0]['arguments'] == payload['extraction']['arguments']
        assert db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert all(r[0] == 0 for r in db.execute('SELECT credit FROM runtime_actions'))
        assert not db.execute("SELECT 1 FROM records WHERE record_type IN ('observation','assessment')").fetchall()
        assert replay['SQL_query_only'] and replay['all_SQL_tables_and_histories_unchanged']
        assert not replay['original_input_bytes_read'] and len(replay['allowed_saved_artifacts']) == 2
        assert set(replay['actual_artifact_reads']) == set(replay['allowed_saved_artifacts'])
        assert replay['source_work_disabled']
        assert replay['reacquisition_host_calls_disabled']
        assert replay['attempted_reacquisition_host_events'] == []
        return {'case': name, 'status': 'passed', 'selected_operations': 1, 'admissions': 1,
            'cells': len(cells), 'values': [row['value'] for row in cells],
            'all_actual_SQL_tables_match': len(expected_sql), 'bindings_and_source_bytes_verified': True,
            'native_source_arithmetic': native,
            'actions': 3, 'own_observations': 3, 'controller_credit': 0,
            'fresh_replay_source_helpers_disabled': len(replay['source_work_disabled'])}
    finally:
        db.rollback()
        db.close()


if __name__ == '__main__':
    manifest = read(PIN/'SOURCE_MANIFEST.json')
    drift = []
    for row in manifest['files']:
        assert sha(PIN/row['pin_relative_path']) == row['sha256']
        if sha(Path(row['origin'])) != row['sha256']:
            drift.append(row['origin'])
    for name in ('gene_annotation_episode/literature_partner_calculations.py',
                 'gene_annotation_episode/literature_partner_inputs.py',
                 'gene_annotation_episode/literature_partner_storage.py',
                 'gene_annotation_episode/literature_partner_source_fields.py',
                 'gene_annotation_episode/literature_partner_native_inputs.py',
                 'gene_annotation_episode/literature_partner_defined_units.py',
                 'method_loop/durable.py',
                 'gene_annotation_episode/literature_partner_prompt.py',
                 'gene_annotation_episode/literature_episodes.py',
                 'gene_annotation_episode/literature_experimental_prompt.py',
                 'gene_annotation_episode/episode_services.py',
                 'tests/test_literature_partner_defined_integration.py'):
        assert sha(PIN/name) == sha(BASE.parent.parent/name), name
    files = read(BASE/'PARTNER_DEFINED_FINAL_FILES_MANIFEST_018.json')['files']
    for item in files:
        assert sha(BASE/item['path']) == item['sha256'], item['path']
        assert (BASE/item['path']).stat().st_size == item['size']
    completion = read(BASE/'PARTNER_DEFINED_COMPLETION_018.json')
    for name, digest in completion['top_receipt_hashes'].items():
        assert sha(BASE/name) == digest, name
    result = {'status': 'passed', 'written_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Independent SQL/source/pin inspection of controlled examples; no new source interpretation',
        'model_backed': False, 'pin_files_verified': len(manifest['files']),
        'pin_manifest_sha256': sha(PIN/'SOURCE_MANIFEST.json'),
        'final_example_manifest_files_verified': len(files),
        'top_receipt_hashes_verified': len(completion['top_receipt_hashes']),
        'main_origins_different_from_pin': drift, 'changed_literature_paths_match_pin': True,
        'cases': [audit_case(case) for case in read(EXAMPLES/'REOPEN_RECEIPT.json')['cases']],
        'audit_script_sha256': sha(Path(__file__))}
    output = BASE/'PARENT_CHECK_018.json'
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'cases': len(result['cases']),
        'pin_files_verified': result['pin_files_verified'], 'main_source_drift': drift}))
