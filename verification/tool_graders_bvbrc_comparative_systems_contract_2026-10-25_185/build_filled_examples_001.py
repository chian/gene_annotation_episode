"""Review-only filled proposed handoffs, not a ComparativeSystems grader.

Manual schema assembly with independent arithmetic witnesses. The existing
Data query encoder/reader builds one explicitly synthetic QualifiedResult.
No real host admission, network acquisition or ComparativeSystems parser runs.
"""
import copy, csv, hashlib, io, json, math, socket
from pathlib import Path
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_data_query import encode_native_query
from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot
from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
from gene_annotation_episode.bvbrc_data_schema import validate as validate_data

BASE=Path(__file__).resolve().parent
SCHEMA=json.loads((BASE/'HANDOFF_SCHEMAS_001.json').read_text())
EXAMPLES=[]
NETWORK_ATTEMPTS=[]
def blocked(*args,**kwargs):
    NETWORK_ATTEMPTS.append('forbidden_network_call')
    raise AssertionError('network forbidden for contract example construction')
socket.create_connection=blocked
socket.getaddrinfo=blocked
def save(name, typ, val, basis='manually_assembled_proposed_contract_over_source_executed_synthetic'):
    EXAMPLES.append(dict(example_id=name,schema_name=typ,basis=basis,value=val))
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def cr(owner,pointer,kind='sheet'): return dict(kind=kind,owner_id=owner,pointer=pointer)
def loc(doc,pointer='',table=None,row=None,col=None,field=None):
    is_data=doc=='synthetic_data_pathway'
    return dict(source_ref=doc if is_data else 'synthetic_source_'+doc,raw_artifact_ref='synthetic_data_pathway_bytes' if is_data else 'synthetic_artifact_'+doc,
        document_id=None if is_data or doc.endswith('_input') else doc,json_pointer=pointer,table=table,row_ordinal=row,column_ordinal=col,native_field=field)
def num(value,unit,pop,*,origin='program_reported_derived',method='native_field',refs=(),codes=(),state=None):
    return dict(state=state or ('available' if value is not None else 'missing'),value=value,unit=unit,
        origin=origin,population_id=pop,method_id=method,input_refs=list(refs),uncertainty=None,qualification_codes=list(codes))
def ent(kind,**vals):
    e={k:None for k in SCHEMA['$defs']['EntityV1']['properties']};e['kind']=kind;e.update(vals);return e
def population(pid,kind,members,*,member_kind='genome_id',complete='complete_for_declared_population',codes=(),occ=None,source=(),relationship='not_applicable'):
    unit={'genome_id':'genome','record_id':'record','family_id':'family','ec_number':'ec_token','role_id':'role_token','feature_id':'feature'}[member_kind]
    return dict(population_id=pid,kind=kind,member_kind=member_kind,members=members,source_locations=list(source),
        raw_occurrence_count=num(len(members) if occ is None else occ,unit,pid,origin='derived_retained_records',method='record_occurrences',codes=codes),
        distinct_valid_member_count=num(len(set(members)),unit,pid,origin='derived_retained_records',method='distinct_valid_members',codes=codes),
        completeness=complete,missing_members=[],unresolved_members=[],relationship_to_original_task=relationship,qualification_codes=list(codes))
def original(job,gids):
    return dict(application='ComparativeSystems',task_ref='synthetic_task_'+job,request_source_ref='synthetic_request_'+job,
        genome_ids=gids,genome_groups=[],output_path='synthetic_workspace_not_a_real_destination',output_file=job,
        executed_genome_ids=gids,executed_population_evidence=[loc(job+'_input','/genome_ids')])
def sheet(job,gids):
    return dict(version='bvbrc_comparative_systems_sheet_v1',analysis_id=job,original_request=original(job,gids),
        source_documents=[],producer_evidence=[dict(evidence_id='source670b',identity_kind='source_executed',
        repository_url='https://github.com/BV-BRC/comparative_systems_service',commit='670b3b6dd09509ebc62fb6f1b1caf3e38c33bd33',
        source_sha256='052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f',runtime_version='Python 3.12.3',
        dependency_version='pandas 2.2.3; NumPy 2.2.6; synthetic bvbrc_api stub',reference_release=None,source_locations=[])],
        populations=[population(job+'_requested','requested_direct_genomes',gids)],
        document_selection=dict(version='bvbrc_comparative_systems_document_selection_v1',documents=[],authoritative_views=[],dependent_views=[]),
        population_assignments=dict(version='bvbrc_comparative_systems_population_assignments_v1',assignments=[dict(
            population_id=job+'_requested',kind='requested_direct_genomes',view_id=None,entity=None,component_kind=None)]),
        native_documents=[],family_rows=[],pathway_rows=[],pathway_ec_rows=[],subsystem_rows=[],association_rows=[],overview_rows=[],variant_rows=[],
        supplied_record_sets=None,reference_memberships=[],duplicate_groups=[],join_results=[],requirements=[],diagnostics=[])
