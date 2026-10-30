"""Serialize explicitly synthetic, hand-worked planning examples.

This is not a native reader, experimental run or production calculator. Numerical
expectations below are authored literals. Symbolic fixture identities are not
Store registrations or claims that Cooler/HIC files were observed.
"""
from pathlib import Path
from copy import deepcopy as copy
import hashlib
import json

ROOT=Path(__file__).resolve().parent
records=[]
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def identity(label,format_name):
    symbolic=("SYMBOLIC_PLANNING_FIXTURE_NOT_NATIVE_BYTES:"+label).encode()
    h=hashlib.sha256(symbolic).hexdigest()
    return {"artifact_ref":"artifact_"+h,"sha256":h,"size_bytes":len(symbolic),"format":format_name}
def add(name,definition,value): records.append({"example_key":name,"schema_definition":definition,"record":value})
def scalar(v): return {"value":v,"state":"finite"}
def unit(kind): return {"kind":kind,"source_unit":"contacts" if "contact" in kind and kind!="contact_pairs" else None}
def m(v,kind="count",state="derived",reason=None,numerator=None,denominator=None,pop="p0"):
    return {"value":v,"state":state,"unit":unit(kind),"reason":reason,"population_key":pop,
            "numerator":numerator,"denominator":denominator,"uncertainty":{"kind":"not_measured","value":None,"unit":None}}
def flag(v,reason=None,state="derived"):
    return {"value":v,"state":state,"reason":reason,"population_key":"p0"}
def failure(code,stage="calculation",requirement="complete_population",pair=None):
    return {"code":code,"stage":stage,"input_key":"contact0","population_key":"p0","element_key":None,
            "pair_key":pair,"artifact_ref":None,"locator":None,"field_path":None,"partial_artifact_refs":[],"requirement":requirement}
RAW={"kind":"raw","weight_column":None,"convention":None}
WEIGHTED={"kind":"precomputed_weighted","weight_column":"weight","convention":"multiplicative"}
CP={"minimum_separation_bins":1,"fold_threshold":2,"threshold_comparison":"strict_gt","expectation":"same_population_distance_mean","missing_policy":"exclude_declared_masked_bins_require_complete_population"}
IP={"window_bins":1,"z_threshold":-1,"threshold_comparison":"strict_lt","zscore_ddof":0,"boundary_rule":"strict_two_neighbor_minimum","window_end_rule":"all_full_windows","missing_policy":"complete_window"}
def quals(weighted=False,interpretation="complete_population",eligibility="eligible",extent="complete",reasons=()):
    return {"data_extent":extent,"reference_relation":"consistent_assertions","normalization_kind":"precomputed_weighted" if weighted else "raw","normalization_state":"available" if weighted else "not_requested","eligibility":eligibility,"interpretation":interpretation,"reasons":list(reasons)}
