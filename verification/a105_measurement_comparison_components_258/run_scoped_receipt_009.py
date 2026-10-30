"""Scoped final verification with exact attempted inputs and local import closure."""
from pathlib import Path
from copy import deepcopy
import hashlib,importlib.metadata,json,sys,traceback
import pytest
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=P/'scoped_receipt_009'
if OUT.exists():raise RuntimeError('Receipt directory already exists')
OUT.mkdir();sys.path.insert(0,str(R))
from gene_annotation_episode import literature_measurement_comparison_inputs as inputs
original=inputs.read_measurement_comparison_inputs
calls=[]
def put(raw,family):
 h=hashlib.sha256(raw).hexdigest();p=OUT/family/h;p.parent.mkdir(exist_ok=True)
 if not p.exists():p.write_bytes(raw)
 return {'path':str(p.relative_to(OUT)),'bytes':len(raw),'sha256':h}
def wrapped(selection,*,read_source):
 row={'selection':put(json.dumps(selection,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),'selections'),'source_reads':[]}
 calls.append(row)
 def read(ref,representation):
  answer=read_source(ref,representation)
  row['source_reads'].append({'source_ref':ref,'representation':representation,'artifact_ref':answer['artifact_ref'],'content':put(answer['content'],'source_bytes')})
  return answer
 try:
  result=original(selection,read_source=read)
  row['extraction']=put(json.dumps(result,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),'extractions')
  return result
 except Exception as error:
  row['failure']={'type':type(error).__name__,'code':getattr(error,'code',None),'field':getattr(error,'field',None)}
  raise
inputs.read_measurement_comparison_inputs=wrapped
code=pytest.main(['tests/test_literature_measurement_comparison_components_258.py::test_actual_original_nfn_mechanical_binding','tests/test_literature_measurement_comparison_components_258.py::test_original_source_rejects_wrong_endpoint_unit_and_continuation_row','-q','--tb=short'])
(OUT/'READ_REQUESTS.json').write_text(json.dumps(calls,indent=2)+'\n')
files=[];outside=[]
for name,module in sorted(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file:continue
 p=Path(file).resolve()
 if p.suffix not in ('.py','.so'):continue
 try:relative=p.relative_to(R)
 except ValueError:continue
 if '.venv' in relative.parts:
  if p.suffix=='.so':outside.append({'module':name,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  continue
 if relative.parts[0] not in ('gene_annotation_episode','tests','method_loop'):continue
 raw=p.read_bytes();target=OUT/'import_closure'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 files.append({'module':name,'path':str(relative),'sha256':hashlib.sha256(raw).hexdigest()})
packages={name:importlib.metadata.version(name) for name in ('pytest','jsonschema','referencing','numpy')}
(OUT/'IMPORT_CLOSURE.json').write_text(json.dumps({'python':sys.version,'packages':packages,'local_files':files,'loaded_binary_dependencies':outside},indent=2)+'\n')
(OUT/'STATUS.json').write_text(json.dumps({'pytest_exit_code':int(code),'reader_calls_captured':len(calls),'local_import_files_copied':len(files),'actual_authorized_reader_callbacks_captured':True,'selected_operation_or_model_investigation_executed':False},indent=2)+'\n')
print(json.dumps({'pytest_exit_code':int(code),'reader_calls':len(calls),'local_import_files':len(files)}))
raise SystemExit(code)
