"""Apply the real corrected presentation to immutable original run009 contexts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.alignment_result_presentation import alignment_report_presentation
from gene_annotation_episode.bvbrc_alignment_bundle_contracts import decode_reference
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt

source = EVIDENCE / 'runs/msa_dna-_7cous9_'
output = EVIDENCE / 'recorded-prompt-030'
output.mkdir()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def all_hashes(directory):
    return {str(p.relative_to(directory)): sha(p) for p in directory.rglob('*') if p.is_file()}
before = all_hashes(source)
producer_paths = [ROOT / 'gene_annotation_episode' / name for name in
    ('scientific_process_prompt.py', 'alignment_result_presentation.py')]
producer_before = {str(p.relative_to(ROOT)): sha(p) for p in producer_paths}
def forbidden(*args, **kwargs):
    raise AssertionError('Recorded prompt check attempted network or subprocess execution')
socket.socket.connect = forbidden
subprocess.run = forbidden
subprocess.Popen = forbidden

body = json.loads((source / 'publication.json').read_text())
result_source = body['source_ref']
pin = body['publication_inputs']['adapter_implementation_sha256']
results_id = body['episode_id']
checks = []

def numbers(value):
    if type(value) in (int, float):
        return [value]
    if isinstance(value, dict):
        return [number for child in value.values() for number in numbers(child)]
    if isinstance(value, list):
        return [number for child in value for number in numbers(child)]
    return []

with sqlite3.connect('file:' + str(source / 'state/state.sqlite3') + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT m.* FROM runtime_model_calls m JOIN runtime_episodes e USING(run_id,episode_id) "
        "WHERE json_extract(e.path,'$[#-1][0]')='scientific_process' ORDER BY m.call_index").fetchall()
    for index, row in enumerate(rows):
        original_text = (source / f'scientific-presentation-{index}.txt').read_text()
        original_task, original_steering = original_text.split('\n\nSTEERING', 1)
        # The exact prior recurring instruction block is retained in its TASK.
        instructions = original_task.split('\n\nAssigned work\n\n', 1)[0].removeprefix('TASK\n\n')
        context = json.loads(row['request'])['context']
        untouched = deepcopy(context)
        current = render_scientific_process_prompt(context, instructions)
        task, steering = current.split('\n\nSTEERING', 1)
        assert task == original_task
        assert context == untouched
        negatives = (result_source, pin, row['episode_id'], results_id)
        assert all(value not in current for value in negatives)
        fields = []
        for report in context.get('child_reports', []):
            projected = alignment_report_presentation(report)
            assert numbers(projected) == numbers(report)
            for name, entries in report.items():
                if not isinstance(entries, list):
                    continue
                for offset, entry in enumerate(entries):
                    if not isinstance(entry, dict) or set(entry) != {'source_ref', 'field', 'value'}:
                        continue
                    if not entry['field'].startswith('bvbrc_alignment_field:'):
                        continue
                    _, _, field = decode_reference(entry['field'])
                    presented = projected[name][offset]
                    assert presented['selected_field'] == field
                    if isinstance(entry['value'], dict):
                        for key in ('value', 'unit', 'units', 'origin', 'status', 'numerator', 'denominator', 'uncertainty'):
                            if key in entry['value']:
                                assert presented['value'][key] == entry['value'][key]
                    if field == 'missing':
                        assert len(presented['value']) == len(entry['value'])
                        for old, new in zip(entry['value'], presented['value']):
                            for key in ('reason_code', 'reason', 'role', 'requirement_id'):
                                if key in old:
                                    assert old[key] == new[key]
                    fields.append(field)
        (output / f'scientific-presentation-{index}.txt').write_text(current)
        checks.append({'call_index': row['call_index'], 'task_unchanged': True,
            'context_unchanged': True, 'negative_identifiers_absent': True,
            'old_result_source_occurrences': original_steering.count(result_source),
            'new_result_source_occurrences': steering.count(result_source),
            'projected_selected_fields': fields, 'all_numbers_preserved': True,
            'old_steering_lines': len(original_steering.splitlines()),
            'new_steering_lines': len(steering.splitlines()),
            'new_prompt_sha256': hashlib.sha256(current.encode()).hexdigest()})

assert len(checks) == 9
assert sum(bool(item['old_result_source_occurrences']) for item in checks) == 6
after = all_hashes(source)
assert before == after
producer_after = {str(p.relative_to(ROOT)): sha(p) for p in producer_paths}
assert producer_before == producer_after
receipt = {'status': 'recorded_prompt_assertions_passed', 'workflow_started': False,
    'configured_model_used': False, 'original_run_unchanged': True,
    'source_run': str(source.relative_to(ROOT)), 'producer_hashes': producer_after,
    'script_sha256': sha(Path(__file__)), 'checks': checks}
(EVIDENCE / 'recorded-prompt-030.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'contexts': len(checks),
    'previously_affected_contexts': 6, 'original_run_unchanged': True}))
