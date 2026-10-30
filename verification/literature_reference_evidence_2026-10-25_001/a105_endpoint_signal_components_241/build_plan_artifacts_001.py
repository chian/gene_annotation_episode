"""Planning artifacts only. Exclusive create; no production edits or science loop."""
from pathlib import Path
from copy import deepcopy
import json, hashlib
P=Path(__file__).parent
case=Path('research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238')
def out(name,value):
 with (P/name).open('x') as f: json.dump(value,f,indent=2,ensure_ascii=False); f.write('\n')
def obj(p): return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def arr(s,**kw): return {'type':'array','items':deepcopy(s),**kw}
def nullable(s): return {'anyOf':[deepcopy(s),{'type':'null'}]}
text={'type':'string','minLength':1}; ref=deepcopy(text); num={'type':'number'}; integer={'type':'integer','minimum':0}
def enum(v): return {'enum':v}
def const(v): return {'const':v}
w=obj({'source_ref':ref,'representation':enum(['original','text']),'start':integer,'end':{'type':'integer','minimum':1},'quote':text})
rw=obj({**w['properties'],'artifact_ref':ref})
box=arr(integer,minItems=4,maxItems=4)
iw=obj({'region':box,'meaning':enum(['initial_trace','displayed_baseline_at_addition','selected_late_trace'])})
ORDER=['initial','baseline_at_addition','late']
CTX=['subject','organism','genotype','construct','preparation','partners','experiment','condition','endpoint','normalization','intended_variable','functional_assertion','correction_discussion','limitations','repetition']
REL={
 'axis_scale':['common_affine','nonlinear','unknown','conflicting'],
 'ordinate_direction':['increases_upward','increases_downward','unknown','conflicting'],
 'measurement_stage':['endpoint_amplitude','initial_rate','other','unknown','conflicting'],
 'correction_stage':['not_applied','already_applied','unknown','conflicting'],
 'baseline_basis':['source_displayed_extrapolation','matched_control','new_fit','unknown','conflicting'],
 'baseline_applicability':['supported','explicit_conditional_scenario','unsupported','unknown','conflicting'],
 'fast_component_completion':['supported','explicit_conditional_scenario','unsupported','unknown','conflicting'],
 'additive_interpretation':['nonnegative_additive','signed_decomposition','unknown','conflicting']}
def interp(v,enriched=False):
 return obj({**({'kind':const('source_interpretation')} if enriched else {}),'value':enum(v),'witnesses':arr(rw if enriched else w)})
point=obj({'x':integer,'y':integer,'y_enclosure':nullable(arr(integer,minItems=2,maxItems=2)),
 'support_region':box,'maximum_rgb':{'type':'integer','minimum':0,'maximum':255},
 'image_witness':iw,'semantic_witnesses':arr(w),'physical_estimate_owner':nullable(w)})
image=obj({'source_ref':ref,'expected_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
 'width':{'type':'integer','minimum':1},'height':{'type':'integer','minimum':1},'panel_region':box,
 'image_origin':enum(['published','synthetic']), 'points':obj({r:nullable(point) for r in ORDER})})
COMP=['total_amplitude','corrected_amplitude','additional_amplitude','retained_fraction','additional_fraction']
ALL=COMP+[r+'_variance' for r in COMP]
req=obj({'version':const('a105_endpoint_signal_selection_v1'),'source_ref':ref,
 'source_kind':enum(['primary_source','retained_extraction','synthetic_fixture']),
 'context':obj({r:nullable(w) for r in CTX}),
 'relationships':obj({r:interp(v) for r,v in REL.items()}), 'image':nullable(image),
 'covariance_source_ref':nullable(ref), 'requested_cells':arr(enum(ALL),uniqueItems=True)})
