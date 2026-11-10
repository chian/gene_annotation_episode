"""Frozen A103 inputs and receipt-time publication over the shared HPC service."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import zlib

from .communication import plain
from .domain import canonical
from .a103_scoring import VERSION as SCIENTIFIC_PROFILE, digest, require
from .a103_hpc_worker import VERSION as NATIVE_VERSION
from .a103_native_requests import prepare, publish_result
from .hpc_result_receipts import planned_input_files


VERSION = 'a103_shared_hpc_custody_v1'
REQUEST_PROVIDER = 'host.a103.hpc_request'
RESULT_PROVIDER = 'host.a103.hpc_admission'
SOURCES = ('__init__.py','a103_scoring.py','a103_detection.py','comparative_ops.py',
    'acquisition.py','public_configuration.py','domain.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def install(store):
    for table in ('a103_hpc_requests','a103_hpc_results'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+' (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')


def source(store,provider,body):
    artifact = store.artifact(canonical(body),'application/json')
    return store.put('source',{'provider':provider,'accession':digest(body),'uri':None,
        'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':VERSION,
        'retrieved_at':None,'operand_refs':body['scope']['subject_refs']},origin='tool')['id']


def registered(store,reference,table,provider):
    row = store.get(reference)
    if row.get('provider')!=provider:return None
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone()
    saved = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?',(reference,)).fetchone() if exists else None
    require(saved is not None and row['origin']=='tool' and row['version']==VERSION,'a103_original_hpc_grant_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(row['artifact_ref']))==body,'a103_hpc_custody_conflict')
    return body


def request_body(store,reference):
    return registered(store,reference,'a103_hpc_requests',REQUEST_PROVIDER)


def result_body(store,reference):
    return registered(store,reference,'a103_hpc_results',RESULT_PROVIDER)


def existing_local(store,operation,args,scope,known):
    """Reuse only actual received numerical publications, never private output."""
    from .a103_publication import received_measurement
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='a103_operations'").fetchone()
    if not exists:return []
    for row in store.db.execute('SELECT request,result FROM a103_operations ORDER BY rowid'):
        request,outcome = json.loads(row['request']),json.loads(row['result'])
        if (request.get('name')!=operation or request.get('args')!=args or request.get('scope')!=scope
                or outcome.get('status')!='completed' or not set(outcome['record_refs'])<=known):continue
        if any((measurement:=received_measurement(store,ref)) is not None
                and measurement['body']['producer_operation']==operation for ref in outcome['record_refs']):
            return list(outcome['record_refs'])
    return []


def freeze(registry,operation,args,resource_id,*,context,scope,known,invocation):
    import Bio
    store = registry.store
    install(store)
    plan = prepare(registry,operation,args,context=context,scope=scope,known=known,invocation=invocation)
    assets = {}
    for field,asset in plan['assets'].items():
        raw = Path(asset['path']).read_bytes()
        identity = asset['identity']
        require(len(raw)==identity['byte_length'] and sha(raw)==identity['sha256'],'a103_hpc_original_input_bytes_conflict')
        assets[field] = {'bytes_base64':base64.b64encode(raw).decode(),'sha256':sha(raw),
            'byte_length':len(raw),'source_ref':asset['source_ref'],'identity':identity}
        plan['native_request'][field] = None
        plan['assets'][field] = {key:value for key,value in asset.items() if key!='path'}
    directory = Path(__file__).parent
    sources = {'gene_annotation_episode/'+name:(directory/name).read_text() for name in SOURCES}
    snapshot = canonical(sources)+'\n'
    worker = (directory/'a103_hpc_worker.py').read_text()
    manifest = {name:sha(text.encode()) for name,text in sources.items()}
    manifest['a103-worker.py'] = sha(worker.encode())
    logical = digest({'operation':operation,'arguments':args,'scope':scope,'profile':SCIENTIFIC_PROFILE,
        'updates':plan['updates'],'target_mapping':plan['target_mapping']})
    request = {'version':NATIVE_VERSION,'scientific_profile':SCIENTIFIC_PROFILE,'biopython_version':Bio.__version__,
        'plan':plan,'assets':assets,'code_manifest':manifest,'code_manifest_sha256':sha(canonical(manifest).encode()),
        'source_snapshot_sha256':sha(snapshot.encode())}
    raw = (canonical(request)+'\n').encode()
    body = {'version':VERSION,'run_id':context.run_id,'scope':plain(scope),'operation':operation,
        'logical_work_sha256':logical,'request':request,'request_sha256':sha(raw),
        'worker_sha256':manifest['a103-worker.py'],'code_manifest_sha256':request['code_manifest_sha256'],
        'resource_id':resource_id,'evidence_refs':plan['evidence_refs'],
        'files':{'a103-worker.py':worker,'a103-sources.json':snapshot,'a103-request.json':raw.decode()}}
    with store.transaction():
        reference = source(store,REQUEST_PROVIDER,body)
        store.db.execute('INSERT OR IGNORE INTO a103_hpc_requests VALUES(?,?)',(reference,canonical(body)))
    return reference,body


def commission(body,resources):
    from .hpc_scientific_commission import commission as describe
    request = body['request']
    native = request['plan']['native_request']
    return describe(resource_id=body['resource_id'],resource=resources[body['resource_id']],
        tool='a103.'+native['operation'],request_sha256=body['request_sha256'],worker_sha256=body['worker_sha256'],
        implementation_sha256=body['code_manifest_sha256'],parameters={'operation':body['operation'],'profile':SCIENTIFIC_PROFILE},
        files=body['files'],worker_name='a103-worker.py',request_name='a103-request.json',
        program='a103_gene_context_native',version=NATIVE_VERSION,
        features={'input_bytes':sum(asset['byte_length'] for asset in request['assets'].values()),
            'retained_input_bytes':len(canonical(native).encode()),
            'panel_rows':len(native.get('rows',[])),'binding_count':len(native.get('bindings',[])),
            'query_symbols':len(native.get('query_sequence',''))},
        preparation='Prepare the resource and execute this declared gene-context request. Choose the '
            'scripts, environment and commands needed for jsonschema and Biopython '
            +request['biopython_version']+', preserving its actual inputs, software identity and '
            'scientific output contract. Keep environment and temporary files within the assigned '
            'workspace. Gene-context calculations run on allocated compute nodes; retain the original '
            'result in HPC_UNIT_DIRECTORY.',
        objective='Execute this exact A103 investigation over its declared genomic records, loci, panels '
            'or completed detection output. Preserve unknowns, missing identity, sampling dependence and '
            'original scope. No particular association or function is expected. Return original scientific '
            'measurements; HPC operational acceptance is separate from A103 credit.')


def admit(registry,expected,hpc_ref,*,context,known,reader):
    store = registry.store
    require(expected['run_id']==context.run_id,'a103_hpc_receiving_run_conflict')
    require(set(expected['evidence_refs'])<=known,'a103_hpc_original_operands_not_received')
    authority = reader(context,hpc_ref)
    receipt,plan,unit = authority['receipt'],authority['plan'],authority['unit']
    result = receipt['document']
    require(receipt['scope']==expected['scope'],'a103_hpc_original_scope_conflict')
    workspace = plan['manifest']['workspace']
    staged = {row['path']:row for row in planned_input_files(plan)}
    require(all(workspace+'/'+name in staged and staged[workspace+'/'+name]['sha256']==sha(text.encode())
        for name,text in expected['files'].items()),'a103_hpc_original_staged_files_conflict')
    require(authority['resource_id']==expected['resource_id'] and unit['argv']==[
        authority['resource']['python_executable'],'-B',workspace+'/a103-worker.py',workspace+'/a103-request.json'],
        'a103_hpc_original_command_conflict')
    require(result.get('program')=='a103_gene_context_native' and result.get('version')==NATIVE_VERSION
        and result.get('request_sha256')==expected['request_sha256']
        and result.get('worker_sha256')==expected['worker_sha256']
        and result.get('code_manifest_sha256')==expected['code_manifest_sha256']
        and result.get('pbs_job_id')==receipt['job_id'] and result.get('compute_hostname')
        and not result['compute_hostname'].startswith(('aurora-uan','login')),'a103_hpc_original_identity_conflict')
    require(result['returncode']==receipt['unit']['returncode'],'a103_hpc_execution_outcome_conflict')
    records = []
    if result['completed']:
        require(result['returncode']==0 and result['scientific_profile']==SCIENTIFIC_PROFILE
            and result['biopython_version']==expected['request']['biopython_version']
            and result['payload_encoding']=='zlib_base64','a103_hpc_qualified_native_result_required')
        decoder = zlib.decompressobj()
        raw = decoder.decompress(base64.b64decode(result['payload'],validate=True),128*1024**2)
        require(decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
            and sha(raw)==result['payload_sha256'],'a103_hpc_original_payload_conflict')
        native = json.loads(raw)
        require(native['producer_operation']==expected['operation'],'a103_hpc_original_operation_conflict')
        # Use the same host augmentation, original numerical publisher and
        # per-use attachment refresh. No context job or search runs here.
        records,_ = publish_result(registry,expected['request']['plan'],native)
    else:
        require(result['returncode']!=0 and result.get('failure'),'a103_hpc_original_failure_reason_required')
    body = {'version':VERSION,'scope':expected['scope'],'request_ref':expected['source_ref'],
        'logical_work_sha256':expected['logical_work_sha256'],'hpc_result_ref':hpc_ref,
        'hpc_source_artifact_ref':authority['source_artifact_ref'],'pbs_job_id':receipt['job_id'],
        'operation':expected['operation'],'completed':result['completed'],'failure':result.get('failure'),
        'python_version':result.get('python_version'),'measurement_refs':records,
        'scientific_credit':'existing_A103_measurement_and_per_use_attribution; not_HPC_acceptance'}
    reference = source(store,RESULT_PROVIDER,body)
    store.db.execute('INSERT OR IGNORE INTO a103_hpc_results VALUES(?,?)',(reference,canonical(body)))
    return [reference,*records]


def receive(registry,context,known,*,reader):
    store = registry.store
    requests = {body['request_sha256']:{**body,'source_ref':ref} for ref in known
        if (body:=request_body(store,ref)) is not None}
    completed = {(body['request_ref'],body['hpc_result_ref']) for ref in known
        if (body:=result_body(store,ref)) is not None}
    generated,needs = [],[]
    for reference in sorted(known):
        record = store.get(reference)
        if record.get('provider')!='episode.hpc_result':continue
        document = json.loads(store.get_artifact(record['artifact_ref'])).get('document',{})
        request = requests.get(document.get('request_sha256'))
        if document.get('program')!='a103_gene_context_native' or request is None:continue
        if (request['source_ref'],reference) in completed:continue
        missing = set(request['evidence_refs'])-known
        if missing:
            body = {'version':VERSION,'scope':request['scope'],'request_ref':request['source_ref'],
                'hpc_result_ref':reference,'operation':request['operation'],'status':'pending_attribution',
                'missing_record_refs':sorted(missing),'scientific_credit':0.}
            generated.append(source(store,'host.a103.hpc_pending_attribution',body))
            for target in request['scope']['subject_refs']:
                needs.append((request['source_ref'],{'target_ref':target,'policy':'a103_received_hpc_context',
                    'missing':['original_received_context_operands'],'required_operands':{'source_refs':sorted(missing)}}))
            continue
        try:
            with store.transaction():
                received = admit(registry,request,reference,context=context,known=known,reader=reader)
            generated.extend(received)
        except (ValueError,KeyError,OSError,TypeError) as error:
            body = {'version':VERSION,'scope':request['scope'],'request_ref':request['source_ref'],
                'hpc_result_ref':reference,'operation':request['operation'],'status':'scientific_admission_unavailable',
                'reason':str(error),'scientific_credit':0.}
            generated.append(source(store,'host.a103.hpc_admission_failure',body))
    return list(dict.fromkeys(generated)),needs


def execution_findings(store,context,known):
    findings = []
    for reference in sorted(known):
        record = store.get(reference)
        if record.get('provider')==RESULT_PROVIDER:
            body = result_body(store,reference)
        elif record.get('provider') in {'host.a103.hpc_pending_attribution','host.a103.hpc_admission_failure'}:
            require(record['origin']=='tool' and record['version']==VERSION,'a103_hpc_status_source_required')
            body = json.loads(store.get_artifact(record['artifact_ref']))
        else:continue
        if not (store.scope_contains(plain(context.scope),body['scope']) or store.scope_contains(body['scope'],plain(context.scope))):continue
        findings.append({'source_ref':reference,'receiving_scope':plain(context.scope),**deepcopy(body)})
    admissions = {(row['request_ref'],row['hpc_result_ref']):row['source_ref'] for row in findings if 'completed' in row}
    for row in findings:
        replacement = admissions.get((row['request_ref'],row['hpc_result_ref']))
        row['current'] = 'status' not in row or replacement is None
        if not row['current']:row['resolved_by_admission_ref'] = replacement
    return findings