def fixture_sheet(label, matrix, contact_mode, weighted=False):
    # Input representation only: emit every upper-triangle cell of the authored matrix.
    n=len(matrix); count=n*(n+1)//2
    contact_file=identity(label+":contact-native-symbol","cooler_hdf5_v3")
    element_file=identity(label+":elements-symbol","bed_outer_span_v1")
    refspec={"assembly_accession":None,"assembly_label":"fixture_assembly","contigs":[{"chromosome":"chrA","length_bp":n*10}],"source_ref":"fixture:reference"}
    norm=copy(WEIGHTED if weighted else RAW)
    assignments=[]
    if contact_mode:
        for i,(key,cls,pos) in enumerate([("E","enhancer",1),("P","promoter",21),("Q","promoter",31)]):
            assignments.append({"element_key":key,"source_data_row":i,"class":cls,"gene_links":[],"anchor":{"policy":"supplied_position","position_bp":pos}})
    md={"reference":copy(refspec),"samples":[{"sample_key":"sample0","condition_key":None,"replicate_key":None,"assay":"Hi-C","source_ref":"fixture:metadata"}],"contact_sample_links":[{"contact_input_key":"contact0","sample_key":"sample0","fraction":None,"source_ref":"fixture:metadata"}],"dependence_groups":[],"native_attribute_bindings":[],"supplied_uncertainty":[]}
    region={"population_key":"p0","chromosome":"chrA","start_bp":0,"end_bp":n*10}
    request={"version":"chromatin_interaction_request_v1","operation":"analyze_chromatin_interactions","analysis_modes":["cis_anchor_contact_enrichment" if contact_mode else "cross_window_insulation_heuristic"],"contact":{"input_key":"contact0","file":contact_file,"source_ref":"fixture:contact","format":"cooler_hdf5_v3","group_path":"/","resolution_bp":10,"value_field":"count","value_kind":"contact_count","value_unit":"contacts","specimen_key":"sample0"},"populations":[region],"elements":({"input_key":"elements0","file":element_file,"source_ref":"fixture:elements","format":"bed_outer_span_v1","reference":copy(refspec),"assignments":assignments} if contact_mode else None),"normalization":norm,"supplied_metadata":md,"output_prefix":"chromatin"}
    bins=[{"bin_id":i,"chromosome_index":0,"start_bp":i*10,"end_bp":(i+1)*10} for i in range(n)]
    rows=[]
    for i in range(n):
        for j in range(i,n): rows.append({"bin1_id":i,"bin2_id":j,"value":scalar(matrix[i][j]),"source_block":-1,"source_row":len(rows)})
    table_defs=[]
    for role,size in [("bins",n),("contacts",count),("weights",n if weighted else None),("cell_states",0),("dense_values",None)]:
        fields=[{"name":k,"dtype":d} for k,d in ([('bin1_id','<i8'),('bin2_id','<i8'),('value','<i8'),('source_block','<i8'),('source_row','<i8')] if role=="contacts" else [('bin1_id','<i8'),('bin2_id','<i8'),('state','|u1')])]
        dtype=({"kind":"scalar","dtype":"utf8_tsv_int64"} if role=="bins" else {"kind":"scalar","dtype":"<f8"} if role=="weights" else {"kind":"structured","fields":fields}) if size is not None else None
        table_defs.append({"table_key":"p0."+role,"population_key":"p0","role":role,"availability":"present" if size is not None else "not_requested" if role=='weights' else "not_native_representation","absence_reason":None,"encoding":("tsv" if role=="bins" else "npy") if size is not None else None,"shape":[size,4] if role=="bins" else [size] if size is not None else None,"dtype_descriptor":dtype,"row_count":size,"native_source_locator":{"kind":"hdf5_path","value":"/bins" if role in {"bins","weights"} else "/pixels"} if size is not None else None,"extent":"complete" if size is not None else "unavailable","file":identity(label+":"+role,"chromatin_contact_tables_v1:"+role) if size is not None else None})
    rawpop={"directed_cells":n*n,"unique_unordered_cells":count,"stored_rows":count,"explicit_zero_rows":1 if n==4 else 16,"implicit_zero_directed_cells":0,"native_nonfinite_directed_cells":0,"unavailable_directed_cells":0,"validated_observed_row_count":count}
    pe={"population_key":"p0","selected_region":region,"extent":"complete","bin_count":n,"fixed_bin_size_bp":10,"native_storage_mode":"symmetric-upper","data_table_keys":[t['table_key'] for t in table_defs],"raw_cell_population":rawpop,"normalization":{"specification":norm,"availability":"available" if weighted else "not_requested","vector_table_key":"p0.weights" if weighted else None,"native_weight_dtype":"float64" if weighted else None,"valid_bin_count":n if weighted else None,"masked_bin_count":0 if weighted else None,"invalid_bin_count":0 if weighted else None},"read_evidence":{"axes_extent":"complete","index_extent":"complete","selected_records_extent":"complete","required_native_row_ranges":[{"table_path":"/pixels","start_row":0,"end_row":count}],"expected_block_count":None,"read_block_count":None,"failed_block_ids":[],"implicit_zero_semantics":"validated_sparse_absence","symmetry":"native_symmetric_upper"},"failures":[]}
    metadata={"source_file":contact_file,"source_ref":"fixture:contact","format":"cooler_hdf5_v3","format_version":3,"group_path":"/","coordinate_system":"zero_based_half_open","bin_type":"fixed","bin_size_bp":10,"storage_mode":"symmetric-upper","value_field":"count","value_dtype":"<i8","native_value_dtype":"int64","value_kind":"contact_count","value_unit":"contacts","attributes":[{"path":"/@format","dtype":"utf8","shape":[],"value_state":"decoded","value":"HDF5::Cooler"},{"path":"/@format-version","dtype":"int64","shape":[],"value_state":"decoded","value":3}],"vectors":[{"name":"weight","native_path":"/bins/weight","chromosome_index":None,"resolution_bp":10,"dtype":"float64","length":n,"extent":"complete","meaning":"normalization_weight"}] if weighted else [],"reference_assertion":copy(refspec)}
    extract={"format":"cooler_hdf5_v3","format_version":3,"native_metadata":metadata,"chromosomes":[{"chromosome_index":0,"chromosome":"chrA","length_bp":n*10}],"populations":[copy(pe)],"table_drafts":[{k:v for k,v in t.items() if k!='file'} for t in table_defs],"failures":[]}
    parsed=None; anchors=[]; pairs=[]
    if contact_mode:
        erows=[]
        for a,idx in zip(assignments,[0,2,3]):
            pos=a['anchor']['position_bp']; key=a['element_key']; ordinal=a['source_data_row']
            erows.append({"source_data_row":ordinal,"source_line":ordinal+1,"columns":["chrA",str(pos),str(pos+1),key,"0","."],"chromosome":"chrA","start_bp":pos,"end_bp":pos+1,"name":key,"element_key":key,"class":a['class'],"gene_links":[],"anchor":a['anchor'],"anchor_position_bp":pos})
            anchors.append({"element_key":key,"source_data_row":ordinal,"class":a['class'],"chromosome":"chrA","anchor_position_bp":pos,"bin_id":idx,"bin_ordinal":idx,"membership":"inside","reference_relation":"consistent_assertions","reason":None})
        parsed={"source_file":element_file,"input_data_row_count":3,"rows":erows,"rejected_rows":[],"other_lines":[],"extent":"complete","failures":[]}
        for key,idx,pos,raw,source_row in [("P",2,21,6,2),("Q",3,31,0,3)]:
            pairs.append({"pair_key":"p0.E."+key,"population_key":"p0","enhancer_element_key":"E","promoter_element_key":key,"enhancer_bin_id":0,"promoter_bin_id":idx,"enhancer_bin_ordinal":0,"promoter_bin_ordinal":idx,"enhancer_anchor_bp":1,"promoter_anchor_bp":pos,"raw_contact":m(raw,"source_contact","observed"),"cell_origin":"explicit_native","source_locators":[{"kind":"native_row","value":{"table_path":"/pixels","row_index":source_row}}],"reference_relation":"consistent_assertions","reason":None})
    assertions=[{"assertion_key":"native_ref","input_key":"contact0","origin":"native","reference":copy(refspec)},{"assertion_key":"supplied_ref","input_key":"contact0","origin":"supplied","reference":copy(refspec)}]
    if contact_mode: assertions.append({"assertion_key":"element_ref","input_key":"elements0","origin":"supplied","reference":copy(refspec)})
    relations=[{"contact_input_key":"contact0","element_input_key":"elements0" if contact_mode else None,"population_key":"p0","relation":"consistent_assertions","basis":"label_agreement","assertion_keys":[x['assertion_key'] for x in assertions],"chromosome":"chrA","native_length_bp":n*10,"supplied_length_bp":n*10}]
    metarel={"reference_assertions":assertions,"reference_relations":relations,**{k:copy(md[k]) for k in ['samples','contact_sample_links','dependence_groups','supplied_uncertainty']},"failures":[]}
    sheet={"version":"chromatin_interaction_sheet_v1","request":request,"native":{"metadata":metadata,"chromosomes":extract['chromosomes']},"references":{"assertions":assertions,"relations":relations},"samples":{k:copy(md[k]) for k in ['samples','contact_sample_links','dependence_groups','supplied_uncertainty']},"elements":parsed,"populations":[{**copy(pe),"element_anchor_rows":anchors,"pair_rows":pairs}],"data_tables":table_defs,"failures":[]}
    views={"version":"chromatin_contact_table_fixture_v1","populations":[{"population_key":"p0","bins":bins,"contacts":rows,"weights":[{"bin_id":i,"value":scalar(v)} for i,v in enumerate([1,2,1,2])] if weighted else None,"cell_states":[],"dense_values":None}]}
    return request,extract,parsed,metarel,sheet,views

