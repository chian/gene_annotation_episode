"""Contract conformance only. Does not import a scientific/runtime implementation."""
from copy import deepcopy as cp
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import quote, unquote
import jsonschema

P=Path(__file__).resolve().parent
S=json.loads((P/'SCHEMAS_004.json').read_text())
D=S['$defs']
checks=[]
def load(name): return json.loads((P/name).read_text())
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def require(condition,code):
    if not condition: raise AssertionError(code)
def finite(v):
    if type(v) is float: require(math.isfinite(v),'nonfinite_json')
    elif type(v) is str: v.encode('utf-8','strict')
    elif type(v) is dict:
        require(all(type(k) is str for k in v),'nonstring_key')
        for value in v.values(): finite(value)
    elif type(v) is list:
        for value in v: finite(value)
    else: require(v is None or type(v) in (int,bool),'not_finite_json')
tc=jsonschema.Draft202012Validator.TYPE_CHECKER.redefine('integer',lambda _,v:type(v) is int)
tc=tc.redefine('number',lambda _,v:type(v) in (int,float) and math.isfinite(v))
Validator=jsonschema.validators.extend(jsonschema.Draft202012Validator,type_checker=tc)
def shape(name,v):
    finite(v)
    Validator({**S,'$ref':'#/$defs/'+name}).validate(v)
def test(name,function): function();checks.append(name)
def reject(name,function):
    try: function()
    except (AssertionError,ValueError,TypeError,UnicodeError,jsonschema.ValidationError):
        checks.append(name);return
    raise AssertionError('expected rejection: '+name)
def read_pointer(v,pointer):
    for token in pointer.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        v=v[int(token)] if type(v) is list else v[token]
    return v
def encoding(b):
    shape('EncodingBasis',b)
    kind=b['basis']
    if kind=='unknown':
        require(b['encoding']=='unknown' and all(b[k] is None for k in ('metadata_id','evidence','declaration','native_locator')),'unknown_encoding_payload')
    elif kind=='explicit_source_bound_declaration':
        require(b['encoding'] in ('phred33','phred64') and b['metadata_id'] is not None and b['evidence'] is not None
            and b['declaration']['encoding']==b['encoding'] and b['declaration']['basis']=='explicit_assumption'
            and b['native_locator'] is None,'declaration_basis_conflict')
    else:
        require(b['encoding']=={'native_bam_phred':'bam_phred','native_sam_phred':'phred33'}[kind]
            and b['native_locator'] is not None and all(b[k] is None for k in ('metadata_id','evidence','declaration')),
            'native_encoding_basis_conflict')
def native(doc):
    shape('NativeDocument',doc)
    a=doc['artifact'];b=a['content_binding']
    require(a['document_id']==doc['document_id'],'document_identity')
    for key,other in [('source_ref','source_ref'),('content_ref','artifact_ref'),('sha256','sha256'),('byte_count','byte_count')]:
        require(a[key]==b[other],'content_binding_conflict')
    poprefs={p['id'] for p in doc['populations']}
    ids=[]
    for collection in ('cells','categories','labels','sequence_records','alignment_records','alignment_headers'):
        for row in doc[collection]:
            ids.append(row['id']);require(row['artifact_ref']==a['id'],'native_artifact_ref')
    require(len(ids)==len(set(ids)),'duplicate_native_identity')
    for c in doc['cells']:
        require(c['population_ref'] is None or c['population_ref'] in poprefs,'cell_population')
    for p in doc['populations']:encoding(p['encoding_basis'])
    for record in doc['alignment_records']:
        if a['actual_format']=='sam_1_6':require(record['native_quality_symbols'] is not None,'sam_quality_token_required')
        if a['actual_format']=='bam_1':require(record['native_quality_symbols'] is None,'bam_has_no_quality_symbols')
