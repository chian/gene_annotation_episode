from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_metacats_calculators import (
    metacats_group_counts, metacats_statistics, metacats_effects, adjust_p_values)
from test_bvbrc_metacats_biological_calculators import SAVED


CASES = ('aa_three_groups', 'aa_two_groups', 'all_missing', 'metadata_only_first_group',
         'native_pair_tail_underflow', 'official_na', 'twelve_groups')


def load_case(case):
    path = SAVED / ('EXAMPLES_002' if case == 'twelve_groups' else 'EXAMPLES_001')
    return (json.loads((path / (case + '-inputs.json')).read_text()),
            json.loads((path / (case + '-answer.json')).read_text()))


def calculate_saved(example, family):
    stats = metacats_statistics(example['counts'], **example['statistical_parameters'])
    effects = metacats_effects(example['counts'], **example['effect_parameters'])
    family = {**family, 'test_ids': [r['test_id'] for r in stats['omnibus']]}
    adjusted = adjust_p_values(tuple({'test_id': r['test_id'], 'value': r['mathematical_p']}
        for r in stats['omnibus']), family=family, method='holm', alpha=.05,
        dependence_assumption='none_required_between_tests')
    return {'statistics': stats, 'effects': effects, 'holm': adjusted}


def identity_map(old_counts, new_counts, old_answer, new_answer):
    mapping, records = {}, []
    old_tests = old_answer['statistics']['omnibus'] + old_answer['statistics']['pairs']
    new_tests = new_answer['statistics']['omnibus'] + new_answer['statistics']['pairs']
    assert len(old_tests) == len(new_tests)
    for old_site, new_site in zip(old_counts['sites'], new_counts['sites']):
        old_id, new_id = old_site['table_id'], new_site['table_id']
        mapping[old_id] = new_id
        old_ids = [t['test_id'] for t in old_tests if t['raw_table_id'] == old_id]
        new_ids = [t['test_id'] for t in new_tests if t['raw_table_id'] == new_id]
        assert len(old_ids) == len(new_ids)
        mapping.update(zip(old_ids, new_ids))
        records.append({'old_table_id': old_id, 'new_table_id': new_id,
                        'old_test_ids': old_ids, 'new_test_ids': new_ids})
    return mapping, records


def substitute_ids(value, mapping):
    """Verification-only correspondence, never a production identity alias."""
    if isinstance(value, dict):
        return {k: substitute_ids(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute_ids(v, mapping) for v in value]
    if isinstance(value, str):
        base, separator, suffix = value.partition('/')
        if base in mapping:
            return mapping[base] + separator + suffix
    return value


@pytest.mark.parametrize('case', CASES)
def test_historical_saved_count_replay_is_exact_with_io_and_native_execution_disabled(case, monkeypatch):
    old, expected = load_case(case)
    before = json.dumps(old, sort_keys=True, allow_nan=False)
    def forbidden(*args, **kwargs): raise AssertionError('saved_replay_attempted_io_or_native_work')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_input_formats.parse_metacats_input_fasta', forbidden)
    assert calculate_saved(old, expected['holm']['family']) == expected
    assert json.dumps(old, sort_keys=True, allow_nan=False) == before
    assert all(s['table_id'].startswith('metacats_counts:') for s in old['counts']['sites'])


@pytest.mark.parametrize('case', CASES)
def test_future_native_rebuild_changes_only_identities_and_their_references(case):
    old, expected = load_case(case)
    snapshot = deepcopy(old)
    new_counts = metacats_group_counts(old['alignment'], **old['counts_arguments'])
    assert all(s['table_id'].startswith('metacats_counts_v2:') for s in new_counts['sites'])
    rebuilt = {**old, 'counts': new_counts}
    answer = calculate_saved(rebuilt, expected['holm']['family'])
    mapping, records = identity_map(old['counts'], new_counts, expected, answer)
    assert len(records) == len(old['counts']['sites'])
    assert substitute_ids(old['counts'], mapping) == new_counts
    assert substitute_ids(expected, mapping) == answer
    assert old == snapshot


def test_confirmed_native_count_collision_now_has_two_distinct_future_ids():
    collision = json.loads((SAVED / 'NATIVE_COUNT_IDENTITY_COLLISION_004.json').read_text())
    original = metacats_group_counts(collision['alignment'], **collision['original_parameters'])
    changed = metacats_group_counts(collision['alignment'], **collision['changed_parameters'])
    assert collision['original_counts']['sites'][0]['table_id'] == collision['changed_counts']['sites'][0]['table_id']
    assert original['sites'][0]['table_id'] != changed['sites'][0]['table_id']
    assert original['sites'][0]['observed_counts'] == [[6, 0], [0, 6]]
    assert changed['sites'][0]['observed_counts'] == [[3, 3], [3, 3]]
    for key, counts in (('original', original), ('changed', changed)):
        args = collision[key + '_parameters']
        alignment = collision['alignment']
        payload = {'analysis_id': args['analysis_id'], 'population': args['population'],
            'alignment_id': alignment['alignment_id'], 'artifact': alignment['artifact'],
            'category_id': args['category_id'], 'group_order': args['group_order'], 'column': 0,
            'parameters': {k: args[k] for k in ('case_policy', 'terminal_mask', 'native_input_hash_policy')},
            'assignments': sorted(args['assignments'], key=lambda row: row['row_index'])}
        expected_id = 'metacats_counts_v2:' + hashlib.sha256(json.dumps(payload, sort_keys=True,
            separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        assert counts['sites'][0]['table_id'] == expected_id


def test_native_assignment_permutation_preserves_id_and_full_assignment_changes_it():
    old, _ = load_case('aa_two_groups')
    args = deepcopy(old['counts_arguments'])
    original = metacats_group_counts(old['alignment'], **args)
    args['assignments'].reverse()
    assert metacats_group_counts(old['alignment'], **args) == original
    args['assignments'][0]['member_key']['occurrence_index'] += 1
    amended = metacats_group_counts(old['alignment'], **args)
    assert amended['sites'][0]['observed_counts'] == original['sites'][0]['observed_counts']
    assert amended['sites'][0]['table_id'] != original['sites'][0]['table_id']
