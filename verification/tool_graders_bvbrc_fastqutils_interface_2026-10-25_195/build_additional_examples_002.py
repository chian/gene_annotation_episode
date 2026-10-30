"""Additional handwritten missing/partial/assumed-lineage contract oracles."""
from copy import deepcopy as cp
import build_examples_002 as x

# The full unknown-encoding example keeps the exact native documents/counts.
sheet=cp(x.sheet)
sheet['supplied_metadata']=sheet['supplied_metadata'][1:]
for p in sheet['populations'][:3]:
    p.update(quality_encoding='unknown',encoding_evidence_refs=[],encoding_basis=x.unknown_encoding())
req={'id':x.identity('requirement','/documents/reads/unknown_quality_encoding'),'code':'unknown_quality_encoding',
    'affected_refs':[sheet['populations'][2]['id']],'required_data':'quality_encoding','state':'unavailable',
    'source_refs':[x.READS['source_ref']]}
sheet['requirements'].append(req)
parameters=cp(x.parameters)
parameters['calculations'][1].update(state='unavailable',requirement_refs=[req['id']],diagnostic_codes=['unknown_quality_encoding'])
result=cp(x.calculated)
result['sheet_sha256']=x.digest(sheet);result['parameters']=parameters;result['requirements']=[req]
for c in result['components']:
    c['parameter_sha256']=x.digest(parameters)
    c['id']=x.identity('component','/sheets/'+result['sheet_sha256']+'/parameters/'+x.digest(parameters)+
        '/calculations/'+c['calculation_id']+'/'+c['metric']+'/'+('none' if c['threshold'] is None else str(c['threshold'])))
    if c['method']=='quality_phred_v1':
        c.update(state='missing',value=None,numerator=None,denominator=None,encoding_basis=x.unknown_encoding(),
                 diagnostic_codes=['unknown_quality_encoding'])
provider=cp(x.provider);provider['metadata_bindings']=provider['metadata_bindings'][1:]
x.write('UNAVAILABLE_SHEET_002.json',sheet)
x.write('UNAVAILABLE_COMPONENTS_002.json',result)
x.write('UNAVAILABLE_PARAMETERS_002.json',provider)
cases=cp(x.partial)
for case in cases:
    if case['name'].startswith('selected_number_unknown_encoding'):
        c=next(c for c in result['components'] if c['metric']=='phred_implied_expected_errors')
        case['expected']['records']=[x.fact_record('component',x.component_payload(c),c['id'],'missing',
            sources=[x.READS['source_ref']],requirements=[req['id']],codes=['unknown_quality_encoding'])]
        case['expected']['requirement_refs']=[req['id']]

# Truncated FASTQ: one complete retained record; the suffix has no guessed row.
raw=b'@r1\nACGTN\n+\nIIIII\n@r2\nGGCTA\n+\nII'
(x.HERE/'fixtures/partial_reads.fastq').write_bytes(raw)
binding=x.content('partial_reads195',raw)
pops=[x.population('partial_reads',binding,'fastq_reads','fastq_reads'),
      x.population('partial_reads',binding,'fastq_bases','fastq_bases'),
      x.population('partial_reads',binding,'fastq_quality_characters','fastq_bases')]
for p in pops:p.update(scope='partial',representation='emitted_bytes')
cells=[]
for metric,value,unit,pop in [('fastq_read_count',1,'reads',pops[0]),('fastq_base_count',5,'bases',pops[1]),
    ('fastq_min_length',5,'bases',pops[0]),('fastq_max_length',5,'bases',pops[0])]:
    cells.append(x.cell('partial_reads',binding,len(cells),metric,value,unit,pop['id']))
for i,(symbol,count) in enumerate([('A',1),('C',1),('G',1),('T',1),('N',1),('other_iupac',0),('invalid',0)]):
    cells.append(x.cell('partial_reads',binding,len(cells),'fastq_symbol_count',count,'bases',pops[1]['id'],row=i,ax=x.axis('symbol',symbol)))
