"""Record the verified FastqUtils return-order repair and installed package."""
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
assert hashlib.sha256(raw).hexdigest() == '6268ecc12e97be1866d3f1efffd4d798974fa3afb11bc28f36ecf006b24340de'
assert not (HERE / 'PROGRESS_UPDATE_043.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope = read(scope_path)
scope_hash = sha(scope_path)
checks = read(F / 'return_revision_002/receipt.json')
assert checks['passed'] and checks['exit_code'] == 0 and checks['changed_sources'] == []
assert checks['case_counts'] == {'passed': 31, 'failure': 0, 'error': 0, 'skipped': 0}
cases = list(ET.parse(F / 'return_revision_002/tests.xml').iter('testcase'))
assert len(cases) == 31 and all(c.find(t) is None for c in cases for t in ('failure', 'error', 'skipped'))
assert any(c.get('name') == 'test_canonical_storage_preserves_original_requested_field_order' for c in cases)
package = read(F / 'package_verification_004/receipt.json')
assert package['passed'] and package['build_exit_code'] == package['installed_exit_code'] == 0
assert package['changed_sources'] == package['changed_build_sources'] == []
assert package['source_count'] == 1095 and len(package['required_packaged_files']) == 26
assert package['numerical_answers'] == {'read_count': 2, 'gc': 5 / 9, 'errors': .001, 'retained': .75}
installed = read(F / 'package_verification_004/installed_result.json')
assert installed['saved_communication_without_science'] and installed['changed_parameters_preserve_original']
assert installed['fact_family_count'] == 7 and installed['field_count'] == 9
assert installed['changed_threshold_fractions'] == {'40': 1, '41': 0}
assert installed['host_custody_verified'] is installed['live_service_execution_verified'] is False
for dirname in ('return_revision_002', 'package_verification_004'):
    before = read(F / dirname / 'source_before.json')
    assert before == read(F / dirname / 'source_after.json')
    assert {name: sha(F / 'return_revision_002/candidate' / name) for name in before} == before
assert {row['path'] for row in read(F / 'return_revision_002/delta.json')} == {
    'gene_annotation_episode/bvbrc_fastqutils_returns.py', 'tests/test_bvbrc_fastqutils_returns.py'}
item = {'id': 'FASTQUTILS-RETURN-ORDER-AND-PACKAGE-043',
    'kind': 'candidate_return_order_repair_and_installed_package_verified_full_Workflow_pending',
    'summary': 'Canonical JSON exposed a real return-array order defect. The candidate now follows '
        'the original requested field order. The two-file correction passed31 return/catalog tests '
        'with1095 frozen paths unchanged. The built package contains all26 FastqUtils files and '
        'reproduces the original provider result:2reads,GC5/9,Phred-model errors0.001 under explicit '
        'Phred33,and Hostile6/8. Changed quality thresholds40and41 yield fractions1and0 from the '
        'saved sheet without parsing/network; original results remain unchanged. Seven-family '
        'saved communication passes with all scientific calculators disabled.',
    'qualification': 'Scientific24-file provider pin remains e25e6accdeb551f989701d50b2bfed8a6f9393da31848cbc62a0fb2f5856e135. '
        'Earlier268-case receipt remains evidence for its original return source;31 current cases '
        'are not added as disjoint tests. Package001 failed from absent local build backend;002 '
        'built but the probe used the wrong stage field;003 revealed the real ordering defect. '
        'All failures are preserved. This does not prove full host custody/Workflow, live service '
        'or production application. Unsupported native sections remain required unfinished work.',
    'reports': [{'path': str((F / name).relative_to(ROOT)), 'sha256': sha(F / name)} for name in (
        'evidence_return_order_001/diagnosis.json', 'evidence_return_order_001/CORRECTION.md',
        'return_revision_002/receipt.json', 'return_revision_002/tests.xml', 'return_revision_002/delta.json',
        'return_revision_002/source_before.json', 'return_revision_002/source_after.json',
        'package_verification_001/receipt.json', 'package_verification_002/receipt.json',
        'package_verification_003/receipt.json', 'package_verification_004/receipt.json',
        'package_verification_004/installed_result.json')]}
assert item['id'] not in {e['id'] for e in work['verification_evidence']}
work['verification_evidence'].append(item)
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0] != 'C-L209-FastqUtils':
            continue
        row['integration_verification'] = 'corrected_return_order31tests_and_installed_package_pass_full_host_Workflow_and_application_unfinished'
        row['evidence_ids'].append(item['id'])
        if group == 'rows':
            row['overall'] = 'candidate_scientific_return_library_and_package_verified_full_host_Workflow_and_application_unfinished'
            row['note'] += ' Update043: ' + item['summary'] + ' ' + item['qualification']
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
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False, 'changes': changes, 'added_evidence': [item],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_043.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 43, 'changed_rows_and_bindings': len(changes),
    'status_sha256': record['new_status_sha256']}))
