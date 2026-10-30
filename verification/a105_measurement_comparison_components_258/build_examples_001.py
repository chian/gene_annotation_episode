"""Hand-construct schema illustrations only; this is not the proposed reader/calculator."""
from build_plan_001 import *
import math

def write(name, data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def empty_reasons():return {k:[] for k in REASONS}
def create_case(case, nfn=False, shared=False):
 lines=['SYNTHETIC PLANNING ILLUSTRATION; NOT ORIGINAL PAPER DATA OR EXECUTED EXTRACTION.']
 def add(t):
  start=len(('\n'.join(lines)+'\n').encode());lines.append(t)
  return {'start':start,'end':start+len(t.encode()),'quote':t}
 context=add('The studied molecule and construct are paired within the declared synthetic experimental model.')
 fit=add('Rounded apparent saturation parameter fitted by Lineweaver Burk extrapolation; measurement time window unspecified.' if nfn else 'Synthetic unbiased common quantity estimates with known joint estimator covariance; no unidentified fixed bias has been quantified.')
 assay=add('The left protocol uses added hydrogenase and 10 micromolar ferredoxin; the right uses 50 micromolar ferredoxin. Both use pH7 and 37C.' if nfn else 'Both synthetic estimates concern the same quantity, protein denominator and source population under the stipulated unbiased model.')
 optical_support=add('At one selected optical channel, the direct rate observation is y=h-alpha*f; applicability to a fitted apparent Vmax remains unestablished.') if nfn else None
 scenario_support=add('For sensitivity arithmetic only, stipulate true left report-scale quantity equals the right report, and separately stipulate that the linear mixture equation applies to both fitted summaries.') if nfn else None
 definition={}
 records={};numbers={};labels={};units={};ep={}
 vals={'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'8.6'} if nfn else {'left':'20','right':'22'}
 for role,val in vals.items():
  endpoint={'left':'NADH formation','right':'ferredoxin reduction','epsilon_signal':'NADH differential extinction','epsilon_nuisance':'ferredoxin differential extinction'}[role] if nfn else role+' common quantity'
  name='apparent Vmax' if nfn and role in ('left','right') else 'extinction coefficient' if role.startswith('epsilon') else 'estimate'
  unit='mM^-1cm^-1' if role.startswith('epsilon') else 'U/mg' if nfn else 'umol/min/mg'
  text=role+' '+endpoint+' '+name+(' approximately ' if nfn else ' ')+val+' '+unit+'.'
  records[role]=add(text);numbers[role]=(text.index(val),text.index(val)+len(val))
  a=text.index(endpoint);ep[role]={**records[role],'start':records[role]['start']+len(text[:a].encode()),'end':records[role]['start']+len(text[:a+len(endpoint)].encode()),'quote':endpoint}
  a=text.index(name);labels[role]={**records[role],'start':records[role]['start']+len(text[:a].encode()),'end':records[role]['start']+len(text[:a+len(name)].encode()),'quote':name}
  a=text.index(unit);units[role]={**records[role],'start':records[role]['start']+len(text[:a].encode()),'end':records[role]['start']+len(text[:a+len(unit)].encode()),'quote':unit}
  if nfn and role in ('left','right'):
   entity='NADH' if role=='left' else 'ferredoxin'
   definition[role]=add('One unit was equivalent to 1 umol of '+entity+' per min.')
 raw=('\n'.join(lines)+'\n').encode(); digest=hashlib.sha256(raw).hexdigest();source='source_'+digest;artifact='artifact_'+digest
 def w(v):return {**v,'source_ref':source,'representation':'original'}
 def rw(v):return {**w(v),'artifact_ref':artifact}
 def sub(v,token):
  start=v['quote'].index(token); return {'quote':token,'start':v['start']+len(v['quote'][:start].encode()),'end':v['start']+len(v['quote'][:start+len(token)].encode())}
 def meaning(value,witness=context):return {'value':value,'witnesses':[] if value=='unknown' else [w(witness)]}
 def retainedmeaning(v):return {'value':v['value'],'witnesses':[{**x,'artifact_ref':artifact} for x in v['witnesses']]}
 selection={'version':'a105_measurement_comparison_selection_v1','source_ref':source,'source_kind':'synthetic_fixture','assertion':{'question':'quantitative_activity','molecule':w(context),'functional_assertion':w(context)},'quantities':{},'relationships':{},'common_quantity':{},'common_model':None,'optical':None,'covariance_source_refs':[],'requested_cells':list(CELL_NAMES)}
 retained={};values={}
 for role in ROLES:
  if role not in vals:selection['quantities'][role]=None;retained[role]=None;values[role]=None;continue
  text=records[role]['quote'];a,b=numbers[role]
  number={'witness':w(records[role]),'number_start':a,'number_end':b}
  kind='extinction_coefficient' if role.startswith('epsilon') else 'apparent_specific_activity' if nfn else 'specific_activity'
  scale='parameter_estimate' if role.startswith('epsilon') else 'fitted_asymptote' if nfn else 'reported_mean'
  normal='extinction_unit' if role.startswith('epsilon') else 'protein_mass'
  unit=w(units[role])
  if nfn and role in definition:
   dw=definition[role]; entity='NADH' if role=='left' else 'ferredoxin';clause=sub(dw,'1 umol of '+entity+' per min')
   unit={'kind':'source_defined_rate_unit','witness':unit,'definition':{'bridge':w(dw),'clause':w(clause),'amount':{'witness':w(dw),'number_start':dw['quote'].index('1'),'number_end':dw['quote'].index('1')+1},'amount_unit':w(sub(dw,'umol')),'time_unit':w(sub(dw,'min')),'endpoint':w(ep[role]),'endpoint_entity':w(sub(ep[role],entity)),'definition_entity':w(sub(dw,entity))}}
  qs={'layout':'labelled_record','record':w(records[role]),'number':number,'row_label':w(sub(records[role],role)),'quantity_label':w(labels[role]),'unit':unit,'quantity_kind':meaning(kind),'estimator_scale':meaning(scale),'semantics':meaning('reported_point_estimate'),'qualification':meaning('source_qualified_approximate' if nfn else 'reported_point'),'normalization':meaning(normal),'subject':{x:w(context) if x in ('molecule','construct') else None for x in SUBJECT},'assay':{x:None for x in ASSAY},'physical_identity':None,'dependency_witnesses':[],'uncertainty':{'statistic':meaning('unreported'),'magnitude':None,'interval':None,'confidence_level':None,'unit':None,'unit_relationship':meaning('unknown'),'count':None,'repetition_basis':meaning('unknown'),'estimate_basis':meaning('unknown')}}
  qs['assay'].update(assay=w(assay),conditions=w(assay),direct_endpoint=w(ep[role]),inferred_quantity=w(labels[role]),fit_basis=w(fit),denominator=w(units[role]))
  selection['quantities'][role]=qs
  location={**rw(records[role]),'start':records[role]['start']+len(text[:a].encode()),'end':records[role]['start']+len(text[:b].encode()),'quote':vals[role]}
  key='measurement_'+hashlib.sha256(json.dumps(location,sort_keys=True).encode()).hexdigest()
  unitcode='mM^-1cm^-1' if role.startswith('epsilon') else 'umol/min/mg'
  value={'role':role,'native_token':vals[role],'native_value':float(vals[role]),'native_exact':q(vals[role]),'canonical_value':float(vals[role]),'canonical_exact':q(vals[role]),'canonical_unit':unitcode,'relation':'point','approximate':nfn,'estimator_scale':scale,'quantity_kind':kind,'semantics':'reported_point_estimate','normalization':normal,'origin':'synthetic','owner_key':key,'physical_owner_key':None,'dependency_keys':[key],'source_locations':[location],'reasons':empty_reasons()}
  values[role]=value
  all_witness=[]
  def collect(x):
   if isinstance(x,dict):
    if set(x)==set(D['witness']['properties']):
     enriched={**x,'artifact_ref':artifact}
     if enriched not in all_witness:all_witness.append(enriched)
    else:
     for v in x.values():collect(v)
   elif isinstance(x,list):
    for v in x:collect(v)
  collect(qs)
  retained[role]={'selection':qs,'number':{'selector':{**number,'witness':rw(records[role])},'raw_token':vals[role],'native_exact':q(vals[role]),'relation':'point','approximate':nfn,'measurement_key':key},'witnesses':all_witness,'count_reading':None,'reported_uncertainty':{'statistic':'unreported','magnitude_exact':None,'interval_exact':None,'confidence_level_exact':None,'unit':None,'meaning':'reported_spread_not_joint_estimator_covariance'},'value':value}
 defaults={'construct':'same_construct_supported','preparation':'unknown','preparation_target':'unknown' if nfn else 'same_population_estimand_supported','protocol':'additional_differences' if nfn else 'matched_except_intended_change','endpoint':'fixed_reaction_conversion' if nfn else 'same_quantity','denominator':'same_basis_supported','functional_bearing':'existence_only' if nfn else 'same_quantitative_assertion','attribution':'unknown' if nfn else 'isolated_supported','sampling':'independence_not_established','systematic_coverage':'identified_unresolved' if nfn else 'not_established','left_validity':'identified_unresolved_interference' if nfn else 'endpoint_quantification_supported','right_validity':'endpoint_quantification_supported','left_readout_isolation':'mixed_optical_contributions' if nfn else 'isolated_signal_supported','right_readout_isolation':'isolated_signal_supported'}
 selection['relationships']={k:meaning(defaults[k],assay) for k in REL}
 conversions={}
 selection['common_quantity']={'label':w(context),'unit':'umol/min/mg'}
 for role in ('left','right'):
  coeff={'origin':'implicit_unit_coefficient','number':None,'implicit_value':q(1),'support':[w(context)]}
  cs={'kind':'fixed_reaction_scale' if nfn else 'identity','direction':meaning('same_direction_supported'),'support_status':meaning('supported'),'reaction':w(context) if nfn else None,'endpoint_species':w(ep[role]),'common_species':w(context),'endpoint_coefficient':coeff if nfn else None,'common_coefficient':coeff if nfn else None}
  selection['common_quantity'][role+'_conversion']=cs
  conversions[role]={'kind':cs['kind'],'multiplier_exact':q(1),'status':'supported','model_key':'model_'+hashlib.sha256(json.dumps(cs,sort_keys=True).encode()).hexdigest(),'source_witnesses':[rw(context)]}
 blocks=[]
 if nfn:
  selection['optical']={'signal_role':'left','observation_equation':'y=h+s*alpha*f','nuisance_sign':-1,'sign_support':[w(optical_support)],'raw_optical_relation':meaning('supported',optical_support),'coefficient_applicability':meaning('supported',optical_support),'estimate_scale_applicability':meaning('unknown'),'nuisance_quantity_linkage':meaning('unknown'),'scenario':{'kind':'required_interference_on_selected_report_scale','anchor_role':'right','common_rate_equality':meaning('stipulated_sensitivity',scenario_support),'linear_mixture_on_estimate_scale':meaning('stipulated_sensitivity',scenario_support)}}
 else:
  selection['common_model']={'kind':'common_unbiased_quantity','applicability':meaning('supported',fit),'variance_interpretation':'known_joint_estimator_covariance','combination':'generalized_least_squares'}
  matrix=[[20,17],[17,25]] if shared else [[4,1],[1,9]]
  doc={'version':'a105_measurement_comparison_covariance_v1','roles':['left','right'],'owner_keys':[values[r]['owner_key'] for r in ('left','right')],'units':['umol/min/mg']*2,'dependency_keys':[values[r]['dependency_keys'] for r in ('left','right')],'covariance':matrix,'basis':'joint_covariance_of_selected_estimates','variance_status':'known','origin':'synthetic','systematic_coverage':'included_as_declared','derivation':'synthetic_model'}
  covraw=(json.dumps(doc,indent=2)+'\n').encode();covhash=hashlib.sha256(covraw).hexdigest();covsource='source_'+covhash;covartifact='artifact_'+covhash
  selection['covariance_source_refs']=[covsource]
  block={k:v for k,v in doc.items() if k not in ('version','covariance')};block.update(source_ref=covsource,artifact_ref=covartifact,matrix_exact=[[q(x) for x in row] for row in matrix],status='available',reasons=empty_reasons(),raw_document_utf8=covraw.decode());blocks=[block]
  (OUT/(case+'_COVARIANCE_SOURCE_001.json')).write_bytes(covraw)
 relationships={k:retainedmeaning(v) for k,v in selection['relationships'].items()}
 artifacts=[{'source_ref':source,'artifact_ref':artifact,'representation':'original'}]+[{'source_ref':b['source_ref'],'artifact_ref':b['artifact_ref'],'representation':'original'} for b in blocks]
 extraction={'version':'a105_measurement_comparison_extraction_v1','selection':selection,'quantities':retained,'relationships':relationships,'conversions':conversions,'covariance_blocks':blocks,'source_refs':[x['source_ref'] for x in artifacts],'source_artifacts':artifacts,'dependency_fingerprints':[]}
 assertionkey='assertion_'+hashlib.sha256(case.encode()).hexdigest();contribution='contribution_'+hashlib.sha256((case+'pair').encode()).hexdigest()
 calculation={'version':'a105_measurement_comparison_calculation_inputs_v1','selection':selection,'quantities':values,'conversions':conversions,'relationships':relationships,'covariance_blocks':blocks,'assertion_key':assertionkey,'contribution_key':contribution,'source_artifacts':artifacts}
 def cell(name,value=None,*,conditional=False,reason=None,unit='dimensionless',interp='unavailable',roles=('left','right'),exact=True):
  reasons=empty_reasons()
  if reason:reasons[reason[0]].extend(reason[1])
  return {'component':name,'value':None if conditional else None if value is None else float(value),'exact_value':None if conditional or value is None or not exact else q(value),'conditional_value':None if not conditional or value is None else float(value),'conditional_exact_value':None if not conditional or value is None or not exact else q(value),'status':'unavailable' if value is None else 'conditional_scenario' if conditional else 'populated','unit':unit,'relation':'point','approximate':nfn,'interpretation':interp,'formula':COMPONENTS[name][0],'meaning_code':name,'origin':'synthetic' if name.startswith('native_') else 'derived','input_origins':['synthetic'],'operand_roles':list(roles),'operand_keys':[values[r]['owner_key'] for r in roles if values[r] is not None],'model_keys':[],'contribution_key':contribution,'uncertainty':{'covariance_source_refs':selection['covariance_source_refs'] if not name.startswith('native') else [],'variance_status':'known' if blocks else 'not_selected','scope':'selected_estimator_covariance' if blocks and name in ('difference_variance','difference_standard_uncertainty','standardized_difference','squared_standardized_difference','combined_variance','combined_standard_uncertainty') else 'not_applicable','sampling_distribution':'not_assumed'},'reasons':reasons}
 cells={name:cell(name,reason=('source',['quantity_not_selected'])) for name in CELL_NAMES}
 L,R=Fraction(vals['left']),Fraction(vals['right'])
 for role,val in (('left',L),('right',R)):
  cells['native_'+role]=cell('native_'+role,val,unit='U/mg' if nfn else 'umol/min/mg',interp='native_report',roles=(role,))
  cells['converted_'+role]=cell('converted_'+role,val,unit='umol/min/mg',interp='supported_reexpression',roles=(role,))
 for name,val,unit,exact in [('protocol_difference',L-R,'umol/min/mg',True),('protocol_ratio',L/R,'dimensionless',True),('protocol_log_ratio',math.log(float(L/R)),'dimensionless',False)]:cells[name]=cell(name,val,unit=unit,interp='descriptive_protocol_comparison',exact=exact)
 commonnames=('common_difference','common_ratio','common_log_ratio','difference_variance','difference_standard_uncertainty','standardized_difference','squared_standardized_difference','weight_left','weight_right','combined_estimate','combined_variance','combined_standard_uncertainty')
 if nfn:
  for name in commonnames:cells[name]=cell(name,reason=('relationship',['protocols_not_matched','validity_unresolved','common_model_not_selected']))
  alpha=Fraction('8.6')/Fraction('1.2')
  cells['spectral_multiplier']=cell('spectral_multiplier',alpha,interp='spectral_sensitivity',roles=('epsilon_nuisance','epsilon_signal'),unit='umol_signal_equivalent_per_umol_nuisance')
  cells['spectral_multiplier_variance']=cell('spectral_multiplier_variance',reason=('source',['covariance_not_supplied']),roles=('epsilon_nuisance','epsilon_signal'))
  for name in ('observed_interference','corrected_estimate','corrected_estimate_variance'):
   cells[name]=cell(name,reason=('source',['nuisance_quantity_unmeasured']),unit='umol/min/mg',roles=('left','epsilon_signal','epsilon_nuisance','nuisance'))
   cells[name]['reasons']['relationship'].append('estimate_scale_model_unknown')
  cells['required_interference_scenario']=cell('required_interference_scenario',L-R,conditional=True,unit='umol_signal_equivalent/min/mg_on_apparent_report_scale',interp='stipulated_report_scale_scenario')
  cells['required_nuisance_equivalent_scenario']=cell('required_nuisance_equivalent_scenario',(L-R)/(-alpha),conditional=True,unit='umol_nuisance_equivalent/min/mg_on_apparent_report_scale',interp='stipulated_report_scale_scenario',roles=('left','right','epsilon_signal','epsilon_nuisance'))
 else:
  C=[[Fraction(x) for x in row] for row in matrix];a,b,c=C[0][0],C[0][1],C[1][1];vd=a+c-2*b;wl=(c-b)/vd;wr=(a-b)/vd;mu=wl*L+wr*R;vm=(a*c-b*b)/vd
  out={'common_difference':L-R,'common_ratio':L/R,'common_log_ratio':math.log(float(L/R)),'difference_variance':vd,'difference_standard_uncertainty':math.sqrt(float(vd)),'standardized_difference':float(L-R)/math.sqrt(float(vd)),'squared_standardized_difference':(L-R)**2/vd,'weight_left':wl,'weight_right':wr,'combined_estimate':mu,'combined_variance':vm,'combined_standard_uncertainty':math.sqrt(float(vm))}
  for name,v in out.items():cells[name]=cell(name,v,interp='known_covariance_common_estimate' if name.startswith(('weight','combined')) else 'known_covariance_standardization' if 'standardized' in name else 'common_estimand_comparison',exact=name not in ('common_log_ratio','difference_standard_uncertainty','standardized_difference','combined_standard_uncertainty'),unit='umol/min/mg' if name in ('common_difference','combined_estimate','difference_standard_uncertainty','combined_standard_uncertainty') else '(umol/min/mg)^2' if name.endswith('variance') else 'dimensionless')
 sheet={'version':'a105_measurement_comparison_sheet_v1','axis':'A105','section':'measurement_comparison_validity','assertion_key':assertionkey,'contribution_key':contribution,'cells':list(cells.values()),'relationship_meanings':defaults,'estimate_bindings':[{'role':r,'owner_key':v['owner_key'],'physical_owner_key':v['physical_owner_key'],'dependency_keys':v['dependency_keys'],'unit':v['canonical_unit'],'estimator_scale':v['estimator_scale']} for r,v in values.items() if v is not None],'dependence':[{'roles':['left','right'],'relation':'sampling_unknown'}],'assumptions':['common_rate_equality_stipulated','linear_estimate_scale_mapping_stipulated'] if nfn else ['common_unbiased_quantity_model','no_reference_distribution_assumed'],'annotation_credit':None,'remaining_limits':list(LIMITS)}
 for name,data in [('selection',selection),('extraction',extraction),('calculation_inputs',calculation),('sheet',sheet)]:
  jsonschema.Draft202012Validator(schema(name)).validate(data);write(case+'_'+name.upper()+'_ILLUSTRATION_001.json',data)
 (OUT/(case+'_SYNTHETIC_PLANNING_SOURCE_001.txt')).write_bytes(raw)
 return {'case':case,'source_kind':'synthetic_fixture','status':'hand_constructed_schema_illustration_not_executed_reader_or_calculator','source_data_claim':'parent_supplied_corrected_Nfn_conversion_reexpressed_as_synthetic_planning_bytes_not_original_source' if nfn else 'parent_supplied_synthetic_known_unbiased_estimate_model','source_positive_matched_covariance_coverage':False,'shared_variance16_meaning':'stipulated_known_common_random_error_not_unknown_fixed_bias' if shared else None}
manifest=[create_case('NFN_PARENT_CONVERSION',True),create_case('SYNTHETIC_KNOWN_COVARIANCE'),create_case('SYNTHETIC_SHARED_RANDOM_ERROR',shared=True)]
write('EXAMPLE_STATUS_001.json',manifest)
print('Twelve hand-constructed planning payloads validated against draft schemas; no proposed reader/calculator implemented or executed.')
