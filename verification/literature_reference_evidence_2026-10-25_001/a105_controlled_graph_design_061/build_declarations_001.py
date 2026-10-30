"""Proposal artifacts only. No production reader or scientific grading implementation."""
from copy import deepcopy
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE/'baseline/verification/literature_reference_evidence_2026-10-25_001/a105_controlled_response_design_056/reader_stage_007/SELECTION_SCHEMA_007.json'
old=json.loads(OLD.read_text())
def obj(properties):
 return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def arr(items): return {'type':'array','items':items}
def ref(name): return {'$ref':'#/$defs/'+name}
def nullable(value): return {'anyOf':[value,{'type':'null'}]}
def enum(*values): return {'enum':list(values)}
text={'type':'string','minLength':1}; integer={'type':'integer','minimum':0}; number={'type':'number'}
sha={'type':'string','pattern':'^[a-f0-9]{64}$'}
scale=obj({'status':enum('known','unknown','conflicting'),'kind':nullable(enum('linear','logarithmic','nonlinear')),'basis':enum('source_text_literal','image_episode_interpretation','unresolved'),'witnesses':arr(ref('Witness'))})
scale['allOf']=[{'if':{'properties':{'status':{'const':'known'}}},'then':{'properties':{'kind':enum('linear','logarithmic','nonlinear'),'basis':enum('source_text_literal','image_episode_interpretation'),'witnesses':{'minItems':1}}},'else':{'properties':{'kind':{'type':'null'},'basis':{'const':'unresolved'}}}}]
selection=deepcopy(old)
selection['properties']['version']={'const':'controlled_response_source_selection_v2'}
selection['$defs']['AxisScale']=scale
selection['$defs']['GraphMeasurement']['properties']['terminal_edge']=enum('upper','lower')
selection['$defs']['GraphMeasurement']['required'].append('terminal_edge')
selection['$defs']['GraphMeasurement']['properties']['axis']['properties']['scale']=ref('AxisScale')
selection['$defs']['GraphMeasurement']['properties']['axis']['required'].append('scale')
# 'linear_bar' continues to name a linear-reader request; explicitly nominated non-linear scale yields unsupported.
defs=deepcopy(selection['$defs'])
request=obj({'version':{'const':'controlled_response_rate_figure_selection_v1'},'images':arr(ref('Image')),'measurement':ref('GraphMeasurement')})
request['$defs']=deepcopy(defs);request['$schema']='https://json-schema.org/draft/2020-12/schema'
D=deepcopy(defs)
D['Rational']=obj({'numerator':{'type':'string','pattern':'^-?(0|[1-9][0-9]*)$'},'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}})
D['Diagnostic']=obj({'code':enum('graph_image_unavailable','graph_image_unsupported','graph_nonopaque_roi','graph_scale_unknown','graph_scale_conflicting','graph_scale_unsupported','graph_scale_literal_unsupported','graph_tick_ambiguous','graph_tick_conflicting','graph_tick_unreadable','graph_tick_literal_unsupported','graph_tick_literal_numeric_range','graph_tick_projection_rounded','graph_unit_ambiguous','graph_unit_conflicting','graph_unit_unreadable','graph_unit_unknown','graph_unit_unsupported','graph_unit_defined_bridge_unselected','graph_no_bar_pixels','graph_ambiguous_bar_runs','graph_terminal_edge_clipped','graph_axis_degenerate','graph_pixel_bounds_outside_image','graph_numerical_model_range','graph_canonical_display_range','graph_image_label_interpretation','graph_axis_scale_interpretation','graph_conditional_digitization','graph_ordinate_projection_rounded','graph_opposite_edge_clipped','graph_axis_multiplier_unsupported'),'field':text,'domain':enum('source_representation','source_binding','reader_capability','source_interpretation','dependency'),'source_refs':arr(text)})
diags=arr(ref('Diagnostic'))
D['TextLocator']=obj({'kind':{'const':'text'},'source_ref':text,'artifact_ref':text,'byte_sha256':sha,'start':integer,'end':{'type':'integer','minimum':1}})
D['ImageLocator']=obj({'kind':{'const':'image'},'original_source_ref':text,'original_artifact_ref':text,'original_byte_sha256':sha,'region':ref('Box')})
D['WitnessRecord']=obj({'selection':ref('Witness'),'artifact_ref':nullable(text),'byte_sha256':nullable(sha),'canonical_locator':nullable({'oneOf':[ref('TextLocator'),ref('ImageLocator')]}),'authentication':enum('exact_utf8_byte_span','image_bytes_and_geometry_only','unavailable'),'attribution':enum('literal_source_record','investigating_episode_interpretation'),'diagnostics':diags})
D['SourceRecord']=obj({'source_ref':text,'representation':enum('original','text'),'artifact_ref':nullable(text),'byte_sha256':nullable(sha),'state':enum('available','unavailable'),'diagnostics':diags})
D['DependencyError']=obj({'code':text,'field':text})
D['ImageRecord']=obj({'image_id':text,'source_ref':text,'artifact_ref':nullable(text),'byte_sha256':nullable(sha),'original_source_ref':text,'original_artifact_ref':nullable(text),'original_byte_sha256':nullable(sha),'actual_format':nullable(text),'actual_mode':nullable(text),'width':nullable(integer),'height':nullable(integer),'frame_count':nullable(integer),'mapping':deepcopy(defs['Image']['properties']['mapping']),'pillow_version':text,'error':nullable(ref('DependencyError'))})
D['AxisScaleRecord']=obj({'selection':ref('AxisScale'),'witnesses':arr(ref('WitnessRecord')),'effective_kind':enum('linear','logarithmic','nonlinear','unknown','conflicting'),'support':enum('literal_source_text','episode_image_interpretation','unavailable','unresolved'),'diagnostics':diags})
D['AxisLiteralRecord']=obj({'selection':ref('AxisLiteral'),'candidates':arr(ref('WitnessRecord')),'fragments':arr(ref('WitnessRecord')),'raw_literal':nullable(text),'exact_value':nullable(ref('Rational')),'qualification':enum('source_text_literal','episode_image_transcription','unresolved'),'status':enum('parsed','ambiguous','unreadable','conflicting','unsupported','dependency_unavailable'),'diagnostics':diags})
units=enum('umol/min','nmol/min','mmol/min','uM/min','nM/min','per_min','per_s','umol/min/mg','nmol/min/mg')
canonical=enum('umol/min','uM/min','per_min','umol/min/mg')
D['GraphUnitRecord']=obj({'selection':ref('AxisLiteral'),'witness':nullable(ref('WitnessRecord')),'raw_unit':nullable(text),'canonical_unit':nullable(canonical),'exact_scale':nullable(ref('Rational')),'native_registry_unit':nullable(units),'definition_witnesses':{'type':'null'},'status':enum('supported','unknown','unsupported','numeric_range','dependency_unavailable','endpoint_correspondence_unknown'),'diagnostics':diags})
D['ExactBounds']=obj({'lower':ref('Rational'),'upper':ref('Rational')})
D['FloatBounds']=obj({'lower':number,'upper':number})
D['Run']=obj({'top':integer,'bottom':integer})
D['ExactPixelEdge']=obj({'terminal_edge':enum('upper','lower'),'nominal':ref('Rational'),'bounds':ref('ExactBounds')})
D['ExactAxis']=obj({'first_pixel':ref('Rational'),'second_pixel':ref('Rational'),'first_value':ref('Rational'),'second_value':ref('Rational'),'unit':units,'slope':ref('Rational')})
D['PixelResult']=obj({'version':{'const':'controlled_response_rate_pixels_v1'},'status':enum('measured','unreadable','ambiguous','unsupported','dependency_unavailable'),'image_id':text,'image_sha256':nullable(sha),'original_image_sha256':nullable(sha),'mapped_roi':nullable(ref('ImageLocator')),'recipe':ref('BarSelection'),'terminal_edge':enum('upper','lower'),'image_size':nullable(obj({'width':integer,'height':integer})),'qualifying_runs':arr(ref('Run')),'pixel_edge':nullable(ref('ExactPixelEdge')),'axis':nullable(ref('ExactAxis')),'native_ordinate':nullable(ref('Rational')),'native_bounds':nullable(ref('ExactBounds')),'bound_kind':{'const':'conditional_digitization_not_confidence_interval'},'core_version':{'const':'literature_bar_ordinate_v1'},'core_sha256':sha,'core_counting_calibration':{'const':'host_pixel_identity_not_scientific_data'},'diagnostics':diags})
D['CanonicalDisplay']=obj({'value':nullable(number),'threshold':nullable(number),'unit':nullable(canonical),'relation':enum('eq','lt','le','gt','ge','none'),'approximate':{'type':'boolean'},'diagnostics':diags})
D['NativeProjection']=obj({'value':nullable(number),'threshold':{'type':'null'},'relation':enum('interval','none'),'approximate':{'type':'boolean'},'unit':nullable(units),'status':enum('point','missing','ambiguous','conflicting','unsupported'),'origin':{'const':'graph_derived'},'digitization_interval':nullable(ref('FloatBounds'))})
D['MeasurementExtractionV2']=obj({'selection':ref('GraphMeasurement'),'candidates':{'type':'array','maxItems':0},'fragments':arr(ref('WitnessRecord')),'unit':nullable(ref('GraphUnitRecord')),'graph_witnesses':arr(ref('WitnessRecord')),'reading_status':enum('graph_digitized','ambiguous','unreadable','conflicting','unsupported','dependency_unavailable'),'source_observation_id':nullable(text),'canonical_display':ref('CanonicalDisplay'),'pixel_result':ref('PixelResult'),'diagnostics':diags})
result=obj({'version':{'const':'controlled_response_rate_figure_extraction_v1'},'selection':deepcopy({k:v for k,v in request.items() if k not in ('$schema','$defs')}),'sources':arr(ref('SourceRecord')),'images':arr(ref('ImageRecord')),'axis_scale':ref('AxisScaleRecord'),'axis_literals':obj({'first':ref('AxisLiteralRecord'),'second':ref('AxisLiteralRecord'),'unit':ref('AxisLiteralRecord')}),'measurement':ref('MeasurementExtractionV2'),'operand_projection':ref('NativeProjection'),'diagnostics':diags})
result['$defs']=D;result['$schema']='https://json-schema.org/draft/2020-12/schema'
for name,value in [('SELECTION_SCHEMA_V2_001.json',selection),('GRAPH_REQUEST_SCHEMA_001.json',request),('GRAPH_RESULT_SCHEMA_001.json',result)]:
 (HERE/name).write_text(json.dumps(value,indent=2)+'\n')
delta={'proposal_only':True,'old_selection_version':'controlled_response_source_selection_v1','new_selection_version':'controlled_response_source_selection_v2','selection_delta':[{'path':'/$defs/GraphMeasurement/properties/terminal_edge','change':'required upper|lower mechanical edge choice'},{'path':'/$defs/GraphMeasurement/properties/axis/properties/scale','change':'required closed AxisScale declaration'},{'path':'/$defs/AxisScale','change':'new closed status,kind,basis,witnesses type'}],'old_output_version':'controlled_response_source_extraction_v1','proposed_output_version':'controlled_response_source_extraction_v2','output_delta':{'MeasurementExtraction.reading_status':'add graph_digitized; old states retained','MeasurementExtraction.pixel_result':'null for old/text branch; PixelResult for v2 graph','MeasurementExtraction.unit':'UnitRecord for text; GraphUnitRecord for graph (selection is AxisLiteral; definition_witnesses=null)','ArmExtraction':'add graph_details:null|{axis_scale:AxisScaleRecord,axis_literals:{first:AxisLiteralRecord,second:AxisLiteralRecord,unit:AxisLiteralRecord}}; all arms carry field in v2','other_fields':'unchanged007 types and frozen006 calculation_inputs'},'wrapper':'read_controlled_response_rate_figure(arguments, *, read_source) -> GraphResult','consumer':'Future explicitly released new v2 controlled-response adapter calls separate wrapper. Frozen v1/008 remains unchanged; no runtime/schema registration authorized.'}
(HERE/'EXACT_DELTA_001.json').write_text(json.dumps(delta,indent=2)+'\n')
print('wrote three closed JSON schemas and explicit version delta')
