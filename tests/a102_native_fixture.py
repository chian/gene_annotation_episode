"""Retained real structures through the ordinary A102 recursive workflow.

Decisions and finite horizons are scripted here. Parsing, structural native
algorithms, automatic graders, child returns, receipts and credit are real.
"""
from collections import defaultdict
import asyncio
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.a102_investigation import (
    A102ServiceFactory,A102Subtree,create_a102_workflow,initial_report)
from gene_annotation_episode.a102_tools import A102ToolRegistry
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand


ROOT=Path(__file__).resolve().parents[1]
REAL=Path(__file__).with_name('fixtures')/'a102/real'
PUBLICATION=ROOT/'research/slotted_process_library/publications/2026-10-24-001'


def supplied_sequence(filename):
    return ''.join(s.strip() for s in (REAL/filename).read_text().splitlines() if not s.startswith('>'))


def coordinate_source(store,filename):
    manifest=json.loads((REAL/'manifest.json').read_text())
    artifact=store.artifact((REAL/filename).read_bytes(),
        'chemical/x-pdb' if filename.endswith('.pdb') else 'chemical/x-mmcif')
    return store.put('source',{'provider':'retained.a102.coordinate_file','accession':filename,
        'uri':manifest['coordinate_urls'][filename],'artifact_ref':artifact,'text_ref':None,
        'request_ref':None,'version':'retained_public_structure_20261102','retrieved_at':None},origin='external')['id']


class NativeCase:
    def __init__(self,path,store,*,sequence_file,target_file,reference_file,usalign,foldseek=None,
                 discover=False,fragment=None,region=None,workflow_run_id='a102-real-native',
                 decision_protocol=None,tool_retrieval=None):
        self.path,self.store,self.discover,self.fragment=path,store,discover,fragment
        query=supplied_sequence(sequence_file)
        if fragment:query=query[:fragment]
        self.target,=store.create_problem(raw_sequence=query,molecule='protein')['subject_refs']
        self.scope={'subject_refs':[self.target]}
        self.material_ref=self.target;self.investigation_scope=self.scope
        if region is not None:
            self.material_ref=store.put('feature',{'subject_ref':self.target,'kind':'sequence_region',
                'segments':[{'start':region[0],'end':region[1]}],'strand':'.','context_refs':[]},origin='reasoning')['id']
            self.investigation_scope={'subject_refs':[self.target],'segments':[
                {'target_ref':self.target,'start':region[0],'end':region[1],'unit':'aa'}]}
            self.fragment=True
        self.files=[target_file,reference_file]
        self.file_refs=[coordinate_source(store,f) for f in self.files]
        self.tools=A102ToolRegistry(store,a102_work_directory=path/'native',
            usalign_executable=usalign,foldseek_executable=foldseek)
        setup=A102ServiceFactory(str(PUBLICATION),tool_retrieval or
            {'version':'scientific_tool_retrieval_v1','mode':'literal_test_v1'})
        self.states,self.stages={},defaultdict(int)
        self.capacity_retries=defaultdict(int);self.last_decisions={}
        self.resource_views=defaultdict(list);self.credit_before_inspection=None
        self.flow=create_a102_workflow(store,self.tools,self,path/'workflow',workflow_run_id,self.controller,
            decision_protocol=decision_protocol,
            episode_service_factory=setup,episode_service_binding={'fixture':'a102_real_native_v1'},
            episode_service_inputs='actual_tool_registry_v1',annotation_child_roles=('scientific_process','literature','launch','monitor','results'),
            initial_known_record_refs=list(dict.fromkeys([self.target,self.material_ref,*self.file_refs])))
        self.subtree=A102Subtree(path/'workflow')

    def has_session(self,episode_id,role):return False
    def conversation_key(self,episode_id,role):return None
    async def release(self,episode_id):pass

    def controller(self,path,initial):
        from method_loop.identities import EpisodeRef
        episode_id=EpisodeRef('a102-real-native',path).episode_id
        horizon=1 if path[-1][0]=='annotation' else 4
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon+self.capacity_retries[episode_id] else 1),
                parameters,{'fixture':'finite_native_validation_horizon'})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    async def retry_capacity(self,episode_id,state):
        if (state.get('feedback') or {}).get('code')!='local_resource_busy':return None
        self.capacity_retries[episode_id]+=1
        for _ in range(1800):
            if self.tools.local_resources.snapshot()['available']['job_slots']:
                return deepcopy(self.last_decisions[episode_id])
            await asyncio.sleep(.5)
        raise TimeoutError('Shared local host stayed occupied; no structural result was fabricated')

    def _binding_ref(self,source):
        for row in self.store.db.execute('SELECT source_ref,body FROM a102_structure_bindings'):
            if json.loads(row['body'])['file_source_ref']==source:return row['source_ref']
        raise AssertionError('Expected real bound model was not published')

    async def complete(self,episode_id,role,instructions,state,output_schema):
        retry=await self.retry_capacity(episode_id,state)
        if retry is not None:return retry
        assert not state.get('feedback'),state.get('feedback')
        path=json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',
            (episode_id,)).fetchone()[0]);episode_role=path[-1][0]
        self.states[episode_id]=deepcopy(state)
        self.resource_views[episode_role].append(deepcopy(state.get('resource_context')))
        stage=self.stages[episode_id];self.stages[episode_id]+=1
        if episode_role=='annotation':
            selected=self.subtree.commission(self.store,target_ref=self.material_ref,scope=self.investigation_scope,
                completeness='fragment' if self.fragment else 'unknown',child_tool_info=[{'name':name,'resources':'local'} for name in
                    ('structure.bind','structure.inspect','structure.discover','structure.align')],
                question='Investigate the structure of this anonymous supplied protein; retain real native geometry and unresolved function.')
            result={'selection':selected,'report_update':{}}
            self.last_decisions[episode_id]=deepcopy(result)
            return result
        report=initial_report()
        if stage<2:
            filename=self.files[stage]
            arguments={'file_source_ref':self.file_refs[stage],'target_ref':self.material_ref if stage==0 else None,
                'format':'pdb_3x_text' if filename.endswith('.pdb') else 'pdbx_mmcif_text',
                'chain_id':'A','model_ordinal':0,'block_ordinal':0,
                'origin':'predicted' if filename.startswith('AF_') else 'experimental',
                'origin_witness_refs':[self.file_refs[stage]],
                'qualifications':['Retained AlphaFold model_v6; native B column is model confidence, not a geometric weight.']
                    if filename.startswith('AF_') else (['Deposited C154G construct, not implicit wild-type geometry.'] if filename=='1PV7.cif' else [])}
            selection={'kind':'tool','tool':'structure.bind','arguments':arguments}
        elif stage==2:
            q,t=[self._binding_ref(ref) for ref in self.file_refs]
            selection={'kind':'tool','tool':'structure.discover' if self.discover else 'structure.align',
                'arguments':{'target_binding_ref':q,'primary':True,
                    **({'reference_binding_refs':[t]} if self.discover else {'reference_binding_ref':t})}}
        else:
            self.credit_before_inspection=state['current_credit']
            report.update(structural_summary='native_geometry_retained',
                scope_status='partial',limitations=['function_features_unassessed','alternatives_unassessed'])
            selection={'kind':'tool','tool':'episode.credit','arguments':{'limit':24,'offset':0}}
        result={'selection':selection,'report_update':report}
        self.last_decisions[episode_id]=deepcopy(result)
        return result

    async def run(self):
        root=self.flow.build('annotation','root','Investigate the supplied anonymous protein structurally.',self.scope)
        record=await root.run_async(self.flow.context)
        await root.build_result(record)
        return record
