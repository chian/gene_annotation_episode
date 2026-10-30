"""Hand-constructed SYNTHETIC expected output, not a native reader implementation."""
import json,hashlib,sys
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[2]))
from gene_annotation_episode.literature_binding_visual_inputs import _Inputs
from gene_annotation_episode.literature_assay_inputs import _Sources
request=json.loads((HERE/'SYNTHETIC_REQUEST_001.json').read_text());g=request['measurement']
bitmap=(HERE/'synthetic_pixels/positive_upper.png').read_bytes();labels=b'Linear scale\n4\n0\numol/min\n'
h=lambda b:hashlib.sha256(b).hexdigest()
ref=request['images'][0]['source_ref'];labelref=g['axis']['first']['tick']['candidates'][0]['source_ref']
content={ref:bitmap,labelref:labels}
def callback(r,k):return {'artifact_ref':'artifact_synthetic_'+('figure' if r==ref else 'labels'),'content':content[r]}
images=_Inputs(callback);image_record=images.image(request['images'][0]);assert image_record['error'] is None
sources=_Sources(callback)
def wr(w):
 native={k:v for k,v in w.items() if k!='kind'};sources.witness(native,'synthetic_example')
 return {'selection':w,'artifact_ref':callback(w['source_ref'],w['representation'])['artifact_ref'],'byte_sha256':h(labels),'canonical_locator':{'kind':'text','source_ref':w['source_ref'],'artifact_ref':callback(w['source_ref'],w['representation'])['artifact_ref'],'byte_sha256':h(labels),'start':w['start'],'end':w['end']},'authentication':'exact_utf8_byte_span','attribution':'literal_source_record','diagnostics':[]}
def rational(n,d=1):f=Fraction(n,d);return {'numerator':str(f.numerator),'denominator':str(f.denominator)}
scale_wr=[wr(w) for w in g['axis']['scale']['witnesses']]
axis={}
for name in ['first','second','unit']:
 al=g['axis'][name]['tick'] if name!='unit' else g['axis']['unit'];w=al['candidates'][0]
 axis[name]={'selection':al,'candidates':[wr(w)],'fragments':[],'raw_literal':w['quote'],'exact_value':rational(int(w['quote'])) if name!='unit' else None,'qualification':'source_text_literal','status':'parsed','diagnostics':[]}
unit={'selection':g['axis']['unit'],'witness':axis['unit']['candidates'][0],'raw_unit':'umol/min','canonical_unit':'umol/min','exact_scale':rational(1),'native_registry_unit':'umol/min','definition_witnesses':None,'status':'supported','diagnostics':[]}
diag={'code':'graph_conditional_digitization','field':'measurement','domain':'source_interpretation','source_refs':[ref,labelref]}
pixel={'version':'controlled_response_rate_pixels_v1','status':'measured','image_id':'figure','image_sha256':h(bitmap),'original_image_sha256':h(bitmap),'mapped_roi':{'kind':'image','original_source_ref':ref,'original_artifact_ref':'artifact_synthetic_figure','original_byte_sha256':h(bitmap),'region':[10,5,30,105]},'recipe':g['bar_selection'],'terminal_edge':'upper','image_size':{'width':40,'height':110},'qualifying_runs':[{'top':20,'bottom':60}],'pixel_edge':{'terminal_edge':'upper','nominal':rational(41,2),'bounds':{'lower':rational(39,2),'upper':rational(43,2)}},'axis':{'first_pixel':rational(20),'second_pixel':rational(60),'first_value':rational(4),'second_value':rational(0),'unit':'umol/min','slope':rational(-1,10)},'native_ordinate':rational(79,20),'native_bounds':{'lower':rational(77,20),'upper':rational(81,20)},'bound_kind':'conditional_digitization_not_confidence_interval','core_version':'literature_bar_ordinate_v1','core_sha256':next(row['sha256'] for row in json.loads((HERE/'BASELINE_001.json').read_text())['files'] if row['path']=='gene_annotation_episode/literature_figure_measurements.py'),'core_counting_calibration':'host_pixel_identity_not_scientific_data','diagnostics':[diag]}
measurement={'selection':g,'candidates':[],'fragments':[],'unit':unit,'graph_witnesses':scale_wr+[axis[x]['candidates'][0] for x in ['first','second','unit']],'reading_status':'graph_digitized','source_observation_id':'synthetic_expected_only_'+h(json.dumps(request,sort_keys=True).encode())[:24],'canonical_display':{'value':3.95,'threshold':None,'unit':'umol/min','relation':'eq','approximate':True,'diagnostics':[]},'pixel_result':pixel,'diagnostics':[diag]}
expected={'version':'controlled_response_rate_figure_extraction_v1','selection':request,'sources':[{'source_ref':r,'representation':'original' if r==ref else 'text','artifact_ref':callback(r,'original')['artifact_ref'],'byte_sha256':h(b),'state':'available','diagnostics':[]} for r,b in content.items()],'images':[image_record],'axis_scale':{'selection':g['axis']['scale'],'witnesses':scale_wr,'effective_kind':'linear','support':'literal_source_text','diagnostics':[{'code':'graph_axis_scale_interpretation','field':'measurement.axis.scale','domain':'source_interpretation','source_refs':[labelref]}]},'axis_literals':axis,'measurement':measurement,'operand_projection':{'value':3.95,'threshold':None,'relation':'interval','approximate':True,'unit':'umol/min','status':'point','origin':'graph_derived','digitization_interval':{'lower':3.85,'upper':4.05}},'diagnostics':[diag]}
validator=Draft202012Validator(json.loads((HERE/'GRAPH_RESULT_SCHEMA_001.json').read_text()));validator.validate(expected)
rejected=[]
for label,modify in [('extra_root',lambda d:d.update(new_score=1)),('extra_pixel_number',lambda d:d['measurement']['pixel_result'].update(scientific_score=1)),('missing_graph_provenance',lambda d:d['measurement']['pixel_result'].pop('original_image_sha256'))]:
 d=deepcopy(expected);modify(d);assert list(validator.iter_errors(d));rejected.append(label)
(HERE/'SYNTHETIC_OUTPUT_001.json').write_text(json.dumps(expected,indent=2)+'\n')
(HERE/'EXPECTED_OUTPUT_RECEIPT_001.json').write_text(json.dumps({'kind':'hand_constructed_synthetic_expected_record_not_native_reader_output','schema_valid':True,'schema_rejections':rejected,'source_quotes_checked_by_frozen_source_helper':True,'image_record_checked_by_frozen049':True,'covariance_or_scoring_created':False},indent=2)+'\n')
print(json.dumps({'expected_record_schema_valid':True,'native_reader_output':False,'schema_rejections':rejected},indent=2))
