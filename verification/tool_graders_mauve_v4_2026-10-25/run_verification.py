"""Reproduce the retained native example and labelled synthetic numeric cases.

No native program, network client, scientific service, or installation runs.
The test builders explicitly label their metadata/task custody as synthetic.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from gene_annotation_episode.mauve_v4_formats import parse_mauve_v4
from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
from gene_annotation_episode.mauve_v4_format_contracts import validate_mauve_v4_document
from gene_annotation_episode.mauve_v4_calculation_contracts import validate_mauve_v4_components
from test_mauve_v4_formats import native, parse, OFFICIAL
from test_mauve_v4_calculators import selection, bound_inputs


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size}


def mutations(value, prefix=()):
    if isinstance(value, (dict, list)):
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in items:
            yield prefix + (key,)
            yield from mutations(item, prefix + (key,))


def main():
    data = OFFICIAL.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == 'a0e700b702070ebd061f6ca5c5b0d9338ad8c330ad16b94c9a0090041cd8cd88'
    parsed = parse_mauve_v4(data, artifact={'source_ref': 'official:koadman/mauve:small.mauve',
        'raw_artifact_ref': str(OFFICIAL.relative_to(ROOT)), 'sha256': digest}, encoding='ascii')
    document = parsed['value']; chosen = selection(document, denominator='native_declared_length')
    chosen['population_id'] = 'official:small.mauve:all_observed_explicit_segments'
    result = calculate_mauve_v4_segments(document, selection=chosen, inputs=None)
    assert parsed['status'] == 'ok'
    assert [r['known_union_bases']['value'] for r in result['coverage']] == [690, 2000]
    assert result['coverage'][0]['complement_intervals'] == [[578, 581]]
    artifacts = [save('official_small.document.json', document), save('official_small.components.json', result)]
    supplied = bound_inputs()
    synthetic = parse(native('4 -2 1\n4 1 1\n4 1 1\n', lengths=(100, 100)))['value']
    s = selection(synthetic, denominator='validated_staged_length')
    components = calculate_mauve_v4_segments(synthetic, selection=s, inputs=supplied)
    artifacts += [save('synthetic_reverse_overlap.document.json', synthetic),
                  save('synthetic_supplied_inputs.json', supplied),
                  save('synthetic_reverse_overlap.components.json', components)]
    # Exercise every saved nested operand with five invalid-shaped replacements.
    # Some replacements legitimately remain valid; only unexpected exception
    # types are failures. Semantic corruption is checked by the targeted tests.
    shapes, unexpected = 0, []
    small = parse(native('GappedAlignment\n4 1 1\nACGT\nACGT\n'))['value']
    small_components = calculate_mauve_v4_segments(small,
        selection=selection(small, denominator='native_declared_length'), inputs=None)
    for value, validator in ((small, validate_mauve_v4_document), (small_components, validate_mauve_v4_components)):
        for path in mutations(value):
            for replacement in (None, True, {}, [], float('nan')):
                altered = deepcopy(value); node = altered
                for key in path[:-1]: node = node[key]
                node[path[-1]] = replacement; shapes += 1
                try: validator(altered)
                except ValueError: pass
                except Exception as error:
                    unexpected.append({'validator': validator.__name__, 'path': list(path), 'type': type(error).__name__})
    assert not unexpected, unexpected
    paths = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in (
        'mauve_v4_formats', 'mauve_v4_format_contracts', 'mauve_v4_calculators', 'mauve_v4_calculation_contracts')]
    paths += [ROOT / 'tests/test_mauve_v4_formats.py', ROOT / 'tests/test_mauve_v4_calculators.py', Path(__file__)]
    summary = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'command': 'python3 verification/tool_graders_mauve_v4_2026-10-25/run_verification.py',
        'official_native': {'path': str(OFFICIAL.relative_to(ROOT)), 'sha256': digest, 'bytes': len(data),
            'upstream_repository': 'koadman/mauve', 'revision': '56238aefa0f0c25134f3f0b244c0d7560cbaa9d7',
            'receipt': 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/ACQUISITION_RECEIPTS_003.json'},
        'official_example': {'intervals': 5, 'explicit_segments': 8, 'native_lengths': [693, 2000],
            'known_union_bases': [690, 2000], 'member0_uncovered': [[578, 581]],
            'gapped_width': 269, 'gapped_nongaps': [4, 269], 'gapped_gaps': [265, 0],
            'gapped_identical_canonical': 4, 'gapped_comparable_canonical': 4,
            'shared_coordinate_only_anchor_identities': 'missing'},
        'synthetic_example': {'provenance': 'Deliberately synthetic native text and synthetic task/source binding metadata; not a BV-BRC result.',
            'source_lengths': [6, 4], 'native_declared_lengths': [100, 100],
            'member0_reverse_symbols': components['member_segments'][0]['aligned_sequence'],
            'coverage_counts': [{k: row[k]['value'] for k in ('known_union_bases', 'placement_bases',
                'multiply_represented_bases', 'excess_placement_bases', 'coverage_fraction')} for row in components['coverage']]},
        'shape_mutation_checks': shapes, 'unexpected_exception_count': len(unexpected),
        'owned_source_hashes': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
        'artifacts': artifacts,
        'limits': {'native_execution': 'not run', 'live_service': 'not verified', 'episode_integration': 'not implemented by workload A',
                   'genome_census': 'not inferred', 'new_installation': 'none'}}
    save('VERIFICATION_001.json', summary)
    print(json.dumps({'official_example': summary['official_example'], 'synthetic_example': summary['synthetic_example'],
                      'shape_mutation_checks': shapes, 'unexpected_exception_count': len(unexpected)}, indent=2))


if __name__ == '__main__':
    main()
