"""Independent exact-source/arithmetic audit; pure calls use030's own pin only."""
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PIN = BASE / 'literature_model_run_030/pin_001'
sys.path.insert(0, str(PIN))
from gene_annotation_episode.literature_rate_native_inputs import read_rate_source_inputs, validate_native_selection
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            assert self.table is None
            self.table = []
        elif self.table is not None and tag == 'tr':
            self.row = []
        elif self.row is not None and tag in ('td', 'th'):
            self.cell = tag
            self.parts = []

    def handle_data(self, data):
        if self.cell is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell == tag:
            self.row.append(' '.join(''.join(self.parts).split()))
            self.cell, self.parts = None, []
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def witnesses(value):
    if isinstance(value, dict):
        if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote'}:
            yield value
        else:
            for item in value.values():
                yield from witnesses(item)
    elif isinstance(value, list):
        for item in value:
            yield from witnesses(item)


def main():
    reset = load(HERE / 'RESET_READ_RECEIPT_001.json')
    assert reset['complete'] and len(reset['acknowledged_chunks']) == 49
    pin_manifest = load(PIN / 'SOURCE_MANIFEST.json')
    for row in pin_manifest['files']:
        path = PIN / row['pin_relative_path']
        assert path.stat().st_size == row['size'] and sha(path) == row['sha256'], path
    records = load(HERE / 'PUBLIC_SOURCE_RECORDS_001.json')
    source_ref, source = next(iter(records.items()))
    source_bytes = {'original': (HERE / 'PRIMARY_ORIGINAL_001.html').read_bytes(),
                    'text': (HERE / 'PRIMARY_TEXT_001.txt').read_bytes()}
    capture = load(HERE / 'CAPTURE_RECEIPT_001.json')
    for representation, field in [('original', 'artifact_ref'), ('text', 'text_ref')]:
        actual = hashlib.sha256(source_bytes[representation]).hexdigest()
        assert actual == capture['authenticated_artifacts'][source[field]]['sha256']

    def read_source(reference, representation):
        assert reference == source_ref and representation in source_bytes
        field = 'artifact_ref' if representation == 'original' else 'text_ref'
        return {'artifact_ref': source[field], 'content': source_bytes[representation]}

    parser = Tables()
    parser.feed(source_bytes['original'].decode())
    heading = 'Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)'
    tables = [table for table in parser.tables if any(row and row[0] == heading for row in table)]
    assert len(tables) == 1
    table = tables[0]
    first = next(i for i,row in enumerate(table) if row and row[0] == heading)
    rows = dict(table[first+1:])
    assert rows['Fd + Hyd'] == '5' and rows['Fd'] == '0.02' and rows['Hyd'] == '<0.01'
    data = load(HERE / 'PUBLIC_SAVED_PAYLOADS_001.json')
    checks, count = {}, 0
    for decision, saved in data.items():
        payload = saved['saved_payload']
        selected = payload['native_selection']
        for witness in witnesses(selected):
            raw = source_bytes[witness['representation']]
            assert witness['source_ref'] == source_ref
            assert raw[witness['start']:witness['end']].decode() == witness['quote']
            count += 1
        fresh = read_rate_source_inputs(selected, read_source=read_source)
        assert fresh == payload['sheet']['extraction']
        validate_native_selection(selected, fresh)
        arms = {row['arm']: row for row in fresh['rows']}
        result = populate_rate_contrast(fresh, reference_arm='reference', test_arm='test',
                 reference_condition=arms['reference']['condition'], test_condition=arms['test']['condition'],
                 dependence=selected['dependence']['value'], observation_model=selected['observation_model']['value'])
        assert result == payload['sheet']
        assert all(row['unit'] == 'umol/min/mg' for row in fresh['rows'])
        assert all(row['uncertainty']['kind'] == 'unreported' and row['uncertainty']['count'] is None for row in fresh['rows'])
        checks[decision] = {'complete_saved_extraction_reproduced': True, 'complete_saved_sheet_reproduced': True,
                           'unit': 'umol_H2/min/mg_purified_Bcd_Etf_preparation',
                           'cell_values': {key: {'value': cell['value'], 'threshold': cell['threshold'],
                                         'bound': cell['bound'], 'unavailable_reason': cell['unavailable_reason']}
                                           for key,cell in result['cells'].items()}}
    a, b = Fraction('5'), Fraction('0.02')
    exact = {'reference_rate': a, 'test_rate': b, 'rate_difference': a-b,
             'retained_fraction': b/a, 'fractional_decrease': 1-b/a}
    for name, value in exact.items():
        assert data['29']['saved_payload']['sheet']['cells'][name]['value'] == float(value)
    reference_29 = data['29']['saved_payload']['sheet']['extraction']['rows'][0]['source']['location']
    reference_31 = data['31']['saved_payload']['sheet']['extraction']['rows'][0]['source']['location']
    assert reference_29 == reference_31
    c = data['31']['saved_payload']['sheet']['cells']['test_rate']
    assert c['value'] is None and c['threshold'] == .01 and c['bound'] == 'lt'
    for name in ('rate_difference','retained_fraction','fractional_decrease'):
        assert data['31']['saved_payload']['sheet']['cells'][name]['value'] is None
    imports = {}
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('gene_annotation_episode', 'method_loop')) and getattr(module,'__file__',None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN.resolve()), name
            imports[name] = str(path.relative_to(PIN.resolve()))
    receipt = {'passed': True, 'scope': 'Retained original source and saved model-selected inputs; independent offline pure recomputation. No new model/episode/native population or parent delivery.',
               'original_pin_files_verified': len(pin_manifest['files']), 'pin_manifest_sha256': sha(PIN/'SOURCE_MANIFEST.json'),
               'exact_selected_witness_occurrences': count, 'original_HTML_table_rows': table,
               'selected_population_checks': checks,
               'exact_decimal_arithmetic_29': {name: {'numerator': str(value.numerator), 'denominator': str(value.denominator)} for name,value in exact.items()},
               'same_published_reference_source_locator': reference_29,
               'source_censoring_preserved': True, 'shared_source_cell_is_not_independent_replication': True,
               'application_imports_from_original_pin': imports,
               'original_live_database_writes': 0, 'new_model_calls': 0, 'runtime_actions_added': 0, 'runtime_observations_added': 0}
    with (HERE / 'SOURCE_AND_ARITHMETIC_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'pin_files': len(pin_manifest['files']), 'witness_occurrences': count,
                      'reproduced_native_extractions_and_sheets': 2, 'exact_reference_token_shared': True}))


if __name__ == '__main__':
    main()
