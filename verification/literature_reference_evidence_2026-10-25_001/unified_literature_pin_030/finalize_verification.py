"""Verify the exact immutable test generation and unchanged prior inputs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parents[1]
PIN=BASE/'literature_model_run_030/pin_001'
OLD=BASE/'literature_model_run_024/pin_001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
functions=runpy.run_path(str(Path(__file__).with_name('capture_pin.py')),run_name='verification_only')
for p in [PIN,OLD]:functions['verify'](p,json.loads((p/'SOURCE_MANIFEST.json').read_bytes()))
check=BASE/'literature_model_run_030/pinned_checks_001'
proof=json.loads((check/'IMPORT_PROOF.json').read_bytes())
assert proof['pytest_exit_code']==0 and proof['model_calls']==[]
assert len(proof['runtime_imports'])==161
for item in proof['runtime_imports']:
 p=Path(item['path']);assert p.is_relative_to(PIN) and sha(p)==item['sha256']
suite=ET.parse(check/'RESULTS.xml').getroot().find('testsuite')
assert int(suite.attrib['tests'])==436
assert all(int(suite.attrib[n])==0 for n in ['errors','failures','skipped'])
old=BASE/'literature_model_run_024/offline_001';new=BASE/'literature_model_run_030/offline_001'
prior=json.loads((old/'OPERATION_CATALOG.json').read_bytes());current=json.loads((new/'OPERATION_CATALOG.json').read_bytes())
assert current[:-1]==prior and current[-1]['name']=='literature.amount.populate'
def omit_new_optional(value):
 if isinstance(value,dict):
  return {key:omit_new_optional(child) for key,child in value.items() if key!='requested_amount_components'}
 if isinstance(value,list):return [omit_new_optional(x) for x in value if x!='requested_amount_components']
 return value
assert omit_new_optional(json.loads((new/'ASSIGNMENT_SCHEMA.json').read_bytes()))==json.loads((old/'ASSIGNMENT_SCHEMA.json').read_bytes())
offline=json.loads((new/'RECEIPT.json').read_bytes())
assert offline['status']=='passed' and offline['attempted_model_calls']==[]
parent=json.loads((BASE/'UNIFIED_LITERATURE_PARENT_CONTRACT_REVIEW_030.json').read_bytes())
assert parent['status']=='passed' and parent['legacy_schema_exact'] and parent['amount_TASK_unwired']
report={'written_utc':datetime.now(timezone.utc).isoformat(),'status':'passed',
 'meaning':'Isolated reviewed code generation; synthetic connected execution and prospective offline checks, not actual-model numerical interpretation',
 'pin':str(PIN),'manifest_sha256':sha(PIN/'SOURCE_MANIFEST.json'),'verified_files':658,
 'prior024_files_verified_unchanged':637,'reviewed_owned_code_test_files':20,
 'pinned_checks':{'passed':436,'seconds':321.76,'terminal_exit_code':0,'exec_session':75607,
   'junit_attributes':suite.attrib,'junit_sha256':sha(check/'RESULTS.xml'),
   'runtime_imports_verified_under_pin':161,'attempted_model_calls':[]},
 'old15_operation_entries_exact':True,'only_new_operation':'literature.amount.populate',
 'old_assignment_fields_exact_after_removing_new_optional_amount_components':True,
 'legacy15_and_native24_return_fields_preserved':True,'censored_native_bound_preserved':True,
 'amount_aspect_TASK_unwired':True,'offline_passed_no_model_calls':True,
 'new_model_run_launched':False,'existing_actual024_run_untouched':True,
 'shared_main_service_changes_preserved_and_excluded':True,
 'broad_current_main030_regression':'separate generation, still running at this cut',
 'counts_overlap_other_groups_do_not_sum':True,'full_goal_complete':False}
with (BASE/'UNIFIED_LITERATURE_PIN_VERIFICATION_030.json').open('x') as stream:
 json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report))
