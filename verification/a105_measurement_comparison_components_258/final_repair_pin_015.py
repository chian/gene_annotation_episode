"""Pin the completed265 repair; package an actual qualified coefficient example."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1];sys.path.insert(0,str(R))
from gene_annotation_episode.literature_measurement_comparison_inputs import compile_measurement_comparison_inputs
from gene_annotation_episode.literature_measurement_comparison_calculations import populate_measurement_comparison
from gene_annotation_episode.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK

def record(path):
 raw=path.read_bytes();return dict(path=str(path.relative_to(R)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,value):
 p=P/name
 if p.exists():raise RuntimeError('Refuse overwrite')
 p.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n');return record(p)
receipt=P/'scoped_receipt_014';calls=json.loads((receipt/'READ_REQUESTS.json').read_text())
for call in calls:
 if 'extraction' not in call:continue
 e=json.loads((receipt/call['extraction']['path']).read_text())
 reading=e['conversions']['left']['coefficient_readings']['endpoint']
 if reading is not None and reading['reading']['approximate'] and reading['reading']['selector']['witness']['quote']=='2' and reading['source_context']['quote']=='Reaction coefficient approximately 2.':break
else:raise RuntimeError('Actual qualified reader example missing')
i=compile_measurement_comparison_inputs(e);sheet=populate_measurement_comparison(i);cells={c['component']:c for c in sheet['cells']}
assert cells['native_left']['value']==20 and cells['native_right']['value']==22
assert cells['converted_left']['value'] is None
assert cells['converted_left']['reasons']['implementation']==['uncertain_conversion_unimplemented']
example={n:write('QUALIFIED_COEFFICIENT_'+n+'_ACTUAL_015.json',v) for n,v in [('EXTRACTION',e),('CALCULATION_INPUTS',i),('SHEET',sheet)]}
owned=['gene_annotation_episode/literature_measurement_comparison_inputs.py','gene_annotation_episode/literature_measurement_comparison_calculations.py','gene_annotation_episode/literature_measurement_comparison_prompt.py','tests/test_literature_measurement_comparison_components_258.py']
for path in owned:
 assert (R/path).read_bytes()==(P/'repair014_final_code'/path).read_bytes()
 assert (R/path).read_bytes()==(receipt/'import_closure'/path).read_bytes()
old=json.loads((P/'FINAL_PIN_AND_SCOPE_010.json').read_text())
for row in old['frozen_shared_implementation_files']:
 assert hashlib.sha256((R/row['path']).read_bytes()).hexdigest()==row['sha256']
assert hashlib.sha256(MEASUREMENT_COMPARISON_TASK.encode()).hexdigest()==old['task_sha256']
for path in ('gene_annotation_episode/literature_measurement_comparison_prompt.py',):
 assert record(R/path)['sha256']==next(r['sha256'] for r in old['owned_files'] if r['path']==path)
write('REPAIR_FINAL_PIN_015.json',dict(status='root265_pure_defects_repaired_and_scoped_cohort_passed',
 owned_files=[record(R/p) for p in owned],schema_resources=[record(P/(n+'_SCHEMA_004.json')) for n in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET','COVARIANCE_DOCUMENT')],
 extraction_version='a105_measurement_comparison_extraction_v2',calculation_inputs_version='a105_measurement_comparison_calculation_inputs_v2',
 callable_signatures_unchanged=True,selection_sheet_covariance_contract_shapes_unchanged=True,
 source_facts_and_synthetic_fixture_status='preserved_as_declared',
 fix1=dict(whole_snapshot_content_digest_checked=True,bound_original_artifact_checked=True,available_without_raw_snapshot_rejected=True,malformed_and_nonutf8_unavailable_partials_retained=True),
 fix2=dict(authenticated_coefficient_reading_and_context_retained=True,qualified_conversion_does_not_erase_native_partials=True,no_silent_v1_migration=True),
 verification=dict(targeted_covariance='4 passed; REPAIR_COVARIANCE_TARGETED_011.txt',targeted_coefficients='18 passed; REPAIR_COEFFICIENT_TARGETED_013.txt',
 final_affected_cohort='62 passed; REPAIR_FINAL_COHORT_014.txt',exact_reader_input_and_import_receipt=str(receipt.relative_to(R)),
 failed_selector_attempt_retained='REPAIR_COEFFICIENT_TARGETED_012.txt and repair012_coefficient_code; two range selectors excluded their trailing decimal point and were corrected'),
 actual_qualified_example=example,previous010_pin_and_artifacts_unchanged=True,shared_implementation_paths_unchanged=len(old['frozen_shared_implementation_files']),
 task_sha256=old['task_sha256'],prompt_module_unchanged=True,
 future_repository_cold_path='Compare original saved typed objects/custody/equality; do not invoke pure reader/compile validators or recalculate there.',
 selected_binding_or_shared_edits=False,actual_model_backed_investigation=False,primary_positive_matched_covariance_coverage=False,A105_or_full_goal_complete=False))
print('Corrected015 pin written:62 affected checks passed, old010 preserved, exact004 resources and v2 inputs.')
