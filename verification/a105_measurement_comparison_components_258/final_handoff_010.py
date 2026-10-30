"""Package actual authenticated outputs and unchanged tested code without new reads."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1];sys.path.insert(0,str(R))
from gene_annotation_episode.literature_measurement_comparison_inputs import compile_measurement_comparison_inputs
from gene_annotation_episode.literature_measurement_comparison_calculations import populate_measurement_comparison,validate_measurement_comparison_sheet
from gene_annotation_episode.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK

def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(name,data):
 p=P/name
 if p.exists():raise RuntimeError('Refuse to overwrite '+str(p))
 raw=(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode();p.write_bytes(raw);return dict(path=str(p.relative_to(R)),sha256=sha(raw),bytes=len(raw))
def loads(p):return json.loads(p.read_text())
def originals(receipt):
 calls=loads(receipt/'READ_REQUESTS.json')
 for c in calls:
  if 'extraction' in c:
   yield c,loads(receipt/c['extraction']['path'])
examples=[]
for label,receipt,predicate in [
 ('ORIGINAL_NFN',P/'scoped_receipt_009',lambda e:e['selection']['source_kind']=='primary_source'),
 ('SYNTHETIC_COMMON',P/'scoped_receipt_008',lambda e:e['selection']['source_kind']=='synthetic_fixture' and e['covariance_blocks'] and e['covariance_blocks'][0]['status']=='available' and e['covariance_blocks'][0]['roles']==['left','right'] and e['covariance_blocks'][0]['matrix_exact']==[[{'numerator':'4','denominator':'1'},{'numerator':'1','denominator':'1'}],[{'numerator':'1','denominator':'1'},{'numerator':'9','denominator':'1'}]]),
 ('SYNTHETIC_SINGULAR_KNOWN',P/'scoped_receipt_008',lambda e:e['covariance_blocks'] and e['covariance_blocks'][0]['status']=='available' and e['covariance_blocks'][0]['variance_status']=='known' and e['covariance_blocks'][0]['matrix_exact']==[[{'numerator':'4','denominator':'1'}]*2]*2 and e['quantities']['left']['value']['canonical_exact']==e['quantities']['right']['value']['canonical_exact']),
 ('SYNTHETIC_SINGULAR_PLUGIN',P/'scoped_receipt_008',lambda e:e['covariance_blocks'] and e['covariance_blocks'][0]['status']=='available' and e['covariance_blocks'][0]['variance_status']=='estimated' and e['covariance_blocks'][0]['matrix_exact']==[[{'numerator':'4','denominator':'1'}]*2]*2 and e['quantities']['left']['value']['canonical_exact']==e['quantities']['right']['value']['canonical_exact'])]:
 call,e=next((c,e) for c,e in originals(receipt) if predicate(e))
 i=compile_measurement_comparison_inputs(e);sheet=populate_measurement_comparison(i);validate_measurement_comparison_sheet(sheet,inputs=i)
 files={name:write(label+'_'+name+'_ACTUAL_010.json',obj) for name,obj in [('SELECTION',e['selection']),('EXTRACTION',e),('CALCULATION_INPUTS',i),('SHEET',sheet)]}
 examples.append({'case':label,'source_status':'authenticated_original_parent_converted_case_engineering_binding' if label=='ORIGINAL_NFN' else 'authenticated_synthetic_fixture_not_scientific_measurement','no_source_callback_used_during_this_detached_packaging':True,'actual_reader_receipt':str(receipt.relative_to(R)),'source_reads':call['source_reads'],'files':files,'cells':{c['component']:{k:c[k] for k in ('value','exact_value','conditional_value','conditional_exact_value','status','unit','interpretation','reasons')} for c in sheet['cells']}})
write('ACTUAL_EXAMPLES_INDEX_010.json',examples)
paths=['gene_annotation_episode/literature_measurement_comparison_inputs.py','gene_annotation_episode/literature_measurement_comparison_calculations.py','gene_annotation_episode/literature_measurement_comparison_prompt.py','tests/test_literature_measurement_comparison_components_258.py']
current=[]
for path in paths:
 raw=(R/path).read_bytes();frozen=(P/'attempt009_code'/path).read_bytes();assert raw==frozen
 if path.startswith('gene_annotation_episode/'):
  assert raw==(P/'scoped_receipt_008/import_closure'/path).read_bytes()
 current.append(dict(path=path,sha256=sha(raw),bytes=len(raw)))
planning=loads(P/'READ_AND_SCOPE_MANIFEST_001.json')
shared=[]
for item in planning['complete_implementation_files_read']:
 path=Path(item['path']);digest=sha(path.read_bytes());assert digest==item['sha256'];shared.append(dict(path=str(path.relative_to(R)),sha256=digest,unchanged_from_planning_read=True))
assert sha(MEASUREMENT_COMPARISON_TASK.encode())=='cd98aa8e5208a0b1c7f2d0b67c3e522589313474a52f613be157f8985577382e'
status={'status':'bounded_pure_implementation_verified','owned_files':current,'frozen_shared_implementation_files':shared,'full_scoped_test_attempt008':dict(log='PYTEST_ATTEMPT_008.txt',result='40 passed',receipt='scoped_receipt_008',reader_requests_captured=81,local_import_files_copied=17),'targeted_original_provenance_correction_attempt009':dict(log='PYTEST_ATTEMPT_009.txt',result='2 passed',receipt='scoped_receipt_009',change='Only test-fixture coefficient subjects changed to NADH/ferredoxin; production code unchanged from40-pass run.'),'task_sha256':sha(MEASUREMENT_COMPARISON_TASK.encode()),'all_requested_original_schema_resources_003_preserved':True,'reconstructed_early_failed_code_receipts':'INITIAL_ATTEMPT_CODE_RECEIPTS_004.json explicitly labels reconstructed001-003','selected_operation_integration':False,'persistence_or_cold_typed_child_return':False,'actual_model_backed_literature_investigation':False,'primary_positive_matched_covariance_coverage':False,'A105_adequate_or_complete':False,'whole_goal_complete':False,'target_transfer_or_W05':False,'runtime_controller_or_credit_edits':False}
write('FINAL_PIN_AND_SCOPE_010.json',status)
print(json.dumps({'actual_output_packages':len(examples),'owned_code_and_test_hashes_pinned':len(current),'shared_complete_paths_unchanged':len(shared),'task_sha256':status['task_sha256']}))