out('INPUT_SCHEMA_001.json',req)
exact=obj({'numerator':{'type':'string','pattern':'^-?[0-9]+$'},'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}})
error=obj({'code':text,'field':text})
source=obj({'source_ref':ref,'representation':enum(['original','text']),'artifact_ref':nullable(ref),
 'sha256':nullable(text),'error':nullable(error)})
model=obj({'version':const('a105_endpoint_signal_covariance_v1'),
 'basis':enum(['joint_manual_reading_error','joint_physical_ordinate_estimates']),
 'primitive_order':const(ORDER),'primitive_owners':arr(ref,minItems=3,maxItems=3),
 'primitive_units':const(['native_ordinate_pixel']*3),
 'covariance':arr(arr(num,minItems=3,maxItems=3),minItems=3,maxItems=3),
 'variance_status':enum(['known','estimated','unknown']),
 'origin':enum(['source_reported','source_derived','synthetic']),
 'provenance_witnesses':arr(w),
 'affine_mapping_witnesses':arr(w)})
out('COVARIANCE_SCHEMA_001.json',model)
ptout=obj({'selection':point,'coordinate_owner':ref,'physical_estimate_owner':nullable(ref),
 'x':integer,'y':integer,'y_enclosure':nullable(arr(integer,minItems=2,maxItems=2)),
 'support':obj({'qualifying_pixel_count':integer,'point_rgb':arr(integer,minItems=3,maxItems=3),
 'authentication':const('source_bytes_geometry_and_ink_only')}),
 'semantic_witnesses':arr(rw),'physical_owner_witness':nullable(rw),
 'origin':enum(['graph_derived_manual','synthetic']), 'error':nullable(error)})
# A failed selected point still retains its request while no authenticated ordinate is emitted.
ptextract=obj({'selection':nullable(point),'observation':nullable(ptout),'error':nullable(error)})
covout=obj({'source_ref':ref,'artifact_ref':nullable(ref),'sha256':nullable(text),
 'model':nullable(model),'exact_covariance':nullable(arr(arr(exact,minItems=3,maxItems=3),minItems=3,maxItems=3)),
 'error':nullable(error)})
ext=obj({'version':const('a105_endpoint_signal_inputs_v1'),'arguments':req,
 'source_ref':ref,'source_kind':req['properties']['source_kind'],
 'context':obj({r:nullable(obj({'value':text,'witness':rw})) for r in CTX}),
 'context_errors':obj({r:nullable(error) for r in CTX}),
 'relationships':obj({r:obj({'interpretation':nullable(interp(v,True)),'error':nullable(error)}) for r,v in REL.items()}),
 'image':nullable(obj({'source_ref':ref,'artifact_ref':nullable(ref),'sha256':nullable(text),
 'width':nullable(integer),'height':nullable(integer),'format':nullable(enum(['PNG','JPEG'])),
 'mode':nullable(enum(['RGB','RGBA','L'])),'panel_region':box,'error':nullable(error)})),
 'points':obj({r:ptextract for r in ORDER}), 'covariance':nullable(covout),
 'source_artifacts':arr(source),'input_origins':arr(enum(['graph_derived_manual','reported','derived','synthetic']),uniqueItems=True)})
out('EXTRACTION_SCHEMA_001.json',ext)
REASONS=['source_unavailable','missing_initial','missing_baseline_at_addition','missing_late',
 'axis_scale_unestablished','ordinate_direction_unresolved','measurement_stage_not_endpoint',
 'correction_already_applied','correction_stage_unresolved','baseline_basis_unsupported',
 'baseline_applicability_unresolved','fast_component_completion_unresolved','zero_total_amplitude',
 'reading_enclosure_unreported','reading_denominator_contains_zero','covariance_unreported',
 'covariance_unavailable','covariance_status_unknown','covariance_basis_not_applicable',
 'numerical_projection_range']
cell=obj({'component':enum(ALL),'value':nullable(num),'conditional_value':nullable(num),
 'exact_value':nullable(exact),'conditional_exact_value':nullable(exact),
 'lower':nullable(num),'upper':nullable(num),'exact_lower':nullable(exact),'exact_upper':nullable(exact),
 'unit':enum(['direction_oriented_pixel','dimensionless','pixel^2','dimensionless^2']),
 'status':enum(['populated','conditional_scenario','unavailable']),
 'origin':const('derived'),'input_origins':ext['properties']['input_origins'],
 'formula':text,'meaning':text,'conditional_on':arr(text,uniqueItems=True),
 'unavailable_reasons':arr(enum(REASONS),uniqueItems=True),
 'qualifications':arr(enum(['manual_reading_not_physical_measurement','reading_bounds_not_statistical_CI',
 'nonnegative_additive_model_incompatible','physical_covariance_unreported',
 'synthetic_covariance_model','not_molecular_attribution','first_order_covariance_propagation']),uniqueItems=True),
 'bound_kind':enum(['manual_reading_enclosure_not_confidence_interval','none']),
 'primitive_owners':arr(nullable(ref),minItems=3,maxItems=3),
 'contribution_key':ref,'uncertainty_basis':nullable(enum(['joint_manual_reading_error','joint_physical_ordinate_estimates']))})
sheet=obj({'version':const('a105_endpoint_signal_components_v1'),'axis':const('A105'),
 'section':const('endpoint_signal_contribution'),'requested_cells':req['properties']['requested_cells'],
 'cells':arr(cell,uniqueItems=True),'input_snapshot':ext,
 'joint_propagation':nullable(obj({'basis':model['properties']['basis'],'origin':model['properties']['origin'],
 'primitive_order':const(ORDER),'primitive_owners':model['properties']['primitive_owners'],
 'component_order':const(COMP),'exact_covariance':arr(arr(exact,minItems=5,maxItems=5),minItems=5,maxItems=5)}))})
out('SHEET_SCHEMA_001.json',sheet)
# UTF8 byte witnesses are rebuilt from actual retained source, not borrowed character offsets.
raw=(case/'originals/primary_text.txt').read_bytes()
def witness(lit):
 b=lit.encode(); start=raw.index(b)
 return {'source_ref':'source_kaster_primary','representation':'text','start':start,'end':start+len(b),'quote':lit}
def reading(x,y,lo,hi,meaning):
 return {'x':x,'y':y,'y_enclosure':[lo,hi],'support_region':[x-2,lo,x+3,hi+1],
 'maximum_rgb':180,'image_witness':{'region':[x-2,lo,x+3,hi+1],'meaning':meaning},
 'semantic_witnesses':[witness('correct for by extrapolation')], 'physical_estimate_owner':None}
relations={r:{'value':v[0],'witnesses':[witness('correct for by extrapolation')]} for r,v in REL.items()}
relations['ordinate_direction']['value']='increases_upward'
relations['baseline_applicability']['value']='explicit_conditional_scenario'
relations['fast_component_completion']['value']='explicit_conditional_scenario'
context={r:None for r in CTX}
for key,lit in {'subject':'MvhADG/HdrABC complex','organism':'M. marburgensis (DSM 2133)',
 'condition':'1.6 M potassium phosphate (pH 7)', 'endpoint':'followed photometrically at 320 nm',
 'correction_discussion':'With this correction a stoichiometry of ∼0.6 mol MTZ reduced per mole of CoM-S-S-CoB added was found',
 'limitations':'MTZ reduction continued slowly','partners':'CoM-S-S-CoB','experiment':'Time course with 90 nmol MTZ and 72 nmol CoM-S-S-CoB'}.items():
 context[key]=witness(lit)
example={'version':'a105_endpoint_signal_selection_v1','source_ref':'source_kaster_primary','source_kind':'primary_source',
 'context':context,'relationships':relations,
 'image':{'source_ref':'source_kaster_original_figure4','expected_sha256':hashlib.sha256((case/'originals/figure4.jpg').read_bytes()).hexdigest(),
 'width':479,'height':262,'panel_region':[58,8,226,226],'image_origin':'published','points':dict(zip(ORDER,[
 reading(65,39,38,40,'initial_trace'),reading(75,170,168,172,'displayed_baseline_at_addition'),reading(190,181,180,183,'selected_late_trace')]))},
 'covariance_source_ref':None,'requested_cells':ALL}
out('EXAMPLE_INPUT_001.json',example)
out('PAIRED_NUMERICAL_EXPECTATION_001.json',{'scientific_status':'proposal_not_production_run','source_origin':'graph_derived_manual',
 'total_amplitude':{'value':142,'exact':[142,1],'unit':'direction_oriented_pixel','lower':140,'upper':145},
 'corrected_amplitude':{'conditional_value':131,'exact':[131,1],'lower':128,'upper':134},
 'additional_amplitude':{'conditional_value':11,'exact':[11,1],'lower':8,'upper':15},
 'retained_fraction':{'conditional_value':131/142,'exact':[131,142],'enclosure':[[128,143],[67,71]]},
 'additional_fraction':{'conditional_value':11/142,'exact':[11,142],'enclosure':[[4,71],[15,143]]},
 'variance_cells':{'all':None,'reason':'covariance_unreported'},'physical_covariance':None,
 'published_corrected_ratio':{'approximate_value':0.6,'correction_stage':'already_applied','apply_F_again':False,
 'production_parser_added_in_241':False},'same_contribution_identities':['D=C+G','C=F*D','H=1-F'],
 'not_established':['physical_experimental_covariance','physical_preparation_count','molecular_q_minus_g','installed_selected_delivery','A105_adequacy']})
# Reviewed source TASK is copied verbatim as a proposal, not implemented yet.
proposal=(case/'TASK_PROPOSAL_001.md').read_text()
task=proposal.split('## TASK\n\n',1)[1].split('\n## Separate STEERING responsibility',1)[0].strip()
with (P/'PROMPT_CONSTANT_PLAN_001.txt').open('x') as f: f.write(task+'\n')
print('Planning artifacts created exclusively:',len(list(P.iterdir())))
