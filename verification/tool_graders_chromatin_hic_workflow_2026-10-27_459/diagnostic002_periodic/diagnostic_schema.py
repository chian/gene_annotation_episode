"""Paired diagnostic only: unchanged real saved inputs, no episode execution."""
from pathlib import Path
import faulthandler
import hashlib
import json
import sys
import time

directory, input_path = map(Path, sys.argv[1:3])
mode = sys.argv[3]
assert mode in ('periodic', 'no_periodic')
fatal = (directory / 'fatal-faults.txt').open('w')
periodic = (directory / 'periodic-stacks.txt').open('w')
faulthandler.enable(file=fatal, all_threads=True)
if mode == 'periodic':
    faulthandler.dump_traceback_later(30, repeat=True, exit=False, file=periodic)

from jsonschema import Draft202012Validator
from gene_annotation_episode.runtime import _action_generation_schema, _decode_recorded_action_response
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.practical_execution_records import validate_assignment, validate_receipt
from gene_annotation_episode.practical_execution_credit import project_practical_credit

value = json.loads(input_path.read_bytes())
iterations = int(sys.argv[4]) if len(sys.argv) > 4 else value['iterations']
assert iterations > 0
manifest, receipts = value['practical']['manifest'], value['practical']['receipts']
assert len(receipts) == 1 and receipts[0]['tool_name'] == 'practical.job.start'
started = time.monotonic()
steps = (directory / 'steps.jsonl').open('w', buffering=1)
completed = 0


def record(stage, **fields):
    steps.write(json.dumps({'stage': stage, 'elapsed_seconds': time.monotonic() - started, **fields}) + '\n')


record('start', mode=mode, input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest())
for iteration in range(iterations):
    for ordinal, call in enumerate(value['calls']):
        schema, response = call['request']['schema'], call['response']
        record('provider_validation_start', iteration=iteration, call=ordinal)
        Draft202012Validator(_action_generation_schema(schema)).validate(response)
        record('domain_validation_start', iteration=iteration, call=ordinal)
        decoded = _decode_recorded_action_response(response, schema,
            recorded_selection=call['recorded_selection'])
        assert canonical(decoded['selection']) == canonical(call['recorded_selection'])
        Draft202012Validator(schema).validate(decoded)
        record('domain_validation_complete', iteration=iteration, call=ordinal)
    record('practical_validation_start', iteration=iteration)
    assert validate_assignment(manifest['assignment']) == manifest['assignment']
    for receipt in receipts:
        assert validate_receipt(receipt) == receipt
    credit = project_practical_credit(manifest['assignment'], manifest['initial_validations'], receipts)
    assert credit['credit'] == 7 and credit['initial_credit'] == 0
    completed += 1
    record('iteration_complete', iteration=iteration, original_practical_credit=credit['credit'])

faulthandler.cancel_dump_traceback_later()
result = {'mode': mode, 'completed_iterations': completed, 'retained_calls_per_iteration': len(value['calls']),
    'actual_receipt_count': len(receipts), 'original_practical_credit': credit['credit'],
    'elapsed_seconds': time.monotonic() - started, 'new_workflow_actions': 0, 'native_dispatches': 0}
(directory / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
