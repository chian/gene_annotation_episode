"""Actual structural launch/receiving/results children, with no handoff credit leak."""
from copy import deepcopy
import asyncio
import json
import os

import pytest

from gene_annotation_episode.a102_investigation import initial_report
from gene_annotation_episode.domain import obj
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand
from gene_annotation_episode.state import Store
from a102_native_fixture import NativeCase


def child(role,assignment,scope,schema):
    return {'kind':'episode_child','role':role,'assignment':assignment,'scope':scope,
        'goal':'Execute or collect the original A102 structural job.',
        'purpose':'Return actual native results through the original receiving interface.',
        'schema_json':json.dumps(schema),'initial_report_json':'{}'}


class ResourceCase(NativeCase):
    def controller(self,path,initial):
        from method_loop.identities import EpisodeRef
        episode_id=EpisodeRef('a102-real-native',path).episode_id
        horizon={'annotation':1,'scientific_process':5,'launch':1,'launch_local':2,'results':1}[path[-1][0]]
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon+self.capacity_retries[episode_id] else 1),parameters,
                {'fixture':'explicit_resource_horizon'})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    def handoff_schema(self):
        resource=self.flow.episode_bindings.for_role('launch')
        return obj({'handoff':resource.fact_sources('launch')['execution_handoff']['report_schema']})

    async def complete(self,episode_id,role,instructions,state,output_schema):
        retry=await self.retry_capacity(episode_id,state)
        if retry is not None:return retry
        path=json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',(episode_id,)).fetchone()[0])
        kind=path[-1][0];stage=self.stages[episode_id]
        if kind=='annotation' or kind=='scientific_process' and stage<2:
            return await super().complete(episode_id,role,instructions,state,output_schema)
        assert not state.get('feedback'),state.get('feedback')
        self.states[episode_id]=deepcopy(state);self.stages[episode_id]+=1
        resource=self.flow.episode_bindings.for_role('launch');adapter=next(iter(resource.adapters.values()))
        if kind=='scientific_process':
            if stage==2:
                q,t=[self._binding_ref(ref) for ref in self.file_refs]
                assignment={'version':'resource_launch_assignment_v1','job_request':{
                    'operation':'structure.align','arguments':{'target_binding_ref':q,'reference_binding_ref':t,'primary':True}},
                    'immutable_input_versions':[],'constraints':{'cpu':1},'resource_selection':None,
                    'software_knowledge_refs':[],'resource_knowledge_refs':[]}
                self.launch_assignment=deepcopy(assignment)
                selection=child('launch',assignment,self.scope,self.handoff_schema())
            elif stage==3:
                assert state['current_credit']==0
                handoff=state['child_reports'][-1]['handoff']
                self.handoff=handoff
                schema=obj({'records':{'type':'array','items':{'type':'string','format':'reference'},'x-source':'committed_record_refs'}})
                selection=child('results',{'version':'resource_results_assignment_v1','handoff':handoff,
                    'requested_data_selector':{}},self.scope,schema)
            else:
                self.credit_before_inspection=state['current_credit']
                selection={'kind':'tool','tool':'episode.credit','arguments':{'limit':24,'offset':0}}
            result={'selection':selection,'report_update':initial_report()}
            self.last_decisions[episode_id]=deepcopy(result)
            return result
        if kind=='launch':
            assignment={**self.launch_assignment,'resource_selection':adapter.selection()}
            result={'selection':child('launch_local',assignment,self.scope,self.handoff_schema()),'report_update':{}}
        else:
            result={'selection':{'kind':'tool','tool':'a102.native.collect' if kind=='results' else
                'a102.native.execute' if stage==0 else 'a102.native.status','arguments':{}},'report_update':{}}
        self.last_decisions[episode_id]=deepcopy(result)
        return result


def test_resource_children_deliver_metadata_before_scientific_results(tmp_path):
    program=os.environ.get('A102_USALIGN')
    if not program:pytest.skip('Set A102_USALIGN for the real structural resource workflow')
    with Store(tmp_path/'state') as store:
        case=ResourceCase(tmp_path,store,sequence_file='P0ABA6.faa',target_file='AF_P0ABA6.pdb',
            reference_file='AF_Q9KNH4.pdb',usalign=program)
        result=asyncio.run(case.run())
        assert case.credit_before_inspection>0
        assert result.controller_state.current_credit==pytest.approx(case.credit_before_inspection)
        roles={json.loads(row[0])[-1][0] for row in store.db.execute('SELECT path FROM runtime_episodes')}
        assert {'annotation','scientific_process','launch','launch_local','results'}<=roles
        assert store.db.execute('SELECT count(*) FROM a102_resource_jobs WHERE state="completed"').fetchone()[0]==1
        native=store.db.execute('SELECT source_ref FROM a102_native_publications').fetchone()[0]
        for row in store.db.execute('SELECT episode_id,path FROM runtime_episodes'):
            kind=json.loads(row['path'])[-1][0]
            if kind in {'launch','launch_local'}:assert native not in case.flow.receipts.known(row['episode_id'])