def source_doc(sh,path,docid,role,profile):
    raw=path.read_bytes()
    d=dict(document_id=docid,role=role,format_profile=profile,source_ref='synthetic_source_'+docid,
        raw_artifact_ref='synthetic_artifact_'+docid,byte_count=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
        transfer_body_complete='complete',object_complete='complete',original_task_ref=sh['original_request']['task_ref'],
        producer_evidence_id='source670b',basis='source_executed_synthetic')
    sh['source_documents'].append(d)
    sh['document_selection']['documents'].append(dict(document_id=docid,role=role,format_profile=profile,producer_evidence_id='source670b',
        input=dict(kind='possessed_artifact',source_ref=d['source_ref'],raw_artifact_ref=d['raw_artifact_ref'])))
    return d
def native_result(d,tables,metadata=()):
    ts=[]
    for table,text,dialect in tables:
        rows=list(csv.reader(io.StringIO(text),delimiter='\t'))
        headers=rows[:1]
        ts.append(dict(table=table,json_pointer='/'+table if d['format_profile'].endswith('json_v1') else '',raw_text=text,
            dialect=dialect,headers=headers,rows=[dict(row_ordinal=i,tokens=r,status='ok',numeric_fields=[],qualification_codes=[])
                for i,r in enumerate(rows[1:])]))
    return dict(version='bvbrc_comparative_systems_native_v1',status='ok',document=d,tables=ts,metadata=list(metadata),reported_numbers=[],diagnostics=[])
def base_row(doc,e,i=0,codes=()):
    return dict(document_id=doc,native_row_ordinal=i,entity=e,source_locations=[loc(doc,row=i)],qualification_codes=list(codes))
def association(doc,table,record,i,record_set=None):
    ids={k:record.get('id' if k=='record_id' else k) or None for k in SCHEMA['$defs']['AssociationRowV1']['properties']['identifiers']['properties']}
    return dict(association_id=f'{doc}_{table}_{i}',document_id=None if record_set else doc,record_set_id=record_set,
        table=table,row_ordinal=i,identifiers=ids,active_category=record.get('active'),
        fields=[dict(name=k,raw_text=str(v),location=loc(doc,table=table,row=i,col=j,field=k)) for j,(k,v) in enumerate(record.items())],
        identity_status='valid',coordinate_convention='not_applicable',qualification_codes=[])
def add_json(sh,job,suffix,docid,role,profile,tables):
    p=BASE/'source_executed_synthetic'/job/(job+suffix)
    d=source_doc(sh,p,docid,role,profile);val=json.loads(p.read_text())
    nr=native_result(d,[(t,val[t],'pandas_tsv' if t=='genes' else 'manual_tabs_unquoted') for t in tables],
        [dict(location=loc(docid,'/'+k),value=v) for k,v in val.items() if k not in tables])
    sh['native_documents'].append(nr)
    return val,nr
def add_view(sh,vid,doc,table): sh['document_selection']['authoritative_views'].append(dict(view_id=vid,document_id=doc,table=table))
def component_request(cid,quantity,e,vid,pop,*,record_set=None,family_kind=None,reference=None,category=None):
    return dict(component_id=cid,quantity=quantity,entity=e,
        view_selection=dict(kind='supplied_record_set' if record_set else 'native_view',view_id=vid,record_set_id=record_set),
        population_id=pop,family_kind=family_kind,comparison_genome_ids=None,reference_membership_id=reference,category=category,native_formula=None)
def params(req):return dict(version='bvbrc_comparative_systems_calculation_parameters_v1',requests=req,
    duplicate_policy='preserve_native_occurrences_and_deduplicate_identical_record_ids',absolute_tolerance=1e-12,relative_tolerance=1e-12)
