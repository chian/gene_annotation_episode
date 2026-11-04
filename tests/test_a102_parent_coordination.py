"""Real runtime parent communication and hard-coded axis admission."""
from copy import deepcopy
import asyncio
import json

import pytest

from gene_annotation_episode.a102_investigation import initial_report
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand
from gene_annotation_episode.state import Store
from a102_native_fixture import NativeCase


class CoordinationCase(NativeCase):
    def controller(self,path,initial):
        horizon=3 if path[-1][0]=='annotation' else 1
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon else 1),parameters,
                {'fixture':'finite_shared_parent_validation'})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    async def complete(self,episode_id,role,instructions,state,output_schema):
        assert not state.get('feedback'),state.get('feedback')
        path=json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',(episode_id,)).fetchone()[0])
        stage=self.stages[episode_id];self.stages[episode_id]+=1
        context=EpisodeReturnRecords(self.store,self.flow.run_id,failure_prefix='test_').context(episode_id)
        binding=self.flow.scientific_process_binding
        if path[-1][0]=='annotation':
            if stage==0:
                selected=self.subtree.commission(self.store,target_ref=self.target,scope=self.scope,completeness='unknown',
                    child_tool_info=[{'name':'structure.model_request','resources':'local'}],question='Request missing structural information.')
                sibling=deepcopy(selected['assignment'])
                sibling['selection']['evidence_axis']=self.subtree.library.reference('A101')
                assert binding.prepare_assignment(context,'scientific_process',sibling,self.scope,'sibling-preparation')
            elif stage==1:
                needs=state['shared_information_context']['needs'];assert len(needs)==1
                self.need=needs[0]['publication_ref']
                selected={'kind':'tool','tool':'shared.resolve_information_need','arguments':{
                    'need_ref':self.need,'status':'unavailable','evidence_refs':[],
                    'reason':'No novel prediction resource is configured in this validation.'}}
            else:
                assert state['shared_information_context']['needs'][0]['status']=='unavailable'
                selected={'kind':'tool','tool':'shared.list_information','arguments':{'kind':'all','offset':0,'limit':24}}
            return {'selection':selected,'report_update':{}}
        assignment=deepcopy(state['scientific_process']['assignment'])
        same=binding.prepare_assignment(context,'scientific_process',assignment,self.scope,'same-axis-preparation')
        assert same['selection']['evidence_axis']['option_id']=='A102'
        assignment['selection']['evidence_axis']=self.subtree.library.reference('A101')
        with pytest.raises(ContractError,match='cross_axis_descendant_requires_shared_parent'):
            binding.prepare_assignment(context,'scientific_process',assignment,self.scope,'cross-axis-attempt')
        return {'selection':{'kind':'tool','tool':'structure.model_request','arguments':{
            'target_ref':self.target,'reason':'Need a target model with origin and mapped coordinates.',
            'available_record_refs':[self.target]}},'report_update':initial_report()}


def test_parent_coordinates_missing_model_and_axes_stay_siblings(tmp_path):
    with Store(tmp_path/'state') as store:
        case=CoordinationCase(tmp_path,store,sequence_file='P0A858.faa',target_file='AF_P0A858.pdb',
            reference_file='1YPI.cif',usalign=None)
        record=asyncio.run(case.run())
        assert record.controller_state.current_credit==0
        assert store.db.execute('SELECT count(*) FROM a102_resource_jobs').fetchone()[0]==0
        assert store.count('assessment')==store.count('annotation')==0
        parent=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='annotation'").fetchone()[0]
        assert all(row['name'].startswith('shared.') for row in case.flow.catalog(case.scope,
            source=type('Source',(),{'path':(('annotation','root'),)})()))
