"""Record actual applied return repairs and isolated Fastq format work."""
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
V = ROOT / 'verification'
P = V / 'tool_graders_typed_return_performance_2026-10-25_197'
G = V / 'tool_graders_genome_alignment_requirement_scope_2026-10-25_203'
F = V / 'tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204'
A = V / 'tool_graders_verified_return_repairs_application_2026-10-25_206'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reports(paths):
    return [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in paths]


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '89605f9520c6051b76e02ff6926f0311bc46a2e5d2b61cacdadbd9e100b9272b'
assert not (HERE / 'PROGRESS_UPDATE_044.json').exists()
work = json.loads(raw); original = deepcopy(work)
scope_path = HERE / work['scope_file']; scope = read(scope_path); scope_hash = sha(scope_path)
application = read(A / 'APPLICATION_RECEIPT_001.json')
assert application['applied'] and application['verified_target_paths'] == 1046
assert application['production_modules'] == 4 and application['new_tests'] == 1
assert application['unexpected_changed_paths'] == []
assert {name: sha(ROOT / name) for name in read(A / 'APPLICATION_AFTER_001.json')} == read(A / 'APPLICATION_AFTER_001.json')
for path in (P / 'full_workflow_001/receipt.json', G / 'repair_host_001/receipt.json', G / 'repair_episode_001/receipt.json'):
    assert read(path)['exit_code'] == 0
for path, count in ((P / 'full_workflow_001/tests.xml', 3), (G / 'repair_host_001/tests.xml', 13),
                    (G / 'repair_episode_001/tests.xml', 6), (F / 'saved_forms_development_001.xml', 8)):
    cases = list(ET.parse(path).iter('testcase'))
    assert len(cases) == count and all(c.find(k) is None for c in cases for k in ('failure','error','skipped'))
native = read(F / 'native_examples_001/receipt.json')
assert len(native['cases']) == 5 and all(case['exit_code'] == 0 for case in native['cases'])

applied = {'id': 'TYPED-RETURN-AND-GENOME-REPAIR-APPLICATION-044',
    'kind': 'four_reviewed_production_modules_applied_composed_Workflow_verification_pending',
    'summary': 'Applied the exact three197 return-validation performance modules and the one203 GenomeAlignment '
        'reference-domain repair, plus its test. All1046 application targets were checked; no unrelated changes. '
        '197 has596 distinct passing cases and its separately reproduced original GenomeAlignment failure; '
        'all three selected full Workflow cases passed.203 has855 distinct passes, including the original '
        'failure,13 host checks and six Workflow checks. Native requested returns remain690/693,40/48,50,52.',
    'qualification': 'The two suites describe separate frozen candidates and are not added into a disjoint total. '
        'The newly composed candidate is separately undergoing its exact failed-case and Workflow verification. '
        'Shared optimization caches pure grammar compilation and fixed private templates only, not custody, '
        'payload or possession verdicts. Saved 197 results marginal gains are[0,0,0,0,3,0,3] for proteome '
        'and[0,0,0,0,0,0,3] for ComparativeSystems; cumulative credit is a different quantity. '
        'No method_loop, scientific formula, completed observation or live service claim changed.',
    'reports': reports([A / 'APPLICATION_RECEIPT_001.json', A / 'APPLICATION_PLAN_001.json',
        A / 'APPLICATION_BEFORE_001.json', A / 'APPLICATION_AFTER_001.json', P / 'APPLICATION_BOUNDARY.json',
        P / 'FINAL_VERIFICATION.md', P / 'full_workflow_001/receipt.json',
        P / 'accounting_audit_002/WORKFLOW_ACCOUNTING.json', P / 'freeze_audit_001/FINAL_SOURCE_FREEZE_CHECK.json',
        G / 'REPAIR_DIFF_001.patch', G / 'REPAIR_VERIFICATION_002.md', G / 'FINAL_AUDIT_001.json',
        G / 'repair_host_001/receipt.json', G / 'repair_episode_001/receipt.json'])}