def ratio_component(req,n,d,nunit,dunit,outunit,scale=1,codes=(),refs=(),component_population=None):
    pop=req['population_id'];result=None if d==0 else scale*n/d
    out=num(result,outunit,pop,origin='derived_calculation',method='ratio',refs=refs,codes=tuple(codes)+(('empty_denominator',) if d==0 else ()))
    rr=dict(numerator=num(n,nunit,pop,origin='derived_retained_records',method='distinct_valid_members',refs=refs),
        denominator=num(d,dunit,pop,origin='derived_retained_records',method='distinct_valid_members',refs=refs),scale=scale,
        output=out,genome_population_id=pop,component_population_id=component_population)
    if nunit=='genome_ec_pair':rr['numerator']['method_id']='distinct_valid_genome_ec_pairs'
    if nunit=='genome_role_pair':rr['numerator']['method_id']='distinct_valid_genome_role_pairs'
    if dunit.endswith('_opportunity'):rr['denominator']['method_id']='opportunity_product'
    if req['view_selection']['kind']=='supplied_record_set':
        rr['numerator']['origin']='derived_supplied_records';rr['denominator']['origin']='derived_supplied_records'
    return dict(component_id=req['component_id'],quantity=req['quantity'],entity=req['entity'],value=out,ratio=rr,
        input_refs=list(refs),population_ids=[pop],reference_membership_id=req['reference_membership_id'],qualification_codes=list(codes))
def components(sh,pa,cc):return dict(version='bvbrc_comparative_systems_components_v1',formula_version='bvbrc_comparative_systems_formulas_v1',
    analysis_id=sh['analysis_id'],sheet_sha256=digest(sh),parameters=pa,components=cc,requirements=[],diagnostics=[])

# A: source-executed pathway/subsystem report and raw retained populations.
job='discard_and_dependence';main=sheet(job,['1.1','2.1','3.1']);inp=json.loads((BASE/'source_executed_synthetic'/job/'inputs.json').read_text())
loss=['native_first_object_discard','native_query_completeness_unknown']
pv,pnr=add_json(main,job,'_pathways_tables.json','pathways','pathway_summary','comparative_systems_pathways_json_v1',['pathway','ecnumber','genes'])
sv,snr=add_json(main,job,'_subsystems_tables.json','subsystems','subsystem_summary','comparative_systems_subsystems_json_v1',['subsystems','genes'])
for table,suffix,doc,profile in [('pathways_tsv','_pathways.tsv','pathway_raw','comparative_systems_pathways_tsv_v1'),('subsystems_tsv','_subsystems.tsv','subsystem_raw','comparative_systems_subsystems_tsv_v1')]:
    p=BASE/'source_executed_synthetic'/job/(job+suffix);d=source_doc(main,p,doc,'pathway_associations' if doc=='pathway_raw' else 'subsystem_associations',profile)
    main['native_documents'].append(native_result(d,[(table,p.read_text(),'pandas_tsv')]))
    for i,r in enumerate(csv.DictReader(io.StringIO(p.read_text()),delimiter='\t')):main['association_rows'].append(association(doc,table,r,i))
    add_view(main,doc,doc,table)
main['populations'] += [population('pathway_native_genomes','native_view_represented_genomes',pv['genome_ids'],codes=loss,source=[loc('pathways','/genome_ids')]),
    population('subsystem_native_genomes','native_view_represented_genomes',sv['genome_ids'],codes=loss,source=[loc('subsystems','/genome_ids')]),
    population('pathway_native_ecs','selected_component_membership',['1.1.1.1','2.2.2.2'],member_kind='ec_number'),
    population('subsystem_native_roles','selected_component_membership',['r1','r2'],member_kind='role_id')]
pe=ent('pathway',pathway_id='P_TEST');se=ent('subsystem',subsystem_id='S_TEST',superclass_native='synthetic',superclass_aggregation='SYNTHETIC',class_name='Synthetic class',subclass='Synthetic subclass',subsystem_name='Synthetic subsystem')
add_view(main,'pathway_summary','pathways','pathway')
add_view(main,'subsystem_summary','subsystems','subsystems')
main['population_assignments']['assignments'] += [
    dict(population_id='pathway_native_genomes',kind='native_view_represented_genomes',view_id='pathway_summary',entity=None,component_kind=None),
    dict(population_id='subsystem_native_genomes',kind='native_view_represented_genomes',view_id='subsystem_summary',entity=None,component_kind=None),
    dict(population_id='pathway_native_ecs',kind='selected_component_membership',view_id='pathway_raw',entity=pe,component_kind='ec_number'),
    dict(population_id='subsystem_native_roles',kind='selected_component_membership',view_id='subsystem_raw',entity=se,component_kind='role_id')]
