"""Root authenticates original selected scientific outputs, without new source work."""
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
AUDIT = BASE / 'a105_model_saved_source_audit_060'
LIVE = BASE / 'literature_model_run_030/live_001'
PIN = BASE / 'literature_model_run_030/pin_001'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def witness_nodes(value):
    if isinstance(value, dict):
        if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote'}:
            yield value
        else:
            for child in value.values():
                yield from witness_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from witness_nodes(child)


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.cells, self.parts = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.cells = []
        elif tag in ('td', 'th') and self.cells is not None:
            self.parts = []

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.parts is not None:
            self.cells.append(' '.join(''.join(self.parts).split()))
            self.parts = None
        elif tag == 'tr' and self.cells is not None:
            self.rows.append(self.cells)
            self.cells = None


def main():
    reset = load(BASE / 'model_source_parent_reset_060/READ_RECEIPT.json')
    assert reset['reader'] == 'root' and reset['complete']
    assert len(reset['acknowledged_chunks']) == reset['chunks_total'] == 49
    for row in reset['documents']:
        assert sha(Path(row['path'])) == row['sha256'], row['path']
    manifest = load(AUDIT / 'MANIFEST_001.json')
    for name, row in manifest['files'].items():
        path = AUDIT / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    final = load(AUDIT / 'FINAL_VERIFY_001.json')
    assert final['passed'] and final['manifest_sha256'] == sha(AUDIT / 'MANIFEST_001.json')
    original_pin = load(PIN / 'SOURCE_MANIFEST.json')
    for row in original_pin['files']:
        path = PIN / row['pin_relative_path']
        assert path.stat().st_size == row['size'] and sha(path) == row['sha256'], str(path)
    actions = load(AUDIT / 'PUBLIC_SELECTED_ACTIONS_001.json')
    payloads = load(AUDIT / 'PUBLIC_SAVED_PAYLOADS_001.json')
    records = load(AUDIT / 'PUBLIC_SOURCE_RECORDS_001.json')
    source_ref, source = next(iter(records.items()))
    original_episode = load(AUDIT / 'ORIGINAL_EPISODE_REQUEST_001.json')
    # Read only the two original selected public actions and cited artifacts.
    # Concurrent unrelated model work may change the live database.
    with sqlite3.connect((LIVE / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('begin')

        def record(reference):
            return json.loads(db.execute('select data from records where id=?', (reference,)).fetchone()['data'])

        def artifact(reference):
            row = db.execute('select sha256,size from artifacts where id=?', (reference,)).fetchone()
            raw = (LIVE / 'state/artifacts' / row['sha256'][:2] / row['sha256']).read_bytes()
            assert len(raw) == row['size'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            return raw

        assert record(source_ref) == source
        for representation, field, suffix in [('original', 'artifact_ref', 'html'), ('text', 'text_ref', 'txt')]:
            assert artifact(source[field]) == (AUDIT / f'PRIMARY_{representation.upper()}_001.{suffix}').read_bytes()
        request = json.loads(db.execute('select request from runtime_episodes where episode_id=?',
                                      (original_episode['episode_id'],)).fetchone()['request'])
        assert request == original_episode['request']
        for action in actions:
            row = db.execute('select action,result,credit from runtime_actions where run_id=? and episode_id=? and decision_index=?',
                             (action['run_id'], action['episode_id'], action['decision_index'])).fetchone()
            assert hashlib.sha256(row['action'].encode()).hexdigest() == action['action_json_sha256']
            assert hashlib.sha256(row['result'].encode()).hexdigest() == action['result_json_sha256']
            assert json.loads(row['action']) == action['action'] and json.loads(row['result']) == action['result']
            saved = payloads[str(action['decision_index'])]
            sheet_source = record(action['result']['result']['sheet_ref'])
            assert sheet_source == saved['source_record']
            assert json.loads(artifact(sheet_source['artifact_ref'])) == saved['saved_payload']
            assert json.loads(artifact(sheet_source['request_ref'])) == saved['original_request']
            assert saved['original_request']['arguments'] == saved['saved_payload']['native_selection'] == action['action']['arguments']
            assert saved['saved_payload']['sheet']['cells'] == action['result']['result']['cells']
    representations = {'text': (AUDIT / 'PRIMARY_TEXT_001.txt').read_bytes(),
                       'original': (AUDIT / 'PRIMARY_ORIGINAL_001.html').read_bytes()}
    witness_count = 0
    for saved in payloads.values():
        for witness in witness_nodes(saved['saved_payload']['native_selection']):
            assert witness['source_ref'] == source_ref
            assert representations[witness['representation']][witness['start']:witness['end']].decode() == witness['quote']
            witness_count += 1
    parser = TableRows()
    parser.feed(representations['original'].decode())
    start = next(index for index, row in enumerate(parser.rows)
                 if row and row[0] == 'Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)')
    rows = dict(parser.rows[start + 1:start + 9])
    assert (rows['Fd + Hyd'], rows['Fd'], rows['Hyd']) == ('5', '0.02', '<0.01')
    cells29 = payloads['29']['saved_payload']['sheet']['cells']
    exact = {'reference_rate': Fraction(5), 'test_rate': Fraction('0.02'),
             'rate_difference': Fraction(5) - Fraction('0.02'),
             'retained_fraction': Fraction('0.02') / 5,
             'fractional_decrease': 1 - Fraction('0.02') / 5}
    for name, value in exact.items():
        assert Fraction(str(cells29[name]['value'])) == value
    cells31 = payloads['31']['saved_payload']['sheet']['cells']
    assert cells31['test_rate']['value'] is None and cells31['test_rate']['threshold'] == .01 and cells31['test_rate']['bound'] == 'lt'
    for cells in (cells29, cells31):
        assert cells['reference_mean_se']['value'] is None and cells['test_mean_se']['value'] is None
        assert cells['signed_profile_log_ratio']['value'] is None and cells['source_signed_index']['value'] is None
    first = payloads['29']['saved_payload']['sheet']['extraction']['rows'][0]['source']['location']
    second = payloads['31']['saved_payload']['sheet']['extraction']['rows'][0]['source']['location']
    assert first == second
    owner_proof = load(AUDIT / 'SOURCE_AND_ARITHMETIC_RECEIPT_001.json')
    assert owner_proof['passed'] and owner_proof['exact_selected_witness_occurrences'] == witness_count == 78
    output = {'passed': True, 'root_reset_chunks': 49, 'root_reset_document_entries': len(reset['documents']),
              'sealed_owner_artifacts_verified': len(manifest['files']),
              'original030_pin_files_verified': len(original_pin['files']),
              'actual_original_selected_requests_payloads_reauthenticated_mode_ro': [29, 31],
              'exact_source_witness_occurrences': witness_count,
              'original_HTML_row_associations_verified': True,
              'independent_exact_arithmetic_29': {name: str(value) for name, value in exact.items()},
              'same_published_reference_location': True, 'censoring_and_unknown_statistics_preserved': True,
              'root_fresh_reader_calculator_rerun': False,
              'scope': 'Root source review/reset and scientific meaning accepted for descriptive coupled H2 contrasts only. No intrinsic Bcd loss, independent replication, reliability scalar, target credit or typed-delivery/reconstruction claim.'}
    with Path(__file__).with_name('SCIENTIFIC_REVIEW_RECEIPT_001.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
