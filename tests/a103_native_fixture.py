"""Real genomic inputs through the actual A103 episode and receipt runtime.

The finite controller budgets and optional scripted smoke choices are explicit
engineering constraints. A configured model chooses scientific actions in the
fresh investigation entry point; expected functional labels stay in this file.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import asyncio
import hashlib
import io
import json
from pathlib import Path

from Bio import SeqIO

from gene_annotation_episode.a103_investigation import A103ServiceFactory,A103Subtree,initial_report
from gene_annotation_episode.a103_tools import A103ToolRegistry,NAMES
from gene_annotation_episode.a103_publication import received_measurement
from gene_annotation_episode.a103_attachments import received_attachments
from gene_annotation_episode.a101_investigation import A101Subtree,initial_report as sequence_report
from gene_annotation_episode.decision_context import PROTOCOL,apply_state_frame
from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit,create_evidence_root_workflow
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand
from gene_annotation_episode.homology_jobs import HomologyJobs,FileAsset,digest as file_digest
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.domain import obj
from a103_parent_dispatch import pending_sequence_requests


ROOT = Path(__file__).resolve().parents[1]
REAL = Path(__file__).with_name('fixtures')/'a103'/'real'
PUBLICATION = ROOT/'research/slotted_process_library/publications/2026-10-24-001'
PROGRAM = ROOT/'resources/software/infernal-1.1.5/hmmer/src/phmmer'
ROLES = ('scientific_process','literature','launch','monitor','results')
CASES = {
    'poxa':{'target':'P39280','files':['ecoli-window.gb','salmonella-window.gb','porphyromonas-kama.gb'],
        'selectors':[{'locus_tag':'b4146'},{'locus_tag':'STM4333'},{'protein_id':'AAQ66184.1'}],
        'leads':['P39280','P0A6N4','P0A8N7','Q8ZKB8','P64036','Q9ZJ12']},
    'bioy':{'target':'D5ARG8','files':['rcapsulatus-bioy.gb','bsubtilis-bioy.gb'],
        'selectors':[{'protein_id':'WP_013068946.1'},{'protein_id':'NP_388918.1'}],
        'leads':['D5ARG8','O07620']},
    'yjef':{'target':'P31806','files':['ecoli-window.gb'],'selectors':[{'locus_tag':'b4167'}],
        'leads':['P31806','P40165','P36059']},
    'mj0044':{'target':'Q60352','files':['mj0044-window.gb','mthermo-ipk.gb','tacidophilum-ipk.gb'],
        'selectors':[{'protein_id':'WP_010869535.1'},{'protein_id':'WP_010875687.1'},{'protein_id':'WP_010900530.1'}],
        'leads':['Q60352','O26153','Q9HLX1','Q8H1F7']},
}


def genomic_source(store,filename):
    manifest = json.loads((REAL/'manifest.json').read_text())['genomic_files'][filename]
    content = (REAL/filename).read_bytes()
    assert hashlib.sha256(content).hexdigest()==manifest['sha256']
    artifact = store.artifact(content,'text/plain')
    return store.put('source',{'provider':'retained.a103.genome','accession':manifest['request']['id'],
        'uri':manifest['source_url'],'artifact_ref':artifact,'text_ref':artifact,
        'request_ref':store.artifact(json.dumps({'request':manifest['request']}),'application/json'),
        'version':'retained_genomic_records_20261103','retrieved_at':None},origin='external')['id']


def protein_inputs(store):
    manifest = json.loads((REAL/'manifest.json').read_text())
    references = {}
    for filename,metadata in manifest['protein_metadata_files'].items():
        assert hashlib.sha256((REAL/filename).read_bytes()).hexdigest()==metadata['sha256']
        value = json.loads((REAL/filename).read_text())
        artifact = store.artifact((REAL/filename).read_bytes(),'application/json')
        source = store.put('source',{'provider':'retained.uniprot','accession':filename,
            'uri':metadata['source_url'],'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
            'version':'retained_public_protein_metadata_20261103','retrieved_at':None},origin='external')['id']
        for row in value['results']:
            sequence = row['sequence']['value']
            reference = store.put('reference',{'reference_type':'protein','source_ref':source,
                'accession':row['primaryAccession'],'label':'Acquired protein '+row['primaryAccession'],
                'sequence_ref':store.artifact(sequence,'text/plain'),'molecule':'protein','length':len(sequence),
                'term_refs':[],'context_refs':[]},origin='external')['id']
            references[row['primaryAccession']] = (reference,source,sequence)
    return references


class A103NativeCase:
    def __init__(self,directory,store,*,case,connection=None,smoke=False,wiring_smoke=False,native_policy=None,retained_inputs=None):
        self.directory,self.store,self.case = directory,store,case
        self.connection,self.smoke = connection,smoke
        self.wiring_smoke = wiring_smoke
        self.retained_inputs = deepcopy(retained_inputs)
        definition = CASES[case]
        self.proteins = protein_inputs(store)
        if retained_inputs is None:
            self.target, = store.create_problem(raw_sequence=self.proteins[definition['target']][2],molecule='protein')['subject_refs']
        else:
            targets=[row[0] for row in store.db.execute('SELECT id FROM inputs')
                if store.get(row[0]).get('sequence_ref') and store.get_artifact(store.get(row[0])['sequence_ref']).decode().strip()
                    ==self.proteins[definition['target']][2]]
            if len(targets)!=1:raise ValueError('retained_case_target_identity_conflict')
            self.target=targets[0]
        self.scope = {'subject_refs':[self.target]}
        self.files = definition['files'][:2] if wiring_smoke else definition['files']
        self.file_refs = [genomic_source(store,f) for f in self.files]
        self.selectors = definition['selectors'][:2] if wiring_smoke else definition['selectors']
        self.native_policy = native_policy if native_policy is not None else LocalJobPolicy(128*1024**2,32*1024**2,180)
        self.tools = A103ToolRegistry(store,a103_work_directory=directory/'native',
            target_genomic_sources={self.target:[self.file_refs[0]]},job_limits=self.native_policy.to_dict())
        panel = directory/'reference-panel.faa'
        entries = {accession:value[2] for accession,value in self.proteins.items()}
        for filename in self.files:
            for record in SeqIO.parse(REAL/filename,'genbank'):
                for i,feature in enumerate(record.features):
                    if feature.type=='CDS' and feature.qualifiers.get('translation'):
                        entries[record.id+'.CDS.'+str(i)] = ''.join(feature.qualifiers['translation'])
        query = self.proteins[definition['target']][2]
        panel.write_text(''.join('>'+name+'\n'+seq+'\n' for name,seq in entries.items() if seq!=query))
        panel_artifact=store.artifact(panel.read_bytes(),'text/plain')
        self.panel_source=store.put('source',{'provider':'retained.a103.search_database','accession':'actual-bounded-reference-panel',
            'uri':None,'artifact_ref':panel_artifact,'text_ref':panel_artifact,
            'request_ref':store.artifact(json.dumps({'original_genomic_sources':self.file_refs,
                'excluded_target_peptide_sha256':hashlib.sha256(query.encode()).hexdigest(),
                'meaning':'actual search database; excluded peptide and unverified CDSs cannot support nondetection'}),'application/json'),
            'version':'a103_real_bounded_reference_panel_v1','retrieved_at':None},origin='external')['id']
        policy = self.native_policy
        self.jobs = HomologyJobs.create(directory/'jobs',executable=FileAsset(PROGRAM,file_digest(PROGRAM)),
            reference_database=FileAsset(panel,file_digest(panel)),policy=policy,max_cpu=1)
        self.homology = HomologyEpisodes(self.jobs,parser_policy=policy,
            credit_projector=lambda *a,**k:0,credit_binding={'kind':'unused_legacy_channel'},
            monitoring_projector=lambda *a,**k:0,monitoring_binding={'kind':'unused_legacy_channel'})
        self.states,self.stages = {},defaultdict(int)
        self.episode_for_path={}
        self.resource_views,self.before_credit_read = [],None
        self.helper_pairs,self.pending_helper_pair = set(),None
        self.synthesis_requested = retained_inputs is not None
        self.evidence_epoch,self.last_science_epoch = 0,-1
        self.query_subjects = {}
        self.root_finished = False
        self.asked,self.last,self.helper_queries = set(),{},set()
        self.next_science_budget = 10
        self.run_id = 'a103-real-'+case+('-smoke' if smoke else '-model')
        if retained_inputs is not None:
            self.run_id+='-retained-'+hashlib.sha256(str(directory).encode()).hexdigest()[:12]
        setup = A103ServiceFactory(str(PUBLICATION),{'version':'scientific_tool_retrieval_v1','mode':'literal_test_v1'})
        initial = list(dict.fromkeys([self.target,self.panel_source,*self.file_refs,*[r for entry in self.proteins.values() for r in entry[:2]]]))
        if retained_inputs is not None:
            initial=list(dict.fromkeys([*initial,*store.reference_subset(retained_inputs['record_refs'],self.scope)]))
            self.seed_completed_searches(set(initial),hashlib.sha256(panel.read_bytes()).hexdigest())
            # Input delivery can include newly collected native evidence from
            # an interrupted producer. Grade that receipt before any episode
            # projection; a credit inspection must not activate the grading.
            from gene_annotation_episode.a103_attachments import refresh
            generated,_=refresh(store,set(initial),self.scope)
            initial=list(dict.fromkeys([*initial,*generated]))
        self.flow = create_evidence_root_workflow(store,self.tools,self,directory/'workflow',self.run_id,self.controller,
            job_episodes=self.homology,resource_estimator=ResourceToolEstimator(),
            decision_protocol=PROTOCOL,episode_service_factory=setup,
            episode_service_binding={'kind':'a103_real_native_case_v1'},episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=ROLES,initial_known_record_refs=initial)
        self.subtree = A103Subtree(directory/'workflow')
        self.sequence_subtree = A101Subtree(directory/'workflow')

    def has_session(self,episode_id,role):
        return self.connection.has_session(episode_id,role) if self.connection else episode_id in self.states

    def conversation_key(self,episode_id,role):
        return self.connection.conversation_key(episode_id,role) if self.connection else (episode_id,0)

    async def release(self,episode_id):
        if self.connection:await self.connection.release(episode_id)

    def controller(self,path,initial):
        role = path[-1][0]
        budget = ((1 if self.smoke and not self.wiring_smoke else 40) if role=='annotation' else
            (6 if self.wiring_smoke and self.next_science_budget!=2 else 3 if self.smoke and not self.wiring_smoke else self.next_science_budget) if role=='scientific_process' else
            {'launch':12,'launch_local':12,'results':12,'monitor':3}.get(role,4))
        def estimate(history,parameters,contexts):
            episode=self.episode_for_path.get(tuple(map(tuple,path)))
            phase_done=role in {'launch','launch_local','results'} and episode is not None and self.stages[episode]>={
                'launch':1,'launch_local':4,'results':2}[role]
            scientific = self.states.get(episode,{}).get('scientific_process',{}).get('assignment',{})
            if role=='scientific_process' and scientific.get('selection',{}).get('evidence_axis',{}).get('option_id')=='A103':
                latest=self.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
                    "AND result IS NOT NULL ORDER BY rowid DESC LIMIT 1",(self.run_id,episode)).fetchone()
                last_action=json.loads(latest[0]) if latest else {}
                manual_need=last_action.get('tool')=='shared.request_information'
                if manual_need:
                    known=set(self.flow.receipts.known(episode))
                    association=any(r['body']['schema'] in {'a103_recurrence_v1','a103_fusion_v1','a103_cooccurrence_v1'}
                        for ref in known if (r:=received_measurement(self.store,ref)) is not None)
                    pending=self.sequence_requests(known)
                    # An explicit need returns to the parent promptly. A
                    # followup still performs its independent context work.
                    phase_done = (not scientific.get('context',{}).get('received_attribution_followup')
                        or bool(pending) or association and not self.native_context_steps(known))
                elif last_action.get('tool')=='episode.credit':
                    known=set(self.flow.receipts.known(episode))
                    association=any(r['body']['schema'] in {'a103_recurrence_v1','a103_fusion_v1','a103_cooccurrence_v1'}
                        for ref in known if (r:=received_measurement(self.store,ref)) is not None)
                    phase_done=association and not self.native_context_steps(known) and not self.sequence_requests(known)
                elif last_action.get('tool') in {'context.compare_neighborhoods','context.fusion','context.cooccurrence'}:
                    # Automatic per-use needs should reach the parent without
                    # waiting for the model to restate the same missing map.
                    known=set(self.flow.receipts.known(episode))
                    phase_done=bool(self.sequence_requests(known))
            done = phase_done or len(history)>=budget or path[-1][0]=='annotation' and self.root_finished
            return YieldEstimate(len(history),NumericBand.exact(0 if done else 1),parameters,
                {'validation':'finite_action_budget; not_biological_saturation','budget':budget})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    def sequence_requests(self,known):
        measurements=[r['body'] for ref in known if (r:=received_measurement(self.store,ref)) is not None]
        components={row['protein_reference_ref'] for body in measurements if body['schema']=='a103_neighborhood_v1'
            for row in body['cds'] if row.get('protein_reference_ref')}
        needs=self.store.db.execute("SELECT source_ref,body FROM shared_investigation_publications "
            "WHERE run_id=? AND kind='need' ORDER BY rowid",(self.run_id,)).fetchall()
        return pending_sequence_requests(self.store,self.target,known,received_attachments(self.store,known),
            [(ref,json.loads(raw)) for ref,raw in needs],submitted_queries=self.helper_queries,
            native_component_refs=components)

    def search_operands(self,known):
        exists=self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone()
        if not exists:return []
        from gene_annotation_episode.a103_detection import search_receipt
        searches=[]
        for row in self.store.db.execute('SELECT source_ref,body FROM homology_result_snapshots ORDER BY rowid'):
            if row['source_ref'] not in known:continue
            body=json.loads(row['body'])
            query=self.query_subjects.get(body['query_sequence_sha256'])
            if query not in known or body['native_source_ref'] not in known:continue
            search_receipt(self.store,row['source_ref'],body['native_source_ref'],query,known)
            searches.append({'component_ref':query,'snapshot_ref':row['source_ref'],
                'native_source_ref':body['native_source_ref'],'database_source_ref':self.panel_source,
                'query_sequence_sha256':body['query_sequence_sha256']})
        return searches

    def seed_completed_searches(self,known,database_sha):
        exists=self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone()
        if not exists:return
        subjects=defaultdict(list)
        for ref in sorted(known):
            record=self.store.get(ref)
            if record.get('sequence_ref') and self.store.subject_molecule(ref)=='protein':
                peptide=self.store.get_artifact(record['sequence_ref']).decode().strip().upper()
                subjects[hashlib.sha256(peptide.encode()).hexdigest()].append(ref)
        from gene_annotation_episode.a103_detection import search_receipt
        for row in self.store.db.execute('SELECT source_ref,body FROM homology_result_snapshots'):
            body=json.loads(row['body']);key=body['query_sequence_sha256']
            if row['source_ref'] not in known or body['native_source_ref'] not in known or body['database_sha256']!=database_sha:
                continue
            candidates=subjects.get(key,[])
            if not candidates:continue
            query=body.get('query_ref') if body.get('query_ref') in candidates else self.target if self.target in candidates else candidates[0]
            search_receipt(self.store,row['source_ref'],body['native_source_ref'],query,known)
            self.query_subjects[key]=query;self.helper_queries.add(key)

    def retained_context(self,known):
        grades={r['measurement_ref']:r for r in received_attachments(self.store,known)}
        result={'locus_bindings':[],'neighborhoods':[],'context_measurements':[]}
        for ref in sorted(known):
            native=received_measurement(self.store,ref)
            if native is None or native['body']['target_ref']!=self.target:continue
            body=native['body'];schema=body['schema']
            if schema=='a103_locus_binding_v1':
                link=grades.get(ref,{}).get('target_link',{})
                result['locus_bindings'].append({'binding_ref':ref,'accession':body['accession'],
                    'file_source_ref':body['file_source_ref'],
                    'selection_status':body['selection_status'],
                    'target_attribution':{key:link[key] for key in ('state','factor','coverage','route','locus_application') if key in link}})
            elif schema=='a103_neighborhood_v1':
                result['neighborhoods'].append({'neighborhood_ref':ref,'binding_ref':body['binding_ref'],
                    'accession':body['accession'],'cds':[{key:cds[key] for key in
                        ('source_feature_index','protein_reference_ref','segments','strand','focal') if key in cds} for cds in body['cds']]})
            elif schema in {'a103_recurrence_v1','a103_fusion_v1','a103_cooccurrence_v1'}:
                result['context_measurements'].append({'measurement_ref':ref,'schema':schema,
                    'qualified_score':grades.get(ref,{}).get('score'),'missing':grades.get(ref,{}).get('missing',[])})
        return result

    def native_context_steps(self,known):
        """Concrete available context operands, never an axis-wide multiplier."""
        context=self.retained_context(known)
        steps=[]
        if self.case=='yjef':return steps
        bound_files={row['file_source_ref'] for row in context['locus_bindings']}
        manifest=json.loads((REAL/'manifest.json').read_text())['genomic_files']
        for source,filename,selector in zip(self.file_refs,self.files,self.selectors,strict=True):
            if source not in bound_files:
                steps.append({'tool':'context.bind_locus','arguments':{
                    'target_ref':self.target,'file_source_ref':source,'format':'genbank',
                    'accession':manifest[filename]['request']['id'],'selector':selector,
                    'sequence_source_ref':None,'genetic_code':None}})
        covered={row['binding_ref'] for row in context['neighborhoods']}
        for binding in context['locus_bindings']:
            if binding['selection_status']=='selected' and binding['binding_ref'] not in covered:
                right_bp=(8000 if binding['accession'].startswith('AE015924') else 15000) if self.case=='poxa' else 3000
                steps.append({'tool':'reference.neighborhood','arguments':{
                    'binding_ref':binding['binding_ref'],'left_bp':3000,'right_bp':right_bp}})
        def peptide_hash(ref):
            if ref not in known:return None
            record=self.store.get(ref)
            if not record.get('sequence_ref') or self.store.subject_molecule(ref)!='protein':return None
            return hashlib.sha256(self.store.get_artifact(record['sequence_ref']).decode().strip().upper().encode()).hexdigest()
        focal={peptide_hash(self.target)}
        neighbors=set()
        for neighborhood in context['neighborhoods']:
            for cds in neighborhood['cds']:
                key=peptide_hash(cds.get('protein_reference_ref'))
                if key is not None:(focal if cds.get('focal') else neighbors).add(key)
        detected=set()
        for ref in known:
            native=received_measurement(self.store,ref)
            if native is not None and native['body']['schema']=='a103_detection_v1':
                body=native['body']
                if body['target_ref']==self.target:
                    detected.add((body.get('neighborhood_ref'),peptide_hash(body['component_ref'])))
        required={(peptide_hash(operand.get('query_ref')),operand.get('neighborhood_ref'))
            for grade in received_attachments(self.store,known) if grade['target_ref']==self.target
            for operand in grade.get('required_operands',[])
            if operand.get('use')=='partner_in_exact_neighborhood'}
        for search in self.search_operands(known):
            key=search['query_sequence_sha256']
            for neighborhood in context['neighborhoods']:
                selected=(key,neighborhood['neighborhood_ref']) in required or (
                    self.case=='bioy' and key not in focal and key in neighbors)
                if not selected:continue
                if (neighborhood['neighborhood_ref'],key) in detected:continue
                steps.append({'tool':'context.detection_inventory','arguments':{
                    **{name:search[name] for name in ('component_ref','snapshot_ref','native_source_ref','database_source_ref')},
                    'target_ref':self.target,'binding_refs':[neighborhood['binding_ref']],
                    'neighborhood_ref':neighborhood['neighborhood_ref']}})
                detected.add((neighborhood['neighborhood_ref'],key))
        return steps

    def context_gaps(self,known):
        """Case coverage requirements, without supplying a relationship or score."""
        measurements={ref:native['body'] for ref in known if
            (native:=received_measurement(self.store,ref)) is not None and
            native['body']['target_ref']==self.target}
        bodies=list(measurements.values())
        if self.case=='yjef':
            return [] if any(b['schema']=='a103_fusion_v1' for b in bodies) else ['actual_fusion_measurement']
        bindings={ref:b['file_source_ref'] for ref,b in measurements.items()
            if b['schema']=='a103_locus_binding_v1'}
        neighborhoods={ref:b['binding_ref'] for ref,b in measurements.items()
            if b['schema']=='a103_neighborhood_v1'}
        covered={bindings[neighborhoods[row['neighborhood_ref']]] for b in bodies
            if b['schema']=='a103_recurrence_v1' for row in b['rows']
            if row['neighborhood_ref'] in neighborhoods and neighborhoods[row['neighborhood_ref']] in bindings}
        return [f'comparative_context_for_supplied_genomic_source:{ref}' for ref in self.file_refs if ref not in covered]

    def region_correspondence_leads(self,known):
        if self.case!='yjef':return []
        from gene_annotation_episode.sequence_attribution import sequence_link
        def segments(positions):
            result=[]
            for position in sorted(set(positions)):
                if result and result[-1][1]==position:result[-1][1]=position+1
                else:result.append([position,position+1])
            return result
        leads=[]
        for accession in CASES[self.case]['leads']:
            if accession==CASES[self.case]['target']:continue
            reference,_,peptide=self.proteins[accession]
            if reference not in known:continue
            link=sequence_link(self.store,self.target,peptide,known)
            pairs=link.get('pairs',[])
            if link['state']!='evaluated' or not pairs:continue
            leads.append({'actual_query_ref':self.target,'component_ref':reference,
                'mapped_target_segments':segments(p[0] for p in pairs),
                'mapped_reference_segments':segments(p[1] for p in pairs),
                'native_witnesses':link['witnesses'],
                'meaning':'Read-only projection of received native residue maps; gaps and unpaired positions remain unmapped. No fusion or activity is established by this projection.'})
        return leads

    def _binding(self):
        for row in self.store.db.execute('SELECT source_ref,body FROM a103_bindings ORDER BY rowid'):
            body = json.loads(row['body'])
            if body['file_source_ref']==self.file_refs[0]:return row['source_ref']
        raise AssertionError('Expected executed genomic binding')

    async def complete(self,episode_id,role,instructions,frame,output_schema):
        path = json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',(episode_id,)).fetchone()[0])
        self.episode_for_path[tuple(map(tuple,path))]=episode_id
        if frame.get('kind') in {'decision_bootstrap','decision_update'}:
            self.states[episode_id] = apply_state_frame(self.states.get(episode_id),frame)
        state = self.states.get(episode_id,{})
        axis = state.get('scientific_process',{}).get('assignment',{}).get('selection',{}).get('evidence_axis',{}).get('option_id')
        helper = axis=='A101'
        if path[-1][0]=='scientific_process' and not self.smoke and not helper:
            return await self.connection.complete(episode_id,role,instructions,frame,output_schema)
        if (state.get('feedback') or {}).get('code')=='local_resource_busy':
            for _ in range(600):
                if self.tools.local_resources.snapshot()['available']['job_slots']:
                    return deepcopy(self.last[episode_id])
                await asyncio.sleep(.5)
            raise TimeoutError('Shared host remained occupied; preserved native handle was not restarted')
        feedback=state.get('feedback') or {}
        if (path[-1][0]=='annotation' and feedback.get('kind')=='report_delivery_failure'
                and feedback.get('reason','').startswith('a103_')):
            from gene_annotation_episode.a103_investigation import measurement_report_schema
            self.stages[episode_id]+=1
            return {'response':{'response_type':'select_action','selection':{'kind':'redeliver_report',
                'delivery_ref':feedback['delivery_ref'],
                'purpose':'Receive the existing native context records and frozen credit. The unsupported interpretation remains rejected.',
                'schema_json':json.dumps(measurement_report_schema())},'report_update':{}}}
        if (self.smoke or helper or path[-1][0]!='scientific_process') and state.get('feedback'):
            raise AssertionError(state['feedback'])
        self.resource_views.append({'path':path,'resource_context':state.get('resource_context')})
        stage = self.stages[episode_id]
        if helper:
            required = ((('launch','execution_handoff'),) if stage==0 else
                (('results','committed_record_refs'),('results','job_result_progress')) if stage==1 else ())
            for target_role,source_name in required:
                key = (episode_id,target_role,source_name)
                if key not in self.asked:
                    self.asked.add(key)
                    return {'response':{'response_type':'request_context','lookup':{
                        'view':'composition_information','operation':'episode.return_contract',
                        'arguments':{'role':target_role,'source':source_name}}}}
        self.stages[episode_id]+=1
        def fact_form(**fields):return obj({name:{'$ref':'episode-fact:'+source} for name,source in fields.items()})
        def child(role,assignment,schema,goal):return {'kind':'episode_child','role':role,'assignment':assignment,
            'scope':self.scope,'goal':goal,'purpose':goal,'schema_json':json.dumps(schema),'initial_report_json':'{}'}
        if helper or path[-1][0] in {'launch','launch_local','results'}:
            report = sequence_report() if helper else {}
            if helper and stage==0:
                requested = state['scientific_process']['assignment']['context']['requested_evidence_subjects']
                assignment = {'version':'resource_launch_assignment_v1','job_request':{'query_ref':requested['query_ref'],'cpu':1},
                    'immutable_input_versions':[],'constraints':{'cpu':1},'resource_selection':None,
                    'software_knowledge_refs':[],'resource_knowledge_refs':[]}
                selection = child('launch',assignment,fact_form(handoff='execution_handoff'),'Run the explicitly requested native sequence search.')
            elif helper:
                selection = child('results',{'version':'resource_results_assignment_v1','handoff':state['child_reports'][-1]['handoff'],
                    'requested_data_selector':{}},fact_form(records='committed_record_refs',coverage='job_result_progress'),
                    'Collect actual native sequence evidence and recorded search coverage.')
            elif path[-1][0]=='launch':
                binding = self.flow.episode_bindings.for_role('launch');adapter, = binding.adapters.values()
                assignment = deepcopy(state['assignment']);assignment['resource_selection'] = adapter._selection(1)
                selection = child('launch_local',assignment,state['requested_form'],'Establish the selected bounded native sequence job.')
            elif path[-1][0]=='launch_local':
                selection = {'kind':'tool','tool':('homology.configure','homology.stage','homology.submit','homology.check_handoff')[stage],
                    'arguments':{}}
            else:
                selection = {'kind':'tool','tool':'homology.extract' if stage==0 else 'homology.coverage',
                    'arguments':{'offset':0,'limit':2048} if stage==0 else
                    {'snapshot_ref':state['last_local_outcome']['result']['snapshot_ref']}}
            response = {'response':{'response_type':'select_action','selection':selection,'report_update':report}}
            self.last[episode_id] = deepcopy(response)
            return response
        if path[-1][0]=='annotation':
            known = set(self.flow.receipts.known(episode_id))
            if stage>0 and self.pending_helper_pair is not None:
                # Actual returned native records trigger A103 grading at receipt.
                # A parent delivery records the information flow explicitly.
                pair,need_ref = self.pending_helper_pair
                self.pending_helper_pair = None
                self.evidence_epoch += 1
                evidence = list(self.flow.receipts.known(episode_id,record_type='observation'))
                for search in self.search_operands(known):
                    evidence.extend(search[name] for name in ('component_ref','snapshot_ref','native_source_ref','database_source_ref'))
                evidence=list(dict.fromkeys(evidence))
                if need_ref:
                    return {'response':{'response_type':'select_action','selection':{'kind':'tool',
                        'tool':'shared.resolve_information_need','arguments':{'need_ref':need_ref,'status':'partially_fulfilled',
                            'evidence_refs':evidence,'reason':'Received actual sequence comparisons for this particular context attribution; remaining scopes retain their own needs.'}},'report_update':{}}}
            if stage>0:
                # Explicit manual requests can precede a context measurement
                # (e.g. fusion boundaries). They are parent decisions, separate
                # from the hard-coded numerical grading route.
                pending = self.sequence_requests(known)
                if pending:
                    request = pending[0]
                    pair = request['query_ref'],next(iter(request['reference_refs']),None)
                    self.helper_pairs.add(pair)
                    self.helper_queries.add(request['query_sequence_sha256']);self.next_science_budget = 2
                    self.query_subjects[request['query_sequence_sha256']]=request['query_ref']
                    need_ref = next(iter(request['need_refs']),None)
                    self.pending_helper_pair = pair,need_ref
                    selection = self.sequence_subtree.commission(self.store,target_ref=self.target,scope=self.scope,
                        completeness='unknown',child_tool_info=[{'name':name,'resources':'local'} for name in
                            ('source.read','state.query')],
                        question='Investigate the actual sequence correspondence requested by the sibling A103 context investigation. '
                            'Search the declared bounded reference panel with the explicitly requested query, retain actual residue maps, native scores and search coverage, '
                            'and return the records needed for component/region attribution. This is evidence about the original target question; '
                            'external evidence subjects are not new annotation targets. Preserve differences and unsupported functional specificity.',
                        evidence_refs=request['evidence_refs'],context={'requested_evidence_subjects':{
                            'query_ref':pair[0],'reference_ref':pair[1],
                            'requested_query_refs':request['requested_query_refs'],
                            'reference_refs':request['reference_refs'],'neighborhood_refs':request['neighborhood_refs']},
                            'information_need_ref':need_ref,'purpose':'specific_context_component_or_region_correspondence',
                    'validation_budget':'Two scripted scientific execution commissions through existing native HMMER launch/results roles; no functional verdict is supplied.'})
                    return {'response':{'response_type':'select_action','selection':selection,'report_update':{}}}
                if (self.synthesis_requested and self.last_science_epoch==self.evidence_epoch
                        and not self.native_context_steps(known) and not self.context_gaps(known)):
                    # The restricted root exposes shared metadata tools, not
                    # episode.credit. Publish the actually received records;
                    # root credit is already host-projected from receipts.
                    from gene_annotation_episode.a103_investigation import received_context_records
                    self.root_finished = True
                    return {'response':{'response_type':'select_action','selection':{'kind':'tool',
                        'tool':'shared.publish_information','arguments':{'target_ref':self.target,
                            'evidence_refs':received_context_records(self.store,known,self.scope),
                            'qualification':'The receiving parent has reviewed these actual context records and per-use grades. '
                                'Measured association remains separate from unresolved activity, necessity and unexamined sequence.'}},'report_update':{}}}
                self.synthesis_requested = True
            self.next_science_budget = 10
            self.last_science_epoch = self.evidence_epoch
            manifest = json.loads((REAL/'manifest.json').read_text())
            sources = [{'file_source_ref':ref,'format':'genbank','accession':manifest['genomic_files'][file]['request']['id'],
                'selector_lead':selector,'material_relation':'supplied_target_genomic_file' if i==0 else 'reference_genomic_lead'}
                for i,(ref,file,selector) in enumerate(zip(self.file_refs,self.files,self.selectors,strict=True))]
            next_steps=self.native_context_steps(known)
            remaining=self.context_gaps(known)
            selected_task=('synthesis' if not next_steps and not remaining
                else 'locus_identity' if next_steps and next_steps[0]['tool']=='context.bind_locus'
                else 'neighborhood_organization' if next_steps and next_steps[0]['tool']=='reference.neighborhood'
                else 'component_attribution' if next_steps else 'fusion_and_regions' if self.case=='yjef' else 'comparative_context')
            selection = self.subtree.commission(self.store,target_ref=self.target,scope=self.scope,task=selected_task,
                child_tool_info=[{'name':name,'resources':'local'} for name in (*NAMES,'source.read','state.query','sequence.sites')],
                question='Measure gene-context relationships for the supplied protein using the actual genomic records. '
                    'Reuse the explicit retained locus and neighborhood facts. A relationship can be defined by correspondence '
                    'to a particular received sequence family; characterize its molecular function separately. '
                    'Use supplied genomic files and protein reference leads, verify locus and component attribution, '
                    'measure useful context relationships and alternatives, and publish missing facts to the shared parent. '
                    'After locus/neighbor inventory, test an explicit relationship with the relevant comparative, fusion '
                    'or detection operation. On parent followup, reuse acquired context and newly received maps. '
                    'Completed native search operands are supplied explicitly: use context.detection_inventory when '
                    'presence or scoped nondetection is needed, without repeating that completed search. '
                    'Complete available native_context_steps, then compare the retained neighborhoods or measure the fusion. '
                    'Keep nonblocking questions about molecular activity shared while executable context work remains. '
                    'When both remaining_context_coverage and native_context_steps are empty, review the retained '
                    'qualified measurements with episode.credit and return their synthesis and limitations. '
                    'Inspect episode.credit after the native context work to review its automatically graded facts. '
                    'Choose the scientific work. Keep exact molecular activity and any unavailable context unresolved. '
                    'For this case, '+{
                        'bioy':'measure which already-queried neighboring component families occur at each bound locus and compare their actual organization.',
                        'yjef':'map the supplied domain-family leads to nonoverlapping regions and measure their linkage in the same actual coding product.',
                        'mj0044':'compare organization at the target and supplied reference loci, retaining measured differences and unknown component identities.',
                        'poxa':'measure recurring associations and contrast them with a related alternative context when the data permits. '
                            'Inspect the supplied wider flanks for additional component leads, retain actual distances, '
                            'and preserve source taxonomy and related sampling in the declared comparison groups.',
                    }[self.case]+' No expected outcome or score is supplied.',
                context={'genomic_files':sources,'reference_proteins':[
                    {'reference_ref':r[0],'source_ref':r[1],'accession':accession}
                    for accession,r in self.proteins.items() if accession in CASES[self.case]['leads']],
                    'received_attribution_followup':stage>0 or self.retained_inputs is not None,
                    'actual_search_database_source_ref':self.panel_source,
                    'received_native_search_operands':self.search_operands(known),
                    'received_region_correspondence':self.region_correspondence_leads(known),
                    'retained_context':self.retained_context(known),
                    'native_context_steps':next_steps,
                    'remaining_context_coverage':remaining,
                    'validation_budget':'10 scientific own actions per commission; initial explicit information needs return to the parent promptly. This is a bounded engineering investigation, not an optimal stopping claim.'},
                evidence_refs=tuple(known))
            return {'response':{'response_type':'select_action','selection':selection,'report_update':{}}}
        report = initial_report()
        if self.wiring_smoke:
            assert self.case=='poxa','The wiring smoke uses the declared two-locus panel.'
            bindings = {json.loads(r['body'])['file_source_ref']:r['source_ref'] for r in
                self.store.db.execute('SELECT source_ref,body FROM a103_bindings')}
            neighbors = {r['body']['binding_ref']:(r['source_ref'],r['body']) for ref in self.flow.receipts.known(episode_id)
                if (r:=received_measurement(self.store,ref)) is not None and r['body']['schema']=='a103_neighborhood_v1'}
            measured = any(r['body']['schema']=='a103_recurrence_v1' for ref in self.flow.receipts.known(episode_id)
                if (r:=received_measurement(self.store,ref)) is not None)
            if measured:
                selection = {'kind':'tool','tool':'episode.credit','arguments':{'limit':8,'offset':0}}
                report.update(context_summary='association_measured',scope_status='partial',
                    limitations=['exact_chemistry_unestablished','alternatives_unassessed'])
            elif stage<2:
                i=stage
                selection = {'kind':'tool','tool':'context.bind_locus','arguments':{'target_ref':self.target,
                    'file_source_ref':self.file_refs[i],'accession':json.loads((REAL/'manifest.json').read_text())['genomic_files'][self.files[i]]['request']['id'],
                    'format':'genbank','sequence_source_ref':None,'genetic_code':None,'selector':self.selectors[i]}}
            elif stage<4:
                selection = {'kind':'tool','tool':'reference.neighborhood','arguments':{
                    'binding_ref':bindings[self.file_refs[stage-2]],'left_bp':3000,'right_bp':6000}}
            else:
                rows=[]
                for i,file in enumerate(self.file_refs):
                    ref,body = neighbors[bindings[file]]
                    anchor = json.loads(self.store.db.execute('SELECT body FROM a103_bindings WHERE source_ref=?',(bindings[file],)).fetchone()[0])
                    partner = next(r for r in body['cds'] if r['qualifiers'].get('gene')==['efp'])
                    rows.append({'neighborhood_ref':ref,'left_feature_index':anchor['locus']['source_feature_index'],
                        'right_feature_index':partner['source_feature_index'],'sampling_group':'genome-'+str(i)})
                selection = {'kind':'tool','tool':'context.compare_neighborhoods','arguments':{
                    'target_ref':self.target,'partner_reference_ref':self.proteins['P0A6N4'][0],
                    'definition_source_refs':self.file_refs,'rows':rows,'definition':{
                        'maximum_gap_bp':200,'maximum_intervening_genes':0,'orientation':'divergent','order':'any'}}}
            response={'response':{'response_type':'select_action','selection':selection,'report_update':report}}
            self.last[episode_id]=deepcopy(response)
            return response
        if stage==0:
            selection = {'kind':'tool','tool':'context.bind_locus','arguments':{'target_ref':self.target,
                'file_source_ref':self.file_refs[0],'accession':json.loads((REAL/'manifest.json').read_text())['genomic_files'][self.files[0]]['request']['id'],
                'format':'genbank','sequence_source_ref':None,'genetic_code':None,'selector':self.selectors[0]}}
        elif stage==1:
            selection = {'kind':'tool','tool':'reference.neighborhood','arguments':{'binding_ref':self._binding(),'left_bp':3000,'right_bp':12000}}
        else:
            self.before_credit_read = state['current_credit']
            selection = {'kind':'tool','tool':'episode.credit','arguments':{'limit':8,'offset':0}}
            report.update(context_summary='organization_measured',scope_status='partial',
                limitations=['source_labels_only','exact_chemistry_unestablished','alternatives_unassessed'])
        response={'response':{'response_type':'select_action','selection':selection,'report_update':report}}
        self.last[episode_id]=deepcopy(response)
        return response

    async def run(self):
        root = self.flow.build('annotation','root','Investigate genomic context of the anonymous supplied protein.',self.scope)
        record = await root.run_async(self.flow.context)
        await root.build_result(record)
        known = set(self.flow.receipts.known(root.source.episode_id))
        credit = NativeEvidenceRootCredit()(self.store,self.scope,known_record_refs=known)
        measurements = [{'source_ref':r['source_ref'],'kind':r['grade']['kind'],
            'producer_operation':r['body']['producer_operation'],'raw_value':r['grade']['raw_value']}
            for ref in known if (r:=received_measurement(self.store,ref)) is not None]
        actions = [{'path':json.loads(r[0]),'action':json.loads(r[1]),'result':json.loads(r[2])}
            for r in self.store.db.execute('SELECT e.path,a.action,a.result FROM runtime_actions a '
                'JOIN runtime_episodes e USING(run_id,episode_id) WHERE a.run_id=? AND a.result IS NOT NULL ORDER BY a.rowid',
                (self.run_id,))]
        result = {'case':self.case,'decision_mode':'scripted_engineering_smoke' if self.smoke else
            'fresh_A103_decisions_on_explicit_retained_real_evidence' if self.retained_inputs is not None else
            'fresh_A103_model_scientific_decisions_with_scripted_parent_and_native_A101_execution',
            'retained_input_provenance':self.retained_inputs,
            'credit':credit,'measurements':measurements,'before_credit_read':self.before_credit_read,
            'configured_native_policy':self.native_policy.to_dict(),
            'returned_forms':[json.loads(r[0]) for r in self.store.db.execute(
                'SELECT form FROM runtime_report_attempts WHERE run_id=? AND form IS NOT NULL',(self.run_id,))],
            'resource_views':self.resource_views,'actions':actions,
            'native_job_count':len(list((self.directory/'native').glob('*/native-handle.json'))),
            'interpretation':'native_genomic_calculations; no_new_biological_experiments_or_expected_function_in_investigation'}
        from a103_run_audit import audit
        result['audit']=audit(self,root.source.episode_id,credit)
        result['total_native_job_count']=result['audit']['total_native_jobs']
        (self.directory/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