pmap={'genome_count':('reported_genome_count','genome'),'ec_count':('reported_ec_token_count','ec_token'),
    'gene_count':('reported_feature_token_count','feature_token'),'genome_ec':('reported_genome_ec_count','genome_ec_pair'),
    'ec_conservation':('reported_ec_conservation_percent','percent'),'gene_conservation':('reported_gene_conservation','feature_per_ec_genome')}
p=dict(next(csv.DictReader(io.StringIO(pv['pathway']),delimiter='\t')))
prow=base_row('pathways',pe,codes=loss)
for k,(dest,u) in pmap.items():
    prow[dest]=num(float(p[k]) if '.' in p[k] else int(p[k]),u,'pathway_native_genomes',refs=[cr('pathways','/pathway',kind='native')],codes=loss)
    pnr['reported_numbers'].append(dict(native_field=k,raw_lexeme=p[k],location=loc('pathways','/pathway','pathway',0,list(p).index(k),k),cell=prow[dest]))
main['pathway_rows'].append(prow)
for i,r in enumerate(csv.DictReader(io.StringIO(pv['ecnumber']),delimiter='\t')):
    e=base_row('pathways',ent('pathway_ec',pathway_id='P_TEST',ec_number=r['ec_number']),i,codes=loss)
    for k,(dest,u) in list(pmap.items())[:4]:e[dest]=num(int(r[k]),u,'pathway_native_genomes',codes=loss)
    main['pathway_ec_rows'].append(e)
s=dict(next(csv.DictReader(io.StringIO(sv['subsystems']),delimiter='\t')))
smap={'role_counts':('reported_role_token_count','role_token'),'gene_counts':('reported_feature_token_count','feature_token'),
    'genome_count':('reported_genome_count','genome'),'gene_conservation':('reported_gene_conservation','feature_per_role_genome'),
    'role_conservation':('reported_role_conservation_percent','percent'),'prop_active':('reported_record_genome_fraction','fraction')}
srow=base_row('subsystems',se,codes=loss)
for k,(dest,u) in smap.items():srow[dest]=num(float(s[k]) if '.' in s[k] else int(s[k]),u,'subsystem_native_genomes',codes=loss)
main['subsystem_rows'].append(srow)
for level in ['superclass','class','subclass']:
    main['overview_rows'].append(dict(**base_row('subsystems',ent('overview',superclass_aggregation='SYNTHETIC',class_name='Synthetic class' if level!='superclass' else None,subclass='Synthetic subclass' if level=='subclass' else None)),level=level,
        reported_subsystem_name_count=num(1,'subsystem_name','subsystem_native_genomes'),reported_feature_count=num(4,'feature_token','subsystem_native_genomes')))
vpath=BASE/'source_executed_synthetic'/job/(job+'_subsystems_variant_mtx.tsv')
vd=source_doc(main,vpath,'variants','subsystem_variants','comparative_systems_variant_matrix_source670b_v1')
vr=[line.split('\t') for line in vpath.read_text().splitlines()];vrow=vr[2]
vresult=dict(version='bvbrc_comparative_systems_native_v1',status='partial',document=vd,
    tables=[dict(table='variant_matrix',json_pointer='',raw_text=vpath.read_text(),dialect='pinned_variant_matrix',headers=vr[:2],
    rows=[dict(row_ordinal=0,tokens=vrow,status='invalid',numeric_fields=[],qualification_codes=['variant_matrix_extra_column'])])],metadata=[],reported_numbers=[],diagnostics=[])
main['native_documents'].append(vresult)
main['variant_rows'].append(dict(**base_row('variants',se,codes=['variant_matrix_extra_column']),raw_tokens=vrow,header_field_count=len(vr[0]),data_field_count=len(vrow),
    reported_active_occurrences=num(3,'occurrence','subsystem_native_genomes'),reported_likely_occurrences=num(2,'occurrence','subsystem_native_genomes'),
    reported_inactive_placeholder=num(0,'occurrence','subsystem_native_genomes',codes=['native_category_imputed']),
    reported_missing_genome_count=num(0,'genome','subsystem_native_genomes',codes=['native_category_imputed'])))
main['duplicate_groups']=[dict(group_id='repeated_pathway_f4',kind='identical_record',members=[cr(job,'/association_rows/3'),cr(job,'/association_rows/4')],native_unique_key='pw_f4',affected_field_ids=[])]