M4=[[4,2,6,0],[2,4,2,2],[6,2,4,2],[0,2,2,4]]
M6=[[0,5,0,0,0,0],[5,0,1,0,0,0],[0,1,0,5,0,0],[0,0,5,0,1,0],[0,0,0,1,0,5],[0,0,0,0,5,0]]
def save_input_records(label, values):
    request,ex,parsed,meta,sheet,views=values
    for suffix,name,value in [("request","ChromatinRequest",request),("extraction","ContactExtraction",ex),("metadata","MetadataRelations",meta),("sheet","ContactSheet",sheet),("tables","ContactTableFixture",views)]: add(label+"."+suffix,name,value)
    if parsed is not None: add(label+".elements","ParsedElements",parsed)
    return digest(sheet),[x['file'] for x in sheet['data_tables'] if x['file'] is not None]

def contact_components(sheet,h,files,weighted):
    # Literal expected statistics for the full authored 4x4 matrix.
    stats=[(1,3,6,12,12 if weighted else 6,48 if weighted else 12,4 if weighted else 2,0),(2,2,8,40,14 if weighted else 8,100 if weighted else 40,7 if weighted else 4,1 if weighted else 4),(3,1,0,0,0,0,0,0)]
    su="normalized_contact" if weighted else "source_contact"; qu=su+"_squared"
    distances=[]
    for d,n,rs,rq,s,q,e,v in stats:
        dm={"nominal_distance_pair_count":m(n,"contact_pairs"),"masked_distance_pair_count":m(0,"contact_pairs"),"valid_distance_pair_count":m(n,"contact_pairs"),"raw_distance_sum":m(rs,"source_contact"),"raw_distance_sum_squares":m(rq,"source_contact_squared"),"distance_sum":m(s,su),"distance_sum_squares":m(q,qu),"expected_contact":m(e,su,numerator=s,denominator=n),"distance_population_variance":m(v,qu,numerator=v*n,denominator=n)}
        distances.append({"population_key":"p0","separation_bins":d,"measurements":dm,"qualifications":quals(weighted)})
    pairs=[]
    for key,d,dist,raw,expected,fold in [("P",2,20,6,7 if weighted else 4,0.8571428571428571 if weighted else 1.5),("Q",3,30,0,0,None)]:
        measurements={"raw_contact":m(raw,"source_contact","observed"),"normalized_contact":m(raw,su,"normalized") if weighted else m(None,"normalized_contact","not_measured"),"anchor_distance_bp":m(dist,"bp"),"bin_separation":m(d,"bins"),"expected_contact":m(expected,su,numerator=(14 if weighted else 8) if key=="P" else 0,denominator=2 if key=="P" else 1),"fold_enrichment":m(fold,"dimensionless","derived" if fold is not None else "undefined",None if fold is not None else "zero_denominator",numerator=raw,denominator=expected),"occurrence_multiplicity":m(1),"above_fold_threshold":flag(False) if fold is not None else flag(None,"zero_denominator","undefined")}
        pairs.append({"pair_key":"p0.E."+key,"population_key":"p0","enhancer_element_key":"E","promoter_element_key":key,"enhancer_bin_id":0,"promoter_bin_id":d,"measurements":measurements,"qualifications":quals(weighted,reasons=[] if fold is not None else ['zero_denominator'])})
    pop={"population_key":"p0","source_table_keys":[x['table_key'] for x in sheet['data_tables'] if x['file'] is not None],"pairs":pairs,"distance_expectations":distances,"counts":{k:m(v,"contact_pairs") for k,v in {"requested_pair_count":2,"eligible_pair_count":2,"fold_defined_pair_count":1,"above_threshold_pair_count":0,"distinct_bin_pair_count":2}.items()},"qualifications":quals(weighted),"failures":[failure("zero_denominator",requirement="positive_denominator",pair="p0.E.Q")]}
    return {"version":"chromatin_contact_components_v1","source_sheet_sha256":h,"table_identities":files,"normalization":copy(WEIGHTED if weighted else RAW),"mode":"cis_anchor_contact_enrichment","parameters":CP,"populations":[pop],"failures":[]}

