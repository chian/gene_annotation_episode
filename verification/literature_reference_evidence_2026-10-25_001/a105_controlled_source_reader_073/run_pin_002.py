"""Run the actual frozen source/graph/calculator code, record in-pin imports."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import sys
import time

HERE=Path(__file__).resolve().parent
PIN=HERE/'pin_002'
sys.dont_write_bytecode=True
sys.path.insert(0,str(PIN))
os.chdir(PIN)
import pytest

def fp(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
manifest=json.loads((HERE/'PIN_MANIFEST_002.json').read_text())
assert all(fp(PIN/name)==identity for name,identity in manifest.items())
started=time.time()
test_names=['tests/test_literature_controlled_response'+suffix+'.py' for suffix in ('_inputs','_v2_inputs','_figure_inputs','_owner_calculations','_calculations')]
code=pytest.main(['-q','--tb=short','-p','no:cacheprovider','-c',str(PIN/'pyproject.toml'),'--basetemp',str(HERE/'pytest_tmp_002'),*test_names])
put('PIN_TEST_RESULT_002.json',dict(exit_code=int(code),elapsed_seconds=time.time()-started,test_files=test_names))
if code:sys.exit(code)
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_figure_inputs as graph
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
spec=importlib.util.spec_from_file_location('_actual_source073_fixtures',PIN/test_names[1]);fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
outputs=[]
for index in range(len(fixtures.CASES)):
    f=fixtures.Fixture(index)
    extraction,sheet=f.roundtrip()
    outputs.append(dict(name=f.case['name'],kind='constructed_source_bytes_and_actual063_pixels_actual_full073_reader_separate076corrected068_sheet',
        source_reader_executed=True,callback_calls=f.calls,extraction=extraction,sheet=sheet))
put('ACTUAL_SOURCE_OUTPUTS_002.json',outputs)
put('NUMERICAL_TABLE_002.json',[dict(name=row['name'],source_reader_executed=True,
    controlled_effect=row['sheet']['cells']['controlled_response_difference'],variance=row['sheet']['cells']['contrast_variance'],
    source_profile=row['sheet']['cells']['source_profile_log_ratio'],source_signed_index=row['sheet']['cells']['source_signed_index'],
    source_C_state=row['extraction']['covariance']['source_validation'],provided_owner_projection=row['extraction']['covariance']['provided_owner_projection'],
    reported_uncertainty={r:a['reported_uncertainty']['canonical'] for r,a in row['extraction']['arms'].items() if a},
    contrast_dependencies=row['sheet']['contrast_dependencies']) for row in outputs])
# An independent source-free saved-science pass over ACTUAL saved reader outputs.
def forbidden(*a,**k):raise AssertionError('source/decode/count/populate during detached validation')
for module,names in ((shared,['_Context','_Sources','_Inputs','_native_number','_native_unit','read_controlled_response_inputs']),
    (graph,['read_controlled_response_rate_figure','_strict_decode','_count_bar_runs']),
    (owner,['populate_controlled_response_owner']), (reader,['read_controlled_response_v2_inputs'])):
    for name in names:setattr(module,name,forbidden)
for row in outputs:
    assert reader.validate_controlled_response_v2_extraction(row['extraction']['selection'],row['extraction'])==row['extraction']
    canonical=json.loads(json.dumps(row['extraction'],sort_keys=True))
    assert reader.validate_controlled_response_v2_extraction(canonical['selection'],canonical)==canonical
put('DETACHED_SAVED_VALIDATION_002.json',dict(actual_saved_extractions=len(outputs),canonical_JSON_saved_extractions=len(outputs),all_equal=True,
    source_callbacks_native_literal_readers_decoders_counters_populators_disabled=True,pixel_truth_or_native_custody_authenticated=False))
imports=[]
for name,module in sorted(sys.modules.items()):
    path=getattr(module,'__file__',None)
    if name.startswith('gene_annotation_episode') and path:
        resolved=Path(path).resolve()
        assert resolved.is_relative_to(PIN), (name,str(resolved))
        imports.append(dict(module=name,path=str(resolved.relative_to(PIN)),**fp(resolved)))
assert all(fp(PIN/name)==identity for name,identity in manifest.items())
put('PIN_EXECUTION_RECEIPT_002.json',dict(all_project_imports_in_pin=True,actual_imports=imports,
    pin_files=len(manifest),pin_bytes_unchanged=True,actual_full_source_cases=len(outputs),primary_or_model_or_native_execution=False,
    actual_runtime_observations=0,legacy_baseline_source='original008 final snapshot in pin; unchanged declared helpers plus explicitly recorded current domain.py drift'))
print(json.dumps(dict(actual_source_cases=len(outputs),in_pin_imports=len(imports),detached_saved_extractions=len(outputs))))
