"""Retain biological examples, exact old replay and explicit future ID maps.

This script performs verification on supplied retained files only. It never
reruns a native producer or contacts a service. Existing artifacts are read-only;
all new artifacts are created exclusively below this assigned directory.
"""
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.bvbrc_metacats_input_formats import parse_metacats_input_fasta
from gene_annotation_episode.bvbrc_metacats_biological_calculators import (
    biological_group_counts, biological_group_statistics, biological_group_effects)
from gene_annotation_episode.bvbrc_metacats_calculators import (
    metacats_group_counts, metacats_statistics, metacats_effects, adjust_p_values)
from gene_annotation_episode.bvbrc_metacats_adequacy import expected_count_adequacy

ORIGINAL = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'


def bound(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def save(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    return bound(path)


def native_answer(example, family):
    statistics = metacats_statistics(example['counts'], **example['statistical_parameters'])
    effects = metacats_effects(example['counts'], **example['effect_parameters'])
    family = {**family, 'test_ids': [r['test_id'] for r in statistics['omnibus']]}
    p = tuple({'test_id': row['test_id'], 'value': row['mathematical_p']} for row in statistics['omnibus'])
    holm = adjust_p_values(p, family=family, method='holm', alpha=.05,
                          dependence_assumption='none_required_between_tests')
    return {'statistics': statistics, 'effects': effects, 'holm': holm}


def biological_inputs(old):
    metadata_rows = old['original_metadata_rows']
    metadata = {row[0]: row[1] for row in metadata_rows[1:]}
    assert len(metadata) == len(metadata_rows) - 1
    # The group's first occurrence in original metadata supplies this example's
    # explicitly selected biological column order. It is not alleged R order.
    group_ids = list(dict.fromkeys(row[1] for row in metadata_rows[1:]))
    category, analysis = metadata_rows[0][1], old['counts']['analysis_id']
    evidence = deepcopy(old['counts_arguments']['assignments'][0]['evidence'][:1])
    population = deepcopy(old['counts_arguments']['population'])
    args = {'analysis_id': analysis, 'population': population, 'category_id': category,
        'assignments': [{'category_id': category, 'alignment_id': old['alignment']['alignment_id'],
            'row_index': row['row_index'], 'member_key': None,
            'group_id': metadata[row['member_label']], 'state': 'resolved', 'evidence': evidence}
            for row in old['alignment']['rows']],
        'group_population': {'group_population_id': analysis + '/biological_groups',
            'category_id': category, 'groups': [{'group_id': group, 'raw_group_value': group,
                'evidence': evidence} for group in group_ids], 'completeness': 'complete', 'evidence': evidence},
        'case_policy': 'preserve', 'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'}
    params = {k: deepcopy(v) for k, v in old['statistical_parameters'].items() if k != 'pair_zero_policy'}
    params['pair_df_policy'] = 'standard_pair'
    params['selected_pairs'] = [list(p) for p in itertools.combinations(group_ids, 2)]
    counts = biological_group_counts(old['alignment'], **args)
    return {'input_kind': old['input_kind'], 'alignment': deepcopy(old['alignment']),
        'counts_arguments': args, 'counts': counts, 'statistical_parameters': params,
        'effect_parameters': {'selected_pairs': params['selected_pairs'], 'zero_margin_policy': 'drop_for_raw_effect_only'}}


def biological_answer(example):
    stats = biological_group_statistics(example['counts'], **example['statistical_parameters'])
    effects = biological_group_effects(example['counts'], **example['effect_parameters'])
    family = {'family_id': example['counts']['analysis_id'] + '/all_biological_variable_omnibus',
        'analysis_ids': [example['counts']['analysis_id']], 'category_ids': [example['counts']['category_id']],
        'test_kind': 'omnibus', 'test_ids': [row['test_id'] for row in stats['omnibus']],
        'eligibility': 'variable_site_positive_df', 'population_state': 'complete',
        'total_test_count': len(stats['omnibus']), 'assumption': None,
        'p_value_basis': 'biological_mathematical_recalculation',
        'evidence': example['counts_arguments']['population']['evidence']}
    p = tuple({'test_id': row['test_id'], 'value': row['mathematical_p']} for row in stats['omnibus'])
    return {'statistics': stats, 'effects': effects,
        'expected_adequacy': expected_count_adequacy(stats, statistics_kind='biological'),
        'holm': adjust_p_values(p, family=family, method='holm', alpha=.05,
                                dependence_assumption='none_required_between_tests')}


def identity_map(old_counts, new_counts, old_answer, new_answer):
    mapping, records = {}, []
    old_tests = old_answer['statistics']['omnibus'] + old_answer['statistics']['pairs']
    new_tests = new_answer['statistics']['omnibus'] + new_answer['statistics']['pairs']
    assert len(old_tests) == len(new_tests)
    for a, b in zip(old_counts['sites'], new_counts['sites']):
        old_id, new_id = a['table_id'], b['table_id']
        mapping[old_id] = new_id
        old_ids = [t['test_id'] for t in old_tests if t['raw_table_id'] == old_id]
        new_ids = [t['test_id'] for t in new_tests if t['raw_table_id'] == new_id]
        assert len(old_ids) == len(new_ids)
        mapping.update(zip(old_ids, new_ids))
        records.append({'old_table_id': old_id, 'new_table_id': new_id,
                        'old_test_ids': old_ids, 'new_test_ids': new_ids})
    return mapping, records


def substitute_ids(value, mapping):
    if isinstance(value, dict):
        return {k: substitute_ids(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute_ids(v, mapping) for v in value]
    if isinstance(value, str):
        base, separator, tail = value.partition('/')
        if base in mapping:
            return mapping[base] + separator + tail
    return value


def forbidden(*args, **kwargs):
    raise AssertionError('saved_math_attempted_acquisition_or_native_execution')


def main():
    target = HERE / 'EXAMPLES_001'
    target.mkdir(exist_ok=False)
    source_manifest = json.loads((ORIGINAL / 'SAVED_REPLAY_FINAL_003.json').read_text())
    records, rekeys, historical = [], [], []
    for case in source_manifest['cases']:
        input_path = ROOT / case['effective_inputs']
        answer_path = input_path.with_name(input_path.name.replace('-inputs.json', '-answer.json'))
        old, expected = json.loads(input_path.read_text()), json.loads(answer_path.read_text())
        old_digest, answer_digest = bound(input_path), bound(answer_path)
        input_bytes = (ROOT / old['alignment']['artifact']['raw_artifact_ref']).read_bytes()
        parsed = parse_metacats_input_fasta(input_bytes, artifact=old['alignment']['artifact'])
        assert parsed['status'] == 'ok' and parsed['value'] == old['alignment']
        biological = biological_inputs(old)
        result = biological_answer(biological)
        old_before, bio_before = deepcopy(old), deepcopy(biological)
        with patch('builtins.open', forbidden), patch.object(Path, 'open', forbidden), \
                patch.object(Path, 'read_bytes', forbidden), patch.object(Path, 'read_text', forbidden), \
                patch.object(socket, 'socket', forbidden), patch.object(subprocess, 'Popen', forbidden), \
                patch('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden), \
                patch('gene_annotation_episode.bvbrc_metacats_input_formats.parse_metacats_input_fasta', forbidden):
            assert native_answer(old, expected['holm']['family']) == expected
            assert biological_answer(json.loads(json.dumps(biological))) == result
            assert biological_group_counts(biological['alignment'], **biological['counts_arguments']) == biological['counts']
            changed = deepcopy(biological)
            changed['statistical_parameters']['epsilon'] = .01
            changed_result = biological_answer(changed)
            new_counts = metacats_group_counts(old['alignment'], **old['counts_arguments'])
            rebuilt = native_answer({**old, 'counts': new_counts}, expected['holm']['family'])
            mapping, rows = identity_map(old['counts'], new_counts, expected, rebuilt)
            assert substitute_ids(old['counts'], mapping) == new_counts
            assert substitute_ids(expected, mapping) == rebuilt
            assert biological == bio_before and old == old_before
        assert bound(input_path) == old_digest and bound(answer_path) == answer_digest
        name = case['case']
        records.append({'case': name, 'input_kind': biological['input_kind'],
            'source_input': old_digest, 'source_answer': answer_digest,
            'input': save(target / (name + '-inputs.json'), biological),
            'answer': save(target / (name + '-answer.json'), result),
            'epsilon_0_01_answer': save(target / (name + '-epsilon001-answer.json'), changed_result),
            'column_count': len(biological['counts']['sites']), 'omnibus_tests': len(result['statistics']['omnibus']),
            'pair_tests': len(result['statistics']['pairs']), 'input_parser_matches_saved_alignment': True,
            'saved_no_io_replay_exact': True, 'inputs_unchanged': True})
        rekeys.append({'case': name, 'numerical_and_nonidentity_equality': True, 'mappings': rows})
        historical.append({'case': name, 'source_input': old_digest, 'source_answer': answer_digest,
                           'saved_count_replay_exact_including_identities': True, 'original_files_unchanged': True})
    collision_path = ORIGINAL / 'NATIVE_COUNT_IDENTITY_COLLISION_004.json'
    collision = json.loads(collision_path.read_text())
    original_new = metacats_group_counts(collision['alignment'], **collision['original_parameters'])
    changed_new = metacats_group_counts(collision['alignment'], **collision['changed_parameters'])
    assert original_new['sites'][0]['table_id'] != changed_new['sites'][0]['table_id']
    # Include actual selected statistics as well as both raw table identities.
    collision_params = deepcopy(old['statistical_parameters'])
    collision_params.update(alphabet='aa', selected_pairs=[['A', 'B']])
    collision_maps = []
    for key, rebuilt_counts in (('original', original_new), ('changed', changed_new)):
        old_stats = metacats_statistics(collision[key + '_counts'], **collision_params)
        new_stats = metacats_statistics(rebuilt_counts, **collision_params)
        mapping, rows = identity_map(collision[key + '_counts'], rebuilt_counts,
                                    {'statistics': old_stats}, {'statistics': new_stats})
        assert substitute_ids(collision[key + '_counts'], mapping) == rebuilt_counts
        assert substitute_ids(old_stats, mapping) == new_stats
        collision_maps.append({'case': key, 'mappings': rows, 'new_counts': rebuilt_counts,
                               'new_statistics': new_stats, 'numerical_and_nonidentity_equality': True})
    save(HERE / 'NATIVE_REKEY_MAPPINGS_001.json', {'purpose': 'Verification only; no production identity aliases or migration',
        'native_examples': rekeys, 'confirmed_collision_source': bound(collision_path), 'confirmed_collision': collision_maps})
    save(HERE / 'HISTORICAL_REPLAY_001.json', {'scope': 'Saved-count replay only, no producer/service/episode run',
        'cases': historical, 'all_acquisition_and_parsing_disabled': True})
    source_files = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in (
        'bvbrc_contingency_math', 'bvbrc_metacats_biological_contracts', 'bvbrc_metacats_biological_calculators',
        'bvbrc_metacats_adequacy', 'bvbrc_metacats_calculators', 'bvbrc_metacats_calculation_contracts',
        'bvbrc_alignment_values', 'phylogeny_calculation_contracts', 'phylogeny_format_contracts',
        'bvbrc_metacats_input_formats')]
    save(HERE / 'EXAMPLES_MANIFEST_001.json', {'scope': 'Saved inputs and complete numerical results; no production provider/episode completion',
        'cases': records, 'source_files': [bound(p) for p in source_files], 'script': bound(Path(__file__)),
        'new_service_calls': 0, 'new_native_runs': 0, 'new_hpc_jobs': 0,
        'association_qualification': 'Original unique metadata IDs supply explicit physical-row group joins. Original MemberKey is intentionally null. Biological order follows the declared first-occurrence order in original metadata, including metadata-only groups.'})
    print(json.dumps({'cases': len(records), 'columns': sum(r['column_count'] for r in records),
        'omnibus_tests': sum(r['omnibus_tests'] for r in records), 'pair_tests': sum(r['pair_tests'] for r in records),
        'exact_historical_replays': len(historical), 'future_rekey_cases': len(rekeys),
        'confirmed_collision_has_distinct_new_ids': True, 'new_native_or_service_runs': 0}))


if __name__ == '__main__':
    main()
