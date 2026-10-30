"""Read-only source/context inventory and controlled provider-dispatch evidence.

Writes only this NEW verification directory. No model, network, native execution,
scientific action, episode/controller or source mutation is performed.
"""
import ast
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs/msa_dna-_7cous9_'

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for folder in ('gene_annotation_episode', 'method_loop')
            for p in sorted((ROOT / folder).rglob('*.py'))}

def function_source(path, name):
    text = (ROOT / path).read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            yield node, ast.get_source_segment(text, node)

def instruction_for(role, context):
    from gene_annotation_episode.runtime import INSTRUCTIONS
    from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE
    from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH
    if role == 'scientific_process':
        node, _ = next(function_source('gene_annotation_episode/scientific_process_episodes.py', 'instructions'))
        instructions = next(n.value.value for n in ast.walk(node)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str) and n.value.value.startswith('Determine what'))
    elif role in {'launch', 'launch_api', 'results'}:
        from gene_annotation_episode.execution_episodes import ExecutionEpisodes
        binding = object.__new__(ExecutionEpisodes)
        binding._validate_request = lambda value: value
        instructions = binding.instructions(SimpleNamespace(role=role, assignment=context['execution_assignment']))
    else:
        instructions = INSTRUCTIONS
    return instructions + (KNOWLEDGE if 'tool_knowledge' in context else '') + (LAUNCH if 'launch_instruction_library' in context else '')

async def main():
    from gene_annotation_episode.providers import _SessionConnection, load_config
    from gene_annotation_episode.decision_context import state_frame, INSTRUCTIONS as EXCHANGE
    source_before = source_hashes()
    database = RUN / 'state/state.sqlite3'
    original_files = [database, *(p for p in RUN.glob('*.json') if p.is_file())]
    originals_before = {str(p.relative_to(ROOT)): sha(p) for p in original_files}
    db = sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    samples = {}
    for ep in db.execute('SELECT episode_id,path,state FROM runtime_episodes ORDER BY rowid'):
        role = json.loads(ep['path'])[-1][0]
        assert ep['state'] == 'yielded', 'Do not use active Stores as closed evidence'
        rows = db.execute('SELECT call_index,request FROM runtime_model_calls WHERE episode_id=? ORDER BY call_index', (ep['episode_id'],)).fetchall()
        rows = [rows[0], rows[-1]] if len(rows) > 1 else [rows[0]]
        samples[role] = []
        for row in rows:
            saved = json.loads(row['request'])
            value = {'role': role, 'episode_id': ep['episode_id'], 'call_index': row['call_index'],
                'provenance': 'Closed controlled Workflow; retained native byte examples served by loopback HTTP; scripted decisions; no new native execution; no live BV-BRC; no configured model.',
                'request': saved}
            samples[role].append(value)
            write('retained_' + role + '_' + str(row['call_index']) + '.json', value)
    # Original numerical observations only, never a refit or new controller history.
    observations = [dict(row) for row in db.execute('SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index')]
    actions = [dict(row) for row in db.execute('SELECT episode_id,decision_index,action,credit FROM runtime_actions ORDER BY episode_id,decision_index')]
    write('retained_action_observations.json', {'observations': observations, 'actions': actions})
    db.close()

    class Wire(_SessionConnection):
        def __init__(self, path):
            super().__init__(load_config(), path, ROOT)
            self.sent = []
            self.turn = 0
        async def _rpc(self, method, params):
            self.sent.append((method, deepcopy(params)))
            if method == 'thread/start':
                return {'thread': {'id': 'controlled-thread'}, 'model': params['model'],
                    'reasoningEffort': params['config']['model_reasoning_effort']}
            assert method == 'turn/start'
            self.turn += 1
            turn = 'controlled-turn-' + str(self.turn)
            self.pending.extend([
                {'method': 'item/completed', 'params': {'threadId': 'controlled-thread',
                    'item': {'type': 'agentMessage', 'text': '{"controlled_wire":true}'}}},
                {'method': 'turn/completed', 'params': {'threadId': 'controlled-thread',
                    'turn': {'id': turn, 'status': 'completed'}}}])
            return {'turn': {'id': turn}}

    checks = []
    for role, entries in samples.items():
        wire = Wire(OUT / ('wire_legacy_' + role))
        for sample in entries:
            context = sample['request']['context']
            instructions = instruction_for(role, context)
            await wire.complete(sample['episode_id'], 'REASONING', instructions, deepcopy(context), deepcopy(sample['request']['schema']))
        for sample, (_, sent) in zip(entries, [x for x in wire.sent if x[0] == 'turn/start']):
            actual = sent['input'][0]['text']
            checks.append({'role': role, 'boundary': 'original_saved_full_context', 'call_index': sample['call_index'],
                'starts_task': actual.startswith('TASK\n'), 'has_steering': '\nSTEERING\n' in actual,
                'json_fallback_equals_context': actual == json.dumps(sample['request']['context'], allow_nan=False),
                'actual_text_sha256': hashlib.sha256(actual.encode()).hexdigest()})
        # Synthetic transport frames wrapping exact retained states: dispatch proof,
        # not a claim that the original scripted run used decision_exchange_v1.
        wire = Wire(OUT / ('wire_frames_' + role))
        first, last = entries[0]['request']['context'], entries[-1]['request']['context']
        frames = [state_frame(first), state_frame(last, first),
            {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
             'decision_index': entries[-1]['call_index'], 'exchange_index': 0,
             'result': {'status': 'completed', 'view': 'own_attempts', 'records': [],
                        'total': 0, 'offset': 0, 'returned_count': 0, 'next_query': None, 'unavailable_reasons': []}}]
        instructions = instruction_for(role, first) + '\n' + EXCHANGE
        for frame in frames:
            await wire.complete(entries[0]['episode_id'], 'REASONING', instructions, frame, {})
        for frame, (_, sent) in zip(frames, [x for x in wire.sent if x[0] == 'turn/start']):
            actual = sent['input'][0]['text']
            checks.append({'role': role, 'boundary': frame['kind'], 'provenance': 'synthetic frame around retained original state',
                'starts_task': actual.startswith('TASK\n'), 'has_steering': '\nSTEERING\n' in actual,
                'json_fallback_equals_context': actual == json.dumps(frame, allow_nan=False)})
    originals_after = {str(p.relative_to(ROOT)): sha(p) for p in original_files}
    source_after = source_hashes()
    assert source_before == source_after
    assert originals_before == originals_after
    assert all(row['starts_task'] == (row['role'] == 'scientific_process') for row in checks)
    assert all(row['json_fallback_equals_context'] == (row['role'] != 'scientific_process') for row in checks)
    write('SOURCE_MANIFEST.json', source_before)
    write('PROVIDER_DISPATCH_EVIDENCE.json', {'status': 'observed_current_gap', 'new_workflow_run': False,
        'model_inference': False, 'network': False, 'native_execution': False,
        'source_unchanged': True, 'original_closed_run_files_unchanged': True,
        'original_files': originals_before, 'checks': checks,
        'counts': dict(Counter(row['boundary'] for row in checks))})
    print(json.dumps({'dispatch_calls': len(checks), 'roles': list(samples),
        'text_roles': ['scientific_process'], 'json_roles': [r for r in samples if r != 'scientific_process'],
        'source_files_unchanged': len(source_before), 'original_files_unchanged': len(originals_before)}))

if __name__ == '__main__':
    asyncio.run(main())
