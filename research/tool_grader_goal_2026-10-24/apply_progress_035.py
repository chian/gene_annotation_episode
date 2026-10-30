"""Record applied directional numerical sheets, calculations and verification."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == 'ec23eca93393001a940092151e79e1a04a13ccecc0d964d1640b135323cb40d9'
assert not (HERE / 'PROGRESS_UPDATE_035.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope_hash = hashlib.sha256(scope_path.read_bytes()).hexdigest()
scope = json.loads(scope_path.read_text())
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert hashlib.sha256(authority.read_bytes()).hexdigest() == work['authority_sha256']
base = 'verification/tool_graders_bvbrc_proteome_directional_build_2026-10-25_179/'


def read(name):
    return json.loads((ROOT / (base + name)).read_text())


def hashed(name):
    return {'path':base+name,'sha256':hashlib.sha256((ROOT / (base + name)).read_bytes()).hexdigest()}


application = read('APPLICATION_RECEIPT_001.json')
assert application['production_applied'] and len(application['files']) == 10
assert application['existing_baseline_files_unchanged'] == 868
for item in application['files']:
    assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['after_sha256']
candidate = read('evidence_a/final_test_receipt_001.json')
assert candidate['returncode'] == 0 and candidate['source_test_manifest_unchanged']
applied = read('applied_verification_001/receipt.json')
assert applied['exit_code'] == 0 and not applied['changed_sources']
for result in (candidate,applied):
    assert [(int(s['tests']),int(s['failures']),int(s['errors']),int(s['skipped']))
            for s in result['testsuites']] == [(319,0,0,0)]
package = read('evidence_c/package_001/receipt.json')
assert package['passed'] and package['installed_exit_code'] == 0
native = read('evidence_a/native_artifacts_receipt_002.json')
assert native['source_modules_unchanged']
assert native['saved_observation_replay']['forbidden_call_count'] == 0
assert len(native['complete_scoring_sheets']) == 3

evidence = dict(
    id='PROTEOME-DIRECTIONAL-NUMERICAL-APPLIED-035',
    kind='reviewed_complete_report_numerical_components_applied_and_verified',
    summary='Applied five new numerical module/schema files, four new test files and the explicit schema package-data entry.319 distinct scoped tests passed in the candidate and again in the applied checkout; these are repeated verification of the same319 cases, not638 distinct cases.845 applied source/test/fixture/metadata paths were unchanged. A built and extracted wheel imported the modules and calculated the retained native example correctly.',
    numerical_example='Native2221 query1/subject0 retains529/600 paired coverage,468/529 compatible displayed-symbol identity and61 unresolved pairs. Native2202 preserves conflicting mappings alongside independent union counts. Native2011 preserves a no-hit claim and0/102 displayed coverage without creating a subject or pair identity.',
    qualification='Retained public BLASTP reports and synthetic tests verify numerical behavior, not live BV-BRC jobs. Complete observed/calculated and changed-parameter artifacts exist for all three native reports. Saved recalculation made zero forbidden file/native-parser/network/process calls. Original-input occurrence/execution witnesses, v2 provider publication and typed parent-return integration remain unfinished. Host integration176 remains an isolated candidate; its454-pass/one-fixture-failure core run and ongoing host run are not converted into a passing integration claim.',
    reports=[hashed(name) for name in (
        'APPLICATION_RECEIPT_001.json','PREFLIGHT_001.json',
        'evidence_a/final_test_receipt_001.json','evidence_a/final_tests_001.xml',
        'evidence_a/native_artifacts_receipt_002.json','evidence_a/WORKLOAD_A_REPORT_001.md',
        'evidence_c/package_001/receipt.json','applied_verification_001/receipt.json',
        'applied_verification_001/pytest.xml','CALLER_DECIMAL_CONTEXT_007.md')])
assert evidence['id'] not in {r['id'] for r in work['verification_evidence']}
work['verification_evidence'].append(evidence)
for row in work['rows']:
    if row['id'] == 'C-L206-GenomeComparison':
        row['overall'] = 'legacy_and_complete_directional_numerics_applied_provider_and_parent_return_integration_unfinished'
        row['source_presence'] = 'native_definitions_legacy_and_directional_numerical_modules_and_schema_assets_present'
        row['numerical_sheet'] = 'legacy_native_sheet_and_complete_directional_report_observed_calculated_sheets_applied_verified'
        row['deterministic_calculator'] = 'native_descriptive_and_full_directional_correspondence_components_applied_saved_recalculation_verified'
        row['numerical_verification'] = 'prior_component_evidence_retained_new319distinct_cases_pass_candidate_and_applied_packaged_native_example_verified'
        row['evidence_ids'].append(evidence['id'])
        row['note'] += ' Update035: reviewed179 A/B/C sheets, semantic validation, geometry and complete-report calculations applied in nine new module/schema/test files plus the schema package-data entry.319distinct cases pass both candidate and applied runs (not638distinct),845applied tracked paths unchanged. Built/extracted wheel reproduces529/600coverage,468/529identity,61unresolved pairs. All three full native examples and changed-parameter replay artifacts are retained; no forbidden I/O/native parsing calls during replay. C ratio rendering now uses integer HALF_EVEN arithmetic independent of caller Decimal settings. Existing868baseline files were unchanged by application. Exact producer/input occurrence witnesses and directional v2 provider/return integration remain unfinished.176native-host candidate remains separate; its in-progress evidence is not a passed integration claim. Inventory scope unchanged is not new progress.'
for row in work['resource_bindings']:
    if row['id'] == 'C-L206-GenomeComparison::api':
        row['evidence_ids'].append(evidence['id'])

changes = []
for group,count in (('rows',308),('resource_bindings',288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    prior = {r['id']:r for r in original[group]}
    changes.extend({'group':group,'id':r['id'],'before':prior[r['id']],'after':deepcopy(r)}
                   for r in work[group] if r != prior[r['id']])
assert len(changes) == 2 and work['complete_scientific_tools_claimed'] == 0
assert hashlib.sha256(scope_path.read_bytes()).hexdigest() == scope_hash
updated = (json.dumps(work,indent=2)+'\n').encode()
record = dict(schema='tool_grader_progress_update_v1',date='2026-10-25',
    recorded_at=datetime.now(timezone.utc).isoformat(),author='root',
    previous_status_sha256=before,new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash,previous_goal_turn_classification='progress',
    previous_goal_turn_evidence='Checkpoint034 records the applied form-local validation repair and23 applied controlled Workflow/form checks.',
    this_goal_turn_classification='progress',
    current_progress='Applied complete directional numerical modules, corrected caller-context-dependent rounding, included the schema in the built package and verified319cases against applied sources. Provider/return interfaces are under concrete review; they are not implemented by this checkpoint.',
    changes=changes,added_evidence=[evidence],scope_changes=False,
    specific_pending_NCBI_job_verification_included=False,complete_scientific_tools_claimed=0)
with (HERE / 'PROGRESS_UPDATE_035.json').open('x') as stream:
    json.dump(record,stream,indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint':35,'changed_rows_and_bindings':len(changes),
                  'scope_rows':308,'resource_bindings':288,'status_sha256':record['new_status_sha256']}))
