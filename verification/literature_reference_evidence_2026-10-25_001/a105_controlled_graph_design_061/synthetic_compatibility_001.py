"""SOURCE-FREE DESIGN PROOF ONLY, not a native reader, grader or scientific fixture.
Calls frozen pixel/crop helpers on bitmaps constructed here. Proposed signed-edge
algebra is shown as fixture arithmetic; no production implementation is supplied.
"""
from copy import deepcopy
from fractions import Fraction as F
from hashlib import sha256
from io import BytesIO
import json, math, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from PIL import Image, ImageDraw
from jsonschema import Draft202012Validator
from gene_annotation_episode.literature_figure_measurements import read_bar_ordinate
from gene_annotation_episode.literature_binding_visual_inputs import _Inputs
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.domain import ContractError
baseline_identity=json.loads((HERE/'BASELINE_001.json').read_text())
for row in baseline_identity['files']:
 p=Path(row['path']);p=p if p.is_absolute() else ROOT/p
 assert sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
for name in ['SELECTION_SCHEMA_V2_001.json','GRAPH_REQUEST_SCHEMA_001.json','GRAPH_RESULT_SCHEMA_001.json']:
 Draft202012Validator.check_schema(json.loads((HERE/name).read_text()))
(HERE/'synthetic_pixels').mkdir(exist_ok=True)
recipe={'roi':{'left':10,'top':5,'right':30,'bottom':105},'rgb_min':[0,0,0],'rgb_max':[30,30,30],'minimum_row_fraction':.75,'minimum_run_rows':2,'edge_tolerance_pixels':.5}
identity={'first':{'pixel':0,'value':0},'second':{'pixel':1,'value':1},'unit':'arbitrary_signal'}
records=[]
def bitmap(name,rectangles,mode='RGB'):
 bg=(255,255,255,255) if mode=='RGBA' else 'white'
 image=Image.new(mode,(40,110),bg); draw=ImageDraw.Draw(image)
 for box,colour in rectangles: draw.rectangle(box,fill=colour)
 out=BytesIO();image.save(out,format='PNG');b=out.getvalue();(HERE/'synthetic_pixels'/f'{name}.png').write_bytes(b)
 return image,b

def exact(value): return {'numerator':str(value.numerator),'denominator':str(value.denominator)}
def signed_fixture(run,edge,first=(20,'4'),second=(60,'0'),tol=F(1,2)):
 t,b=run['top'],run['bottom'];p=F(t)+F(1,2) if edge=='upper' else F(b)-F(1,2)
 lo,hi=(F(t)-tol,F(t+1)+tol) if edge=='upper' else (F(b-1)-tol,F(b)+tol)
 p1,v1=F(first[0]),F(first[1]);p2,v2=F(second[0]),F(second[1]);s=(v2-v1)/(p2-p1)
 f=lambda y:v1+(y-p1)*s
 lower,upper=sorted([f(lo),f(hi)])
 return {'nominal':exact(f(p)),'lower':exact(lower),'upper':exact(upper),'unit':'umol/min','origin':'graph_derived','kind':'conditional_fixture_algebra_not_sampling_uncertainty'}
def run(name,rectangles,edge='upper',first=(20,'4'),second=(60,'0'),change=None,mode='RGB'):
 image,b=bitmap(name,rectangles,mode);r=deepcopy(recipe)
 if change:r.update(change)
 result=read_bar_ordinate(b,{**r,'calibration':deepcopy(identity)})
 record={'name':name,'image_sha256':sha256(b).hexdigest(),'core_result':result,'selected_terminal_edge':edge}
 if len(result['qualifying_runs'])==1:
  record['proposed_signed_fixture']=signed_fixture(result['qualifying_runs'][0],edge,first,second)
 records.append(record);return image,b,result,record