def sheet(v):
    shape('Sheet',v)
    require(v['task_ref']==v['original_task']['submission_receipt_ref'],'original_task_ref')
    require(v['original_task']['required_application_id']==v['original_task']['native_application_id']=='FastqUtils','application_identity')
    for d in v['documents']:native(d)
    ids=[r['id'] for key in ('libraries','stages','associations','populations','measurements','categories','requirements','native_lineage') for r in v[key]]
    require(len(ids)==len(set(ids)),'duplicate_sheet_identity')
    populations={p['id'] for p in v['populations']};artifacts={d['artifact']['id'] for d in v['documents']}
    for c in v['measurements']:
        require(c['artifact_ref'] in artifacts and (c['population_ref'] is None or c['population_ref'] in populations),'sheet_cell_relationship')
    original=v['original_task']['submitted_parameters']
    for library in v['libraries']:
        require(library['submitted_value']==read_pointer(original,library['input_pointer']),'original_library_pointer')
    for st in v['stages']:
        require(st['requested_token']==original['recipe'][st['recipe_ordinal']],'original_recipe_occurrence')
        require(st['observed_state']=='unknown','fixture_cannot_claim_stage_completion')
    metadata={m['metadata_id']:m for m in v['supplied_metadata']}
    for p in v['populations']:
        encoding(p['encoding_basis'])
        b=p['encoding_basis']
        if b['basis']=='explicit_source_bound_declaration':
            m=metadata[b['metadata_id']]
            require(m['value']==b['declaration'] and m['evidence']==b['evidence'],'sheet_assumption_preservation')
def components(v,s):
    shape('Components',v);require(v['sheet_sha256']==digest(s),'saved_sheet_hash')
    ph=digest(v['parameters']);ms={c['id'] for c in s['measurements']};ps={p['id'] for p in s['populations']}
    jobs={j['calculation_id']:j for j in v['parameters']['calculations']}
    for c in v['components']:
        require(c['parameter_sha256']==ph and c['calculation_id'] in jobs,'component_parameters')
        require(set(c['operand_measurement_refs'])<=ms and set(c['population_refs'])<=ps,'component_reference')
        if c['encoding_basis'] is not None:encoding(c['encoding_basis'])
        if c['lineage_basis'] is not None:
            b=c['lineage_basis'];require(b==jobs[c['calculation_id']]['lineage_basis'],'lineage_basis_preserved')
            if b['basis']=='explicit_source_bound_declaration':
                selected=next(m for m in s['supplied_metadata'] if m['metadata_id']==b['metadata_id'])
                require(selected['value']==b['declaration'] and selected['evidence']==b['evidence'],'lineage_source_preserved')
def available(row):
    if row['state']!='available' or row['payload'] is None:return False
    p=row['payload']
    if row['kind'] in ('measurement','component'):return p['state']=='available' and type(p['value']) in (int,float) and math.isfinite(p['value'])
    if row['kind']=='population':return p['scope']=='complete'
    if row['kind']=='association':return p['state']=='established'
    return True
def projected(v):
    shape('ProjectedField',v);s=v['selection'];n=v['matched_count'];rows=v['records']
    if s['cardinality']=='one_target':
        require(s['expected_cardinality']==1,'one_target_expected_one')
        require(len(rows)==(1 if n==0 else n),'one_target_envelope_cardinality')
        if n==0:require(rows[0]['record_ref'] is None and rows[0]['payload'] is None and rows[0]['state']!='available','fabricated_absent_fact')
        cardinality_ok=n<=1
    else:
        require(len(rows)==n and all(r['record_ref'] is not None for r in rows),'exact_rows_are_actual_records')
        cardinality_ok=n==s['expected_cardinality']
        if n==0 and 'missing_artifact' in v['diagnostic_codes']:cardinality_ok=False
    for r in rows:
        require(r['kind']==s['target']['kind'],'fact_family_conflict')
        if r['payload'] is None:require(r['record_ref'] is None and r['state']!='available','null_actual_payload')
    expected=cardinality_ok and (s['availability_requirement']=='typed_state' or all(available(r) for r in rows))
    require(v['satisfied']==expected,'availability_or_cardinality_conflict')
    require((v['state']=='satisfied')==v['satisfied'],'satisfaction_state_conflict')
def refs(v):
    if isinstance(v,dict):
        if '$ref' in v:yield v['$ref']
        for x in v.values():yield from refs(x)
    elif isinstance(v,list):
        for x in v:yield from refs(x)

for name in ['SCHEMAS_002.json','SCHEMAS_003.json','SCHEMAS_004.json']:
    test('schema-valid:'+name,lambda name=name:jsonschema.Draft202012Validator.check_schema(load(name)))