def projection(label,sheet,components,kind,fields,rows,selection=None, saved=False):
    bundle={"sheet":{"artifact_ref":"artifact_"+components['source_sheet_sha256'],"sha256":components['source_sheet_sha256'],"size_bytes":len(canonical(sheet)),"format":"chromatin_interaction_sheet_v1"},"tables":components['table_identities']}
    spec={"kind":kind,"fields":fields}
    if kind!="population_metrics": spec['selection']=selection or {"by":"page","page":{"offset":0,"limit":20}}
    selector={"version":"chromatin_interaction_result_selector_v1","mode":"saved_sheet_recalculation" if saved else "native_result","saved_sheet_bundle":bundle if saved else None,"population_keys":["p0"],"parameters":components['parameters'],"projection":spec}
    prows=[]
    for row in rows:
        base={k:v for k,v in row.items() if k not in {'measurements','fields'}}
        base['fields']={f:copy(row.get('measurements',row.get('fields'))[f]) for f in fields}
        prows.append(base)
    result={"version":"chromatin_interaction_projection_v1","source_sheet_sha256":components['source_sheet_sha256'],"parameters":components['parameters'],"kind":kind,"population_keys":["p0"],"requested_fields":fields,"rows":prows,"page":None if kind=="population_metrics" or spec['selection']['by']=="keys" else {"offset":0,"returned_count":len(rows),"total_row_count":len(rows),"has_more":False},"qualifications":[quals(components['parameters']['normalization']['kind']=='precomputed_weighted',interpretation='heuristic_prediction' if kind in {'insulation_windows','domains'} else 'complete_population')],"failures":copy((components['contact'] or components['insulation'])['populations'][0]['failures'])}
    add(label+".selector","ResultSelector",selector); add(label+".projection","RequestedProjection",result)
    return selector,result,bundle

cases={}
for label,weighted in [("raw",False),("weighted",True)]:
    vals=fixture_sheet(label,M4,True,weighted); h,files=save_input_records(label,vals); sheet=vals[4]
    cc=contact_components(sheet,h,files,weighted)
    parameters={"normalization":copy(WEIGHTED if weighted else RAW),"contact":CP,"insulation":None}
    components={"version":"chromatin_interaction_components_v1","source_sheet_sha256":h,"table_identities":files,"parameters":parameters,"contact":cc,"insulation":None,"failures":[]}
    add(label+".contact_components","ContactComponents",cc); add(label+".components","ChromatinComponents",components)
    sel,proj,bundle=projection(label,sheet,components,"contact_pairs",["raw_contact","normalized_contact","expected_contact","fold_enrichment","above_fold_threshold"],cc['populations'][0]['pairs'])
    cases[label]={"values":vals,"components":components,"selector":sel,"projection":proj,"bundle":bundle}