# B: full input list as a separate synthetic later Data response. It includes
# the lost row, but is not evidence that an actual later acquisition reproduces history.
# This separate hypothetical Solr response has one document per unique id.
# The producer witness's repeated identical occurrence remains in its raw files.
data_rows=list({r['id']:r for r in inp['pathway_response']}.values())
req={'version':'bvbrc_data_request_v2','collection':'pathway','mode':'page','filters':[{'field':'genome_id','operator':'in','value':inp['genome_ids']}],
    'fields':list(data_rows[0]),'sort':[{'field':'id','direction':'asc'}],'offset':0,'limit':100}
# Stable sort request and supplied row order are matched in this synthetic envelope.
data_rows=sorted(data_rows,key=lambda r:r['id']);raw=json.dumps({'responseHeader':{'status':0},'response':{'numFound':len(data_rows),'numFoundExact':True,'start':0,'docs':data_rows}},separators=(',',':')).encode()
prepared=encode_native_query(req,base_url='https://www.bv-brc.org/api')
native=prepared['native_request'];snap=SourceSnapshot('bvbrc_data',native['url'],copy.deepcopy(prepared['effective_request']),
    'SYNTHETIC_CONTRACT_EXAMPLE_NOT_RETRIEVED',raw,'application/solr+json',{'status':200,'body_complete':True,'automatic_redirects':False,
    'effective_url':native['url'],'request':copy.deepcopy(native),'header_items':[]})
parse=parse_data_snapshot(snap,prepared=prepared)
selector={'version':'bvbrc_data_result_selector_v2','page':None,'projection':{'family':'query_metadata'},'inputs':[],'supplied_metadata':[]}
binding=dict(source_ref='synthetic_data_pathway',native_artifact_ref='synthetic_data_pathway_bytes',native_sha256=hashlib.sha256(raw).hexdigest(),
    grading_artifact_ref='synthetic_data_pathway_grade',collection='pathway',acquisition_assignment_sha256=digest({'synthetic':True}),selector_sha256=digest(selector))
qualified=validate_data('QualifiedResult',dict(version='bvbrc_data_qualified_result_v1',service='bvbrc_data',binding=binding,
    host_qualification=dict(run_id='SYNTHETIC_NO_HOST_ADMISSION',source_episode_id='synthetic_data_results',receiver_episode_id='synthetic_comparative_results',
    scope_sha256=digest({'synthetic':True}),receipt_verified=True,native_bytes_verified=True,grading_custody_verified=True,original_selection_verified=True,
    input_bindings_verified=True,receiver_possession_verified=True,possession_basis='admitted_return'),
    grading=dict(version='bvbrc_data_grading_v1',prepared=prepared,selector=selector,parse_result=parse,page_components=calculate_page_counts(parse['sheet']),
    facet_components=None,feature_sequence_sheet=None,feature_sequence_components=None,molecular_sheet=None,input_bindings=[],metadata_bindings=[]),input_results=[]))
wrapper=dict(qualified_result=qualified,raw_binding=dict(source_ref=binding['source_ref'],raw_artifact_ref=binding['native_artifact_ref'],
    sha256=binding['native_sha256'],byte_count=len(raw),bytes_key=binding['native_artifact_ref']))
(BASE/'SYNTHETIC_DATA_RESPONSE_001.json').write_bytes(raw)
snap_evidence=dict(kind='single_complete_response',snapshot_id=None,source_locations=[loc('synthetic_data_pathway','/response')])
sel=dict(version='bvbrc_comparative_systems_data_selection_v1',record_sets=[dict(record_set_id='later_pathway_records',collection='pathway',
    source_refs=[binding['source_ref']],declared_genome_population=population('later_pathway_genomes','declared_query_genomes',inp['genome_ids'],relationship='later_selected_snapshot'),
    query_population_key=prepared['query_population']['population_key'],selected_fields=prepared['effective_request']['fields'],sort=prepared['effective_request']['sort'],
    annotation_filter='exact_PATRIC',relationship_to_original_task='later_selected_snapshot',snapshot_evidence=snap_evidence,release=None,roles=['pathway_records'])])
records=[]
for i,nr in enumerate(parse['sheet']['rows']):
    rec=data_rows[i]
    records.append(dict(record_set_id='later_pathway_records',source_ref=binding['source_ref'],native_sha256=binding['native_sha256'],page_row_key=nr['row_key'],native_unique_key=nr['native_id'],native_row=nr,
        association=association('synthetic_data_pathway','data_rows',rec,i,'later_pathway_records'),filter_state='included',
        duplicate_state='identical_repeat' if i>0 and rec==data_rows[i-1] else 'unique',qualification_codes=['annotation_filter_applied','later_snapshot_not_original']))