test('all-local-definition-references-resolve',lambda:require(all(r.startswith('#/$defs/') and r[8:] in D for r in refs(S)),'unresolved_schema_ref'))
for name,definition in [('ORIGINAL_TASK_002.json','Host_OriginalTask'),('RESULT_SELECTOR_PRE_DOWNLOAD_002.json','Host_ResultSelector'),
    ('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json','Host_ArtifactBundle'),('SUPPLIED_VALUES_002.json',None),
    ('PROVIDER_PARAMETERS_002.json','ProviderParameters'),('POSSESSED_PARAMETERS_002.json','ProviderParameters'),
    ('REQUESTED_FORM_002.json','RequestedForm'),('EXPECTED_METADATA_002.json','Metadata'),('EXPECTED_FACTS_002.json','Facts'),
    ('EXPECTED_PROVIDER_RESULT_002.json','ProviderResult')]:
    test('shape:'+name,lambda name=name,definition=definition:shape(definition,load(name)) if definition else [shape('SuppliedValue',v) for v in load(name)])
for name in ['EXPECTED_NATIVE_DOCUMENTS_002.json']:
    test('native:'+name,lambda:[native(v) for v in load(name)])
test('partial-native-document',lambda:native(load('PARTIAL_NATIVE_DOCUMENT_002.json')))
for prefix in ['EXPECTED','UNAVAILABLE','ASSUMED_LINEAGE']:
    a=load(prefix+'_SHEET_002.json');b=load(prefix+'_COMPONENTS_002.json')
    test('sheet:'+prefix,lambda a=a:sheet(a));test('components:'+prefix,lambda a=a,b=b:components(b,a))
facts=load('EXPECTED_FACTS_002.json')
for field,value in facts.items():test('requested-field:'+field,lambda value=value:projected(value))
for case in load('UNAVAILABLE_AND_PARTIAL_002.json'):
    test('missing-partial:'+case['name'],lambda case=case:projected(case['expected']))