projection("raw_distances",cases['raw']['values'][4],cases['raw']['components'],"distance_expectations",["valid_distance_pair_count","distance_sum","expected_contact","distance_population_variance"],cases['raw']['components']['contact']['populations'][0]['distance_expectations'])
projection("raw_saved",cases['raw']['values'][4],cases['raw']['components'],"contact_pairs",["fold_enrichment"],cases['raw']['components']['contact']['populations'][0]['pairs'],saved=True)

vals=fixture_sheet("insulation",M6,False); h,files=save_input_records("insulation",vals); sheet=vals[4]
windows=[]
for k,cv,z in [(1,5,0.816496580927726),(2,1,-1.224744871391589),(3,5,0.816496580927726),(4,1,-1.224744871391589),(5,5,0.816496580927726)]:
    is_boundary=k in {2,4}
    fields={"boundary_position_bp":m(k*10,"bp"),"nominal_window_cell_count":m(1,"contact_pairs"),"valid_window_cell_count":m(1,"contact_pairs"),"known_cross_contact_sum":m(cv,"source_contact"),"cross_contact_sum":m(cv,"source_contact"),"cross_contact_mean":m(cv,"source_contact_per_pair",numerator=cv,denominator=1),"insulation_z":m(z,"dimensionless",numerator=-2.4 if is_boundary else 1.6,denominator=1.9595917942265424),"boundary_strength":m(1.224744871391589,"dimensionless") if is_boundary else m(None,"dimensionless","not_measured"),"is_boundary":flag(is_boundary)}
    windows.append({"population_key":"p0","boundary_bin_id":k,"boundary_ordinal":k,"measurements":fields,"qualifications":quals(interpretation="heuristic_prediction",eligibility="ineligible_edge" if k in {1,5} else "eligible")})
domain={"domain_key":"p0.domain0","population_key":"p0","left_boundary_bin_id":2,"right_boundary_bin_id":4,"measurements":{"domain_start_bp":m(20,"bp"),"domain_end_bp":m(40,"bp"),"domain_length_bp":m(20,"bp"),"domain_size_kb":m(0.02,"kb",numerator=20,denominator=1000)},"qualifications":quals(interpretation="heuristic_prediction")}
zstats={k:m(v) for k,v in {"nominal_window_count":5,"complete_window_count":5,"omitted_window_count":0,"z_population_count":5,"selected_boundary_count":2,"domain_count":1}.items()}
zstats.update(z_population_mean=m(3.4,"source_contact",numerator=17,denominator=5),z_population_variance=m(3.84,"source_contact_squared",numerator=19.2,denominator=5))
ic={"version":"chromatin_insulation_components_v1","source_sheet_sha256":h,"table_identities":files,"normalization":RAW,"mode":"cross_window_insulation_heuristic","parameters":IP,"populations":[{"population_key":"p0","source_table_keys":[x['table_key'] for x in sheet['data_tables'] if x['file'] is not None],"windows":windows,"statistics":zstats,"domains":[domain],"qualifications":quals(interpretation="heuristic_prediction"),"failures":[]}],"failures":[]}
components={"version":"chromatin_interaction_components_v1","source_sheet_sha256":h,"table_identities":files,"parameters":{"normalization":RAW,"contact":None,"insulation":IP},"contact":None,"insulation":ic,"failures":[]}
add("insulation.insulation_components","InsulationComponents",ic); add("insulation.components","ChromatinComponents",components)
projection("insulation",sheet,components,"insulation_windows",["cross_contact_sum","insulation_z","is_boundary"],windows)
projection("domains",sheet,components,"domains",["domain_start_bp","domain_end_bp","domain_length_bp","domain_size_kb"],[domain])
projection("population",sheet,components,"population_metrics",["bin_count","complete_window_count","selected_boundary_count","domain_count"],[{"population_key":"p0","fields":{"bin_count":m(6),"complete_window_count":m(5),"selected_boundary_count":m(2),"domain_count":m(1)},"qualifications":quals(interpretation="heuristic_prediction")}])

# Complete typed failure examples; none are replaced with a zero matrix.
for name,code,req in [("missing_matrix","input_unavailable","supplied_contact_file"),("malformed_index","malformed_native_index","valid_native_structure"),("missing_weights","normalization_missing","selected_weight_vector"),("partial_matrix","native_output_partial","complete_population"),("unsupported_hic","unsupported_native_format","supported_native_format")]:
    add(name+".failure","Failure",failure(code,stage="native_parse",requirement=req))
    add(name+".unavailable_value","Measurement",m(None,"source_contact","truncated" if name=='partial_matrix' else "missing" if name in {'missing_matrix','missing_weights'} else "incompatible" if name=='unsupported_hic' else "failed",code))
