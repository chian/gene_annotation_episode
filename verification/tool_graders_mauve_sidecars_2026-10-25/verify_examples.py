"""Reproduce B's retained-byte examples; no native execution or acquisition.

Run from the repository root with python3. Test-only binding builders explicitly
provide synthetic task custody and interval maps, never observed BV-BRC facts.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from test_mauve_backbone_formats import NATIVE, backbone, bbcols, selection
from test_mauve_backbone_calculators import source_inputs
from test_mauve_bbcols_calculators import associations, xmfa
from gene_annotation_episode.mauve_backbone_calculators import (
    calculate_mauve_backbone_components, calculate_mauve_bbcols_components,
)


def main():
    destination = Path(__file__).resolve().parent
    native = destination / 'native_examples'
    native.mkdir(exist_ok=True)
    receipts = json.loads((NATIVE.parent / 'SOURCE_RECEIPTS.json').read_text())
    retained = []
    for name in ('separate.xmfa.backbone', 'separate.xmfa.bbcols', 'separate.xmfa',
                 'equCab1.fa', 'canFam2.fa', 'mm9.fa'):
        raw = (NATIVE / name).read_bytes()
        receipt = deepcopy(next(r for r in receipts if r['path'] == 'native_examples/' + name))
        assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
        assert len(raw) == receipt['bytes']
        (native / name).write_bytes(raw)
        retained.append({'retained_local_path': str((native / name).relative_to(ROOT)),
            'copied_from': str((NATIVE / name).relative_to(ROOT)), 'original_receipt': receipt})
    (destination / 'NATIVE_ACQUISITION_RECEIPTS_001.json').write_text(json.dumps(retained, indent=2) + '\n')
    b, cols, primary = backbone()['value'], bbcols()['value'], xmfa()
    inputs, joins = source_inputs(official=True), associations(cols, primary)
    results = {'provenance': {
        'native_bytes': 'Retained official Biopython Mauve examples; original URLs, commit and hashes are in NATIVE_ACQUISITION_RECEIPTS_001.json.',
        'input_and_association_evidence': 'Explicitly synthetic test fixtures. Source FASTA bytes are official, but same-run/task/input/interval bindings are locally declared, not native BV-BRC evidence.',
        'execution': 'Pure parsing and calculation only. No new native job, installation, API request or episode integration was performed.'},
        'backbone_document': b, 'bbcols_document': cols, 'xmfa_document': primary,
        'synthetic_source_inputs': inputs, 'synthetic_associations': joins}
    for k in (2, 3):
        results['backbone_k' + str(k)] = calculate_mauve_backbone_components(b,
            selection=selection(b, threshold=k, denominator='validated_staged_length'), inputs=inputs)
        results['bbcols_k' + str(k)] = calculate_mauve_bbcols_components(cols,
            selection=selection(cols, threshold=k, fraction=True), xmfa_document=primary, associations=joins)
    results['backbone_missing_inputs'] = calculate_mauve_backbone_components(b,
        selection=selection(b, threshold=3, denominator='validated_staged_length'), inputs=None)
    results['bbcols_missing_joins'] = calculate_mauve_bbcols_components(cols,
        selection=selection(cols, threshold=3, fraction=True), xmfa_document=primary, associations=None)
    (destination / 'FILLED_EXAMPLES_001.json').write_text(json.dumps(results, indent=2) + '\n')
    output = {str(k): {'backbone_unions_nt': [r['known_union_bases']['value'] for r in results['backbone_k' + str(k)]['coverage']],
        'backbone_fractions': [r['coverage_fraction']['value'] for r in results['backbone_k' + str(k)]['coverage']],
        'bbcols_union_columns': results['bbcols_k' + str(k)]['intervals'][0]['union_columns']['value'],
        'bbcols_bound_fraction': results['bbcols_k' + str(k)]['intervals'][0]['selected_block_fraction']['value']}
        for k in (2, 3)}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
