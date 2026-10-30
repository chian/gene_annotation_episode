"""Additive review corrections only; exclusive outputs, frozen001 untouched."""
from copy import deepcopy
from pathlib import Path
import hashlib, json
import jsonschema
P=Path(__file__).parent
case=Path('research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238')
def get(n): return json.loads((P/n).read_text())
def put(n,v):
 with (P/n).open('x') as f: json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def obj(p): return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def nullable(s): return {'anyOf':[deepcopy(s),{'type':'null'}]}
manifest=get('PLAN_MANIFEST_001.json')
assert all(hashlib.sha256((P/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in P.iterdir() if f.name.endswith('_001.json') or f.name.endswith('_001.md') or f.name.endswith('_001.txt') or f.name.endswith('_001.py')}
request=get('INPUT_SCHEMA_001.json')
w=deepcopy(request['properties']['context']['properties']['subject']['anyOf'][0])
box=deepcopy(request['properties']['image']['anyOf'][0]['properties']['panel_region'])
image_context=obj({'image_region':box,'meaning':{'const':'finite_selected_late_point_no_physical_time_extracted'}})
for name in ['experimental_system','expression_host']:
 request['properties']['context']['properties'][name]=nullable(w)
 request['properties']['context']['required'].append(name)
request['properties']['context']['properties']['sampling_window']=nullable(image_context)
request['properties']['context']['required'].append('sampling_window')
arrangement=obj({'value':{'enum':['single_preparation','replacement','coexistence','not_applicable','unknown','conflicting']},
 'witnesses':{'type':'array','items':w},'image_regions':{'type':'array','items':box}})
request['properties']['relationships']['properties']['arrangement']=arrangement
request['properties']['relationships']['required'].append('arrangement')
put('INPUT_SCHEMA_002.json',request)
extract=get('EXTRACTION_SCHEMA_001.json')
extract['properties']['arguments']=deepcopy(request)
rw=deepcopy(extract['properties']['context']['properties']['subject']['anyOf'][0]['properties']['witness'])
for name in ['experimental_system','expression_host']:
 extract['properties']['context']['properties'][name]=nullable(obj({'value':{'type':'string','minLength':1},'witness':rw}))
 extract['properties']['context']['required'].append(name)
 extract['properties']['context_errors']['properties'][name]=deepcopy(extract['properties']['context_errors']['properties']['subject'])
 extract['properties']['context_errors']['required'].append(name)
extract['properties']['context']['properties']['sampling_window']=nullable(obj({
 'value':{'const':'finite_selected_late_point_no_physical_time_extracted'},
 'witness':obj({**image_context['properties'],'source_ref':{'type':'string','minLength':1},'artifact_ref':{'type':'string','minLength':1},
 'authentication':{'const':'source_bytes_and_geometry_only'}})}))
extract['properties']['context']['required'].append('sampling_window')
extract['properties']['context_errors']['properties']['sampling_window']=deepcopy(extract['properties']['context_errors']['properties']['subject'])
extract['properties']['context_errors']['required'].append('sampling_window')
enriched=deepcopy(arrangement)
enriched['properties']['witnesses']['items']=rw
enriched['properties']['kind']={'const':'source_interpretation'};enriched['required'].insert(0,'kind')
extract['properties']['relationships']['properties']['arrangement']=obj({'interpretation':nullable(enriched),'error':deepcopy(extract['properties']['context_errors']['properties']['subject'])})
extract['properties']['relationships']['required'].append('arrangement')
cov=get('COVARIANCE_SCHEMA_001.json')
cov['properties']['native_coordinate_basis_witnesses']=cov['properties'].pop('affine_mapping_witnesses')
cov['required'][cov['required'].index('affine_mapping_witnesses')]='native_coordinate_basis_witnesses'
cov['properties']['coordinate_units_status']={'const':'already_in_declared_native_coordinate_units'}
cov['required'].append('coordinate_units_status')
put('COVARIANCE_SCHEMA_002.json',cov)
extract['properties']['covariance']['anyOf'][0]['properties']['model']=nullable(cov)
put('EXTRACTION_SCHEMA_002.json',extract)
sheet=get('SHEET_SCHEMA_001.json');sheet['properties']['input_snapshot']=deepcopy(extract)
COMP=request['properties']['requested_cells']['items']['enum']; base=COMP[:5]
FORMULAS=dict(zip(COMP,['s*(a-t)','s*(a-b)','s*(b-t)','(a-b)/(a-t)','1-(a-b)/(a-t)',
 'J_D*Sigma*J_D_transpose','J_C*Sigma*J_C_transpose','J_G*Sigma*J_G_transpose','J_F*Sigma*J_F_transpose','J_H*Sigma*J_H_transpose']))
MEANINGS=dict(zip(COMP,[
 'Selected total reporter amplitude in direction-oriented native pixels.',
 'Reporter amplitude retained under the selected baseline correction model.',
 'Additional reporter amplitude under the selected baseline correction model.',
 'Corrected-to-total reporter amplitude ratio under the selected model.',
 'Additional-to-total reporter amplitude ratio under the selected model.',
 'First-order variance of the total amplitude in the supplied joint estimate model.',
 'First-order variance of the corrected amplitude in the supplied joint estimate model.',
 'First-order variance of the additional amplitude in the supplied joint estimate model.',
 'First-order variance of the retained fraction in the supplied joint estimate model.',
 'First-order variance of the additional fraction in the supplied joint estimate model.']))
cell=sheet['properties']['cells']['items']
cell['properties']['formula']={'enum':list(FORMULAS.values())}
cell['properties']['meaning']={'enum':list(MEANINGS.values())}
cell['properties']['conditional_on']['items']={'enum':[
 'common_affine_native_ordinate','selected_ordinate_direction','selected_finite_time_coordinate',
 'source_displayed_baseline','baseline_extrapolation_supported','baseline_extrapolation_stipulated',
 'fast_component_completion_supported','fast_component_completion_stipulated','uncorrected_source_trace',
 'same_trace_shared_initial_ordinate','joint_manual_reading_error_model','joint_physical_ordinate_estimate_model',
 'covariance_already_in_native_coordinate_units','known_covariance','estimated_covariance',
 'first_order_covariance_propagation','synthetic_uncertainty_scenario']}
put('SHEET_SCHEMA_002.json',sheet)
put('CELL_CONSTANTS_002.json',{'FORMULAS':FORMULAS,'MEANINGS':MEANINGS,
 'conditional_on':cell['properties']['conditional_on']['items']['enum']})
raw=(case/'originals/primary_text.txt').read_bytes()
caption_start=raw.index(b'Metronidazole (MTZ) reduction with 100% H2 at limiting concentrations',raw.index(b'Fig. 4.\n'))
caption_end=raw.index(b'\n',caption_start)
caption=raw[caption_start:caption_end]
def witness(lit,where=caption):
 b=lit.encode();local=where.index(b);start=(caption_start if where is caption else 0)+local
 return {'source_ref':'source_kaster_primary','representation':'text','start':start,'end':start+len(b),'quote':lit}
ex=get('EXAMPLE_INPUT_001.json')
replacements={
 'subject':'MvhADG/HdrABC complex from M. marburgensis',
 'organism':'M. marburgensis',
 'condition':'The assays were performed at 60 °C in 1.5-mL anaerobic cuvettetes containing 0.75 mL assay mixture with 1.6 M potassium phosphate (pH 7), MvhADG/HdrABC complex (∼0.1 unit), MTZ (90 nmol), and CoM-S-S-CoB as indicated.',
 'partners':'CoM-S-S-CoB',
 'experiment':'Time course with 90 nmol MTZ and 72 nmol CoM-S-S-CoB',
 'endpoint':'followed photometrically at 320 nm',
 'experimental_system':'1.5-mL anaerobic cuvettetes containing 0.75 mL assay mixture'}
for name,lit in replacements.items(): ex['context'][name]=witness(lit)
ex['context']['expression_host']=None
ex['context']['sampling_window']={'image_region':[180,174,202,191],'meaning':'finite_selected_late_point_no_physical_time_extracted'}
ex['image']['panel_region']=[0,0,238,262]
for name in ['axis_scale','ordinate_direction']:
 ex['relationships'][name]['witnesses']=[]
 ex['relationships'][name]['image_regions']=[[18,35,65,225]]
ex['relationships']['measurement_stage']['witnesses']=[witness('followed photometrically at 320 nm')]
ex['relationships']['arrangement']={'value':'coexistence','witnesses':[witness('MvhADG/HdrABC complex from M. marburgensis')],
 'image_regions':[[60,8,170,40]]}
for field in ['initial','late']:
 ex['image']['points'][field]['semantic_witnesses']=[witness(replacements['experiment'])]
put('EXAMPLE_INPUT_002.json',ex)
checks=[]
for name,entry in ex['context'].items():
 if entry is not None and 'start' in entry:
  assert raw[entry['start']:entry['end']].decode()==entry['quote']
  if name in replacements:
   assert caption_start<=entry['start']<entry['end']<=caption_end
  checks.append({'field':'context.'+name,'start':entry['start'],'end':entry['end'],
   'belongs_to_fig4_caption':caption_start<=entry['start']<entry['end']<=caption_end,'exact_utf8_match':True})
for r in ex['relationships'].values():
 for e in r['witnesses']: assert raw[e['start']:e['end']].decode()==e['quote']
for point in ex['image']['points'].values():
 for e in point['semantic_witnesses']: assert raw[e['start']:e['end']].decode()==e['quote']
for n in ['INPUT_SCHEMA_002.json','EXTRACTION_SCHEMA_002.json','SHEET_SCHEMA_002.json','COVARIANCE_SCHEMA_002.json']:
 jsonschema.Draft202012Validator.check_schema(get(n))
jsonschema.validate(ex,request)
# Check original image's declared dimensions, points, support and all image regions.
from PIL import Image
with Image.open(case/'originals/figure4.jpg') as im:
 assert im.size==(ex['image']['width'],ex['image']['height'])
 image=im.convert('RGB')
def inside(a,b):return b[0]<=a[0]<a[2]<=b[2] and b[1]<=a[1]<a[3]<=b[3]
panel=ex['image']['panel_region']
assert inside(panel,[0,0,image.width,image.height])
for r in ex['relationships'].values():
 for region in r['image_regions']: assert inside(region,panel)
assert inside(ex['context']['sampling_window']['image_region'],panel)
for point in ex['image']['points'].values():
 assert inside(point['support_region'],panel)
 assert inside(point['image_witness']['region'],panel)
 assert point['y_enclosure'][0]<=point['y']<=point['y_enclosure'][1]
assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==v for n,v in before.items())
# A lossless fieldwise JSON delta; removed/added fields are exact values, not a summary.
def delta(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)):
   q=path+'/'+k.replace('~','~0').replace('/','~1')
   if k not in a:yield {'op':'add','path':q,'value':b[k]}
   elif k not in b:yield {'op':'remove','path':q,'old_value':a[k]}
   else:yield from delta(a[k],b[k],q)
 elif a!=b:yield {'op':'replace','path':path,'old_value':a,'value':b}
put('EXACT_FIELDWISE_DELTA_002.json',{'base':'frozen001','revisions':{stem:list(delta(get(stem+'_001.json'),get(stem+'_002.json')))
 for stem in ['INPUT_SCHEMA','EXTRACTION_SCHEMA','SHEET_SCHEMA','COVARIANCE_SCHEMA','EXAMPLE_INPUT']}})
put('SCHEMA_SOURCE_CHECKS_002.json',{'status':'passed','schemas_checked':4,'closed_actual_source_example_validated':True,
 'source_sha256':hashlib.sha256(raw).hexdigest(),'original_image_sha256':hashlib.sha256((case/'originals/figure4.jpg').read_bytes()).hexdigest(),
 'fig4_caption_utf8_span':[caption_start,caption_end],'source_span_checks':checks,
 'axis_support_region':[18,35,65,225],'panel_region':panel,'axis_regions_geometry_valid':True,
 'frozen001_files_unchanged':True,'frozen001_sha256':before,'production_files_written':0})
print('002 additive schemas/example/delta: checks passed; frozen001 unchanged.')