add("genuine_zero.raw_value","Measurement",m(0,"source_contact","observed"))
add("genuine_zero.positive_expectation_fold","Measurement",m(0,"dimensionless",numerator=0,denominator=4))
add("zero_expectation.undefined_fold","Measurement",m(None,"dimensionless","undefined","zero_denominator",numerator=0,denominator=0))

# Complete partial-input/output records preserve the known E-P contact without
# pretending that its distance expectation or the unread E-Q contact is zero.
vals=list(copy(cases['raw']['values'])); req,ex,parsed,meta,psheet,pviews=vals
pf=failure('native_output_partial',stage='native_parse')
pf['locator']={'kind':'hdf5_path','value':'/pixels'}
pe=psheet['populations'][0]
pe['extent']='partial';pe['read_evidence']['selected_records_extent']='partial'
pe['read_evidence']['implicit_zero_semantics']='not_established';pe['failures']=[pf]
pe['raw_cell_population'].update(stored_rows=None,explicit_zero_rows=None,implicit_zero_directed_cells=None,native_nonfinite_directed_cells=None,unavailable_directed_cells=None,validated_observed_row_count=3)
pe['pair_rows'][1].update(raw_contact=m(None,'source_contact','truncated','native_output_partial'),cell_origin='unavailable',source_locators=[],reason='native_output_partial')
pviews['populations'][0]['contacts']=pviews['populations'][0]['contacts'][:3]
td=next(t for t in psheet['data_tables'] if t['role']=='contacts')
td.update(extent='partial',shape=[3],row_count=3,file=identity('partial:contacts','chromatin_contact_tables_v1:contacts'))
ex['populations']=[{k:copy(v) for k,v in pe.items() if k not in {'element_anchor_rows','pair_rows'}}]
ex['table_drafts']=[{k:copy(v) for k,v in t.items() if k!='file'} for t in psheet['data_tables']]
ex['failures']=[pf];psheet['failures']=[pf]
ph,pfiles=save_input_records('partial',vals)
pcomp=copy(cases['raw']['components']);pcomp['source_sheet_sha256']=ph;pcomp['table_identities']=pfiles;pcomp['failures']=[pf]
pcc=pcomp['contact'];pcc['source_sheet_sha256']=ph;pcc['table_identities']=pfiles;pcc['failures']=[pf]
pp=pcc['populations'][0];pp['failures']=[pf];pp['qualifications']=quals(interpretation='known_subset',eligibility='incomplete_population',extent='partial',reasons=['incomplete_comparison_population'])
for row in pp['pairs']:
    row['qualifications']=copy(pp['qualifications'])
    row['measurements']['expected_contact']=m(None,'source_contact','truncated','incomplete_comparison_population')
    row['measurements']['fold_enrichment']=m(None,'dimensionless','truncated','incomplete_comparison_population')
    row['measurements']['above_fold_threshold']=flag(None,'incomplete_comparison_population','truncated')
    if row['promoter_element_key']=='Q': row['measurements']['raw_contact']=m(None,'source_contact','truncated','native_output_partial')
for row,(valid,s,q) in zip(pp['distance_expectations'],[(1,2,4),(1,6,36),(0,0,0)]):
    row['qualifications']=copy(pp['qualifications'])
    row['measurements'].update(valid_distance_pair_count=m(valid,'contact_pairs'),raw_distance_sum=m(s,'source_contact'),raw_distance_sum_squares=m(q,'source_contact_squared'),distance_sum=m(s,'source_contact'),distance_sum_squares=m(q,'source_contact_squared'),expected_contact=m(None,'source_contact','truncated','incomplete_comparison_population'),distance_population_variance=m(None,'source_contact_squared','truncated','incomplete_comparison_population'))
pp['counts'].update(eligible_pair_count=m(0,'contact_pairs'),fold_defined_pair_count=m(0,'contact_pairs'),above_threshold_pair_count=m(None,'contact_pairs','truncated','incomplete_comparison_population'))
add('partial.contact_components','ContactComponents',pcc);add('partial.components','ChromatinComponents',pcomp)
_,partial_projection,_=projection('partial',psheet,pcomp,'contact_pairs',['raw_contact','expected_contact','fold_enrichment'],pp['pairs'])
partial_projection['qualifications']=[copy(pp['qualifications'])]

