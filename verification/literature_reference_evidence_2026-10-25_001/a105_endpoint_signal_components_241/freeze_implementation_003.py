"""Exclusive immutable implementation/data/import pin and actual source example."""
from pathlib import Path
import ast,hashlib,importlib,json,shutil,sys
ROOT=Path.cwd().resolve()
OWN=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241'
PIN=OWN/'implementation_003';PIN.mkdir()
MODULES=['gene_annotation_episode.literature_endpoint_signal_inputs','gene_annotation_episode.literature_endpoint_signal_calculations','gene_annotation_episode.literature_endpoint_signal_prompt']
for name in MODULES:importlib.import_module(name)
from gene_annotation_episode.literature_endpoint_signal_inputs import read_endpoint_signal_inputs,endpoint_signal_population_schema,endpoint_signal_extraction_schema,covariance_source_schema
from gene_annotation_episode.literature_endpoint_signal_calculations import populate_endpoint_signal,endpoint_signal_sheet_schema

def put(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
def freeze(path):
 relative=path.relative_to(ROOT);target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(path.read_bytes())
 return {'path':str(relative),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
# Actual imported local module files; no provider requests, data or private logs.
imports=[]
for name,module in sorted(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file:continue
 path=Path(file).resolve()
 if path.suffix=='.py' and path.is_relative_to(ROOT/'gene_annotation_episode'):
  imports.append({'module':name,**freeze(path)})
inputs=[ROOT/'tests/test_literature_endpoint_signal_components_241.py']
inputs += [OWN/x for x in ['INPUT_SCHEMA_002.json','EXTRACTION_SCHEMA_002.json','COVARIANCE_SCHEMA_002.json','SHEET_SCHEMA_002.json',
 'EXAMPLE_INPUT_002.json','CELL_CONSTANTS_002.json','PROMPT_CONSTANT_PLAN_001.txt','PLAN_001.md','PLAN_ADDENDUM_002.md',
 'PLAN_MANIFEST_001.json','PLAN_MANIFEST_002.json','PAIRED_NUMERICAL_EXPECTATION_001.json','RESET_PROVENANCE_001.json',
 'SCHEMA_SOURCE_CHECKS_002.json','TEST_HISTORY_003.json']]
case=ROOT/'research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238'
inputs += [case/'originals'/x for x in ['primary.html','primary_text.txt','figure4.jpg']]
inputs += [ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_contributor_review_240/SHARED_UNCERTAINTY_ORACLE_001.json']
data=[freeze(path) for path in inputs]
for name,fn in [('INPUT',endpoint_signal_population_schema),('EXTRACTION',endpoint_signal_extraction_schema),
 ('COVARIANCE',covariance_source_schema),('SHEET',endpoint_signal_sheet_schema)]:
 assert fn()==json.loads((OWN/(name+'_SCHEMA_002.json')).read_text())
args=json.loads((OWN/'EXAMPLE_INPUT_002.json').read_text())
blobs={('source_kaster_primary','original'):(case/'originals/primary.html').read_bytes(),
 ('source_kaster_primary','text'):(case/'originals/primary_text.txt').read_bytes(),
 ('source_kaster_original_figure4','original'):(case/'originals/figure4.jpg').read_bytes()}
calls=[]
def source(reference,representation):
 calls.append([reference,representation]);raw=blobs[reference,representation]
 return {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw}
extraction=read_endpoint_signal_inputs(args,read_source=source);sheet=populate_endpoint_signal(extraction)
put(PIN/'ACTUAL_SOURCE_EXTRACTION_003.json',extraction)
put(PIN/'ACTUAL_SOURCE_SHEET_003.json',sheet)
put(PIN/'ACTUAL_SOURCE_CUSTODY_003.json',{'read_calls':calls,'distinct_original_publication_count':1,
 'manual_graph_reading':True,'physical_covariance':None,'selected_operation_binding':False})
# AST imports name only; runtime custody uses actual loaded local files above.
asts=[]
for name in MODULES:
 path=Path(importlib.import_module(name).__file__)
 tree=ast.parse(path.read_text())
 asts.append({'module':name,'imports':[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]})
put(PIN/'IMPORT_CUSTODY_003.json',{'actual_local_imports':imports,'static_imports':asts,
 'python':sys.version,'Pillow':importlib.import_module('PIL').__version__,
 'jsonschema':importlib.metadata.version('jsonschema') if hasattr(importlib,'metadata') else None,
 'scope':'Actual local imported .py bytes only. No model/provider traffic or private data inspected.'})
for manifest in ['PLAN_MANIFEST_001.json','PLAN_MANIFEST_002.json']:
 record=json.loads((OWN/manifest).read_text())
 assert all(hashlib.sha256((OWN/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in record['files'])
records=[]
for path in sorted(PIN.rglob('*')):
 if path.is_file():records.append({'path':str(path.relative_to(PIN)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
put(PIN/'MANIFEST_003.json',{'status':'immutable_code_test_source_schema_pin','files':records,
 'excluded':['MANIFEST_003.json self-entry','__pycache__ and pytest caches created by verification'],
 'production_files_added':[n.replace('.','/')+'.py' for n in MODULES],
 'existing_production_files_edited':0,'new_selected_operations':0,'physical_covariance_conversion':False})
print(json.dumps({'pin':str(PIN),'local_imports':len(imports),'source_and_test_files':len(data),
 'source_values':[(c['component'],c['value'],c['conditional_value']) for c in sheet['cells'][:5]],
 'all4schemas_exact':True,'frozen001_002_unchanged':True}))
