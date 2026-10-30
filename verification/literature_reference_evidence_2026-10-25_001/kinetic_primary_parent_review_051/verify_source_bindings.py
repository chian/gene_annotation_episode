"""Literal integrity audit only, for the already interpreted051 source case."""
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / 'a105_kinetic_primary_example_051'
RUN = OWNER / 'controlled_005'


def load(name):
    return json.loads((RUN / name).read_bytes())


def main():
    custody = load('SOURCE_CUSTODY.json')
    raw = {}
    for name in ('primary', 'decoded_primary_table'):
        source = custody[name]
        digest = source['artifact_ref'].removeprefix('artifact_')
        data = (RUN / 'state/artifacts' / digest[:2] / digest).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        raw[source['id']] = data
    primary = raw[custody['primary']['id']]
    table = raw[custody['decoded_primary_table']['id']]
    assert ET.fromstring(primary).findall('.//document/passage')[63].find("infon[@key='xml']").text.encode() == table
    assert custody['decoded_primary_table']['parent_source_refs'] == [custody['primary']['id']]
    count = 0
    def walk(value):
        nonlocal count
        if isinstance(value, dict):
            if {'source_ref', 'representation', 'start', 'end', 'quote'} <= set(value):
                assert value['representation'] == 'original'
                assert raw[value['source_ref']][value['start']:value['end']].decode() == value['quote']
                count += 1
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    selections = load('SOURCE_SELECTIONS.json')
    for alternative in ('IMP', 'FBP'):
        sheet = load('SHEET_' + alternative + '.json')
        assert sheet['selection'] == selections[alternative]
        walk(sheet['selection'])
        walk(sheet['extraction'])
    typed = load('TYPED_PARENT_RETURN.json')
    assert primary[typed['count_source_start']:typed['count_source_end']] == b'three'
    assert primary[typed['count_source_end']:].startswith(b' independent experiments')
    assert typed['count_extraction_status'] == 'reported_in_words_reader_unimplemented'
    with sqlite3.connect((RUN / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
        before = list(db.iterdump())
        def record(ref):
            return json.loads(db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()[0])
        for row in typed['numbers']:
            for role in ('numerator', 'denominator'):
                metadata = row[role]
                assert metadata['uncertainty']['statistic'] == 'unspecified'
                assert metadata['uncertainty']['estimate_basis'] == 'unknown'
                assert metadata['context']['preparation'] is None
                uncertainty = metadata['uncertainty_values']
                if row['component'] == role + '_parameter':
                    expected = 8 if role == 'numerator' else (.0015 if record(metadata['context']['substrate'])['label'] == 'IMP' else .001)
                    assert uncertainty['delivery_status'] == 'requested' and uncertainty['magnitude'] == expected
                    assert uncertainty['count'] is None
                else:
                    assert uncertainty == {'delivery_status': 'not_requested', 'magnitude': None,
                        'interval': None, 'confidence_level': None, 'count': None}
                for ref in (metadata['context']['experiment'], metadata['context']['conditions']):
                    anchor = record(ref)['anchor']
                    assert raw[anchor['source_ref']][anchor['start']:anchor['end']].decode() == anchor['quote']
        assert list(db.iterdump()) == before
    receipt = {'passed': True, 'literal_witness_occurrences_verified': count,
        'derived_table_exact_primary_ancestry': True, 'exact_written_count_span_verified': True,
        'requested_uncertainty_only': True, 'source_processing_added_no_actions': True,
        'scope': 'Mechanical literal/source-binding checks on the previously interpreted case; no new scientific inference'}
    with (OUT / 'SOURCE_BINDINGS_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