# Full finite-worker handoff records, with explicitly symbolic deployment paths.
raw=cases['raw']; req,ex,parsed,meta,sheet,views=raw['values']
software={"python_executable":"/fixture/runtime/python","python_sha256":digest("symbolic-python"),"python_version":"fixture-only","module_root":"/fixture/source","driver_module":"gene_annotation_episode.native_chromatin_interaction_driver","implementation_files":[{"module":"gene_annotation_episode.native_chromatin_interaction_driver","sha256":digest("symbolic-driver")}],"dependencies":[{"distribution":"h5py","version":"fixture-only","package_root":"/fixture/runtime/h5py","files":[{"path":"/fixture/runtime/h5py/__init__.py","sha256":digest("symbolic-h5py"),"size_bytes":1}]}]}
env={"PYTHONPATH":"/fixture/source","PYTHONHOME":"/fixture/runtime","PYTHONNOUSERSITE":"1","PYTHONSAFEPATH":"1","PYTHONDONTWRITEBYTECODE":"1","TMPDIR":"/fixture/job/tmp","TMP":"/fixture/job/tmp","TEMP":"/fixture/job/tmp","XDG_CACHE_HOME":"/fixture/job/cache","PIP_CACHE_DIR":"/fixture/job/cache/pip","OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1"}
rjob={"argv":["/fixture/runtime/python","-B","-m","gene_annotation_episode.native_chromatin_interaction_driver","chromatin-plan.json"],"environment":env,"native_chromatin_interactions":{"request":req,"software":software,"input_bindings":[{"input_key":"contact0","file":req['contact']['file'],"path":"/fixture/retained/contact.native"},{"input_key":"elements0","file":req['elements']['file'],"path":"/fixture/retained/elements.bed"}]}}
attempt={"run_id":"fixture-run","episode_id":"fixture-local-child","resource_id":"fixture-local","execution_id":"fixture-execution","operation_key":"fixture-action","attempt_id":digest("symbolic-attempt"),"requested_job_sha256":digest(rjob),"assignment_sha256":digest("symbolic-assignment")}
outputs=[];declared=[]
for t in sheet['data_tables']:
    role=t['role']; rel="populations/p0/"+{"bins":"bins.tsv","contacts":"contacts.npy","weights":"weights.npy","cell_states":"cell-states.npy","dense_values":"dense-values.npy"}[role]
    spec={"file_key":t['table_key'],"population_key":"p0","role":role,"relative_path":rel,"format":"chromatin_contact_tables_v1:"+role}
    dec={"relative_path":rel,"format":spec['format'],"state":"present" if t['file'] else "absent","sha256":t['file']['sha256'] if t['file'] else None,"size_bytes":t['file']['size_bytes'] if t['file'] else None}
    outputs.append(spec);declared.append({"specification":spec,"declaration":dec})
plan={"version":"chromatin_interaction_run_plan_v1","identity":attempt,"requested_job":rjob,"attempt_directory":"/fixture/job","policy":{"memory_bytes":21474836480,"scratch_bytes":4294967296,"wall_seconds":None},"outputs":outputs}
seal={"version":"chromatin_interaction_population_seal_v1","identity":attempt,"request_sha256":digest(req),"population":ex['populations'][0],"tables":[{"draft":d,"declaration":declared[i]['declaration']} for i,d in enumerate(ex['table_drafts'])],"input_files":[req['contact']['file'],req['elements']['file']],"failures":[]}
sealfile=identity("symbolic-population-seal","chromatin_interaction_population_seal_v1")
bundle={"version":"chromatin_interaction_native_bundle_v1","identity":attempt,"request":req,"software":software,"extraction":ex,"elements":parsed,"metadata":meta,"population_seals":[{"relative_path":"populations/p0/manifest.json","format":sealfile['format'],"state":"present","sha256":sealfile['sha256'],"size_bytes":sealfile['size_bytes']}],"outputs":declared,"failures":[]}
bundlefile=identity("symbolic-bundle","chromatin_interaction_native_bundle_v1")
for role,relative,f in [
 ('original_contact','inputs/contact.native',req['contact']['file']),
 ('original_elements','inputs/elements.bed',req['elements']['file']),
 ('original_metadata','inputs/metadata.json',identity('symbolic-original-metadata','chromatin_supplied_metadata_v1')),
 ('population_manifest','populations/p0/manifest.json',sealfile),
 ('stdout','stdout.log',identity('symbolic-native-stdout','native_stdout')),
 ('stderr','stderr.log',identity('symbolic-native-stderr','native_stderr'))]:
    spec={'file_key':role,'population_key':'p0' if role=='population_manifest' else None,'role':role,'relative_path':relative,'format':f['format']}
    outputs.append(spec)
    declared.append({'specification':spec,'declaration':{'relative_path':relative,'format':f['format'],'state':'present','sha256':f['sha256'],'size_bytes':f['size_bytes']}})
