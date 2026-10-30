"""Independent invented-source probe of the unchanged released confidence reader."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_inputs import _confidence


def main():
    module = ROOT / 'gene_annotation_episode/literature_kinetic_inputs.py'
    expected = '78e0c0094bbffa8306c26a6d134eec74f291c34177a87656ec09f925c2dd1960'
    assert hashlib.sha256(module.read_bytes()).hexdigest() == expected
    cases = []
    for text, expected_error in (
        ('Reported confidence: 95%.', 'partial_source_confidence_level'),
        ('<p>Reported confidence: 95%.</p>', 'partial_source_confidence_level'),
        ('Reported confidence: 95%, as specified.', None),
        ('Reported confidence: 95% (reported).', None),
    ):
        raw = text.encode('utf-8')
        source = identity('source', {'invented_root_punctuation_fixture': text})
        artifact = identity('artifact', hashlib.sha256(raw).hexdigest())

        def read_source(reference, representation):
            assert reference == source and representation == 'original'
            return {'artifact_ref': artifact, 'content': raw}

        start = text.index('95%')
        selected = {'source_ref': source, 'representation': 'original',
                    'start': start, 'end': start + 3, 'quote': '95%'}
        try:
            actual = _confidence(selected, _Sources(read_source))
        except ExperimentalContractError as error:
            actual = {'error_code': error.code, 'field': error.field}
            assert error.code == expected_error
        else:
            assert expected_error is None and actual['value'] == .95
        cases.append({'invented_source_text': text, 'selection': selected, 'actual': actual})
    assert hashlib.sha256(module.read_bytes()).hexdigest() == expected
    receipt = {'passed': True, 'unchanged_helper_sha256': expected, 'cases': cases,
               'meaning': 'Complete authentic sentence-terminal percent fails while comma/space controls parse. Reader capability evidence only; no source-paper coverage or implemented correction.',
               'model_calls': 0, 'runtime_actions': 0, 'runtime_observations': 0}
    output = Path(__file__).with_name('CONFIDENCE_PUNCTUATION_RECEIPT_007.json')
    with output.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'independent_synthetic_cases': len(cases),
                      'released_helper_unchanged': True}))


if __name__ == '__main__':
    main()