record_pop=population('later_pathway_records','supplied_data_records',[r['id'] for r in data_rows],member_kind='record_id',occ=5,
    codes=['later_snapshot_not_original'],relationship='later_selected_snapshot')
supp=dict(version='bvbrc_comparative_systems_supplied_records_v1',selection=sel,record_sets=[dict(record_set_id='later_pathway_records',collection='pathway',population=record_pop,
    pages=[dict(binding=binding,requested_offset=0,response_start=0,returned_row_count=5,reported_total=5,num_found_exact=True,body_complete=True,partial_results=None,snapshot_evidence=snap_evidence)],
    rows=records,annotation_filter='exact_PATRIC',page_coverage='complete',snapshot_consistency='single_response',
    original_query_record_count=num(5,'record','later_pathway_records',origin='derived_supplied_records',method='record_occurrences'),
    locally_included_record_count=num(5,'record','later_pathway_records',origin='derived_supplied_records',method='record_occurrences'))],requirements=[],diagnostics=[])
main['supplied_record_sets']=supp
main['populations'] += [sel['record_sets'][0]['declared_genome_population'],record_pop,
    ]
reference=dict(membership_id='synthetic_four_ECs',component_kind='ec_number',entity=pe,members=['1.1.1.1','2.2.2.2','3.3.3.3','4.4.4.4'],
    map_id='synthetic_map',release=None,completeness='complete_for_declared_population',basis='synthetic_fixture',source_locations=[],qualification_codes=['reference_release_unknown'])
main['reference_memberships']=[reference]
rp=component_request('retained_pathway_percent','pathway_retained_ec_occupancy_percent',pe,'pathway_raw','pathway_native_genomes')
rf=component_request('later_pathway_percent','pathway_record_ec_occupancy_percent',pe,None,'later_pathway_genomes',record_set='later_pathway_records')
rs=component_request('retained_subsystem_percent','subsystem_retained_role_occupancy_percent',se,'subsystem_raw','subsystem_native_genomes')
rr=component_request('synthetic_reference_representation','reference_component_representation',pe,'pathway_raw','pathway_native_genomes',reference='synthetic_four_ECs')
ra=component_request('unambiguous_active_genomes','subsystem_explicit_category_genome_count',se,'subsystem_raw','subsystem_native_genomes',category='active')
rl=component_request('unambiguous_likely_genomes','subsystem_explicit_category_genome_count',se,'subsystem_raw','subsystem_native_genomes',category='likely')
pa=params([rp,rf,rs,rr,ra,rl])
cc=[ratio_component(rp,3,4,'genome_ec_pair','ec_genome_opportunity','percent',100,loss,[cr(job,'/association_rows')],'pathway_native_ecs'),
    ratio_component(rf,4,9,'genome_ec_pair','ec_genome_opportunity','percent',100,['later_snapshot_not_original'],[cr(job,'/supplied_record_sets')],None),
    ratio_component(rs,3,4,'genome_role_pair','role_genome_opportunity','percent',100,loss,[cr(job,'/association_rows')],'subsystem_native_roles'),
    ratio_component(rr,2,4,'ec_token','ec_token','fraction',1,['reference_release_unknown'],[cr(job,'/reference_memberships')],'synthetic_four_ECs')]
for r,n in [(ra,0),(rl,1)]:
    cc.append(dict(component_id=r['component_id'],quantity=r['quantity'],entity=r['entity'],
        value=num(n,'genome','subsystem_native_genomes',origin='derived_calculation',method='explicit_category_exact_set',
            refs=[cr(job,'/association_rows')],codes=loss+['conflicting_native_categories']),ratio=None,input_refs=[cr(job,'/association_rows')],
        population_ids=['subsystem_native_genomes'],reference_membership_id=None,qualification_codes=loss+['conflicting_native_categories']))
mainc=components(main,pa,cc)
save('pathway_subsystem_sheet','ComparativeSystemsSheetV1',main)
save('pathway_subsystem_components','ComparativeSystemsComponentsV1',mainc)
rr_later=component_request('synthetic_reference_later_records','reference_component_representation',pe,None,'later_pathway_genomes',record_set='later_pathway_records',reference='synthetic_four_ECs')
save('saved_sheet_recalculation','ComparativeSystemsComponentsV1',components(main,params([rr_later]),[
    ratio_component(rr_later,3,4,'ec_token','ec_token','fraction',1,['reference_release_unknown','later_snapshot_not_original'],
        [cr(job,'/supplied_record_sets'),cr(job,'/reference_memberships')],'synthetic_four_ECs')]))