outputs.append({'file_key':'bundle','population_key':None,'role':'bundle','relative_path':'bundle.json','format':bundlefile['format']})
# bundle.json is captured separately: it cannot declare its own digest inside itself.
captured=[]
for row,t in zip(declared,sheet['data_tables']):
    captured.append({"specification":row['specification'],"declaration_source":"bundle","capture":{"declared":row['declaration'],"observed":t['file'],"outcome":"verified" if t['file'] else "declared_absent","failure":None},"retained":{"file":t['file'],"path":"/fixture/retained/"+row['specification']['file_key']} if t['file'] else None})
for row in declared[len(sheet['data_tables']):]:
    d=row['declaration'];f={'artifact_ref':'artifact_'+d['sha256'],'sha256':d['sha256'],'size_bytes':d['size_bytes'],'format':d['format']}
    captured.append({'specification':row['specification'],'declaration_source':'bundle','capture':{'declared':d,'observed':f,'outcome':'verified','failure':None},'retained':{'file':f,'path':'/fixture/retained/'+row['specification']['file_key']}})
nativecapture={"original_plan":plan,"source_action_receipt_ref":"fixture:source-action-receipt","writer_closure_receipt_ref":"fixture:writer-closure-receipt","driver_state":"sealed_bundle","bundle":{"file":bundlefile,"path":"/fixture/retained/bundle.json"},"files":captured,"failures":[]}
nativeplan={"version":"chromatin_interaction_result_worker_plan_v1","mode":"native_result","directory":"/fixture/results",**nativecapture,"selector":raw['selector']}
savedselector=copy(raw['selector']);savedselector.update(mode="saved_sheet_recalculation",saved_sheet_bundle=raw['bundle'])
savedplan={"version":"chromatin_interaction_result_worker_plan_v1","mode":"saved_sheet_recalculation","directory":"/fixture/recalculation","sheet_bundle":{"sheet":{"file":raw['bundle']['sheet'],"path":"/fixture/retained/sheet.json"},"tables":[{"file":f,"path":"/fixture/retained/"+f['sha256']} for f in raw['bundle']['tables']]},"selector":savedselector}
workeroutputs=[]
for role,name in [("sheet","sheet.json"),("components","components.json"),("projection","projection.json"),("diagnostics","diagnostics.json")]:
    f=raw['bundle']['sheet'] if role=='sheet' else identity("symbolic-worker-"+role,"chromatin_interaction_"+role+"_v1")
    workeroutputs.append({"role":role,"table_key":None,"declaration":{"relative_path":name,"format":f['format'],"state":"present","sha256":f['sha256'],"size_bytes":f['size_bytes']}})
for row,t in zip(declared,sheet['data_tables']):
    if t['file']: workeroutputs.append({"role":"table","table_key":t['table_key'],"declaration":row['declaration']})
workerresult={"version":"chromatin_interaction_result_worker_result_v1","mode":"native_result","state":"produced","source_sheet_sha256":raw['components']['source_sheet_sha256'],"parameters":raw['components']['parameters'],"outputs":workeroutputs,"failures":[]}
wc={"version":"chromatin_interaction_worker_capture_v1","plan_file":identity("symbolic-worker-plan","chromatin_interaction_result_worker_plan_v1"),"execution_receipt_file":identity("symbolic-worker-receipt","chromatin_interaction_worker_execution_v1"),"worker_result_file":identity("symbolic-worker-result","chromatin_interaction_result_worker_result_v1"),"result":workerresult,"outputs":[{"role":o['role'],"table_key":o['table_key'],"capture":{"declared":o['declaration'],"observed":{"artifact_ref":"artifact_"+o['declaration']['sha256'],"sha256":o['declaration']['sha256'],"size_bytes":o['declaration']['size_bytes'],"format":o['declaration']['format']},"outcome":"verified","failure":None}} for o in workeroutputs],"failures":[]}
diagnostics={"version":"chromatin_interaction_result_diagnostics_v1","mode":"native_result","populations":[{"population_key":"p0","manifest_origin":"bundle","manifest_file":sealfile,"result_extent":"complete","failures":[]}],"failures":[]}
for name,typ,value in [("requested_job","RequestedJob",rjob),("plan","RunPlan",plan),("population_seal","PopulationSeal",seal),("native_bundle","NativeBundle",bundle),("native_capture","NativeCapture",nativecapture),("native_worker_plan","NativeWorkerPlan",nativeplan),("saved_worker_plan","SavedWorkerPlan",savedplan),("worker_result","WorkerResult",workerresult),("worker_capture","WorkerCapture",wc),("diagnostics","Diagnostics",diagnostics)]:add("handoff."+name,typ,value)

payload={"record_type":"synthetic_hand_worked_contract_records_not_native_runs","identities":"Symbolic fixture identities only; no corresponding Store registrations, native files, receipts, deployment or execution are claimed.","records":records}
(ROOT/"WORKED_RECORDS.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
print(json.dumps({"worked_records":len(records),"output":"WORKED_RECORDS.json"}))
