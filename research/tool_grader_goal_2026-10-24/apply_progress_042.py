"""Append verified proteome and ComparativeSystems application facts to existing rows."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
P = ROOT / 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182'
C = ROOT / 'verification/tool_graders_bvbrc_comparative_systems_application_2026-10-25_196'
APPLIED = C / 'apply_20261025T220740_1792966060486420136'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '741a1eac7a9330d483f24712d1297b743ed1e4e61f8b6047c4d177b46025f015'
assert not (HERE / 'PROGRESS_UPDATE_042.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope_hash = sha(scope_path)
scope = read(scope_path)
proteome = read(P / 'APPLICATION_RECEIPT_001.json')
comparative = read(APPLIED / 'APPLICATION_RECEIPT.json')
for receipt in (proteome, comparative):
    assert receipt['production_applied'] and receipt['applied_facade_verified']
    assert receipt['applied_probe_exit_code'] == 0 and not receipt['unexpected_sources']
    assert receipt['live_service_execution_verified'] is False
assert len(proteome['written_paths']) == 25 and proteome['source_count'] == 952
assert comparative['passed'] and comparative['exit_code'] == 0
assert len(comparative['written_paths']) == 99 and comparative['source_count'] == 1045
host = read(P / 'final_host_001/receipt.json')
assert host['passed'] and host['exit_code'] == 0 and not host['changed_sources']
assert host['case_counts'] == {'error': 0, 'failed': 0, 'passed': 188, 'skipped': 0}
assert host['source_count'] == 951
for name, digest in read(APPLIED / 'APPLICATION_SOURCE_AFTER.json').items():
    assert sha(ROOT / name) == digest, name


def evidence(identifier, summary, paths, qualification):
    return {'id': identifier, 'kind': 'verified_production_application_no_live_service_claim',
        'summary': summary, 'qualification': qualification,
        'reports': [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in paths]}


pe = evidence('PROTEOME-DIRECTIONAL-APPLICATION-042',
    'Final frozen host verification passed 188 cases, exit 0, with 951 source paths unchanged. '
    'Together with the retained 737 unit and two actual Workflow cases, this completes the '
    'candidate checks required by its application contract. Applied the exact 25-file delta; '
    'the production facade matches the installed package result and both provider pins are correct.',
    [P / 'final_host_001/receipt.json', P / 'APPLICATION_RECEIPT_001.json',
     P / 'APPLICATION_SOURCE_AFTER_001.json', P / 'applied_native_check_001/result.json'],
    'Native numerical evidence includes retained public BLASTP output; service transport and '
    'task identity are controlled. Live GenomeComparison execution, deployed producer identity '
    'and complete input association remain unverified. No whole-tool completion is claimed.')
ce = evidence('COMPARATIVE-SYSTEMS-APPLICATION-042',
    'All application prerequisites passed, including the retained native/parser/calculator, '
    'provider, typed-return, package and real Workflow checks. Applied the exact 99-file delta '
    'onto the verified proteome application. All 1045 target source paths match. Production '
    'imports and numerical values match the installed package; proteome provider pins remain unchanged.',
    [APPLIED / 'APPLICATION_RECEIPT.json', APPLIED / 'PREFLIGHT_IMMEDIATELY_BEFORE_APPLY.json',
     APPLIED / 'APPLICATION_SOURCE_AFTER.json', APPLIED / 'PROBE_RESULT.json'],
    'Source-executed synthetic producer fixtures and controlled service transport do not '
    'establish live ComparativeSystems execution, authenticated publication or an immutable '
    'Data API snapshot. Earlier failed package/history checks remain retained.')
for item in (pe, ce):
    assert item['id'] not in {e['id'] for e in work['verification_evidence']}
    work['verification_evidence'].append(item)

for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        base_id = row['id'].split('::')[0]
        if base_id == 'C-L206-GenomeComparison':
            item = pe
            row['production_result_binding'] = 'legacy_and_directional_v2_applied_verified_installed_equivalent_facade'
            row['integration_verification'] = '737unit_188host_two_actual_Workflow_cases_package_and_production_facade_pass'
            if group == 'rows':
                row['overall'] = 'legacy_and_directional_v2_applied_controlled_full_path_verified_live_service_unverified'
                row['tool_information'] = 'actual_configured_legacy_and_directional_API_tool_information_applied_verified'
        elif base_id == 'C-L207-ComparativeSystems':
            item = ce
            row['production_result_binding'] = 'selected_API_publication_and_own_received_typed_returns_applied_verified'
            row['integration_verification'] = 'provider127_package_actual_Workflow_and_applied_facade_pass'
            row['invocation_contract'] = 'actual_selected_API_submission_artifact_and_typed_return_path_applied_verified_controlled_transport'
            if group == 'rows':
                row.update(overall='applied_controlled_full_path_and_package_verified_live_service_unverified',
                    tool_information='real_API_tool_information_and_selected_operation_binding_applied',
                    numerical_sheet='native_numerical_sheet_applied_and_tested',
                    metadata_extractor='qualified_Data_extraction_and_actual_host_possession_applied_tested',
                    deterministic_calculator='explicit_saved_sheet_calculators_applied_dependency_precision_tested')
        else:
            continue
        row['evidence_ids'].append(item['id'])
        if group == 'rows':
            row['note'] += ' Update042: ' + item['summary'] + ' ' + item['qualification']

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': previous[r['id']], 'after': deepcopy(r)}
        for r in work[group] if r != previous[r['id']])
assert len(changes) == 4 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': hashlib.sha256(raw).hexdigest(), 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False, 'changes': changes, 'added_evidence': [pe, ce],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_042.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 42, 'changed_rows_and_bindings': len(changes),
    'status_sha256': record['new_status_sha256']}))
