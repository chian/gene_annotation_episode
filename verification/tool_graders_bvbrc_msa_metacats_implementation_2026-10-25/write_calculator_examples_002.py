"""Correct the twelve-group example's R column tokens using retained R output.

001 used unpadded matrix ordinals in a field reserved for actual R column
tokens. The numerical counts/statistics were correct, but that provenance field
was not. Preserve 001 and supersede only this affected example. No native rerun.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import socket
import subprocess
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('examples001', HERE / 'write_calculator_examples_001.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
case = old.NATIVE / 'twelve_groups'
example = old.prepare(case)
runtime_path = old.NATIVE.parent / 'TWELVE_GROUP_ORDER_CHECK_001.json'
raw, _, evidence = old.bound(runtime_path)
runtime = json.loads(raw)
assert runtime['returncode'] == 0
tokens = re.findall(r'"([^\"]*)"', runtime['stdout'].splitlines()[2])
assert len(tokens) == 12 and tokens == [str(i).rjust(2) for i in range(1, 13)]
for group, token in zip(example['counts_arguments']['group_order'], tokens):
    assert int(token) == group['native_group_ordinal']
    group['r_group_token'] = token
    group['evidence'].append(evidence)
example['counts'] = old.metacats_group_counts(example['alignment'], **example['counts_arguments'])
answer = old.calculate(example)
prior = json.loads((HERE / 'EXAMPLES_001/twelve_groups-answer.json').read_text())
for collection in ('omnibus', 'pairs'):
    assert len(answer['statistics'][collection]) == len(prior['statistics'][collection])
    for a, b in zip(answer['statistics'][collection], prior['statistics'][collection]):
        assert (a['column_0based'], a['group_ids']) == (b['column_0based'], b['group_ids'])
        for key in ('chi_square', 'df', 'mathematical_p', 'log_p', 'native_zero_rule_p'):
            assert a[key]['value'] == b[key]['value']
saved = json.dumps(example, allow_nan=False)
with patch('builtins.open', old.forbidden), patch.object(Path, 'read_bytes', old.forbidden), \
        patch.object(Path, 'read_text', old.forbidden), patch.object(socket, 'socket', old.forbidden), \
        patch.object(subprocess, 'Popen', old.forbidden), \
        patch('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', old.forbidden):
    replay = json.loads(saved)
    assert old.calculate(replay) == answer
    changed = deepcopy(replay)
    changed['statistical_parameters']['epsilon'] = .01
    changed_answer = old.calculate(changed)
target = HERE / 'EXAMPLES_002'
target.mkdir(exist_ok=False)
receipt = {'supersedes_example_only': 'EXAMPLES_001/twelve_groups',
    'reason': 'Unpadded native matrix ordinals were incorrectly stored as actual R column tokens in 001.',
    'correction': 'Exact padded R tokens and their retained runtime evidence now populate GroupColumnBinding.',
    'native_programs_rerun': False, 'numerical_statistics_unchanged': True,
    'saved_no_io_replay_equal': True,
    'inputs': old.save(target / 'twelve_groups-inputs.json', example),
    'answer': old.save(target / 'twelve_groups-answer.json', answer),
    'changed_epsilon_answer': old.save(target / 'twelve_groups-epsilon001-answer.json', changed_answer)}
old.save(target / 'CORRECTION_002.json', receipt)
print(json.dumps({'corrected_cases': 1, 'saved_no_io_replay_equal': True,
                  'numerical_statistics_unchanged': True, 'native_programs_rerun': False}))
