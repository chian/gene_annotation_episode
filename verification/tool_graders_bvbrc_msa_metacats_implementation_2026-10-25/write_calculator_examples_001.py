"""Retain complete numerical examples; no service or native program is run."""
from copy import deepcopy
import builtins
import hashlib
import itertools
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
from unittest.mock import patch

import scipy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from gene_annotation_episode.bvbrc_metacats_calculators import (
    metacats_group_counts, metacats_statistics, metacats_effects, adjust_p_values)

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / 'tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases'
BACKEND = {'name': 'scipy_chi2_integer_df_logtail_v1', 'version': scipy.__version__}


def save(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def bound(path):
    data = path.read_bytes()
    name = str(path.relative_to(ROOT))
    artifact = {'raw_artifact_ref': name, 'source_ref': name, 'sha256': hashlib.sha256(data).hexdigest()}
    evidence = {'content': {'source_ref': name, 'artifact_field': 'artifact_ref', 'artifact_ref': name,
        'sha256': artifact['sha256'], 'byte_count': len(data)}, 'pointer': ''}
    return data, artifact, evidence


def prepare(case):
    receipt = json.loads((case / 'RECEIPT.json').read_text())
    for name, original in receipt['files'].items():
        data = (case / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == original['sha256'] and len(data) == original['bytes']
    data, artifact, alignment_evidence = bound(case / 'original.fasta')
    alignment = parse_aligned_fasta(data, artifact=artifact, id_rule='first_whitespace_token')['value']
    metadata_bytes, _, metadata_evidence = bound(case / 'metadata.tsv')
    metadata_rows = [line.split('\t') for line in metadata_bytes.decode().splitlines()]
    category = metadata_rows[0][1]
    metadata = {row[0]: (i, row[1]) for i, row in enumerate(metadata_rows[1:])}
    assert len(metadata) == len(metadata_rows) - 1
    matrix_files = list((case / 'output').glob('*.txt'))
    assert len(matrix_files) == 1
    matrix_bytes, _, matrix_evidence = bound(matrix_files[0])
    native_ordinals = {line.split()[0]: int(line.split()[1]) for line in matrix_bytes.decode().splitlines()}
    group_ordinals = {}
    for member, ordinal in native_ordinals.items():
        group = metadata[member][1]
        assert group_ordinals.setdefault(group, ordinal) == ordinal
    # Explicit source-backed scientific group order. No exported label is used
    # to join samples. Native R character padding is not inferred from this file.
    ordered = sorted(group_ordinals, key=group_ordinals.get)
    groups = [{'category_id': category, 'r_column_index_0based': i,
        'r_group_token': str(group_ordinals[group]), 'native_group_ordinal': group_ordinals[group],
        'group_id': group, 'exported_heading_index_0based': None, 'exported_label_token': None,
        'state': 'resolved', 'evidence': [metadata_evidence, matrix_evidence]} for i, group in enumerate(ordered)]
    assignments = []
    for row in alignment['rows']:
        member = row['member_label']
        metadata_index, group = metadata[member]
        assignments.append({'category_id': category, 'alignment_id': alignment['alignment_id'],
            'row_index': row['row_index'], 'member_key': {'input_binding_id': artifact['raw_artifact_ref'],
            'member_id': member, 'occurrence_index': 0}, 'metadata_row_index': metadata_index,
            'metadata_column_index': 1, 'raw_group_value': group,
            'native_group_ordinal': native_ordinals[member], 'displayed_group_label': None,
            'state': 'resolved', 'evidence': [metadata_evidence, matrix_evidence]})
    population = {'population_id': case.name + '/whole', 'alignment_id': alignment['alignment_id'],
        'row_indices': list(range(len(alignment['rows']))),
        'columns_0based': list(range(alignment['observed_column_count'])),
        'completeness': 'complete', 'evidence': [alignment_evidence]}
    counts_args = {'analysis_id': case.name, 'population': population, 'assignments': assignments,
        'category_id': category, 'group_order': groups, 'case_policy': 'preserve',
        'terminal_mask': 'native_terminal_dash_to_hash', 'native_input_hash_policy': 'exclude_hash'}
    counts = metacats_group_counts(alignment, **counts_args)
    # All these pairs are explicit verification selections, not a production default.
    pairs = list(itertools.combinations(ordered, 2))
    parameters = {'alphabet': receipt['alphabet'], 'epsilon': .001,
        'nucleotide_padding': 'ACGT_at_variable_sites', 'omnibus_continuity': 'r_default_2x2_min_delta',
        'pair_df_policy': 'native_source', 'pair_zero_policy': 'retain_math_and_native_zero_to_one',
        'selected_pairs': pairs, 'distribution_backend': BACKEND}
    return {'input_kind': receipt['input_kind'], 'alignment': alignment,
        'original_metadata_rows': metadata_rows, 'counts_arguments': counts_args,
        'counts': counts, 'statistical_parameters': parameters,
        'effect_parameters': {'selected_pairs': pairs, 'zero_margin_policy': 'drop_for_raw_effect_only'}}


def calculate(example):
    statistics = metacats_statistics(example['counts'], **example['statistical_parameters'])
    effects = metacats_effects(example['counts'], **example['effect_parameters'])
    family = {'family_id': example['counts']['analysis_id'] + '/all_variable_omnibus',
        'analysis_ids': [example['counts']['analysis_id']], 'category_ids': [example['counts']['category_id']],
        'test_kind': 'omnibus', 'test_ids': [r['test_id'] for r in statistics['omnibus']],
        'eligibility': 'variable_site_positive_df', 'population_state': 'complete',
        'total_test_count': len(statistics['omnibus']), 'assumption': None,
        'p_value_basis': 'source_mathematical_recalculation', 'evidence': example['counts_arguments']['population']['evidence']}
    p = [{'test_id': row['test_id'], 'value': row['mathematical_p']} for row in statistics['omnibus']]
    adjusted = adjust_p_values(p, family=family, method='holm', alpha=.05,
        dependence_assumption='none_required_between_tests')
    return {'statistics': statistics, 'effects': effects, 'holm': adjusted}


def forbidden(*args, **kwargs):
    raise AssertionError('saved_calculation_attempted_acquisition_or_parse')


def main():
    target = HERE / 'EXAMPLES_001'
    target.mkdir(exist_ok=False)
    records = []
    for case in sorted(NATIVE.iterdir()):
        example = prepare(case)
        answer = calculate(example)
        native = {}
        paths = list((case / 'output/retained_raw').glob('*-chisqTable.txt'))
        assert len(paths) == 1
        for line in paths[0].read_text().splitlines():
            match = re.match(r'^\s*Site(\d+)\s*\t(.*)', line)
            if match:
                fields = [s.strip() for s in match[2].split('\t')]
                if fields[0] != 'NA':
                    native[int(match[1]) - 1] = (float(fields[0]), float(fields[1]), int(fields[2]))
        assert len(native) == len(answer['statistics']['omnibus'])
        import math
        for row in answer['statistics']['omnibus']:
            stat, p, df = native[row['column_0based']]
            assert math.isclose(row['chi_square']['value'], stat, rel_tol=1e-12, abs_tol=1e-12)
            assert row['df']['value'] == df
            if p == 0:
                assert row['mathematical_p']['value'] is None and row['log_p']['value'] < -700
            else:
                assert math.isclose(row['mathematical_p']['value'], p, rel_tol=1e-12, abs_tol=1e-14)
        serialized = json.dumps(example, allow_nan=False)
        with patch('builtins.open', forbidden), patch.object(Path, 'read_bytes', forbidden), \
                patch.object(Path, 'read_text', forbidden), patch.object(socket, 'socket', forbidden), \
                patch.object(subprocess, 'Popen', forbidden), \
                patch('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden):
            replay = json.loads(serialized)
            assert calculate(replay) == answer
            changed = deepcopy(replay)
            changed['statistical_parameters']['epsilon'] = .01
            recalculated = calculate(changed)
            assert replay == json.loads(serialized)
        records.append({'case': case.name, 'input_kind': example['input_kind'],
            'input': save(target / (case.name + '-inputs.json'), example),
            'answer': save(target / (case.name + '-answer.json'), answer),
            'changed_epsilon_answer': save(target / (case.name + '-epsilon001-answer.json'), recalculated),
            'native_variable_tests_compared': len(native), 'saved_no_io_replay_equal': True})
    sources = [ROOT / 'gene_annotation_episode' / name for name in (
        'bvbrc_alignment_values.py', 'bvbrc_metacats_calculators.py', 'bvbrc_metacats_calculation_contracts.py')]
    manifest = {'scope': 'Pure production calculations on seven retained native-input cases; no service, producer or episode executed',
        'backend': BACKEND, 'cases': records,
        'association_qualification': 'Original identifiers and observed adjusted-matrix ordinals are retained. Group order is explicitly supplied for scientific arithmetic. No deployed R locale/order or exported display-label association is newly claimed.',
        'sources_at_verification': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]}
    save(target / 'manifest.json', manifest)
    print(json.dumps({'cases': len(records), 'native_variable_tests': sum(x['native_variable_tests_compared'] for x in records),
        'saved_no_io_replays': len(records), 'new_service_or_native_runs': 0}))


if __name__ == '__main__':
    main()
