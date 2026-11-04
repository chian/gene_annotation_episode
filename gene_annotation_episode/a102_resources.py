"""Structural execution, monitoring and collection in existing resource roles.

The science episode supplies an exact structural job. Launch children execute
that job, return a checked receiving handle, and results children explicitly
collect its native numerical publications. A handoff alone earns no A102 B.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

from .a102_publication import received_grade
from .a102_scoring import digest,require
from .a102_tools import A102ToolRegistry,catalog
from .communication import plain
from .domain import ContractError,canonical,identity,obj,validate_schema
from .episode_return_records import EpisodeReturnRecords
from .native_lifecycle import NativeJobHandle,status as native_status
from .resource_records import HANDOFF_SCHEMA,LAUNCH_VERSION,RESULTS_VERSION


VERSION='a102_structural_resource_adapter_v1'


def now():return datetime.now(timezone.utc).isoformat()


class A102ResourceAdapter:
    def __init__(self,tools,store,run_id):
        require(isinstance(tools,A102ToolRegistry) and tools.store is store,'a102_resource_registry_required')
        self.tools,self.store,self.run_id=tools,store,run_id
        self.records=EpisodeReturnRecords(store,run_id,failure_prefix='a102_resource_')
        config={'software':tools.a102_software,'directory':str(tools.a102_directory),'policy':tools.a102_policy.to_dict()}
        self.registry_ref=identity('execution_registry',config)
        self.resource_id=identity('resource_binding',{'registry':self.registry_ref,
            'host':tools.local_resources.snapshot()['resource_id']})
        for sql in (
            '''CREATE TABLE IF NOT EXISTS a102_resource_jobs (job_ref TEXT PRIMARY KEY,run_id TEXT,
                request TEXT,scope TEXT,owner_episode_id TEXT,owner_path TEXT,native_operation_key TEXT,
                state TEXT,outcome TEXT,handoff TEXT,handoff_source_ref TEXT)''',
            '''CREATE TABLE IF NOT EXISTS a102_handoff_deliveries (run_id TEXT,episode_id TEXT,job_ref TEXT,
                PRIMARY KEY(run_id,episode_id,job_ref))''',
        ):store.db.execute(sql)

    def as_record(self):
        return {'version':VERSION,'resource_id':self.resource_id,'registry_ref':self.registry_ref,
            'software':deepcopy(self.tools.a102_software),'directory':str(self.tools.a102_directory),
            'policy':self.tools.a102_policy.to_dict(),
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def selection(self):
        return {'resource_id':self.resource_id,'kind':'local','allocation':{'cpu':1,**self.tools.a102_policy.to_dict()},
            'capability_binding_ref':self.registry_ref}

    def capability(self):
        return {'resource_id':self.resource_id,'kind':'local','availability':
            'available' if any(self.tools.a102_software.values()) else 'unavailable',
            'observed_at':now(),'provenance_refs':[self.registry_ref],'knowledge_entry_ids':[],
            'tool_names':['a102.native.execute','a102.native.status','a102.native.collect'],
            'allocation_limits':self.selection()['allocation'],'local_resources':self.tools.local_resources.snapshot()}

    def _job(self,reference):
        row=self.store.db.execute('SELECT * FROM a102_resource_jobs WHERE job_ref=? AND run_id=?',
            (reference,self.run_id)).fetchone()
        require(row is not None,'a102_resource_job_unavailable')
        return row

    def _handoff(self,value):
        validate_schema(value,HANDOFF_SCHEMA);row=self._job(value['execution_handle'])
        require(row['handoff'] is not None and json.loads(row['handoff'])==value
            and value['resource_selection']==self.selection(),'a102_resource_handoff_conflict')
        return row

    def _delivery(self,context,handle):
        row=self._job(handle)
        require(self.store.db.execute('SELECT 1 FROM a102_handoff_deliveries WHERE run_id=? AND episode_id=? AND job_ref=?',
            (self.run_id,context.episode_id,handle)).fetchone() is not None,'a102_resource_handoff_not_received')
        self.store.validate_scope(json.loads(row['scope']),parent_scope=plain(context.scope))
        return row

    def prepare_assignment(self,parent,role,launch_assignment,scope,operation_key):
        value=plain(launch_assignment)
        if role=='results':
            row=self._handoff(value['handoff']);self._delivery(parent,row['job_ref'])
            self.store.validate_scope(scope,parent_scope=json.loads(row['scope']))
            selector=value['requested_data_selector']
            require(not set(selector)-{'source_refs'},'a102_resource_selector_invalid')
            if selector:
                require(isinstance(selector['source_refs'],list) and
                    set(selector['source_refs'])<=set(json.loads(row['outcome'])['record_refs']),
                    'a102_resource_selector_outside_original_results')
            value['adapter_assignment']={'version':'a102_structural_results_assignment_v1','job_ref':row['job_ref'],
                'handoff_source_ref':row['handoff_source_ref'],'scope_sha256':digest(scope),
                'original_job_request_sha256':digest(json.loads(row['request']))}
            return value
        require(role=='launch_local' and value['resource_selection']==self.selection(),
            'a102_resource_local_selection_required')
        for key,amount in value['resource_selection']['allocation'].items():
            require(key not in value['constraints'] or value['constraints'][key]==amount,
                'a102_resource_allocation_conflict')
        job=value['job_request']
        require(set(job)=={'operation','arguments'} and job['operation'] in {'structure.align','structure.discover','structure.reference_align'},
            'a102_resource_explicit_structural_job_required')
        validate_schema(job['arguments'],catalog()[job['operation']]['input_schema'])
        args=job['arguments'];known=set(parent.received_record_refs)
        self.tools._binding(args['measured_binding_ref'] if job['operation']=='structure.reference_align' else args['target_binding_ref'],known,scope)
        references=([args['reference_binding_ref']] if job['operation'] in {'structure.align','structure.reference_align'}
            else args['reference_binding_refs'])
        for ref in references:self.tools._binding(ref,known,scope)
        for row in value['immutable_input_versions']:
            record=self.tools._received(row['reference'],known)
            if row['version'] is not None:
                require(row['version']==str(record.get('version',record.get('revision'))),
                    'a102_resource_input_version_conflict')
            if row['content_sha256'] is not None:
                artifact=record.get('artifact_ref',record.get('sequence_ref'))
                require(artifact is not None and hashlib.sha256(self.store.get_artifact(artifact)).hexdigest()==row['content_sha256'],
                    'a102_resource_input_digest_conflict')
        reference=identity('resource_execution',{'run_id':self.run_id,'operation_key':operation_key,'job':job,'scope':scope})
        serialized=canonical(job)
        old=self.store.db.execute('SELECT request FROM a102_resource_jobs WHERE job_ref=?',(reference,)).fetchone()
        require(old is None or old['request']==serialized,'a102_resource_job_identity_conflict')
        self.store.db.execute('INSERT OR IGNORE INTO a102_resource_jobs VALUES(?,?,?,?,NULL,NULL,NULL,?,NULL,NULL,NULL)',
            (reference,self.run_id,serialized,canonical(scope),'prepared'))
        value['adapter_assignment']={'job_ref':reference}
        return value

    def catalog(self,context):
        names=['a102.native.status','a102.native.execute','a102.native.collect']
        return [{'name':name,'description':{
            'a102.native.execute':'In launch_local, execute only the original immutable structural job using shared local admission. Return a checked receiving handoff; scientific results require explicit collection.',
            'a102.native.status':'Read the actual assigned job state and native measurements. This read launches no job and delivers no scientific grades.',
            'a102.native.collect':'In results, collect only the requested already completed native structural results through the original checked handoff. Complete native comparisons already have automatic A102 graders.'}[name],
            'input_schema':obj({})} for name in names]

    async def execute(self,context,tool_name,arguments,operation_key):
        self.records.authenticate(context)
        row=self._job(context.assignment['adapter_assignment']['job_ref'])
        self.store.validate_scope(plain(context.scope),parent_scope=json.loads(row['scope']))
        if tool_name=='a102.native.execute':
            require(context.role=='launch_local','a102_resource_launch_role_required')
            if row['outcome'] is None:
                job=json.loads(row['request'])
                native_key=row['native_operation_key'] or operation_key
                self.store.db.execute('UPDATE a102_resource_jobs SET owner_episode_id=?,owner_path=?,native_operation_key=?,state=? WHERE job_ref=?',
                    (context.episode_id,canonical(plain(context.path)),native_key,'running',row['job_ref']))
                invocation=self.tools._current_invocation.get()
                require(invocation is not None and invocation[0].episode_id==context.episode_id,
                    'a102_resource_current_action_required')
                with self.tools.current_invocation(context,read_received=invocation[1],tool_name=job['operation'],
                        arguments=job['arguments'],operation_key=native_key):
                    outcome=await self.tools.execute_async(job['operation'],job['arguments'],scope=plain(context.scope),
                        operation_key=native_key,permitted_record_refs=context.received_record_refs)
                if outcome['status']!='completed':
                    self.store.db.execute('UPDATE a102_resource_jobs SET state=? WHERE job_ref=?',
                        ('prepared' if (outcome.get('feedback') or {}).get('retryable') else 'failed',row['job_ref']))
                    return outcome
                receiving={'provider_id':self.resource_id,'target_handle':row['job_ref'],
                    'contract_ref':identity('resource_interface',{'registry_ref':self.registry_ref,'kind':'a102_native_results_v1'})}
                handoff={'version':'execution_handoff_v1','execution_handle':row['job_ref'],
                    'resource_selection':self.selection(),
                    'submitted_input_versions':plain(context.assignment['immutable_input_versions']),
                    'monitoring':receiving,'results':receiving,'checked_at':now(),
                    'check_record_refs':[identity('handoff_receipt',{'job_ref':row['job_ref'],'outcome_sha256':digest(outcome)})],
                    'state':'usable','failure':None}
                metadata=self.tools._source('native.a102.structural_handoff',{'handoff':handoff})
                self.store.db.execute('UPDATE a102_resource_jobs SET state=?,outcome=?,handoff=?,handoff_source_ref=? WHERE job_ref=?',
                    ('completed',canonical(outcome),canonical(handoff),metadata,row['job_ref']))
                row=self._job(row['job_ref'])
            result={'handoff':json.loads(row['handoff']),'state':row['state']};references=[row['handoff_source_ref']]
        elif tool_name=='a102.native.collect':
            require(context.role=='results','a102_resource_results_role_required')
            require(row['state']=='completed' and row['outcome'] is not None,'a102_resource_results_unavailable')
            outcome=json.loads(row['outcome']);selected=context.assignment['requested_data_selector'].get('source_refs')
            references=outcome['record_refs'] if selected is None else list(selected)
            require(set(references)<=set(outcome['record_refs']),'a102_resource_results_selector_conflict')
            result={'native_result':outcome['result'],'collected_record_refs':references,
                'original_native_execution':outcome.get('native_execution')}
        else:
            references=[];result={'job_ref':row['job_ref'],'state':row['state'],
                'native_execution':None if row['outcome'] is None else json.loads(row['outcome']).get('native_execution')}
        return {'status':'completed','record_refs':references,'changed_record_refs':[],'result':result,'feedback':None}

    def facts(self,context,completion_snapshot):
        own=self.store.db.execute('SELECT handoff FROM a102_resource_jobs WHERE run_id=? AND owner_episode_id=? AND handoff IS NOT NULL',
            (self.run_id,context.episode_id)).fetchall()
        delivered=self.store.db.execute('SELECT jobs.handoff FROM a102_handoff_deliveries deliveries '
            'JOIN a102_resource_jobs jobs USING(job_ref) WHERE deliveries.run_id=? AND deliveries.episode_id=?',
            (self.run_id,context.episode_id)).fetchall()
        handoffs={row[0]:json.loads(row[0]) for row in [*own,*delivered] if row[0]}
        if context.role=='results':
            value=plain(context.assignment['handoff']);self._handoff(value);handoffs[canonical(value)]=value
        return {'execution_handoffs':list(handoffs.values())}

    def fact_sources(self,role):return {}

    def resolve(self,context,reference,namespace):
        if reference in {self.resource_id,self.registry_ref}:return True
        for handoff in self.facts(context,{})['execution_handoffs']:
            if reference in {handoff['execution_handle'],*handoff['check_record_refs'],handoff['results']['contract_ref'],handoff['checked_at']}:return True
        return False

    def validate_report(self,context,form,original_schema):pass

    def received_form_references(self,context,handoff,schema,operation_key):
        row=self._handoff(plain(handoff));owner=json.loads(row['owner_path'])
        self.store.validate_scope(json.loads(row['scope']),parent_scope=plain(context.scope))
        path=plain(context.path)
        require(len(path)<len(owner) and owner[:len(path)]==path,'a102_resource_handoff_owner_conflict')
        self.store.db.execute('INSERT OR IGNORE INTO a102_handoff_deliveries VALUES(?,?,?)',
            (self.run_id,context.episode_id,row['job_ref']))
        return [row['handoff_source_ref']]

    def initial_references(self,context):
        if context.role!='results':return []
        return [self._handoff(plain(context.assignment['handoff']))['handoff_source_ref']]

    def check_handoff(self,context,handoff,operation_key):
        row=self._handoff(plain(handoff));self._delivery(context,row['job_ref'])
        return {'status':'completed','record_refs':[row['handoff_source_ref']],'changed_record_refs':[],
            'result':{'handoff':plain(handoff)},'feedback':None}

    def credit_view(self,context,receiver_selection):
        return A102ResourceCredit(self)(context,receiver_selection)


class A102ResourceCredit:
    requires_episode_receipts=True
    def __init__(self,adapter):self.adapter=adapter
    def as_record(self):return {'kind':'a102_resource_information','version':VERSION,
        'run_id':self.adapter.run_id,'handoff_unit':1,'collected_native_comparison_unit':1}
    def __call__(self,context,receiver_selection):
        self.adapter.records.authenticate(context,allow_unsaved=True)
        require(receiver_selection['run_id']==context.run_id and receiver_selection['episode_id']==context.episode_id,
            'a102_resource_credit_receiver_conflict')
        known=set(receiver_selection['known_record_refs'])-set(receiver_selection['initial_known_record_refs'])
        handoffs=0;comparisons=0
        for reference in known:
            source=self.adapter.store.get(reference)
            if source['record_type']!='source':continue
            if source.get('provider')=='native.a102.structural_handoff':
                handoffs+=int(self.adapter.store.db.execute('SELECT 1 FROM a102_resource_jobs WHERE run_id=? AND handoff_source_ref=?',
                    (context.run_id,reference)).fetchone() is not None)
            if context.role=='results':comparisons+=int(received_grade(self.adapter.store,reference) is not None)
        return {'credit':float(handoffs+comparisons),'handoff_count':handoffs,'collected_native_comparison_count':comparisons,
            'interpretation':'operational_information_not_scientific_function_support'}


def validate_results_preparation(store,run_id,selected,actual,child):
    """Authenticate the original host-added C9 wrapper, without re-execution."""
    native=actual.get('adapter_assignment',{})
    if set(native)!={'version','job_ref','handoff_source_ref','scope_sha256','original_job_request_sha256'}:return False
    if native['version']!='a102_structural_results_assignment_v1':return False
    row=store.db.execute('SELECT * FROM a102_resource_jobs WHERE run_id=? AND job_ref=?',
        (run_id,native['job_ref'])).fetchone()
    if row is None or row['handoff'] is None:return False
    if (selected['handoff']!=json.loads(row['handoff'])
            or native['handoff_source_ref']!=row['handoff_source_ref']
            or native['scope_sha256']!=digest(plain(child.scope))
            or native['original_job_request_sha256']!=digest(json.loads(row['request']))):return False
    from method_loop.identities import EpisodeRef
    parent=EpisodeRef(run_id,child.path[:-1]).episode_id
    if store.db.execute('SELECT 1 FROM a102_handoff_deliveries WHERE run_id=? AND episode_id=? AND job_ref=?',
            (run_id,parent,native['job_ref'])).fetchone() is None:return False
    try:store.validate_scope(plain(child.scope),parent_scope=json.loads(row['scope']))
    except ValueError:return False
    return True


class A102ProgressProvider:
    def __init__(self,adapter):self.adapter=adapter
    def as_record(self):return {'version':'a102_progress_provider_v1','adapter':self.adapter.as_record()}
    def scope(self,handle):return json.loads(self.adapter._job(handle)['scope'])
    def direct_dependencies(self,handle,scope):
        self.adapter.store.validate_scope(self.scope(handle),parent_scope=scope);return []
    def observe(self,handle,requested_fields,scope,*,operation_key=None):
        from .progress_records import validate_resource_status
        require(set(requested_fields)<={'execution_status','measurements','log_windows','committed_record_refs','dependencies','result_available'},
            'a102_progress_requested_fields_invalid')
        self.adapter.store.validate_scope(self.scope(handle),parent_scope=scope)
        row=self.adapter._job(handle);state=row['state'];stamp=now();actual=None
        if row['native_operation_key']:
            context=self.adapter.records.context(row['owner_episode_id'])
            job=json.loads(row['request'])
            path=self.adapter.tools.work_directory(context,job['operation'],job['arguments'],json.loads(row['scope']))/'native-handle.json'
            if path.exists():actual=native_status(NativeJobHandle(path))
        if actual is not None and actual['terminal']:state='completed' if row['outcome'] is not None else 'unknown'
        native_state={'prepared':'submitted','running':'running','completed':'completed','failed':'failed'}.get(state,'unknown')
        available=row['outcome'] is not None
        observation={'observed_at':stamp,'state':native_state,'returncode':0 if available else None,
            'failure_code':None,'result_available':available,'measurements':[],'outputs':[],'logs':[],
            'provenance_refs':[],'native':actual or {'state':state}}
        status=validate_resource_status({'version':'resource_execution_status_v1','handle':handle,'observed_at':stamp,
            'lifecycle_state':{'submitted':'pending','running':'executing','completed':'returned','failed':'returned','unknown':None}[native_state],
            'result_available':available,'resource_id':self.adapter.resource_id,'resource_kind':'local',
            'execution_id':handle,'request_sha256':digest(json.loads(row['request'])),'native':observation})
        value={'version':'progress_snapshot_v1','target_handle':handle,'observed_at':stamp,'execution_status':status,
            'provenance_refs':[],'measurements':[],'log_windows':[],'committed_record_refs':[],
            'dependencies':[],'result_available':available}
        source=self.adapter.tools._source('a102.progress.snapshot',value)
        return {**value,'progress_ref':source}
