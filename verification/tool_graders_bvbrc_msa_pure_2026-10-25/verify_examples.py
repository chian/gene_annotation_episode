"""Explicit verification driver; production parsers/calculators perform no I/O.

--native-reference executes only the verbatim native reference-table branch and
snp_line_mod helper on copied retained synthetic alignments/tables. It neither
aligns sequences nor contacts AppService. The default writes complete examples
and proves saved-object recalculation with I/O/parsing/execution disabled.
"""
from __future__ import annotations

import argparse
import builtins
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gene_annotation_episode import bvbrc_msa_formats, phylogeny_formats
from gene_annotation_episode.bvbrc_msa_formats import parse_msa_frequency_table
from gene_annotation_episode.bvbrc_msa_calculators import msa_native_entropy, msa_reference_differences
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from gene_annotation_episode.phylogeny_calculators import alignment_components

OWN = Path(__file__).resolve().parent
BOUNDARY = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25'
ROUNDING = 'binary64_fixed_2_ties_to_even'


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def artifact(data, name):
    return {'raw_artifact_ref': name, 'source_ref': 'verification:' + name,
            'sha256': hashlib.sha256(data).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n')


def native_reference():
    source_path = BOUNDARY / 'retained_sources/p3_msa/service-scripts/App-MSA.pl'
    source = source_path.read_text()
    start = source.index('    if ($params_to_app->{ref_type} && $params_to_app->{ref_type} ne "none") {')
    end = source.index('    @cmd = ("p3x-build-gene-tree"', start)
    helper_start = source.index('sub snp_line_mod {')
    branch, helper = source[start:end], source[helper_start:]
    harness = ('use strict;\nmy ($work_dir, $analysis_base) = @ARGV;\n'
               'my $alignment_file = "$work_dir/${analysis_base}.afa";\n'
               'my $params_to_app = {ref_type => "string"};\n' + branch + helper)
    harness_path = OWN / 'native_reference_branch.pl'
    harness_path.write_text(harness)
    receipts = []
    for alphabet in ('dna', 'protein'):
        destination = OWN / 'native_reference' / alphabet
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'retained.afa').write_bytes((BOUNDARY / 'native_examples' / alphabet / 'output.afa').read_bytes())
        (destination / 'foma.table').write_bytes((BOUNDARY / 'native_examples' / alphabet / 'foma.table').read_bytes())
        argv = ['perl', str(harness_path), str(destination), 'retained']
        result = subprocess.run(argv, cwd=destination, capture_output=True, check=False)
        (destination / 'stdout.txt').write_bytes(result.stdout)
        (destination / 'stderr.txt').write_bytes(result.stderr)
        if result.returncode != 0:
            raise RuntimeError('native reference branch failed: ' + result.stderr.decode())
        receipts.append({'kind': 'actual_native_reference_branch_on_retained_synthetic_alignment_and_native_table',
            'alphabet': alphabet, 'argv': argv, 'cwd': str(destination), 'returncode': result.returncode,
            'complete_AppService_execution': False, 'alignment_execution': False,
            'source': identity(source_path), 'verbatim_branch_sha256': hashlib.sha256(branch.encode()).hexdigest(),
            'verbatim_helper_sha256': hashlib.sha256(helper.encode()).hexdigest(), 'harness': identity(harness_path),
            'artifacts': [identity(destination / name) for name in ('retained.afa', 'retained.snp.tsv', 'stdout.txt', 'stderr.txt')]})
    write_json(OWN / 'NATIVE_REFERENCE_RECEIPTS.json', receipts)


def population(alignment, *, columns=None):
    return {'population_id': alignment['alignment_id'] + '/all-rows', 'alignment_id': alignment['alignment_id'],
            'row_indices': list(range(len(alignment['rows']))),
            'columns_0based': list(range(alignment['observed_column_count'])) if columns is None else columns,
            'completeness': 'complete', 'evidence': []}


def entropy_arguments(alignment, table, alphabet):
    return {'alignment': alignment, 'analysis_id': 'retained-' + alphabet,
            'population': population(alignment), 'alphabet': alphabet, 'case_policy': 'uppercase',
            'terminal_gap': '-', 'observed_table': table, 'native_rounding': ROUNDING}


