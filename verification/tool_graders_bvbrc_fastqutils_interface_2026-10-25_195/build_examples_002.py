"""Write hand-authored contract oracles, not a native parser or calculator.

All numerical values below are stipulated fixture answers. Identity/schema
construction is exercised solely to make the proposed ABI concrete.
"""
from copy import deepcopy as cp
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE/'SCHEMAS_004.json').read_text())
D = SCHEMA['$defs']
ANALYSIS = 'example195'
TASK = 'source_original_submission'

def canonical(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(v): return sha(canonical(v).encode())
def write(name, v): (HERE/name).write_text(json.dumps(v, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
def esc(v): return str(v).replace('~','~0').replace('/','~1')
def identity(kind, pointer): return 'bvbrc_fastqutils_' + kind + ':' + quote(ANALYSIS,safe='') + '/' + quote(pointer,safe='')
def content(name, raw): return {'source_ref':'source_'+name,'artifact_field':'artifact_ref',
    'artifact_ref':'artifact_'+name,'sha256':sha(raw),'byte_count':len(raw)}
def artifact_pointer(doc, binding): return '/documents/'+esc(doc)+'/sha256/'+binding['sha256']
def loc(block, row=None, field='value', ordinal=0): return {'member':None,'block':block,
    'block_ordinal':ordinal,'row_ordinal':row,'field':field,'byte_start':None,'byte_end':None}
def axis(kind='none',label=None,lower=None,upper=None): return {'kind':kind,'label':label,'lower':lower,'upper':upper}
def unknown_encoding(): return {'basis':'unknown','encoding':'unknown','metadata_id':None,
    'evidence':None,'declaration':None,'native_locator':None}
def population(doc,binding,key,kind,ordinal=0,section=None):
    aid=identity('artifact',artifact_pointer(doc,binding))
    return {'id':identity('population',artifact_pointer(doc,binding)+'/populations/'+key+'/'+str(ordinal)),
        'association_ref':None,'kind':kind,'scope':'complete','representation':'emitted_bytes' if doc=='reads' else 'native_report',
        'member_artifact_refs':[aid],'member_record_refs':[],'parent_population_refs':[],'disjoint_from_refs':[],
        'pair_key_rule':None,'quality_encoding':'unknown','encoding_evidence_refs':[],
        'document_ids':[doc],'population_key':key,'population_ordinal':ordinal,
        'section_key':section,'section_ordinal':0 if section else None,'encoding_basis':unknown_encoding()}
def cell(doc,binding,ordinal,metric,value,unit,pop,section='fastq_summary',row=None,ax=None,
         meaning='observed_count',precision='exact_for_retained_population'):
    return {'id':identity('cell',artifact_pointer(doc,binding)+'/cells/'+str(ordinal)),
        'artifact_ref':identity('artifact',artifact_pointer(doc,binding)), 'locator':loc(section,row,metric),
        'metric':metric,'axis':axis() if ax is None else ax,'population_ref':pop,'association_ref':None,
        'state':'available','value':value,'native_token':str(value),'unit':unit,'meaning':meaning,
        'precision':precision,'diagnostic_codes':[],'section_key':section,'section_ordinal':0}
def document(doc,binding,fmt,pops,cells,sections,version=None):
    return {'schema_version':'fastqutils_native_v2','analysis_id':ANALYSIS,'document_id':doc,
        'artifact':{'id':identity('artifact',artifact_pointer(doc,binding)),'source_ref':binding['source_ref'],
        'content_ref':binding['artifact_ref'],'task_ref':TASK,'sha256':binding['sha256'],
        'byte_count':binding['byte_count'],'native_name':'fixture_'+doc,'declared_format':fmt,'actual_format':fmt,
        'compression':'none','transfer_scope':'complete','producer_name':None,'producer_version':version,
        'identity':'handcrafted_synthetic','document_id':doc,'content_binding':cp(binding)},
        'parse_scope':'complete','cells':cells,'categories':[],'raw_blocks':[], 'sequence_records':[],
        'alignment_records':[],'diagnostics':[],'sections':sections,'labels':[],'populations':pops,
        'native_lineage':[],'alignment_headers':[],'reference_dictionary':[],'requirements':[]}
def section(key,cells): return {'key':key,'ordinal':0,'locator':loc(key),'state':'complete',
    'cell_refs':[c['id'] for c in cells],'category_refs':[],'label_refs':[],'raw_block_ordinals':[]}
def measurement_target(doc,metric,section='fastq_summary',row=None,ax=None):
    return {'selection':'semantic','document_id':doc,'section_key':section,'section_ordinal':0,
        'metric':metric,'rows':{'kind':'all'} if row is None else {'kind':'ordinal','ordinal':row},
        'axis':{'kind':'exact','axis':axis() if ax is None else ax}}
def population_target(doc,key): return {'selection':'semantic','document_id':doc,'population_key':key,'population_ordinal':0}
def selection(kind,target,availability='available_value',cardinality='one_target',count=1):
    return {'target':{'kind':kind,'selector':target},'cardinality':cardinality,
        'expected_cardinality':count,'availability_requirement':availability}
def components_target(calc,metric,threshold=None):
    return {'selection':'semantic','calculation_id':calc,'metric':metric,'threshold':threshold}

raw=b'@r1\nACGTN\n+\nIIIII\n@r2\nGGCTA\n+\nIIIII\n'
(HERE/'fixtures/native_reads.fastq').write_bytes(raw)
READS=content('reads195',raw)
native_hostile=[{'version':'1.1.0','aligner':'bowtie2','index':'SYNTHETIC_REFERENCE_ID_NOT_ACQUIRED',
    'options':[],'fastq1_in_name':'nonzero_R1.fastq','fastq1_in_path':'nonzero_R1.fastq',
    'fastq1_out_name':'nonzero_R1.clean_1.fastq.gz','fastq1_out_path':'/fixture/nonzero_R1.clean_1.fastq.gz',
    'fastq2_in_name':'nonzero_R2.fastq','fastq2_in_path':'nonzero_R2.fastq',
    'fastq2_out_name':'nonzero_R2.clean_2.fastq.gz','fastq2_out_path':'/fixture/nonzero_R2.clean_2.fastq.gz',
    'reads_in':8,'reads_out':6,'reads_removed':2,'reads_removed_proportion':0.25}]
hostile_raw=(json.dumps(native_hostile,indent=2)+'\n').encode()
(HERE/'fixtures/native_hostile_1_1_0.json').write_bytes(hostile_raw)
HOSTILE=content('hostile195',hostile_raw)
encoding={'version':'fastqutils_encoding_declaration_v1','document_id':'reads','encoding':'phred33','basis':'explicit_assumption'}
association={'version':'fastqutils_association_assertion_v1','document_id':'hostile',
    'input_pointer':'/paired_end_libs/0','recipe_ordinal':4,'mate':'combined','branch':'clean','basis':'explicit_assertion'}
metadata_raw=(json.dumps({'declarations':[encoding,association]},indent=2)+'\n').encode()
(HERE/'fixtures/metadata.json').write_bytes(metadata_raw)
METADATA=content('metadata195',metadata_raw)
encoding_evidence={'content':METADATA,'pointer':'/declarations/0'}
association_evidence={'content':METADATA,'pointer':'/declarations/1'}
encoding_basis={'basis':'explicit_source_bound_declaration','encoding':'phred33','metadata_id':'encoding_reads',
    'evidence':encoding_evidence,'declaration':encoding,'native_locator':None}
selected_metadata=[{'metadata_id':'encoding_reads','kind':'encoding_declaration','evidence':encoding_evidence,'value':encoding},
    {'metadata_id':'assert_hostile_stage','kind':'association_assertion','evidence':association_evidence,'value':association}]
supplied_values=[{'evidence':m['evidence'],'value':m['value']} for m in selected_metadata]
original_task={'resource_id':'bvbrc_api','task_id':'synthetic_task195','required_application_id':'FastqUtils',
    'native_application_id':'FastqUtils','submitted_parameters':{
        'paired_end_libs':[{'read1':'/fixture/input_R1.fastq','read2':'/fixture/input_R2.fastq','platform':'illumina'}],
        'single_end_libs':[],'srr_libs':[],'recipe':['TRIM','PAIRED_FILTER','FASTQC','ALIGN','SCRUB_HUMAN','SCRUB_HUMAN'],
        'reference_genome_id':'synthetic_reference195','output_path':'/fixture/output','output_file':'fixture'},
    'submitted_start_parameters':{},'scheduler_returned_parameters':None,'effective_parameters':None,
    'submission_receipt_ref':TASK,'submission_operation_key':'synthetic:submission195',
    'submission_source_ref':'source_original_native_request195'}

pops=[population('reads',READS,'fastq_reads','fastq_reads'), population('reads',READS,'fastq_bases','fastq_bases'),
    population('reads',READS,'fastq_quality_characters','fastq_bases')]
cells=[]
for metric,value,unit,pop in [('fastq_read_count',2,'reads',pops[0]),('fastq_base_count',10,'bases',pops[1]),
    ('fastq_min_length',5,'bases',pops[0]),('fastq_max_length',5,'bases',pops[0])]:
    cells.append(cell('reads',READS,len(cells),metric,value,unit,pop['id']))
for n,(symbol,count) in enumerate([('A',2),('C',2),('G',3),('T',2),('N',1),('other_iupac',0),('invalid',0)]):
    cells.append(cell('reads',READS,len(cells),'fastq_symbol_count',count,'bases',pops[1]['id'],row=n,ax=axis('symbol',symbol)))
cells.append(cell('reads',READS,len(cells),'fastq_length_histogram_count',2,'reads',pops[0]['id'],row=0,ax=axis('length_closed',None,5,5)))
cells.append(cell('reads',READS,len(cells),'quality_character_count',10,'bases',pops[2]['id'],row=0,ax=axis('quality_ascii',None,73,73)))
doc=document('reads',READS,'fastq',pops,cells,[section('fastq_summary',cells),section('fastq_records',[])])
for i,(title,seq) in enumerate([('r1','ACGTN'),('r2','GGCTA')]):
    rec={'id':identity('sequence',artifact_pointer('reads',READS)+'/sequences/'+str(i)),
        'artifact_ref':doc['artifact']['id'],'ordinal':i,'title':title,'sequence':seq,
        'quality_symbols':'IIIII','phred_values':None,'locator':loc('fastq_records',i,'record')}
    doc['sequence_records'].append(rec)
for pop in doc['populations']: pop['member_record_refs']=[r['id'] for r in doc['sequence_records']]
hpops=[population('hostile',HOSTILE,'hostile_'+k,'primary_alignment_reads',section='hostile_report') for k in ('in','out','removed')]
hcells=[]
for metric,value,unit,pop in [('hostile_reads_in',8,'reads',hpops[0]),('hostile_reads_out',6,'reads',hpops[1]),
    ('hostile_reads_removed',2,'reads',hpops[2]),('hostile_removed_proportion',0.25,'fraction',hpops[0])]:
    hcells.append(cell('hostile',HOSTILE,len(hcells),metric,value,unit,pop['id'],section='hostile_report',row=0,
        meaning='native_normalized' if metric.endswith('proportion') else 'observed_count',
        precision='native_rounded' if metric.endswith('proportion') else 'exact_for_retained_population'))
hdoc=document('hostile',HOSTILE,'hostile_json_1_1_0',hpops,hcells,[section('hostile_report',hcells)],'1.1.0')
hdoc['native_lineage']=[{'id':identity('lineage',artifact_pointer('hostile',HOSTILE)+'/lineage/0'),
    'kind':'native_report_before_after','before_population_ref':hpops[0]['id'],'after_population_ref':hpops[1]['id'],
    'document_ids':['hostile'],'source_refs':[HOSTILE['source_ref']],'locators':[loc('hostile_report',0)],
    'scope':'artifact_local','task_stage_ref':None}]
documents=[doc,hdoc]

bindings=[{'document_id':name,'selection':{'kind':'output_requirement','requirement_id':req},'format':fmt,'producer_version':ver}
    for name,req,fmt,ver in [('reads','selected_reads','fastq',None),('hostile','selected_hostile','hostile_json_1_1_0','1.1.0'),
                            ('qc','optional_qc','fastqc_html_0_12_1','0.12.1')]]
requests=[{'calculation_id':'composition_reads','method':'composition_v1','population':population_target('reads','fastq_reads')},
    {'calculation_id':'quality_reads','method':'quality_phred_v1','population':population_target('reads','fastq_quality_characters'),
        'quality_thresholds':[30]},
    {'calculation_id':'retention_hostile','method':'retention_v1','comparison_kind':'native_report_retention',
        'before_population':population_target('hostile','hostile_in'),'after_population':population_target('hostile','hostile_out'),
        'before_measurement':measurement_target('hostile','hostile_reads_in','hostile_report',0),
        'after_measurement':measurement_target('hostile','hostile_reads_out','hostile_report',0)}]
provider={'version':'fastqutils_provider_v2','analysis_id':ANALYSIS,'documents':bindings,
    'metadata_bindings':[{k:v for k,v in m.items() if k!='value'} for m in selected_metadata], 'calculation_requests':requests}
missing_req={'id':identity('requirement','/documents/qc/missing_artifact'),'code':'missing_artifact',
    'affected_refs':[identity('document','/documents/qc')],'required_data':'selected_document','state':'unavailable','source_refs':[]}
lineage_req={'id':identity('requirement','/documents/hostile/stage_execution_unknown'),'code':'stage_execution_unknown',
    'affected_refs':[hdoc['artifact']['id']],'required_data':'native_execution_evidence','state':'unresolved','source_refs':[HOSTILE['source_ref']]}
resolutions=[{'document_id':b['document_id'],'selection':b['selection'],'state':'available' if i<2 else 'missing',
    'matched_contents':[[READS],[HOSTILE],[]][i],'artifact_ref':documents[i]['artifact']['id'] if i<2 else None,
    'requirement_refs':[] if i<2 else [missing_req['id']],'diagnostic_codes':[] if i<2 else ['missing_artifact']}
    for i,b in enumerate(bindings)]
library={'id':identity('library','/tasks/'+esc(TASK)+'/inputs/paired_end_libs/0'),'task_ref':TASK,
    'input_pointer':'/paired_end_libs/0','sample_ref':None,'condition_ref':None,'replicate_ref':None,
    'platform':'illumina','evidence_refs':[original_task['submission_source_ref']],
    'submitted_value':original_task['submitted_parameters']['paired_end_libs'][0],'metadata_ids':[]}
stages=[{'id':identity('stage','/tasks/'+esc(TASK)+'/recipe/'+str(i)), 'task_ref':TASK,
    'recipe_ordinal':i,'requested_token':token,'mode':token,'observed_state':'unknown',
    'input_population_refs':[],'output_population_refs':[],'evidence_refs':[original_task['submission_source_ref']],
    'request_pointer':'/submitted_parameters/recipe/'+str(i),'requested_reference_genome_id':'synthetic_reference195'}
    for i,token in enumerate(original_task['submitted_parameters']['recipe'])]
assoc={'id':identity('association','/metadata/assert_hostile_stage'),'task_ref':TASK,'library_ref':library['id'],
    'stage_ref':stages[4]['id'],'mate':'combined','branch':'clean','artifact_refs':[hdoc['artifact']['id']],
    'evidence_refs':[METADATA['source_ref']],'state':'unresolved','basis':'explicit_assertion',
    'metadata_ids':['assert_hostile_stage'],'document_ids':['hostile']}
sheet_pops=cp(pops+hpops)
for p in sheet_pops[:3]:
    p['quality_encoding']='phred33';p['encoding_basis']=cp(encoding_basis);p['encoding_evidence_refs']=[METADATA['source_ref']]
sheet={'schema_version':'fastqutils_sheet_v2','analysis_id':ANALYSIS,'task_ref':TASK,'original_task':original_task,
    'documents':documents,'document_resolutions':resolutions,'libraries':[library],'stages':stages,
    'associations':[assoc],'populations':sheet_pops,'measurements':cells+hcells,'categories':[],
    'supplied_metadata':selected_metadata,'native_lineage':hdoc['native_lineage'],
    'requirements':[missing_req,lineage_req],'diagnostics':[]}
metadata={'schema_version':'fastqutils_metadata_v2','analysis_id':ANALYSIS,'task_ref':TASK,'original_task':original_task,
    'libraries':[library],'stages':stages,'associations':[assoc],'populations':sheet_pops,
    'supplied_metadata':selected_metadata,'native_lineage':hdoc['native_lineage'],
    'requirements':[lineage_req],'diagnostics':[],'measurements':[]}
resolved=[]
for calc,method,ps,ms,kind,thresholds,edge in [
    ('composition_reads','composition_v1',[pops[0]['id'],pops[1]['id']],[c['id'] for c in cells[:2]+cells[4:11]],None,[],None),
    ('quality_reads','quality_phred_v1',[pops[2]['id']],[cells[-1]['id']],None,[30],None),
    ('retention_hostile','retention_v1',[hpops[0]['id'],hpops[1]['id']],[hcells[0]['id'],hcells[1]['id']],
      'native_report_retention',[],hdoc['native_lineage'][0]['id'])]:
    resolved.append({'calculation_id':calc,'method':method,'state':'ready','population_refs':ps,
        'operand_measurement_refs':ms,'comparison_kind':kind,'quality_thresholds':thresholds,
        'read_key_rule':None,'lineage_ref':edge,'requirement_refs':[],'diagnostic_codes':[]})
    resolved[-1]['lineage_basis']=None if edge is None else {'basis':'native_report','metadata_id':None,
        'evidence':None,'declaration':None,'native_lineage_ref':edge}
parameters={'version':'fastqutils_calculators_v2','analysis_id':ANALYSIS,'calculations':resolved}
sheet_hash=digest(sheet);parameter_hash=digest(parameters)
components=[]
def component(job,metric,value,unit,numerator,denominator,threshold=None):
    b=resolved[job]; quality=b['method']=='quality_phred_v1';model=metric.startswith('phred_implied')
    pointer='/sheets/'+sheet_hash+'/parameters/'+parameter_hash+'/calculations/'+b['calculation_id']+'/'+metric+'/'+('none' if threshold is None else str(threshold))
    result={'id':identity('component',pointer),'calculation_id':b['calculation_id'],'metric':metric,'state':'available',
        'value':value,'unit':unit,'method':b['method'],'population_refs':b['population_refs'],
        'operand_measurement_refs':b['operand_measurement_refs'],'numerator':numerator,'denominator':denominator,
        'threshold':threshold,'meaning':'phred_model_prediction' if model else 'native_report_derived' if job==2 else 'derived_descriptive',
        'uncertainty':'phred_model_only' if model else 'native_reporting_precision' if job==2 else 'not_estimated',
        'parameter_sha256':parameter_hash,'diagnostic_codes':['explicit_encoding_assumption'] if quality else [],
        'encoding_basis':cp(encoding_basis) if quality else None,'lineage_basis':cp(b['lineage_basis'])}
    if job==0:
        indices={'gc_acgt_fraction':[4,5,6,7,10], 'n_fraction':[1,8,10],
            'ambiguous_fraction':[1,8,9,10],'mean_read_length':[0,1]}[metric]
        result['operand_measurement_refs']=[cells[i]['id'] for i in indices]
    components.append(result)
component(0,'gc_acgt_fraction',5/9,'fraction',5,9)
component(0,'n_fraction',0.1,'fraction',1,10)
component(0,'ambiguous_fraction',0.1,'fraction',1,10)
component(0,'mean_read_length',5,'bases',10,2)
component(1,'mean_phred',40,'phred',400,10)
component(1,'q_ge_threshold_fraction',1,'fraction',10,10,30)
component(1,'phred_implied_expected_errors',0.001,'expected_errors',0.001,None)
component(1,'phred_implied_error_fraction',0.0001,'fraction',0.001,10)
component(2,'native_report_retention_fraction',0.75,'fraction',6,8)
component(2,'removed_count',2,'reads',2,None)
component(2,'removed_fraction',0.25,'fraction',2,8)
calculated={'schema_version':'fastqutils_components_v2','analysis_id':ANALYSIS,'sheet_sha256':sheet_hash,
    'parameters':parameters,'components':components,'requirements':[],'diagnostics':[]}

selections={
    'read_count':selection('measurement',measurement_target('reads','fastq_read_count')),
    'gc_fraction':selection('component',components_target('composition_reads','gc_acgt_fraction')),
    'expected_errors':selection('component',components_target('quality_reads','phred_implied_expected_errors')),
    'retained_native_report':selection('component',components_target('retention_hostile','native_report_retention_fraction')),
    'qc_status':selection('category',{'selection':'semantic','document_id':'qc','section_key':'fastqc_basic_statistics',
        'section_ordinal':0},'typed_state')}
form={'version':'fastqutils_projection_v2','fields':[{'field':k,'selection':v} for k,v in selections.items()]}
def closure(definitions, names):
    result={}
    def visit(v):
        if isinstance(v,dict):
            if '$ref' in v:
                name=v['$ref'].removeprefix('#/$defs/')
                if name not in result:
                    result[name]=cp(definitions[name]);visit(result[name])
            for x in v.values(): visit(x)
        elif isinstance(v,list):
            for x in v: visit(x)
    for name in names: visit({'$ref':'#/$defs/'+name})
    return result
requested_schema={'type':'object','properties':{k:{'$ref':'#/$defs/ProjectedField','x-bvbrc-fastqutils':v}
    for k,v in selections.items()},'required':list(selections),'additionalProperties':False,
    '$defs':closure(D,['ProjectedField'])}
def declared(fmt,ver): return {'format':fmt,'version':ver,'mode':None,'producer_source_ref':None,'transformation_evidence':[]}
selector={'version':'bvbrc_appservice_result_selector_v1','endpoint':'requested_projection',
    'requirements':[{'requirement_id':b['selection']['requirement_id'],'role':b['document_id'],
        'required':i<2,'declared_format':declared(b['format'],b['producer_version']),
        'producer_rule_evidence':None,'exact_object':None} for i,b in enumerate(bindings)],
    'adapter':{'adapter_id':'bvbrc_fastqutils','adapter_version':'2','parameters':provider},
    'requested_schema':requested_schema,'supplied_metadata':[encoding_evidence,association_evidence],
    'supplied_contents':[],'supplied_capabilities':[]}
def member(doc,binding,requirement):
    return {'role':doc['document_id'],'source_ref':binding['source_ref'],'raw_artifact_ref':binding['artifact_ref'],
        'sha256':binding['sha256'],'byte_count':binding['byte_count'],
        'workspace_object':{'path':'/fixture/output/'+doc['document_id'],'uuid':'synthetic_uuid_'+doc['document_id'],
            'type':'file','metadata_receipt_ref':'source_metadata_receipt_'+doc['document_id']},
        'task_association':{'kind':'task_result_manifest','evidence_ref':'source_manifest195','pointer':'/output_files/'+str(0 if doc['document_id']=='reads' else 1),
            'task_id':original_task['task_id'],'output_path':'/fixture/output','output_uuid':None,
            'byte_version_status':'current_bytes_observed','version_evidence':[]},
        'transfer':{'receipt_ref':'source_transfer_'+doc['document_id'],'body_complete':True,'requested_range':None,
            'observed_range':None,'total_size':binding['byte_count'],'object_complete':'yes'},
        'declared_format':declared(doc['artifact']['actual_format'],doc['artifact']['producer_version']),
        'requirement_ids':[requirement]}
bundle={'version':'bvbrc_appservice_artifact_bundle_v1','original_task':original_task,
    'artifacts':[member(doc,READS,'selected_reads'),member(hdoc,HOSTILE,'selected_hostile')],
    'input_bindings':[],'query_bindings':[],'supplied_scientific_metadata':[encoding_evidence,association_evidence],
    'supplied_contents':[],'acquisition_receipt_refs':['source_transfer_reads','source_transfer_hostile'],
    'requested_selector_sha256':digest(selector),'status':'ok','missing_requirements':[],
    'diagnostics':[{'code':'output_version_unproven','phase':'association','path':'','severity':'qualification',
        'evidence_refs':[b['source_ref']]} for b in (READS,HOSTILE)]}
def fact_record(kind,payload,reference,state='available',sources=None,requirements=None,codes=None):
    return {'kind':kind,'record_ref':reference,'state':state,'payload':payload,'source_refs':sources or [],
        'requirement_refs':requirements or [],'diagnostic_codes':codes or []}
def measurement_payload(c):
    label_ref=None if c['axis']['label'] is None else identity('label','/records/'+esc(c['id'])+'/axis/label')
    return {'measurement_ref':c['id'],'document_id':'reads','quantity':c['metric'],
        'axis':{'kind':c['axis']['kind'],'label_ref':label_ref,'lower':c['axis']['lower'],'upper':c['axis']['upper']},
        'state':c['state'],'value':c['value'],'unit':c['unit'],'meaning':c['meaning'],'precision':c['precision'],
        'population_ref':c['population_ref'],'association_ref':c['association_ref'],
        'native_token_ref':identity('label','/records/'+esc(c['id'])+'/native_token')}
def component_payload(c): return {'component_ref':c['id'],'quantity':c['metric'],
    **{k:cp(c[k]) for k in ('calculation_id','state','value','unit','method','population_refs','operand_measurement_refs',
        'numerator','denominator','threshold','meaning','uncertainty','parameter_sha256','encoding_basis','lineage_basis')}}
def projected(sel,rows,matched,state='satisfied',requirements=None,codes=None):
    return {'selection':sel,'matched_count':matched,'state':state,'satisfied':state=='satisfied',
        'records':rows,'requirement_refs':requirements or [],'diagnostic_codes':codes or []}
facts={'read_count':projected(selections['read_count'],[fact_record('measurement',measurement_payload(cells[0]),cells[0]['id'],sources=[READS['source_ref']])],1)}
for field,index in [('gc_fraction',0),('expected_errors',6),('retained_native_report',8)]:
    c=components[index];sources=[HOSTILE['source_ref']] if index==8 else [READS['source_ref']]
    if index==6:sources.append(METADATA['source_ref'])
    facts[field]=projected(selections[field],[fact_record('component',component_payload(c),c['id'],sources=sources,codes=c['diagnostic_codes'])],1)
absent=fact_record('category',None,None,'missing',requirements=[missing_req['id']],codes=['missing_artifact'])
facts['qc_status']=projected(selections['qc_status'],[absent],0,requirements=[missing_req['id']],codes=['missing_artifact'])

partial=[]
strict=cp(selections['qc_status']);strict['availability_requirement']='available_value'
partial.append({'name':'missing_category_available_required','selection':strict,
    'expected':projected(strict,[absent],0,'missing_value',[missing_req['id']],['missing_artifact'])})
unavailable_sel=selection('component',components_target('quality_reads','phred_implied_expected_errors'),'typed_state')
unavailable_component=cp(components[6]);unavailable_component.update(state='missing',value=None,numerator=None,
    denominator=None,encoding_basis=unknown_encoding(),diagnostic_codes=['unknown_quality_encoding'])
unavailable=fact_record('component',component_payload(unavailable_component),unavailable_component['id'],'missing',
    sources=[READS['source_ref']],codes=['unknown_quality_encoding'])
partial.append({'name':'selected_number_unknown_encoding_typed_state','selection':unavailable_sel,
    'expected':projected(unavailable_sel,[unavailable],1)})
strict_number=cp(unavailable_sel);strict_number['availability_requirement']='available_value'
partial.append({'name':'selected_number_unknown_encoding_available_required','selection':strict_number,
    'expected':projected(strict_number,[unavailable],1,'missing_value',codes=['unknown_quality_encoding'])})
for kind,target in [('population',population_target('qc','fastqc_module')),('association',
    {'selection':'semantic','document_id':'qc','input_pointer':'/paired_end_libs/0','recipe_ordinal':2,'mate':'R1','branch':'report_only'})]:
    sel=selection(kind,target,'typed_state');row=fact_record(kind,None,None,'missing',requirements=[missing_req['id']],codes=['missing_artifact'])
    partial.append({'name':'missing_'+kind+'_typed_state','selection':sel,
        'expected':projected(sel,[row],0,requirements=[missing_req['id']],codes=['missing_artifact'])})
row_selection=selection('measurement',measurement_target('qc','fastqc_base_quality_mean','fastqc_per_base_quality'),
    'typed_state','exact_rows',2)
partial.append({'name':'two_source_rows_absent_no_fabrication','selection':row_selection,
    'expected':projected(row_selection,[],0,'cardinality_mismatch',[missing_req['id']],['selection_cardinality_mismatch'])})
row_excess=selection('measurement',measurement_target('reads','fastq_symbol_count'), 'typed_state','exact_rows',2)
row_excess['target']['selector']['axis']={'kind':'all'}
excess_rows=[fact_record('measurement',measurement_payload(c),c['id'],sources=[READS['source_ref']]) for c in cells[4:11]]
partial.append({'name':'excess_source_rows_retained_no_first_two','selection':row_excess,
    'expected':projected(row_excess,excess_rows,7,'cardinality_mismatch',codes=['selection_cardinality_mismatch'])})
partial_row=cp(facts['read_count']['records'][0]);partial_row['state']='partial';partial_row['payload']['state']='partial'
partial_row['payload']['value']=1
partial.append({'name':'validated_prefix_count_not_whole_file','selection':selections['read_count'],
    'expected':projected(selections['read_count'],[partial_row],1,'missing_value',codes=['partial_transfer'])})
possessed=cp(provider);possessed['documents']=[{'document_id':'reads','selection':{'kind':'possessed_content','content':READS},
    'format':'fastq','producer_version':None}];possessed['calculation_requests']=requests[:2];possessed['metadata_bindings']=possessed['metadata_bindings'][:1]

write('ORIGINAL_TASK_002.json',original_task)
write('SUPPLIED_VALUES_002.json',supplied_values)
write('PROVIDER_PARAMETERS_002.json',provider)
write('POSSESSED_PARAMETERS_002.json',possessed)
write('REQUESTED_FORM_002.json',form)
write('RESULT_SELECTOR_PRE_DOWNLOAD_002.json',selector)
write('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json',bundle)
write('EXPECTED_NATIVE_DOCUMENTS_002.json',documents)
write('EXPECTED_METADATA_002.json',metadata)
write('EXPECTED_SHEET_002.json',sheet)
write('EXPECTED_COMPONENTS_002.json',calculated)
write('EXPECTED_FACTS_002.json',facts)
write('UNAVAILABLE_AND_PARTIAL_002.json',partial)
write('SOURCE_CUSTODY_AND_LINEAGE_002.json',{
    'identity':'handcrafted_contract_oracle_not_authenticated_runtime_execution',
    'existing_original_task_operands':{'parameter_pointer':'/submitted_parameters','start_pointer':'/submitted_start_parameters',
        'pure_task_ref':TASK,'native_task_id':original_task['task_id']},
    'supplied_sources':[{'content':METADATA,'fixture':'fixtures/metadata.json'}],
    'host_metadata_materialization':supplied_values,'preserved_sheet_assumptions':sheet['supplied_metadata'],
    'requested_stage_occurrences':stages,'asserted_association':assoc,
    'observed_native_report_edge':hdoc['native_lineage'][0],
    'native_report_retention_component':components[8],
    'task_stage_join':'unresolved','producer_byte_version':'current_bytes_observed',
    'not_inferred':['deployed_program_version_from_requested_version','stage_completed_from_filename',
        'hostile_index_from_reference_genome_id','requested_library_from_native_basename',
        'producer_byte_version_from_current_download','sequencing_error_rate_from_phred_model']})
write('IDENTITY_VECTORS_002.json',[
    {'kind':'document','analysis_id':ANALYSIS,'pointer':'/documents/reads','encoded':identity('document','/documents/reads')},
    {'kind':'label','analysis_id':ANALYSIS,'pointer':'/unicode/α~1β/percent%/space here',
     'encoded':identity('label','/unicode/α~1β/percent%/space here')},
    {'kind':'library','analysis_id':ANALYSIS,'pointer':'/tasks/'+esc(TASK)+'/inputs/paired_end_libs/0','encoded':library['id']},
    {'kind':'component','analysis_id':ANALYSIS,'pointer':'/sheets/'+sheet_hash+'/parameters/'+parameter_hash+
     '/calculations/quality_reads/phred_implied_expected_errors/none','encoded':components[6]['id']}])
print(json.dumps({'documents':len(documents),'measurements':len(sheet['measurements']),'components':len(components),
    'expected_requested_values':{'read_count':2,'gc_fraction':5/9,'expected_errors':0.001,'retained_native_report':0.75,
        'qc_status_payload':None},'unavailable_and_partial_cases':len(partial),'all_requested_fields_satisfied':True}))
