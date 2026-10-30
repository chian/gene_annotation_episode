"""Verify source conflicts do not erase independent native-denominator facts."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_mauve_v4_calculators import bound_inputs, calculate
from test_mauve_v4_formats import native

rows = []
for problem in ('path', 'sequence', 'span'):
    inputs = bound_inputs()
    raw = native('GappedAlignment\n4 1 1\nACGT\nAAGT\n')
    if problem == 'path':
        inputs['files'][0]['native_path_token'] = '/another/f0'
    elif problem == 'sequence':
        raw = native('GappedAlignment\n4 1 1\nTCGT\nAAGT\n')
    else:
        raw = native('GappedAlignment\n4 5 1\nACGT\nAAGT\n')
    staged = calculate(raw, inputs=inputs, denominator='validated_staged_length')
    declared = calculate(raw, inputs=inputs, denominator='native_declared_length')
    a, b = staged['coverage'][0], declared['coverage'][0]
    assert a['coverage_fraction']['state'] == 'incompatible'
    assert a['coverage_fraction']['value'] is None
    assert b['coverage_fraction']['state'] == 'available'
    assert b['coverage_fraction']['value'] == 4 / 12
    assert a['known_union_bases']['value'] == b['known_union_bases']['value'] == 4
    rows.append({'source_problem': problem, 'staged_fraction': a['coverage_fraction'],
                 'native_fraction': b['coverage_fraction'], 'known_union_bases': 4})

sources = [
    'gene_annotation_episode/mauve_v4_formats.py',
    'gene_annotation_episode/mauve_v4_format_contracts.py',
    'gene_annotation_episode/mauve_v4_calculators.py',
    'gene_annotation_episode/mauve_v4_calculation_contracts.py',
    'gene_annotation_episode/bvbrc_genome_alignment_input_contracts.py',
]
record = {
    'scope': 'Root reviewed all four v4 production modules and directly exercised three synthetic source conflicts with both denominator choices.',
    'finding': 'No denominator-cross-contamination defect found: source conflicts invalidate only the source-dependent fraction; native declarations still give 4/12 with the source qualification retained.',
    'cases': rows,
    'source_hashes': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
    'limits': 'No new native execution, provider wiring, task-custody proof or complete episode-path verification.',
}
out = Path(__file__).with_name('ROOT_DENOMINATOR_REVIEW_003.json')
with out.open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps({'source_conflict_cases': len(rows), 'native_fraction': 4 / 12,
                  'staged_fraction': None, 'production_changes': False}))