def examples():
    all_examples, summary = [], []
    for alphabet in ('dna', 'protein'):
        original_dir = BOUNDARY / 'native_examples' / alphabet
        alignment_bytes = (original_dir / 'output.afa').read_bytes()
        aligned = parse_aligned_fasta(alignment_bytes,
            artifact=artifact(alignment_bytes, 'retained-native/' + alphabet + '/output.afa'),
            id_rule='first_whitespace_token', encoding='ascii')
        table_bytes = (original_dir / 'foma.table').read_bytes()
        parsed = parse_msa_frequency_table(table_bytes,
            artifact=artifact(table_bytes, 'retained-native/' + alphabet + '/foma.table'),
            alphabet=alphabet, layout='current_without_reference', encoding='ascii')
        args = entropy_arguments(aligned['value'], parsed['value'], alphabet)
        components = msa_native_entropy(**args)
        canonical = alignment_components(aligned['value'], population=args['population'], alphabet=alphabet,
                                          case_policy='uppercase', pairs=())
        reference_bytes = (OWN / 'native_reference' / alphabet / 'retained.snp.tsv').read_bytes()
        reference_table = parse_msa_frequency_table(reference_bytes,
            artifact=artifact(reference_bytes, 'retained-native-reference/' + alphabet + '/retained.snp.tsv'),
            alphabet=alphabet, layout='current_with_reference', encoding='ascii')
        assert aligned['status'] == parsed['status'] == reference_table['status'] == components['status'] == 'ok'
        all_examples.append({'kind': 'retained_native_components_on_explicit_synthetic_input',
            'alphabet': alphabet, 'alignment_parse_result': aligned, 'frequency_parse_result': parsed,
            'reference_frequency_parse_result': reference_table, 'entropy_arguments': args,
            'entropy_components': components, 'shared_canonical_components': canonical})
        for site in components['sites']:
            summary.append({'alphabet': alphabet, 'column_1based': site['column_0based'] + 1,
                'counts': site['symbol_counts'], 'eligible': site['eligible_count']['value'],
                'terminal_excluded': site['terminal_gap_excluded_count']['value'],
                'literal_entropy_bits': site['literal_entropy_bits']['value'],
                'canonical_entropy_bits': canonical['sites'][site['column_0based']]['canonical_entropy_bits']['value'],
                'score_recalculated': site['native_score_recalculated']['value'],
                'native_score': parsed['value']['rows'][site['column_0based']]['score']['value'],
                'score_residual': site['score_residual']['value'], 'consensus': site['strict_majority_consensus']})
    data = b'>reference\nA-CGN--\n>member\nAT-TNA-\n'
    synthetic = parse_aligned_fasta(data, artifact=artifact(data, 'synthetic-reference.afa'),
        id_rule='first_whitespace_token', encoding='ascii')['value']
    original_maps = []
    for row in synthetic['rows']:
        offset = 0
        for column, symbol in enumerate(row['sequence']):
            if symbol == '-':
                continue
            start = 100 * (row['row_index'] + 1) + offset
            original_maps.append({'alignment_id': synthetic['alignment_id'], 'row_index': row['row_index'],
                'column_0based': column, 'staged_ungapped_position_0based': offset,
                'original_member': {'input_binding_id': 'synthetic-original', 'member_id': row['member_label']},
                'original_interval_0based_half_open': [start, start + 1], 'strand': '+',
                'translation_table': None, 'transformation_id': 'synthetic-explicit-trim', 'evidence': []})
            offset += 1
    reference_args = {'alignment': synthetic, 'analysis_id': 'synthetic-reference', 'population': population(synthetic),
        'reference': {'alignment_id': synthetic['alignment_id'], 'row_index': 0,
            'original_member': {'input_binding_id': 'synthetic-original', 'member_id': 'reference'},
            'native_ref_type': 'string', 'native_ref_string': '>reference\nA-CGN--',
            'identity_state': 'resolved', 'evidence': []},
        'member_row_indices': [1], 'alphabet': 'dna', 'case_policy': 'uppercase', 'original_correspondences': original_maps}
    ref_result = msa_reference_differences(**reference_args)
    missing_args = deepcopy(reference_args)
    missing_args['original_correspondences'] = []
    missing_result = msa_reference_differences(**missing_args)
    all_examples.append({'kind': 'deliberately_synthetic_reference_coordinate_example', 'arguments': reference_args,
        'reference_components': ref_result, 'missing_map_arguments': missing_args,
        'missing_map_components': missing_result})
    write_json(OWN / 'FILLED_EXAMPLES.json', all_examples)
    write_json(OWN / 'NUMERICAL_SUMMARY.json', summary)
    # Serialize then reload before disabling every supported acquisition path.
    saved = json.loads((OWN / 'FILLED_EXAMPLES.json').read_text())
    def forbidden(*args, **kwargs):
        raise AssertionError('saved replay attempted I/O, parsing or execution')
    targets = ((builtins, 'open'), (os, 'open'), (Path, 'open'), (Path, 'read_text'), (Path, 'read_bytes'),
               (socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'), (subprocess, 'run'),
               (bvbrc_msa_formats, 'parse_msa_frequency_table'), (phylogeny_formats, 'parse_aligned_fasta'))
    patches = [patch.object(obj, key, forbidden) for obj, key in targets]
    for guard in patches: guard.start()
    try:
        for record in saved[:2]:
            assert msa_native_entropy(**record['entropy_arguments']) == record['entropy_components']
            changed = deepcopy(record['entropy_arguments'])
            changed['native_rounding'] = None
            new = msa_native_entropy(**changed)
            assert all(s['native_score_recalculated']['state'] == 'not_measured' for s in new['sites'])
            assert [s['literal_entropy_bits'] for s in new['sites']] == [s['literal_entropy_bits'] for s in record['entropy_components']['sites']]
        assert msa_reference_differences(**saved[2]['arguments']) == saved[2]['reference_components']
        assert msa_reference_differences(**saved[2]['missing_map_arguments']) == saved[2]['missing_map_components']
    finally:
        for guard in reversed(patches): guard.stop()
    write_json(OWN / 'SAVED_REPLAY_RESULT.json', {'status': 'passed', 'saved_examples': 3,
        'literal_entropy_sites': 13, 'reference_comparisons': 7, 'changed_rounding_replays': 2,
        'blocked_calls': [obj.__name__ + '.' + key for obj, key in targets],
        'complete_AppService_execution': False, 'episode_communication_verified': False})
    owned = [ROOT / 'gene_annotation_episode' / name for name in (
        'bvbrc_msa_formats.py', 'bvbrc_msa_format_contracts.py', 'bvbrc_msa_calculators.py',
        'bvbrc_msa_calculation_contracts.py')]
    sources = [BOUNDARY / 'retained_sources/p3_msa' / name for name in (
        'scripts/snp_analysis.pl', 'service-scripts/App-MSA.pl', 'lib/MSA_Sequence_Alignment.pm')]
    shared = [ROOT / 'gene_annotation_episode' / name for name in (
        'bvbrc_alignment_values.py', 'phylogeny_formats.py', 'phylogeny_format_contracts.py',
        'phylogeny_calculators.py', 'phylogeny_calculation_contracts.py')]
    tests = list((ROOT / 'tests').glob('test_bvbrc_msa_*.py'))
    write_json(OWN / 'READ_AND_IMPLEMENTATION_IDENTITIES.json', {'owned': [identity(p) for p in owned],
        'tests': [identity(p) for p in sorted(tests)], 'native_sources': [identity(p) for p in sources],
        'shared_consumers_and_dependencies': [identity(p) for p in shared]})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-reference', action='store_true')
    args = parser.parse_args()
    if args.native_reference:
        native_reference()
    summary = examples()
    print(json.dumps({'native_sites': len(summary), 'all_native_score_residuals_zero':
        all(row['score_residual'] == 0 for row in summary), 'offline_saved_replay': 'passed',
        'native_reference_branch_executed': args.native_reference, 'full_tool_integration': False}))
