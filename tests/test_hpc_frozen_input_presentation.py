"""Replay original oversized HPC inputs without executing a model or native job."""
from copy import deepcopy
import hashlib


from gene_annotation_episode.episodic_workflow.root.hpc_prompt import plan_outcome_view


def test_file_descriptors_use_utf8_bytes_and_keep_declared_digest_visible():
    text = '# molecule \u03b1\n'
    outcome = {'result': {'plan_id': 'plan-original', 'original_prediction': {},
        'practical_assignment': {'requested_job': {'argv': ['actual-command']}},
        'supplied_files': [{'path': '/actual/input.py', 'text': text, 'sha256': 'declared-digest'}]}}
    saved = deepcopy(outcome)
    shown = plan_outcome_view(outcome)['result']['supplied_files'][0]
    assert outcome == saved
    assert shown['sha256'] == 'declared-digest'
    assert shown['text_sha256'] == hashlib.sha256(text.encode('utf-8')).hexdigest()
    assert shown['text_size_bytes'] == len(text.encode('utf-8'))
    assert plan_outcome_view({'result': {'stdout': text}})['result']['stdout'] == text


def test_nested_launch_parameters_are_preserved_as_exact_operands():
    candidate = {'id': 'original', 'queue': 'assigned', 'nodes': 1, 'wall_seconds': 900,
        'units': [], 'preparation': '', 'files': [
            {'path': 'original.txt', 'text': 'Frozen operand\n', 'sha256': 'declared'}]}
    plan = {'plan_id': 'original-plan', 'original_prediction': {},
        'practical_assignment': {'parameters': candidate},
        'launch_assignment': {'parameters': candidate},
        'supplied_files': deepcopy(candidate['files'])}
    original = deepcopy(plan)
    shown = plan_outcome_view({'history': [{'outcome': {'result': plan}}]})['history'][0]['outcome']['result']
    assert shown['practical_assignment'] == original['practical_assignment']
    assert shown['launch_assignment'] == original['launch_assignment']
    assert 'text' not in shown['supplied_files'][0]
    assert plan == original