save('qualified_data_wrapper','QualifiedDataInputV1',wrapper,'synthetic_existing_Data_encoder_reader_output_with_hypothetical_host_flags_NO_REAL_ADMISSION')
save('data_population_selection','DataPopulationSelectionV1',sel)
save('supplied_record_sets','SuppliedRecordSetsV1',supp)
save('pathway_native_document','NativeDocumentResultV1',pnr)
save('document_selection','DocumentSelectionV1',main['document_selection'])
save('calculation_parameters','CalculationParametersV1',pa)
save('population_assignments','PopulationAssignmentsV1',main['population_assignments'])
save('qualified_producer_evidence','QualifiedProducerEvidenceV1',dict(evidence=main['producer_evidence'][0],qualification=dict(original_task_ref=main['original_request']['task_ref'],basis='source_execution',evidence_source_refs=['synthetic_source_execution_receipt'],host_binding_verified=True,evidence_fields_verified=True,receiver_possession_verified=True)),
    'synthetic_source_execution_wrapper_NO_REAL_HOST_ADMISSION')
save('provider_parameters','ProviderParametersV1',dict(analysis_id=job,document_selection=main['document_selection'],population_assignments=main['population_assignments'],
    producer_evidence_selections=[dict(evidence_id='source670b',source_ref='synthetic_source_execution_receipt',raw_artifact_ref='synthetic_source_execution_receipt_bytes',record_path='/producer_evidence')],
    supplied_data_selection=sel,reference_memberships=[reference],calculation_parameters=pa))

# C/D: family native counts, dispersion, decoded zero, and irrecoverable hex overflow.
for family_job in ['families','hex_256']:
    fi=json.loads((BASE/'source_executed_synthetic'/family_job/'inputs.json').read_text())
    fs=sheet(family_job,fi['genome_ids']);fv,fnr=add_json(fs,family_job,'_proteinfams_tables.json',family_job+'_document','family_summary','comparative_systems_families_json_v1',['plfam','pgfam'])
    fpop=family_job+'_native_genomes';fs['populations'].append(population(fpop,'native_view_represented_genomes',fv['genome_ids'],codes=['native_query_completeness_unknown']))
    fs['population_assignments']['assignments'].append(dict(population_id=fpop,kind='native_view_represented_genomes',view_id='plfam',entity=None,component_kind=None))
    for kind in ['plfam','pgfam']:
        add_view(fs,kind, family_job+'_document',kind)
        row=dict(next(csv.DictReader(io.StringIO(fv[kind]),delimiter='\t')));eid=ent('family',family_id=row['family_id'],family_kind=kind)
        fr=base_row(family_job+'_document',eid);rawhex=row['genomes'];overflow=len(rawhex)!=2*len(fv['genome_ids'])
        fr.update(raw_hex_counts=rawhex,positive_genome_ids=fv[kind+'_genomes'][row['family_id']],genome_counts=[])
        for field,col,unit in [('reported_feature_occurrences','feature_count','occurrence'),('reported_genome_count','genome_count','genome'),
            ('reported_length_min','aa_length_min','amino_acid'),('reported_length_max','aa_length_max','amino_acid'),
            ('reported_length_mean','aa_length_mean','amino_acid'),('reported_length_population_sd','aa_length_std','amino_acid')]:
            fr[field]=num(float(row[col]) if '.' in row[col] else int(row[col]),unit,fpop,refs=[cr(family_job+'_document','/'+kind,'native')])
            fnr['reported_numbers'].append(dict(native_field=col,raw_lexeme=row[col],location=loc(family_job+'_document','/'+kind,kind,0,list(row).index(col),col),cell=fr[field]))
        fr['positive_genome_count_from_list']=num(len(set(fr['positive_genome_ids'])),'genome',fpop,origin='derived_retained_records',method='distinct_valid_members')
        for i,g in enumerate(fv['genome_ids']):
            count=None if overflow else int(rawhex[2*i:2*i+2],16)
            fr['genome_counts'].append(dict(genome_id=g,genome_ordinal=i,reported_occurrences=num(count,'occurrence',fpop,method='native_hex_exact_width',
                state='incompatible' if overflow else 'available',codes=['hex_count_width_ambiguous'] if overflow else ['native_query_completeness_unknown']),
                presence_state='incompatible' if overflow else 'recorded_positive' if count else 'no_record_completeness_unknown',source_locations=[loc(family_job+'_document','/'+kind,kind,0,8,'genomes')]))
        fs['family_rows'].append(fr)
    fe=fs['family_rows'][0]['entity'];a=component_request('family_occupancy','family_returned_genome_occupancy',fe,'plfam',fpop,family_kind='plfam')
    b=component_request('family_occurrence_mean','family_occurrences_per_positive_genome',fe,'plfam',fpop,family_kind='plfam')
    c=component_request('family_cv','family_length_cv',fe,'plfam',fpop,family_kind='plfam')
    frow=fs['family_rows'][0];v=lambda k:frow[k]['value']
    fc=[ratio_component(a,len(frow['positive_genome_ids']),len(fv['genome_ids']),'genome','genome','fraction',codes=['native_query_completeness_unknown']),
        ratio_component(b,v('reported_feature_occurrences'),v('reported_genome_count'),'occurrence','genome','occurrence_per_positive_genome'),
        ratio_component(c,v('reported_length_population_sd'),v('reported_length_mean'),'amino_acid','amino_acid','dimensionless')]
    fc[1]['ratio']['numerator']=copy.deepcopy(frow['reported_feature_occurrences'])
    fc[1]['ratio']['denominator']=copy.deepcopy(frow['reported_genome_count'])
    fc[2]['ratio']['numerator']=copy.deepcopy(frow['reported_length_population_sd'])
    fc[2]['ratio']['denominator']=copy.deepcopy(frow['reported_length_mean'])
    fc[2]['value']['method_id']='coefficient_of_variation'
    save(family_job+'_sheet','ComparativeSystemsSheetV1',fs);save(family_job+'_components','ComparativeSystemsComponentsV1',components(fs,params([a,b,c]),fc))