cells.append(x.cell('partial_reads',binding,len(cells),'fastq_length_histogram_count',1,'reads',pops[0]['id'],row=0,ax=x.axis('length_closed',None,5,5)))
cells.append(x.cell('partial_reads',binding,len(cells),'quality_character_count',5,'bases',pops[2]['id'],row=0,ax=x.axis('quality_ascii',None,73,73)))
for c in cells:c.update(state='partial',diagnostic_codes=['partial_transfer'])
doc=x.document('partial_reads',binding,'fastq',pops,cells,[x.section('fastq_summary',cells),x.section('fastq_records',[])])
doc['artifact']['transfer_scope']='partial';doc['parse_scope']='partial'
for section in doc['sections']:section['state']='partial'
record=cp(x.doc['sequence_records'][0]);record['id']=x.identity('sequence',x.artifact_pointer('partial_reads',binding)+'/sequences/0')
record['artifact_ref']=doc['artifact']['id'];doc['sequence_records']=[record]
for p in doc['populations']:p['member_record_refs']=[record['id']]
doc['requirements']=[{'id':x.identity('requirement','/documents/partial_reads/partial_transfer'),'code':'partial_transfer',
    'affected_refs':[doc['artifact']['id']],'required_data':'complete_native_bytes','state':'missing','source_refs':[binding['source_ref']]}]
doc['diagnostics']=[{'code':'partial_transfer','source_refs':[binding['source_ref']],'locator':'/records/1','affected_refs':[doc['artifact']['id']]}]
x.write('PARTIAL_NATIVE_DOCUMENT_002.json',doc)
case=next(c for c in cases if c['name']=='validated_prefix_count_not_whole_file')
case['selection']['target']['selector']['document_id']='partial_reads';case['expected']['selection']=cp(case['selection'])
payload=x.measurement_payload(cells[0]);payload['document_id']='partial_reads'
case['expected']['records']=[x.fact_record('measurement',payload,cells[0]['id'],'partial',sources=[binding['source_ref']],
    requirements=[doc['requirements'][0]['id']],codes=['partial_transfer'])]
case['expected']['requirement_refs']=[doc['requirements'][0]['id']]
x.write('UNAVAILABLE_AND_PARTIAL_002.json',cases)

# Exact zero is truthful only for an actually available complete empty selection.
empty=cp(next(c for c in cases if c['name']=='two_source_rows_absent_no_fabrication'))
empty['name']='exact_zero_rows_missing_source_is_not_empty'
empty['selection']['expected_cardinality']=0
empty['expected']['selection']=cp(empty['selection']);empty['expected']['state']='missing_value'
empty['expected']['diagnostic_codes']=['missing_artifact']
cases.append(empty)
empty_table=cp(empty);empty_table['name']='exact_zero_rows_complete_empty_selection'
empty_table['selection']['target']['selector']['document_id']='reads'
empty_table['selection']['target']['selector']['section_key']='fastq_summary'
empty_table['selection']['target']['selector']['metric']='quality_character_count'
empty_table['selection']['target']['selector']['axis']={'kind':'exact','axis':x.axis('quality_ascii',None,74,74)}
empty_table['expected'].update(selection=cp(empty_table['selection']),state='satisfied',satisfied=True,
    requirement_refs=[],diagnostic_codes=[])
cases.append(empty_table)
x.write('UNAVAILABLE_AND_PARTIAL_002.json',cases)

# Exact native-to-host error shapes and saved wrapper; these are contract data.
native_requirements=cp(x.sheet['requirements'])
def host_requirement(r):
    kind='parser_binding' if r['required_data'] in ('supported_parser','native_version') else (
        'output_bytes' if r['required_data'] in ('complete_native_bytes','full_fastqc_data','earlier_hostile_report','selected_document') else 'scientific_metadata')
    return {'requirement_id':r['id'],'kind':kind,'role':r['required_data'],
        'source_refs':list(dict.fromkeys(r['source_refs'])),'reason_code':'bvbrc_fastqutils_'+r['code']}
saved={'version':'fastqutils_saved_components_v2','calculations':cp(x.calculated),
    'projection_failure_context':{'requirements':native_requirements,'diagnostics':[]},
    'native_requirements':native_requirements,'native_diagnostics':[]}