_,_,positive,p=run('positive_upper',[((10,20,29,59),'black')]);assert positive['qualifying_runs']==[{'top':20,'bottom':60}]
assert p['proposed_signed_fixture']['nominal']==exact(F(79,20))
_,_,negative,n=run('negative_lower',[((10,60,29,79),'black')],edge='lower');assert n['proposed_signed_fixture']['nominal']==exact(F(-39,20))
old=read_bar_ordinate((HERE/'synthetic_pixels/negative_lower.png').read_bytes(),{**recipe,'calibration':{'first':{'pixel':20,'value':4},'second':{'pixel':60,'value':0},'unit':'arbitrary_signal'}})
assert old['cell']['value']==-.05
n['old_direct_scientific_helper_uses_wrong_upper_edge']=old
_,_,_,rev=run('reversed_axis_lower',[((10,60,29,79),'black')],edge='lower',first=(20,'-4'),second=(60,'0'));assert rev['proposed_signed_fixture']['nominal']==exact(F(39,20))
_,_,_,revneg=run('reversed_axis_negative_upper',[((10,20,29,59),'black')],first=(20,'-4'),second=(60,'0'));assert revneg['proposed_signed_fixture']['nominal']==exact(F(-79,20))
_,_,empty,_=run('empty',[]);assert empty['cell']['unavailable_reason']=='no_bar_pixels'
_,_,multiple,_=run('separate_label_or_cap',[((10,10,29,12),'black'),((10,30,29,59),'black')]);assert multiple['cell']['unavailable_reason']=='ambiguous_bar_runs'
_,_,cliptop,c=run('upper_terminal_clipped',[((10,5,29,59),'black')]);assert cliptop['cell']['unavailable_reason']=='truncated_mean_edge';c['proposed_gate']='unreadable: upper terminal == roi.top'
_,_,clipbottom,c=run('lower_terminal_clipped',[((10,60,29,104),'black')],edge='lower');assert clipbottom['qualifying_runs'][0]['bottom']==105;c['proposed_gate']='unreadable: lower terminal == roi.bottom; core itself does not check this'
_,_,baseline,c=run('only_baseline_clipped',[((10,5,29,79),'black')],edge='lower');assert baseline['cell']['unavailable_reason']=='truncated_mean_edge';c['proposed_gate']='selected lower endpoint is available; opposite baseline clipped is retained qualification, no zero-baseline inference'
_,_,interfere,c=run('connected_errorbar_in_narrow_roi',[((17,40,22,79),'black'),((10,60,29,79),'black')],change={'roi':{'left':17,'top':5,'right':23,'bottom':105}});assert interfere['qualifying_runs']==[{'top':40,'bottom':80}];c['limitation']='Sole threshold run cannot distinguish connected same-colour errorbar stem from mean bar; upper endpoint40.5 is not actual bar edge60.5. Needs episode ROI/colour repair or unsupported partial.'
_,_,alpha,c=run('invisible_alpha_black',[((10,20,29,59),(0,0,0,0))],mode='RGBA');assert alpha['qualifying_runs']==[{'top':20,'bottom':60}];c['proposed_gate']='unsupported: nonopaque ROI; core removes alpha and counts invisible RGB'
_,_,aa,c=run('antialias_threshold_excluded',[((10,20,29,59),(80,80,80))]);assert aa['cell']['unavailable_reason']=='no_bar_pixels'
try:
 read_bar_ordinate((HERE/'synthetic_pixels/positive_upper.png').read_bytes(),{**recipe,'calibration':{'first':{'pixel':20,'value':4},'second':{'pixel':60,'value':0},'unit':'umol/min'}})
 raise AssertionError('rateunit unexpectedly accepted')
except ContractError as e:
 unsupported={'code':str(e),'field':e.detail['field_path']};assert str(e)=='unsupported_calibration_unit'
# Actual original/crop pixel equality and geometry from frozen049, no scientific data.
original,b=bitmap('crop_original',[((10,20,29,59),'black')]);crop=original.crop((5,10,35,90));out=BytesIO();crop.save(out,format='PNG');cb=out.getvalue();(HERE/'synthetic_pixels/crop_selected.png').write_bytes(cb)
content={'source_synthetic_original':b,'source_synthetic_crop':cb}
def callback(reference,representation):
 assert representation=='original';return {'artifact_ref':'artifact_'+reference,'content':content[reference]}
