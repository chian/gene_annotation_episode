"""Export actual completed fixture records; never create execution evidence."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG


def forbidden(*args, **kwargs):
    raise AssertionError('Example export attempted live transport')


socket.create_connection = forbidden
socket.socket.connect = forbidden
urllib.request.OpenerDirector.open = forbidden

output = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--admitted-return-diagnostic', action='store_true',
    help='Export the retained run whose full return tests passed but replay comparison failed')
arguments = parser.parse_args()
if arguments.admitted_return_diagnostic:
    base = output / 'admitted-return-replay-diagnostic-state'
    report = json.loads((output / 'replay-assertion-diagnostic.pytest-result.json').read_text())
    log = (output / 'replay-assertion-diagnostic.PYTEST.txt').read_text()
    assert report['exit_code'] == 1 and '1 failed, 2 passed' in log
    suite_status = 'Two full-path tests passed; replay test failed at service/runtime wrapper comparison'
    examples = output / 'admitted-return-examples'
else:
    base = output / 'pytest-state' / 'homology-shared-workflow0'
    report = json.loads((output / 'pytest-result.json').read_text())
    assert report['exit_code'] == 0, 'Default export requires a passing completed suite'
    suite_status = 'All three full-path, partial-publication and replay tests passed'
    examples = output / 'examples'
examples.mkdir(exist_ok=True)


def write(name, value):
    (examples / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


with Store(base / 'state') as store:
    assert store.db.execute('SELECT count(*) FROM runtime_report_attempts WHERE failure IS NOT NULL').fetchone()[0] == 0
    forms = [dict(row) for row in store.db.execute('SELECT * FROM runtime_forms')]
    final_row, = [row for row in forms if 'measurements' in json.loads(row['form'])]
    returned = json.loads(final_row['form'])
    final_ref, = {row['source_ref'] for row in returned['measurements']}
    retained, = [json.loads(path.read_text()) for path in (base / 'run').rglob('bundle_publication.json')
        if final_ref in json.loads(path.read_text())['value']['result_record_refs']]
    publication = retained['value']
    inputs = json.loads(store.get_artifact(publication['publication_inputs_content']['artifact_ref']))
    config = deepcopy(CONFIG)
    config['scientific_adapters'] = [{'adapter_id': 'bvbrc_homology', 'adapter_version': '1',
        'implementation_sha256': inputs['adapter_implementation_sha256']}]
    api = APIServiceExecution(store, run_id=final_row['run_id'], directory=base / 'run',
        configuration={'selected-api': config}, tool_registry=ToolRegistry(store),
        handoff_unit=2, acquired_record_unit=3)
    context = api.appservice.custody.context(final_row['episode_id'])
    body = api.read_result(final_ref, context.scope)
    assert body['publication'] == publication
    write('final-result.json', body)
    write('parent-return.json', returned)
    write('original-request.json', inputs['request'])
    write('original-selector.json', inputs['selector'])
    for role, name in [('blast_json15_raw', 'native-result.json'),
                       ('job_result_manifest', 'native-task-manifest.json')]:
        artifact, = [row for row in body['bundle']['artifacts'] if row['role'] == role]
        raw = store.get_artifact(artifact['raw_artifact_ref'])
        assert hashlib.sha256(raw).hexdigest() == artifact['sha256']
        (examples / name).write_bytes(raw)
    saved = publication['adapter_result']
    sheet_bytes = store.get_artifact(saved['sheet_content']['artifact_ref'])
    component_bytes = store.get_artifact(saved['components_content']['artifact_ref'])
    (examples / 'populated-sheet.json').write_bytes(sheet_bytes)
    (examples / 'original-components.json').write_bytes(component_bytes)
    sheet = json.loads(sheet_bytes)
    recalculated = calculate_homology_scores(sheet, database_model={'temperature_bits': 1})
    assert sheet == json.loads(sheet_bytes)
    write('recalculated-components-temperature-1.json', recalculated)
    source = inputs['request']['input_bindings'][0]['members'][0]['evidence']['content']
    (examples / 'supplied-input.json').write_bytes(store.get_artifact(source['artifact_ref']))
    scientific = inputs['selector']['adapter']['parameters']['scientific_inputs']['content']
    (examples / 'supplied-scientific-inputs.json').write_bytes(store.get_artifact(scientific['artifact_ref']))
    partial_refs = []
    for row in store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=? ORDER BY decision_index',
                               (final_row['episode_id'],)):
        value = json.loads(row['result'])
        reference = value.get('result', {}).get('source_ref')
        if reference is not None and reference != final_ref:
            partial_refs.append(reference)
    partial_ref, = partial_refs
    write('partial-result.json', api.read_result(partial_ref, context.scope))
    counts = {}
    json_fields = {'runtime_model_calls': ('request', 'response', 'timing'),
                   'runtime_actions': ('action', 'result'),
                   'runtime_observations': ('observation',),
                   'runtime_report_attempts': ('contract', 'form', 'failure', 'timing_receipts')}
    for table, fields in json_fields.items():
        records = [dict(row) for row in store.db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
        counts[table] = len(records)
        for row in records:
            for key in fields:
                if row[key] is not None:
                    row[key] = json.loads(row[key])
        write(table + '.json', records)
    original = json.loads(component_bytes)['queries'][0]['conditional_function_weights']
    changed = recalculated['queries'][0]['conditional_function_weights']
    query = sheet['queries'][0]
    measured = query['blast_sheet']['hits'][0]['measurements']
    write('numerical-example.json', {
        'evidence_kind': 'Actual shared Workflow with controlled synthetic native responses and scripted decisions',
        'suite_status': suite_status, 'suite_result': report,
        'live_service_or_configured_model_executed': False,
        'run_id': final_row['run_id'], 'final_source_ref': final_ref,
        'partial_source_ref': partial_ref, 'adapter_implementation_sha256': inputs['adapter_implementation_sha256'],
        'returned_numbers': {row['field']: row['value'] for row in returned['measurements']},
        'paired_query_numerator': measured['observed_paired_query_positions'],
        'query_length_denominator': query['normalized_result']['query']['length'],
        'paired_reference_numerator': measured['observed_paired_reference_positions'],
        'reference_length_denominator': query['normalized_result']['hits'][0]['length'],
        'retained_hit_count': len(query['normalized_result']['hits']),
        'retained_hsp_count': sum(len(hit['hsps']) for hit in query['normalized_result']['hits']),
        'original_temperature': original['parameters']['temperature_bits'],
        'original_unannotated_kernel_mass': original['unannotated_reference_kernel_mass'],
        'recalculation_temperature': changed['parameters']['temperature_bits'],
        'recalculated_unannotated_kernel_mass': changed['unannotated_reference_kernel_mass'],
        'function_assignments': 'Not supplied; no title-derived assignments',
        'conditional_function_weights': original['unadjusted_probabilities'],
        'future_expected_gain': returned['yield']['expected_next_gain'],
        'final_own_action_count': returned['yield']['completed_actions'], 'counts': counts})

digests = {path.name: {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'byte_count': path.stat().st_size} for path in sorted(examples.iterdir())
    if path.is_file() and path.name != 'exported-files.json'}
write('exported-files.json', digests)
print(json.dumps(json.loads((examples / 'numerical-example.json').read_text()), indent=2))
