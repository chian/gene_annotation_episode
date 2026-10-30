"""Record completed Fastq verification and the isolated SRA extension."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
STATUS=HERE/'WORK_STATUS.json'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def reports(base,names):
    return [dict(path=str((base/n).relative_to(ROOT)),sha256=sha(base/n)) for n in names]
def passed_xml(path,count):
    cases=list(ET.parse(path).iter('testcase'))
    assert len(cases)==count and all(c.find(k) is None for c in cases for k in ('failure','error','skipped'))

raw=STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b7288e194808f2da5472d49a255f27263939fe76ac18b87758942f7fc39582bc'
assert not (HERE/'PROGRESS_UPDATE_046.json').exists()
work=json.loads(raw);original=deepcopy(work)
scope_path=HERE/work['scope_file'];scope=read(scope_path);scope_hash=sha(scope_path)
p=V/'tool_graders_fastqutils_cutadapt_verification_2026-10-25_208'
r=read(p/'FINAL_RECEIPT_001.json')
assert r['passed'] and r['test_count']==359 and not r['changed_inputs']
assert all(v==0 for v in r['terminal_exit_codes'].values())
for n,h in r['artifact_hashes'].items():assert sha(p/n)==h
passed_xml(p/'suite_results.xml',359)
combined=dict(id='FASTQUTILS-CUTADAPT-COMBINED-PACKAGE-046',
    kind='isolated_combined_scientific_suite_and_installed_package_verified',
    summary='The exact208 candidate passed359 cases across14 FastqUtils test files. '
        'Its installed wheel reproduced original and Cutadapt/final-read projections, '
        'saved recalculation and strict legacy grammar rejection. All1101 source/input '
        'paths remained unchanged. Scientific closure contains27 files; package contains29 Fastq assets.',
    qualification='This reuses31 prior actual tiny native producer cases; no new producer '
        'or live BV-BRC execution. Full Workflow verification and production application '
        'remain separate.359 is the combined-suite count, not an addition to prior268/77 counts.',
    reports=reports(p,['HANDOFF_001.md','FINAL_RECEIPT_001.json','suite_results.xml',
        'package_verification_001/receipt.json','package_verification_001/installed_result.json']))
p=V/'tool_graders_fastqutils_cutadapt_host_2026-10-25_209'
r=read(p/'FINAL_RECEIPT_001.json')
assert r['passed'] and r['exit_code']==0 and r['typed_boundary_count']==2
assert r['original_full_path_terminal_exit_code']==1
assert r['measurement_values']==[4,4,28,4,3,24] and r['cutadapt_retention']==28/58
assert r['forbidden_call_attempts']==0 and r['additional_selected_actions']==0
assert r['all_original_database_rows_preserved'] and r['forged_value_rejection_count']==3
for n,h in r['artifact_sha256'].items():assert sha(p/n)==h
passed_xml(p/'host_saved_004/results.xml',1)
host=dict(id='FASTQUTILS-NATIVE-CUTADAPT-HOST-SAVED-RETURNS-046',
    kind='actual_host_selected_acquisition_and_typed_admissions_with_controlled_transport',
    summary='Actual selected prepare/submit/status/Workspace operations retained the native '
        'Trim Galore report and final FASTQ and constructed the publication. Both typed '
        'boundaries received [4,4,28,4,3,24] and28/58. Saved continuation passed with science '
        'and transport disabled; forged900 rejected at three contexts.17 actions,0 runtime '
        'observations and every original database row remained unchanged.',
    qualification='Original host run exited1 at a new fixture assertion after both successful '
        'admissions. Its corrected checks ran against saved state, without repeating acquisition. '
        'All failures remain recorded. Controlled service responses and prior native synthetic '
        'inputs do not establish live BV-BRC, configured-model or method_loop behavior. '
        'All2949 tracked inputs unchanged; production not edited.',
    reports=reports(p,['HANDOFF_001.md','FINAL_RECEIPT_001.json','host_run_002/receipt.json',
        'host_saved_004/receipt.json','host_saved_004/evidence/typed_returns.json',
        'host_saved_004/evidence/saved_replay_and_forgery.json']))
p=V/'tool_graders_fastqutils_samstat_contract_2026-10-25_207'
for item in read(p/'SEALED_HANDOFF_MANIFEST_001.json')['files']:
    assert sha(p/item['path'])==item['sha256']
samstat=dict(id='FASTQUTILS-SAMSTAT-SOURCE-NATIVE-CONTRACT-046',
    kind='versioned_source_and_native_contract_ready_implementation_separate',
    summary='Pinned SAMstat2.2.3 and2.5.0 sources were built and exercised in40 tiny input '
        'invocations, retaining37 native HTML reports.44 native evidence assertions passed. '
        'The same12-record input contributes11 versus10 records because the versions exclude '
        'different alignment flags. Contract separates exact counts, rounded values, KDE, '
        'quality summaries, unknown input completeness and unavailable SVG arrays.',
    qualification='207 supplied contracts and native evidence only; no parser/calculator '
        'implementation or live deployment claim. Fresh212/213 implementation follows the '
        'specific shared/current/legacy ports; its later findings and tests are separate evidence.',
    reports=reports(p,['SEALED_HANDOFF_MANIFEST_001.json','FINAL_EVIDENCE_REPORT_001.md',
        'NATIVE_FIELDS_002.json','PARSER_CALCULATOR_PORTS_002.md','ENUM_ADDITIONS_001.json']))
p=V/'tool_graders_fastqutils_sra_implementation_2026-10-25_211'
r=read(p/'FINAL_RECEIPT_001.json')
assert r['passed'] and r['test_count']==86 and r['new_sra_cases']==28
for n,h in r['files'].items():assert sha(p/n)==h
passed_xml(p/'checks_001/results.xml',86)
example=read(p/'numerical_example_001/receipt.json')
assert example['passed'] and example['forbidden_attempts']==0
assert example['values']==[2673129532,35172757,937094000,76.0,1]
sra=dict(id='FASTQUTILS-SRA-PARSER-PROVIDER-SAVED-046',
    kind='isolated_source_grounded_metadata_parser_and_numeric_returns_verified',
    summary='211 implements the five p3-sra numeric fields, per-row metadata retention, '
        'finite schema/metric additions, dispatch and original198/exact208 requested-form '
        'compatibility.28 new SRA tests plus50 mixed report-format and8 saved-form regressions '
        'passed. Actual source output from retained NCBI XML supplies2673129532 bases, '
        '35172757 spots,937094000 archive bytes,length76 and read-types1. Saved JSON replay '
        'preserves those values through the typed form with all acquisition/science disabled.',
    qualification='Source-generated read-types may use a layout fallback; it is not total '
        'reads. Complete metadata arrays do not establish complete experiments, and filenames '
        'do not establish byte/mate joins. The provider envelope is controlled fixture data. '
        'No host custody, full Workflow, live BV-BRC or production application is claimed. '
        '86 includes58 regressions, not86 new tests; it is not summed with208 to claim a new '
        'full-suite result. SRA/SAMstat composition and its verification remain unfinished.',
    reports=reports(p,['HANDOFF_001.md','FINAL_RECEIPT_001.json','checks_001/receipt.json',
        'checks_001/results.xml','numerical_example_001/receipt.json']))
evidence=[combined,host,samstat,sra]
assert not {e['id'] for e in evidence}&{e['id'] for e in work['verification_evidence']}
work['verification_evidence'].extend(evidence)
for group in ('rows','resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0]!='C-L209-FastqUtils':continue
        row['evidence_ids'].extend(e['id'] for e in evidence)
        row['invocation_contract']='candidate_selected_prepare_submit_status_workspace_operations_verified_with_controlled_transport_not_live_service'
        row['native_parser']='isolated_existing_formats_Cutadapt_and_SRA_tested_SAMstat_implementation_and_composition_unfinished'
        row['metadata_extractor']='original_task_source_bound_metadata_and_SRA_per_run_rows_preserved_unknown_joins_explicit'
        row['numerical_verification']='208combined359cases_and_separate211SRA28new_plus58regressions_passed_not_one_composed_suite'
        row['integration_verification']='208package_and209actual_host_two_typed_boundaries_verified_with_qualified_saved_continuation_final208Workflow_pending'
        if group=='rows':
            row['overall']='candidate_package_and_native_host_returns_verified_SRA_isolated_SAMstat_and_production_unfinished'
            row['note']+=' Update046: '+' '.join(e['summary']+' '+e['qualification'] for e in evidence)
changes=[]
for group,count in (('rows',308),('resource_bindings',288)):
    assert len(work[group])==count
    assert [r['id'] for r in work[group]]==[r['id'] for r in original[group]]==[r['id'] for r in scope[group]]
    previous={r['id']:r for r in original[group]}
    changes.extend(dict(group=group,id=r['id'],before=previous[r['id']],after=deepcopy(r))
        for r in work[group] if r!=previous[r['id']])
assert len(changes)==2 and work['complete_scientific_tools_claimed']==0
assert sha(scope_path)==scope_hash
updated=(json.dumps(work,indent=2)+'\n').encode()
record=dict(schema='tool_grader_progress_update_v1',date='2026-10-25',
    recorded_at=datetime.now(timezone.utc).isoformat(),author='root',
    previous_status_sha256=hashlib.sha256(raw).hexdigest(),new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash,scope_changes=False,changes=changes,added_evidence=evidence,
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,complete_scientific_tools_claimed=0)
with (HERE/'PROGRESS_UPDATE_046.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
STATUS.write_bytes(updated)
print(json.dumps(dict(checkpoint=46,changed_rows_and_bindings=len(changes),status_sha256=record['new_status_sha256'])))