provider_result={'adapter_id':'bvbrc_fastqutils','adapter_version':'2','status':'ok','facts':cp(x.facts),
    'missing_requirements':[host_requirement(r) for r in native_requirements],
    'diagnostics':[],'sheet':cp(x.sheet),'components':saved}
x.write('EXPECTED_PROVIDER_RESULT_002.json',provider_result)
x.write('ERROR_SHAPES_002.json',{
    'contract_failure':{'code':'binding_conflict','path':'/documents/0','source_refs':[x.READS['source_ref']],
        'affected_refs':[x.doc['artifact']['id']]},
    'native_requirement':native_requirements[0],
    'host_requirement':host_requirement(native_requirements[0]),
    'native_diagnostic':{'code':'malformed_native','source_refs':[x.READS['source_ref']],
        'locator':'/records/1','affected_refs':[x.doc['artifact']['id']]},
    'host_diagnostic':{'code':'bvbrc_fastqutils_malformed_native','phase':'native_decode',
        'path':'/native_diagnostics/0','severity':'qualification','evidence_refs':[x.READS['source_ref']]},
    'return_error':{'code':'bvbrc_fastqutils_return_saved_projection_invalid','path':'/publication/adapter_result',
        'diagnostics':[{'code':'bvbrc_fastqutils_return_saved_projection_invalid','path':'/publication/adapter_result'}]}})

# Two independent complete FASTQ documents. Their before/after relationship is
# expressly assumed by a selected source declaration, not established by names.
documents=[];bindings=[]
for name,n in [('before_reads',8),('after_reads',6)]:
    raw=b''.join(('@r'+str(i)+'\nACGT\n+\nIIII\n').encode() for i in range(n))
    (x.HERE/('fixtures/'+name+'.fastq')).write_bytes(raw)
    b=x.content(name+'195',raw);bindings.append(b)
    ps=[x.population(name,b,'fastq_reads','fastq_reads'),x.population(name,b,'fastq_bases','fastq_bases'),
        x.population(name,b,'fastq_quality_characters','fastq_bases')]
    for p in ps:p['representation']='emitted_bytes'
    cs=[]
    for metric,value,unit,p in [('fastq_read_count',n,'reads',ps[0]),('fastq_base_count',4*n,'bases',ps[1]),
        ('fastq_min_length',4,'bases',ps[0]),('fastq_max_length',4,'bases',ps[0])]:
        cs.append(x.cell(name,b,len(cs),metric,value,unit,p['id']))
    for i,(symbol,count) in enumerate([('A',n),('C',n),('G',n),('T',n),('N',0),('other_iupac',0),('invalid',0)]):
        cs.append(x.cell(name,b,len(cs),'fastq_symbol_count',count,'bases',ps[1]['id'],row=i,ax=x.axis('symbol',symbol)))
    cs.append(x.cell(name,b,len(cs),'fastq_length_histogram_count',n,'reads',ps[0]['id'],row=0,ax=x.axis('length_closed',None,4,4)))
    cs.append(x.cell(name,b,len(cs),'quality_character_count',4*n,'bases',ps[2]['id'],row=0,ax=x.axis('quality_ascii',None,73,73)))
    d=x.document(name,b,'fastq',ps,cs,[x.section('fastq_summary',cs),x.section('fastq_records',[])])
    d['sequence_records']=[{'id':x.identity('sequence',x.artifact_pointer(name,b)+'/sequences/'+str(i)),
        'artifact_ref':d['artifact']['id'],'ordinal':i,'title':'r'+str(i),'sequence':'ACGT','quality_symbols':'IIII',
        'phred_values':None,'locator':x.loc('fastq_records',i,'record')} for i in range(n)]
    for p in ps:p['member_record_refs']=[r['id'] for r in d['sequence_records']]
    documents.append(d)
declaration={'version':'fastqutils_lineage_declaration_v1','before':x.population_target('before_reads','fastq_reads'),
    'after':x.population_target('after_reads','fastq_reads'),'relation':'successor_population','basis':'explicit_assumption'}
