"""Independent saved-only058 review in its actual pinned implementation.

The primary case was already inspected/interpreted after root's full51-chunk
reset. This authenticates that execution; it does not reread a paper or refit it.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SOURCE = BASE / 'a105_binding_primary_example_058'
PIN = SOURCE / 'pin_003'
RUN = SOURCE / 'run_003'


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = load(SOURCE / 'MANIFEST_003.json')
    for name, row in manifest['files'].items():
        path = SOURCE / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    assert {str(p.relative_to(SOURCE)) for p in SOURCE.rglob('*') if p.is_file()} - set(manifest['excluded']) == set(manifest['files'])
    pin = load(PIN / 'PIN_MANIFEST.json')
    for name, row in pin.items():
        path = PIN / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
        assert not path.stat().st_mode & 0o222
    assert load(SOURCE / 'EXIT_RUN_002.json')['exit_code'] != 0
    assert load(SOURCE / 'EXIT_RUN_003.json')['exit_code'] == 0
    spec = importlib.util.spec_from_file_location('root_pinned_058', PIN / 'run_primary_003.py')
    h = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = h
    spec.loader.exec_module(h)
    h.verify_pin()
    ordinary_rows = load(RUN / 'SELECTED_NATIVE_ROWS.json')
    c4_spec = load(RUN / 'C4_ORIGINAL_COMMISSION.json')
    c4_return = load(RUN / 'C4_ORIGINAL_RETURN.json')
    admitted = load(RUN / 'C4_ADMISSION.json')
    c4_rows = admitted['report']['numbers']
    assert c4_return['form']['numbers'] == c4_rows
    assert len(ordinary_rows) == 16 and len(c4_rows) == 1
    assert c4_rows[0]['component'] == 'interaction_ratio'
    assert c4_spec['child']['request']['message']['episode_assignment']['requested_binding_interaction_components'] == ['interaction_ratio']
    for role in h.ROLES:
        values = c4_rows[0]['roles'][role]['values']
        assert values['delivery_status'] == 'not_requested'
        assert all(value is None for key, value in values.items() if key != 'delivery_status')
    proofs = []
    for directory, expected_rows, expected_observations in (
            ('selected_state', ordinary_rows, 4), ('c4_state', c4_rows, 0)):
        state = RUN / directory
        with sqlite3.connect((state / 'state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            before = list(db.iterdump())
            parents = [row for row in db.execute('SELECT * FROM runtime_episodes')
                       if len(json.loads(row['path'])) == 1]
            parent_row, = parents
            run = parent_row['run_id']
            counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in (
                'runtime_actions', 'runtime_observations', 'literature_binding_interaction_operations')}
            assert counts['runtime_observations'] == expected_observations
            assert counts['runtime_actions'] == (4 if directory == 'selected_state' else 1)
            assert counts['literature_binding_interaction_operations'] == (2 if directory == 'selected_state' else 1)
            assert all(row[0] == 0 for row in db.execute('SELECT credit FROM runtime_actions'))
            attempts = db.execute('SELECT form,failure FROM runtime_report_attempts').fetchall()
            assert len(attempts) == 1 and attempts[0]['failure'] is None
            assert json.loads(attempts[0]['form'])['numbers'] == expected_rows
            sources = [json.loads(row['request'])['message']['episode_assignment']['source_refs']
                       for row in db.execute('SELECT * FROM runtime_episodes')
                       if len(json.loads(row['path'])) > 1]
            refs, = sources
            receipts = [row[0] for row in db.execute('SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=?',
                                                    (run, parent_row['episode_id']))]
            known = tuple(dict.fromkeys([*refs, *receipts, *admitted['received_record_refs']])) if directory == 'c4_state' else tuple(receipts)
            facade = h.Store.__new__(h.Store)
            facade.path, facade.db, facade._savepoint = state, db, 0
            parent = h.context_from_saved(facade, run, parent_row, known)
            artifacts = {facade.get(ref)[key] for ref in refs for key in ('artifact_ref', 'text_ref') if facade.get(ref).get(key)}
            assert list(db.iterdump()) == before
        # Fresh connection; FIRST reconstructed scientific parent projection
        # happens inside h.reconstruct with all original scientific work denied.
        replay = None
        if directory == 'c4_state':
            contract = h.TypedReportContract(h.QUESTION, h.FORM, h.forbidden)
            assert contract.as_record() == c4_spec['child']['request']['report_contract']
            receiver = h.ReceiverBindingV1(None, None, 7, contract,
                h.forbidden, h.forbidden, h.forbidden, h.forbidden)
            replay = c4_spec, c4_return, receiver, admitted
        rebuilt = h.reconstruct(state, run, parent, expected_rows, artifacts, before, replay)
        assert rebuilt['mode_ro_before_first_projection'] and rebuilt['whole_sql_unchanged']
        proofs.append({'state': directory, 'counts': counts, 'reconstruction': rebuilt})
    saved = load(RUN / 'SAVED_EXTRACTION_AND_CALCULATION.json')
    fits = {identity for sheet in saved for identity in sheet['calculation']['physical_fit_ids'].values()}
    assert len(fits) == 6
    for role in (h.ROLES[0], h.ROLES[2]):
        assert saved[0]['calculation']['operand_keys'][role] == saved[1]['calculation']['operand_keys'][role]
    for sheet in saved:
        assert sheet['calculation']['model'] is None
        for role in h.ROLES:
            uncertainty = sheet['extraction']['roles'][role]['uncertainty']
            assert uncertainty['minimum_count']['literal']['status'] == 'exact'
            assert uncertainty['minimum_count']['status'] == 'unsupported_literal'
            assert uncertainty['canonical']['minimum_count'] is None
    permission = load(SOURCE / 'provider_permission_run_004/RECEIPT.json')
    text = (SOURCE / 'provider_permission_run_004/ACTUAL_PROVIDER_TEXT.txt').read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == permission['text_sha256']
    assert permission['original_commission_sha256'] == digest(RUN / 'C4_ORIGINAL_COMMISSION.json')
    assert permission['original_return_sha256'] == digest(RUN / 'C4_ORIGINAL_RETURN.json')
    assert permission['native_pin_manifest_sha256'] == digest(PIN / 'PIN_MANIFEST.json')
    assert '10.3125' in text
    for value in ('32 ± 2', '17 ± 3', '11 ± 1', '>510', '>740', '36.339285714285715'):
        assert value not in text
    h.verify_pin()
    receipt = {'passed': True, 'delivery_files_verified': len(manifest['files']), 'immutable_pin_files_verified': len(pin),
        'saved_only_actual_pinned_reconstructions': proofs, 'six_physical_fits_across_eight_slots': True,
        'unsupported_count_word_and_unknown_model_preserved': True,
        'original_derived_only_C4_typed_rows_and_provider_text_authenticated': True,
        'provider_probe_rerun': False,
        'scope': 'Already interpreted primary case, controlled selected execution and original C4 fixture. No new source reading, parsing/calculation, model inference or complete A105 claim'}
    with (OUT / 'EXECUTION_RECEIPT_003.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
