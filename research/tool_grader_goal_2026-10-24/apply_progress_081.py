"""Record accepted RNA numerical components without counting whole graders."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_081.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
previous = read(HERE / 'PROGRESS_UPDATE_080.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 108
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

packet = ROOT / 'verification/tool_graders_rna_structure_core_2026-10-26_354'
run = packet / 'check006_root_software_code'
receipt = read(run / 'receipt.json')
assert receipt['returncode'] == receipt['metadata']['native_returncode'] == 0
assert receipt['source_pins_unchanged'] is True
assert receipt['metadata']['policy'] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
assert '167 passed' in (run / 'stdout.txt').read_text()
pins = read(run / 'source_pins.json')
assert len(pins) == 14
for row in pins:
    assert sha(ROOT / row['path']) == row['sha256']
    assert sha(run / 'source_snapshot' / row['path']) == row['sha256']
inspection = read(packet / 'ROOT_ARTIFACT_REVIEW_001.json')
assert inspection['retained_examples_checked'] == len(inspection['retained_examples']) == 60
for row in inspection['retained_examples']:
    assert sha(ROOT / row['path']) == row['sha256']
assert sha(packet / 'check005/receipt.json') == inspection['receipt_sha256']
assert sha(packet / 'check005/source_pins.json') == inspection['source_pins_sha256']

names = ['ROOT_REVIEW_001.md', 'ROOT_ARTIFACT_REVIEW_001.json', 'HANDOFF.md',
         'SOURCE_QUALIFICATIONS.md', 'topology_oracles.json']
names += ['check006_root_software_code/' + name for name in (
    'receipt.json', 'selected_request.json', 'source_pins.json', 'stdout.txt', 'stderr.txt')]
evidence = dict(id='RNA-NUMERICAL-COMPONENT-081', kind='reviewed_numerical_component',
    summary='Both RNA tools have accepted pure numerical sheets, native parsers, explicit metadata extraction and deterministic saved-sheet calculators. The 167 dedicated tests pass; original numerical examples and all source pins were inspected. Execution and requested episode returns are unfinished.',
    reports=[dict(path=str((packet / name).relative_to(ROOT)), sha256=sha(packet / name)) for name in names],
    qualification='Synthetic native-format and supplied-topology component verification. No live execution or full production path is established by this component; neither RNA row enters108.')
delivery = ROOT / 'verification/tool_graders_rna_structure_delivery_contract_2026-10-26_355'
assert sha(delivery / 'CONTRACT.md') == '9be6938001095689ea7e002eff459ec7aa8542225c524a4fc082ba8bf1970d79'
interfaces = dict(id='RNA-PRODUCTION-INTERFACES-081', kind='accepted_interfaces_only',
    summary='Exact producer, capture, publication, original-return authentication and saved-sheet interfaces accepted. Fresh357 owns producer files and358 owns results files. Root owns shared integration. New presentation wording awaits requested user feedback.',
    reports=[dict(path=str((delivery / name).relative_to(ROOT)), sha256=sha(delivery / name))
        for name in ('CONTRACT.md', 'ROOT_REVIEW_001.md')],
    qualification='Interface acceptance is not implementation completion or a deployed prompt.')
for item in (evidence, interfaces):
    assert not any(old['id'] == item['id'] for old in status['verification_evidence'])
    status['verification_evidence'].append(item)

ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row.update(overall='numerical_component_verified_production_integration_in_progress',
        source_presence='four_pure_production_modules_inspected',
        numerical_sheet='complete_native_quantities_and_derived_components_verified',
        native_parser='strict_native_json_and_exact_legacy_format_tested_with_synthetic_bytes',
        metadata_extractor='original_input_identity_model_and_sequence_relationships_tested',
        deterministic_calculator='explicit_parameters_and_offline_saved_sheet_recalculation_verified',
        numerical_verification='167_dedicated_tests_and_60_retained_examples_inspected')
    row['evidence_ids'] += [evidence['id'], interfaces['id']]
    row['note'] += (' Update081:354 numerical component accepted after complete source/test review, '
        'literal numerical checks and167 passing tests. 355 production interfaces accepted;357 producer '
        'and358 results implementation are in progress. The earlier absence-of-ViennaRNA probe remains '
        'historical;357 reports a new isolated installation and native tests pending root review. '
        'No execution/return integration or new whole-tool completion is claimed.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {r['id'] for r in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)

checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U02':
        item['current_evidence'] = ('347 run012 completed429 passed,18 failed,5 deselected. Fourteen failures '
            'are one missing-family production helper defect; three are obsolete registry assertions; '
            'one is instruction ordering. Scoped repairs and targeted verification are in progress. '
            'Both VDB rows remain outside108;350 census and352 requested-artifact repairs remain accepted.')
    elif item['id'] == 'U05':
        item['current_evidence'] = ('354 RNA numerical component accepted with167 passing tests and60 '
            'inspected full examples.355 exact producer/results interfaces accepted;357 and358 are '
            'implementing their exclusive files. Shared episode integration remains unfinished and '
            'presentation feedback is pending. Neither RNA tool is counted. All remaining fixed308 '
            'rows and resource bindings remain in scope; W05 and literature grading remain separate.')
assert [(i['id'], i['original_item'], i['status']) for i in checklist] == [
    (i['id'], i['original_item'], i['status']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=[evidence, interfaces],
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[evidence['summary'], interfaces['summary']],
    findings_requiring_repair=[checklist[1]['current_evidence']], work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as f:
    json.dump(update, f, indent=2, ensure_ascii=False)
    f.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.081.writing')
with temporary.open('xb') as f:
    f.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, updated_resource_bindings=0, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    source_pins_verified=len(pins), retained_examples_verified=60, new_status_sha256=sha(STATUS))))