raw=(x.canonical({'association':declaration})+'\n').encode()
(x.HERE/'fixtures/lineage_declaration.json').write_bytes(raw)
decl_content=x.content('lineage195',raw);evidence={'content':decl_content,'pointer':'/association'}
selected={'metadata_id':'retention_assumption','kind':'lineage_declaration','evidence':evidence,'value':declaration}
lineage={'basis':'explicit_source_bound_declaration','metadata_id':'retention_assumption','evidence':evidence,
    'declaration':declaration,'native_lineage_ref':None}
sheet=cp(x.sheet)
sheet.update(documents=documents,document_resolutions=[{'document_id':d['document_id'],
    'selection':{'kind':'output_requirement','requirement_id':d['document_id']},'state':'available',
    'matched_contents':[b],'artifact_ref':d['artifact']['id'],'requirement_refs':[],'diagnostic_codes':[]}
    for d,b in zip(documents,bindings)],associations=[],populations=[p for d in documents for p in d['populations']],
    measurements=[c for d in documents for c in d['cells']],supplied_metadata=[selected],native_lineage=[],requirements=[])
job={'calculation_id':'assumed_read_retention','method':'retention_v1','state':'ready',
    'population_refs':[d['populations'][0]['id'] for d in documents],
    'operand_measurement_refs':[d['cells'][0]['id'] for d in documents],'comparison_kind':'read_retention',
    'quality_thresholds':[],'read_key_rule':None,'lineage_ref':None,'lineage_basis':lineage,
    'requirement_refs':[],'diagnostic_codes':['explicit_lineage_assumption']}
parameters={'version':'fastqutils_calculators_v2','analysis_id':x.ANALYSIS,'calculations':[job]}
cs=[]
for metric,value,unit,num,den in [('read_retention_fraction',0.75,'fraction',6,8),
                               ('removed_count',2,'reads',2,None),('removed_fraction',0.25,'fraction',2,8)]:
    cs.append({'id':x.identity('component','/sheets/'+x.digest(sheet)+'/parameters/'+x.digest(parameters)+
        '/calculations/assumed_read_retention/'+metric+'/none'),
        'calculation_id':'assumed_read_retention','metric':metric,'state':'available','value':value,'unit':unit,
        'method':'retention_v1','population_refs':job['population_refs'],'operand_measurement_refs':job['operand_measurement_refs'],
        'numerator':num,'denominator':den,'threshold':None,'meaning':'derived_descriptive','uncertainty':'not_estimated',
        'parameter_sha256':x.digest(parameters),'diagnostic_codes':['explicit_lineage_assumption'],
        'encoding_basis':None,'lineage_basis':lineage})
result={'schema_version':'fastqutils_components_v2','analysis_id':x.ANALYSIS,'sheet_sha256':x.digest(sheet),
    'parameters':parameters,'components':cs,'requirements':[],'diagnostics':[]}
request={'calculation_id':'assumed_read_retention','method':'retention_v1','comparison_kind':'read_retention',
    'before_population':declaration['before'],'after_population':declaration['after'],
    'before_measurement':x.measurement_target('before_reads','fastq_read_count'),
    'after_measurement':x.measurement_target('after_reads','fastq_read_count')}
sel=x.selection('component',x.components_target('assumed_read_retention','read_retention_fraction'))
fact=x.projected(sel,[x.fact_record('component',x.component_payload(cs[0]),cs[0]['id'],sources=[b['source_ref'] for b in bindings]+[decl_content['source_ref']],
    codes=['explicit_lineage_assumption'])],1)
x.write('ASSUMED_LINEAGE_SHEET_002.json',sheet)
x.write('ASSUMED_LINEAGE_COMPONENTS_002.json',result)
x.write('ASSUMED_LINEAGE_EXAMPLE_002.json',{'identity':'handcrafted_contract_oracle',
    'metadata_binding':{k:v for k,v in selected.items() if k!='value'},
    'supplied_value':{'evidence':evidence,'value':declaration},'calculation_request':request,
    'resolved_job':job,'requested_field':fact,'expected_read_counts':[8,6],'expected_retention':0.75,
    'all_requested_stage_states':'unknown','no_execution_completion_claim':True})
print(x.canonical({'additional_cases':'written','unknown_encoding_read_count':2,
    'unknown_encoding_expected_errors':None,'partial_validated_prefix_read_count':1,
    'assumed_lineage_retention':0.75,'stage_execution':'unknown'}))