assumed=load('ASSUMED_LINEAGE_EXAMPLE_002.json')
test('explicit-lineage-assumption-typed-return',lambda:projected(assumed['requested_field']))
selector=load('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
test('actual-requested-json-schema',lambda:Validator(selector['requested_schema']).validate(facts))
test('immutable-semantic-descriptors',lambda:require(all(selector['requested_schema']['properties'][k]['x-bvbrc-fastqutils']==v['selection'] for k,v in facts.items()),'original_selection_changed'))
provider=selector['adapter']['parameters'];bundle=load('ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json')
test('no-future-output-identity-at-commission',lambda:require(all(d['selection']['kind']=='output_requirement' for d in provider['documents']) and
    not any(a['sha256'] in canonical(provider) for a in bundle['artifacts']) and 'record_ref' not in canonical(provider),'future_artifact_identity_required'))
test('bundle-bound-original-selector',lambda:require(bundle['requested_selector_sha256']==digest(selector),'selector_hash'))
test('exact-possessed-selection',lambda:require(load('POSSESSED_PARAMETERS_002.json')['documents'][0]['selection']['content']==load('EXPECTED_NATIVE_DOCUMENTS_002.json')[0]['artifact']['content_binding'],'possessed_binding'))
errors=load('ERROR_SHAPES_002.json')
for key,definition in [('contract_failure','ContractFailure'),('native_requirement','Requirement'),
    ('host_requirement','Host_AcquisitionRequirement'),('native_diagnostic','Diagnostic'),('host_diagnostic','Host_Diagnostic')]:
    test('exact-error-shape:'+key,lambda key=key,definition=definition:shape(definition,errors[key]))
test('saved-projection-failure-context-retained',lambda:require(load('EXPECTED_PROVIDER_RESULT_002.json')['components']['projection_failure_context']==
    {'requirements':load('EXPECTED_SHEET_002.json')['requirements'],'diagnostics':[]},'failure_context_loss'))
for supplied in load('SUPPLIED_VALUES_002.json'):
    evidence=supplied['evidence'];raw=(P/'fixtures/metadata.json').read_bytes()
    test('source-pointer:'+evidence['pointer'],lambda supplied=supplied,evidence=evidence,raw=raw:require(
        hashlib.sha256(raw).hexdigest()==evidence['content']['sha256'] and len(raw)==evidence['content']['byte_count']
        and read_pointer(json.loads(raw),evidence['pointer'])==supplied['value'],'source_pointer_conflict'))
test('lineage-declaration-source-pointer',lambda:require(read_pointer(json.loads((P/'fixtures/lineage_declaration.json').read_bytes()),
    assumed['supplied_value']['evidence']['pointer'])==assumed['supplied_value']['value'],'lineage_pointer'))
for vector in load('IDENTITY_VECTORS_002.json'):
    expected='bvbrc_fastqutils_'+vector['kind']+':'+quote(vector['analysis_id'],safe='')+'/'+quote(vector['pointer'],safe='')
    test('identity-vector:'+vector['kind'],lambda vector=vector,expected=expected:require(vector['encoded']==expected and
        unquote(expected.split('/',1)[1],errors='strict')==vector['pointer'],'identity_roundtrip'))
test('all62-retained-metrics',lambda:require([r['metric'] for r in load('METRIC_SPECS_002.json')['metrics']]==D['Cell']['properties']['metric']['enum'],'metric_scope_lost'))
test('all17-retained-components',lambda:require([r['metric'] for r in load('COMPONENT_SPECS_002.json')['components']]==D['Component']['properties']['metric']['enum'],'component_scope_lost'))

# Mutations reject implementation shortcuts, rather than merely echoing schema.
bad=cp(load('EXPECTED_SHEET_002.json'));bad['measurements'][0]['value']=True
reject('bool-is-not-read-count',lambda:sheet(bad))
bad_nan=cp(load('EXPECTED_SHEET_002.json'));bad_nan['measurements'][0]['value']=float('nan')
reject('nonfinite-is-not-number',lambda:sheet(bad_nan))
bad_absent=cp(facts['qc_status']);bad_absent['records'][0]['payload']={'value':'pass'}
reject('missing-category-cannot-fabricate-pass',lambda:projected(bad_absent))
bad_satisfied=cp(load('UNAVAILABLE_AND_PARTIAL_002.json')[0]['expected']);bad_satisfied.update(satisfied=True,state='satisfied')
reject('available-required-cannot-pass-missing',lambda:projected(bad_satisfied))
bad_flag=cp(load('SUPPLIED_VALUES_002.json')[1]['value']);bad_flag['completed']=True
reject('caller-completed-flag-not-metadata',lambda:shape('AssociationAssertion',bad_flag))
bad_verified=cp(load('SUPPLIED_VALUES_002.json')[0]['value']);bad_verified['basis']='verified'
reject('encoding-assumption-is-not-verification',lambda:shape('EncodingDeclaration',bad_verified))
bad_source=cp(load('EXPECTED_SHEET_002.json'));bad_source['populations'][0]['encoding_basis']['evidence']['pointer']='/declarations/1'
reject('declaration-source-pointer-must-match',lambda:sheet(bad_source))
bad_hash=cp(load('EXPECTED_COMPONENTS_002.json'));bad_hash['sheet_sha256']='0'*64
reject('saved-sheet-hash-conflict',lambda:components(bad_hash,load('EXPECTED_SHEET_002.json')))
bad_stage=cp(load('ASSUMED_LINEAGE_SHEET_002.json'));bad_stage['stages'][0]['observed_state']='completed'
reject('assumption-cannot-complete-stage',lambda:sheet(bad_stage))
bad_rows=cp(next(c['expected'] for c in load('UNAVAILABLE_AND_PARTIAL_002.json') if c['name']=='excess_source_rows_retained_no_first_two'))
bad_rows['records']=bad_rows['records'][:2]
reject('excess-rows-cannot-be-truncated',lambda:projected(bad_rows))
unnamed=cp(load('EXPECTED_NATIVE_DOCUMENTS_002.json')[0]);unnamed['artifact']['native_name']=None
test('003-native-name-null-preserved',lambda:native(unnamed))
sam_basis={'basis':'native_sam_phred','encoding':'phred33','metadata_id':None,'evidence':None,'declaration':None,
    'native_locator':{'member':None,'block':'bam_records','block_ordinal':0,'row_ordinal':0,'field':'QUAL','byte_start':None,'byte_end':None}}
test('003-sam-encoding-is-native',lambda:encoding(sam_basis))
bad_sam=cp(sam_basis);bad_sam['encoding']='unknown'
reject('sam-format-encoding-is-not-unknown',lambda:encoding(bad_sam))

receipt={'kind':'schema_and_contract_fixture_conformance_only','schema':'SCHEMAS_004.json',
    'schema_sha256':hashlib.sha256((P/'SCHEMAS_004.json').read_bytes()).hexdigest(),
    'passed':len(checks),'failed':0,'checks':checks,'scientific_parsers_executed':0,
    'scientific_calculators_executed':0,'live_submissions':0,'runtime_custody_tested':False,
    'episode_communication_tested':False}
(P/'CONFORMANCE_RECEIPT_002.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'failed':0,'scope':receipt['kind']}))