fastq = {'id': 'FASTQUTILS-CUTADAPT-PORTS-AND-SAVED-FORMS-044',
    'kind': 'native_format_evidence_isolated_extension_and_saved_form_compatibility_development',
    'summary': 'Five actual small Cutadapt4.9/TrimGalore0.6.10 executions retained. Cutadapt reports4 '
        'reads/58 bases in and4 reads/28 bases out; later Trim Galore filtering leaves3 reads/24 bases. '
        'Paired Cutadapt reports4 pairs/116 bases in and4 pairs/56 bases out. Empty text omits other '
        'counters. A separate204 candidate adds23 native metric definitions,6 section keys and15 '
        'population keys, and connects the embedded parser port. The parser workload is separately owned. '
        'Expanded enums exposed rejection of exact old saved forms. The candidate now retains the exact '
        'original packaged grammar and accepts only complete current or complete legacy forms. '
        'Eight development tests passed, including original saved-provider replay without parsing, '
        'calculation, subprocess or network; values2,5/9,0.001,0.75 remain unchanged.',
    'qualification': 'This is not a claim of a finished Cutadapt parser, new full host/Workflow integration, '
        'production application or BV-BRC deployment. These eight tests overlap neither a new full tool '
        'claim nor a frozen all-source integration claim; the candidate is under active separate parser '
        'development. SAMstat, SRA metadata and unverified producer versions remain unfinished. '
        'Existing198 verification stays tied to its exact original files. No historical receipt was rewritten.',
    'reports': reports([F / 'SOURCE_RECEIPTS_001.json', F / 'native_environment_001/receipt.json',
        F / 'native_examples_001/receipt.json', F / 'CUTADAPT_WORKLOAD_001.md',
        F / 'CONTRACT_CORRECTION_002.md', F / 'CONTRACT_CORRECTION_003.md',
        F / 'PREPARATION_RECEIPT_001.json', F / 'COMMON_PORT_MANIFEST_001.json',
        F / 'METRIC_SPECS_002.json', F / 'LEGACY_SCHEMA_RECEIPT_001.json',
        F / 'saved_forms_development_001.xml'])}

for evidence in (applied, fastq):
    assert evidence['id'] not in {e['id'] for e in work['verification_evidence']}
    work['verification_evidence'].append(evidence)

targets = {'C-L202-GenomeAlignment', 'C-L206-GenomeComparison', 'C-L207-ComparativeSystems'}
assert targets <= {r['id'] for r in work['rows']}
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        base_id = row['id'].split('::')[0]
        if base_id in targets:
            row['evidence_ids'].append(applied['id'])
            row['integration_verification'] = 'reviewed_return_repairs_applied_isolated_paths_verified_composed_Workflow_check_pending'
            if base_id == 'C-L202-GenomeAlignment':
                row['numerical_verification'] = 'prior_evidence_retained_855_distinct_repair_checks_pass_including_original_failure_13host_6Workflow'
                if group == 'rows':
                    row['overall'] = 'requirement_reference_repair_applied_isolated_paths_verified_composed_Workflow_pending_live_service_unverified'
            if group == 'rows':
                row['note'] += ' Update044: ' + applied['summary'] + ' ' + applied['qualification']
        elif base_id == 'C-L209-FastqUtils':
            row['evidence_ids'].append(fastq['id'])
            if group == 'rows':
                row['note'] += ' Update044: ' + fastq['summary'] + ' ' + fastq['qualification']

changes = []
for group, count in (('rows',308), ('resource_bindings',288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes += [{'group':group,'id':r['id'],'before':previous[r['id']],'after':deepcopy(r)}
                for r in work[group] if r != previous[r['id']]]
assert len(changes) == 8 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work,indent=2)+'\n').encode()
record = {'schema':'tool_grader_progress_update_v1','date':'2026-10-25',
    'recorded_at':datetime.now(timezone.utc).isoformat(),'author':'root',
    'previous_status_sha256':hashlib.sha256(raw).hexdigest(),
    'new_status_sha256':hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged':scope_hash,'scope_changes':False,'changes':changes,
    'added_evidence':[applied,fastq],'inventory_maintenance_counted_as_implementation_progress':False,
    'specific_pending_NCBI_job_verification_included':False,'complete_scientific_tools_claimed':0}
with (HERE/'PROGRESS_UPDATE_044.json').open('x') as stream:
    json.dump(record,stream,indent=2);stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint':44,'changed_rows_and_bindings':len(changes),
                  'status_sha256':record['new_status_sha256']}))
