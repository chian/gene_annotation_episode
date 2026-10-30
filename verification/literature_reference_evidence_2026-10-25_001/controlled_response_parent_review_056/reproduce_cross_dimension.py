"""Synthetic-only check of cross-pair physical-dimension applicability."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_controlled_response_calculations import populate_controlled_response, PRIMITIVE_ORDER


def main():
    source = ROOT / 'gene_annotation_episode/literature_controlled_response_calculations.py'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    data = json.loads((BASE / 'a105_controlled_response_design_056/pure_stage_003/INPUT_CONTRACT_EXAMPLE_003.json').read_bytes())
    data['covariance'] = None
    data['variance_status'] = 'unknown'
    data['model_kind'] = 'none'
    for i, role in enumerate(PRIMITIVE_ORDER):
        data['arms'][role]['unit'] = 'umol/min' if i < 2 else 'uM/min'
    result = populate_controlled_response(data)
    cells = {name: result['cells'][name] for name in ('condition1_controlled_response',
        'condition0_controlled_response', 'controlled_response_difference')}
    assert cells['condition1_controlled_response']['value'] == 10
    assert cells['condition0_controlled_response']['value'] == 4
    assert cells['condition1_controlled_response']['unit'] == 'umol/min'
    assert cells['condition0_controlled_response']['unit'] == 'uM/min'
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    assert before == after
    receipt = {'calculator_sha256': before, 'scope': 'Synthetic direct pure calculator; no source paper/model/episode',
        'inputs': data, 'cells': cells,
        'cross_dimension_bug_reproduced': cells['controlled_response_difference']['value'] is not None,
        'expected': 'Two valid local pairs remain; cross-condition effect is unavailable with incompatible_unit_dimension'}
    with (OUT / 'CROSS_DIMENSION_BASELINE_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'calculator_sha256': before, 'cross_dimension_bug_reproduced': receipt['cross_dimension_bug_reproduced'],
        'cells': {name: {k: row[k] for k in ('value', 'unit', 'status', 'unavailable_reason')} for name, row in cells.items()}}))


if __name__ == '__main__':
    main()
