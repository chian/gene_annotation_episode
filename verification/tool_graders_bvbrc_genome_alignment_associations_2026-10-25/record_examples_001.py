"""Record C association examples; native files, explicitly synthetic custody."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_bvbrc_genome_alignment_associations import native_case, bind
from test_mauve_v4_calculators import selection
from gene_annotation_episode.bvbrc_genome_alignment_inputs import extract_genome_alignment_inputs
from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments


def main():
    examples = []
    for fmt in ('mauve_v4', 'mauve1_xmfa', 'mauve_backbone', 'mauve_bbcols'):
        case = native_case(fmt)
        extracted = extract_genome_alignment_inputs(case['original_task'],
            supplied_values=case['supplied_values'], supplied_bytes=case['supplied_bytes'],
            retained_records=case['retained_records'])
        case['inputs'] = extracted['value']
        association = bind(case)
        row = {'format': fmt, 'input_extraction': extracted, 'associations': association,
               'parsed_artifacts': case['parsed_artifacts']}
        if fmt == 'mauve_v4':
            doc = case['parsed_artifacts'][0]['document']
            row['native_declared_denominator'] = calculate_mauve_v4_segments(doc,
                selection=selection(doc, denominator='native_declared_length'), inputs=extracted['value'])
            row['original_input_denominator'] = calculate_mauve_v4_segments(doc,
                selection=selection(doc, denominator='validated_staged_length'), inputs=extracted['value'])
            assert [(r['known_union_bases']['value'], r['denominator_bases']['value'])
                    for r in row['native_declared_denominator']['coverage']] == [(690, 693), (2000, 2000)]
            assert all(r['coverage_fraction']['value'] is None
                       for r in row['original_input_denominator']['coverage'])
        assert association['value']['artifacts'][0]['state'] == 'bound'
        assert all(r['input_member'] is None for r in association['value']['native_member_joins'])
        examples.append(row)
    files = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in (
        'bvbrc_genome_alignment_associations', 'bvbrc_genome_alignment_inputs',
        'bvbrc_genome_alignment_retained_records', 'bvbrc_genome_alignment_input_contracts',
        'mauve_v4_formats', 'mauve_v4_format_contracts', 'mauve_v4_calculators',
        'mauve_v4_calculation_contracts', 'mauve_backbone_formats',
        'mauve_backbone_contracts', 'mauve_backbone_calculators')]
    files += [ROOT / 'tests' / name for name in (
        'test_bvbrc_genome_alignment_associations.py', 'test_bvbrc_genome_alignment_retained_records.py',
        'test_mauve_v4_calculators.py')]
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'provenance': 'Official retained native alignment/sidecar bytes. Task, receipts, object IDs and custody are synthetic test fixtures. No live BV-BRC run or authenticated host integration.',
        'limits': ['Original staged bytes and complete retrieval census remain unknown.',
                   'Native source/member and BBCols-to-XMFA joins remain unverified or missing.',
                   'Manifest object association does not establish original producer byte version.',
                   'D/E/F provider and episode integration remain unfinished.'],
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'examples': examples}
    target = Path(__file__).with_name('EXAMPLES_001.json')
    with target.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'examples': len(examples), 'native_members': [len(r['associations']['value']['native_member_joins']) for r in examples],
        'native_coverage': [[690, 693], [2000, 2000]], 'original_input_coverage': [None, None]}))


if __name__ == '__main__':
    main()
