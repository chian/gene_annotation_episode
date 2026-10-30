"""Record the completed frozen FastqUtils unit/return/catalog run, not tool completion."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
F = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '45d4561d5297a13bb626140d2e2a333967812cbb20d3e83822a1f97f160bc323'
assert not (HERE / 'PROGRESS_UPDATE_041.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope_hash = sha(scope_path)
scope = read(scope_path)
receipt = read(F / 'combined_unit_001/receipt.json')
assert receipt['passed'] and receipt['exit_code'] == 0 and not receipt['changed_sources']
assert receipt['source_count'] == 1095
assert receipt['case_counts'] == {'passed': 268, 'failure': 0, 'error': 0, 'skipped': 0}
before = read(F / 'combined_unit_001/source_before.json')
assert before == read(F / 'combined_unit_001/source_after.json')
for name, digest in before.items():
    assert sha(F / 'combined_unit_001/candidate' / name) == digest, name
cases = list(ET.parse(F / 'combined_unit_001/tests.xml').iter('testcase'))
assert len({(case.get('classname'), case.get('name')) for case in cases}) == len(cases) == 268
assert all(case.find(tag) is None for case in cases for tag in ('failure', 'error', 'skipped'))
evidence = {'id': 'FASTQUTILS-COMBINED-FROZEN-268-PASS-041',
    'kind': 'frozen_candidate_scientific_return_codec_and_catalog_verified_full_host_Workflow_pending',
    'summary': 'Eleven FastqUtils contract/parser/calculator/provider/return/catalog test files pass together:268distinct cases,exit0,94.894867920seconds,1095source/fixture paths unchanged. This includes the root canonical-storage field-order repair and its six regression cases. Scientific implementation pin e25e6accdeb551f989701d50b2bfed8a6f9393da31848cbc62a0fb2f5856e135.',
    'qualification': 'The independent copy excludes only unrelated in-progress202host test files and caches. Native fixtures are synthetic or retained source-executed synthetic. This is not full authenticated host/Workflow, installed-wheel, live-service or production-application proof. Earlier receipts retain original failures and dependency hashes. Unsupported Cutadapt/SAMstat/p3-sra remain unfinished.',
    'reports': [{'path': str((F / name).relative_to(ROOT)), 'sha256': sha(F / name)} for name in (
        'combined_unit_001/receipt.json', 'combined_unit_001/source_before.json', 'combined_unit_001/source_after.json',
        'combined_unit_001/cases.json', 'combined_unit_001/tests.xml', 'combined_unit_001/copy_contract.json',
        'evidence_contract_order_001/CORRECTION.md')]}
assert evidence['id'] not in {item['id'] for item in work['verification_evidence']}
work['verification_evidence'].append(evidence)
for row in work['rows']:
    if row['id'] == 'C-L209-FastqUtils':
        row['numerical_verification'] = '268distinct_combined_frozen_contract_native_calculator_provider_return_catalog_cases_pass'
        row['integration_verification'] = 'pure_saved_return_codec_actual_catalog268combined_pass_full_host_Workflow_package_and_application_unfinished'
        row['evidence_ids'].append(evidence['id'])
        row['note'] += ' Update041: combined11-file268case verification passed with1095frozen paths unchanged aftercanonicalstoragefix. Independent rootfixture/codec/catalog consumers verified;202actualhost/Workflow stillunfinished,packageunverified,productionunchanged,liveunverified.'
for row in work['resource_bindings']:
    if row['id'] == 'C-L209-FastqUtils::api':
        row['integration_verification'] = 'pure_saved_return_codec_actual_catalog268combined_pass_full_host_Workflow_package_and_application_unfinished'
        row['evidence_ids'].append(evidence['id'])
changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': previous[r['id']], 'after': deepcopy(r)}
        for r in work[group] if r != previous[r['id']])
assert len(changes) == 2 and work['complete_scientific_tools_claimed'] == 0 and sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': hashlib.sha256(raw).hexdigest(), 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False, 'changes': changes, 'added_evidence': [evidence],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_041.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 41, 'changed_rows_and_bindings': len(changes), 'status_sha256': record['new_status_sha256']}))