# Finite provider and parent quantities: provider facts are an object, as the host expects.
requested=dict(version='bvbrc_comparative_systems_requested_selection_v1',fields=[
    dict(field_id='retained_ec_percent',selector=dict(kind='ratio',component_id='retained_pathway_percent'),expected_cardinality=1,availability_requirement='typed_state'),
    dict(field_id='active_genome_count',selector=dict(kind='computed_measurement',component_id='unambiguous_active_genomes'),expected_cardinality=1,availability_requirement='typed_state'),
    dict(field_id='native_ec_percent',selector=dict(kind='measurement',view_id='pathway_summary',entity=pe,native_field='reported_ec_conservation_percent'),expected_cardinality=1,availability_requirement='typed_state')])
facts={'retained_ec_percent':dict(field_id='retained_ec_percent',values=[cc[0]['ratio']],status='satisfied')}
facts['active_genome_count']=dict(field_id='active_genome_count',values=[cc[4]['value']],status='satisfied')
facts['native_ec_percent']=dict(field_id='native_ec_percent',values=[main['pathway_rows'][0]['reported_ec_conservation_percent']],status='satisfied')
save('requested_selection','RequestedSelectionV1',requested)
save('provider_result','ProviderResultV1',dict(adapter_id='bvbrc_comparative_systems',adapter_version='1',status='ok',sheet=main,components=mainc,facts=facts,missing_requirements=[],diagnostics=[]))
save('parent_return_fact','RequestedFactV1',dict(source_ref='synthetic_original_result',field='retained_ec_percent',value=facts['retained_ec_percent']))
failure=dict(requirement_id='need_complete_original_records',code='population_incomplete',required_input_role='pathway_records',document_id=None,affected_field_ids=['full_original_population_percent'],source_refs=['synthetic_source_pathways'])
save('complete_population_requirement','RequirementV1',failure)
for state in ['available','missing','not_measured','failed','truncated','incompatible','invalid']:
    save('numeric_state_'+state,'NumericCellV1',num(0 if state=='available' else None,'record',None,state=state,origin='derived_retained_records' if state=='available' else 'unavailable',method='record_occurrences' if state=='available' else 'unavailable'),'manually_specified_synthetic_state_example')

payload=dict(version='comparative_systems_contract_examples_v1',classification='REVIEW_ONLY_SYNTHETIC_NOT_SERVICE_OUTPUT_OR_HOST_ADMISSION',
    production_comparative_systems_parser_or_calculator_executed=False,
    network_attempts=NETWORK_ATTEMPTS,
    raw_byte_inputs=[dict(bytes_key='synthetic_data_pathway_bytes',relative_file='SYNTHETIC_DATA_RESPONSE_001.json',sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw))],examples=EXAMPLES)
(BASE/'FILLED_EXAMPLES_001.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
print(json.dumps({'examples':len(EXAMPLES),'source_service_job':False,'production_comparative_systems_grader':False}))