inputs=_Inputs(callback); image_record=inputs.image({'image_id':'crop','source_ref':'source_synthetic_crop','original_source_ref':'source_synthetic_original','mapping':{'original_region':[5,10,35,90],'colour_conversion':'preserve'}})
assert image_record['error'] is None
mapped=inputs.location('crop',[5,10,25,50]);assert mapped['image_region']==[10,20,30,60]
# Actual text exact bytes; image text is separately an attributed nomination.
text=b'Linear scale\n4\n0\numol/min\n'
sources=_Sources(lambda r,k:{'artifact_ref':'artifact_synthetic_labels','content':text})
literal=sources.witness({'source_ref':'source_synthetic_labels','representation':'text','start':13,'end':14,'quote':'4'},'tick')
assert literal['quote']=='4'
# Existing broad-catch limitation, deliberately no native-wrapper/auth success claim.
def forbidden(*_): raise ContractError('synthetic_authorization_denied')
legacy=_Inputs(forbidden).image({'image_id':'blocked','source_ref':'blocked','original_source_ref':'blocked','mapping':None})
assert legacy['error']['code']=='source_read_failed'
# JSON schemas close numeric injection, require edge and scale, retain unresolved scale.
def tw(quote,start,end):return {'kind':'text','source_ref':'source_aaaaaaaaaaaaaaaaaaaaaaaa','representation':'text','start':start,'end':end,'quote':quote}
def al(w):return {'status':'exact','candidates':[w],'fragments':[]}
nomination={'kind':'linear_bar','image_id':'figure','bar_selection':deepcopy(recipe),'terminal_edge':'upper','axis':{'first':{'pixel':20,'tick':al(tw('4',13,14))},'second':{'pixel':60,'tick':al(tw('0',15,16))},'unit':al(tw('umol/min',17,25)),'scale':{'status':'known','kind':'linear','basis':'source_text_literal','witnesses':[tw('Linear scale',0,12)]}}}
request={'version':'controlled_response_rate_figure_selection_v1','images':[{'image_id':'figure','source_ref':'source_bbbbbbbbbbbbbbbbbbbbbbbb','original_source_ref':'source_bbbbbbbbbbbbbbbbbbbbbbbb','mapping':None}],'measurement':nomination}
validator=Draft202012Validator(json.loads((HERE/'GRAPH_REQUEST_SCHEMA_001.json').read_text()));validator.validate(request)
invalid=[]
for label,modify in [('missing_edge',lambda d:d['measurement'].pop('terminal_edge')),('missing_scale',lambda d:d['measurement']['axis'].pop('scale')),('model_tick_value',lambda d:d['measurement']['axis']['first'].update(value=4)),('model_ordinate',lambda d:d['measurement'].update(value=4)),('known_scale_without_witness',lambda d:d['measurement']['axis']['scale'].update(witnesses=[]))]:
 d=deepcopy(request);modify(d);assert list(validator.iter_errors(d));invalid.append(label)
unknown=deepcopy(request);unknown['measurement']['axis']['scale']={'status':'unknown','kind':None,'basis':'unresolved','witnesses':[]};validator.validate(unknown)
# Outward export must use frozen006 Fraction(str(float)), not Fraction(float).
export=[]
for q in [F(1,10),F(1,3),F(-1,3),F(79,20),F(-41,20)]:
 row={'exact':exact(q)}
 for direction in [-1,1]:
  value=float(q)
  if (direction==-1 and F(str(value))>q) or (direction==1 and F(str(value))<q):value=math.nextafter(value,-math.inf if direction==-1 else math.inf)
  assert (F(str(value))<=q if direction==-1 else F(str(value))>=q)
  row['lower' if direction==-1 else 'upper']=value
 export.append(row)
receipt={'version':'controlled_graph_synthetic_compatibility_001','scope':'Proposal-only; constructed PNGs and synthetic label bytes; no source/paper coverage or selected-native implementation','baseline_unchanged':True,'schemas_well_formed':True,'synthetic_bitmaps':records,'direct_rate_unit_failure':unsupported,'crop_049':{'image_record':image_record,'mapped_location':mapped},'source_text_exact_witness':literal,'legacy_049_auth_failure_swallowed_into_record':legacy,'schema_valid_request':request,'schema_rejections':invalid,'unresolved_scale_structurally_preserved':unknown,'outward_decimal_projection_fixture':export,'not_tested':['native proposed wrapper not implemented','full v2 controlled response reader not implemented','authorization prefetch implementation not supplied','any primary figure','selected-native persistence/runtime path','scientific score or covariance'],'warnings':['Errorbar identity and image-label truth are episode interpretations; pixels do not attest them','Existing006 downstream bound float rendering is nearest, not universally outward; exact wrapper bounds remain authoritative']}
(HERE/'SYNTHETIC_COMPATIBILITY_001.json').write_text(json.dumps(receipt,indent=2)+'\n')
(HERE/'SYNTHETIC_REQUEST_001.json').write_text(json.dumps(request,indent=2)+'\n')
for row in baseline_identity['files']:
 p=Path(row['path']);p=p if p.is_absolute() else ROOT/p
 assert sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
print(json.dumps({'passed':True,'constructed_bitmap_cases':len(records)+2,'closed_schemas':3,'schema_rejections':invalid,'native_reader_implemented':False,'primary_figures_read':0,'baseline_unchanged':True},indent=2))
