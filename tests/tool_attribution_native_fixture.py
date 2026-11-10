"""Sequence-only target: real reference geometry, then a late real A101 link.

Choices/horizons are scripted. phmmer, US-align, host receipt-triggered
attachments, trait features and parent credit are actual application behavior.
The local trait probes do not claim characterized biological function.
"""
from copy import deepcopy
import asyncio
import json

from evidence_root_fixture import EvidenceRootCase, REAL
from gene_annotation_episode.a102_attachments import received_attachments
from gene_annotation_episode.a102_investigation import initial_report
from gene_annotation_episode.decision_context import apply_state_frame
from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand


class ReferenceAttributionCase(EvidenceRootCase):
    def __init__(self,directory,store,*,usalign):
        super().__init__(directory,store,case='lacy',usalign=usalign,sequence_only=True)
        self.reference_source=self.inventory['P18817']
        seq=''.join(line.strip() for line in (REAL/'reference_lacy_P18817.faa').read_text().splitlines() if not line.startswith('>'))
        acid=next(i for i,a in enumerate(seq) if i>50 and a in 'DE')
        base={'chemical_role':None,'allowed_symbols':None,'measurement_source_ref':None,'definition_source_refs':[self.trait_definition]}
        self.probes=[{**base,'physical_feature_key':'reference-acidic-role','kind':'chemical_role',
            'chemical_role':'acidic','reference_positions':[acid]},
            {**base,'physical_feature_key':'discontinuous-reference-region','kind':'region_identity',
                'reference_positions':[80,120,160]}]
        self.resolved_needs=set();self.reference_bindings={}

    def controller(self,path,initial):
        role=path[-1][0]
        horizon=(5 if path[-1][1]=='child_0' else 3) if role=='scientific_process' else {
            'annotation':6,'launch':1,'launch_local':4,'results':2}[role]
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon else 1),parameters,
                {'fixture':'finite_reference_then_late_attribution_validation','budget':horizon})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    async def complete(self,episode_id,role,instructions,frame,output_schema):
        row=self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE episode_id=?',(episode_id,)).fetchone()
        path=json.loads(row['path']);request=json.loads(row['request'])
        own_role=path[-1][0]
        task=request['message'].get('episode_assignment',{}).get('context',{}).get('mock_task')
        if own_role!='annotation' and task!='reference_only':
            return await super().complete(episode_id,role,instructions,frame,output_schema)
        assert frame['kind'] in ('decision_bootstrap','decision_update')
        state=apply_state_frame(self.states.get(episode_id),frame);self.states[episode_id]=state
        assert not state.get('feedback'),state.get('feedback')
        self.resource_views.append({'role':own_role,'resource_context':deepcopy(state['resource_context'])})
        stage=self.stages[episode_id];self.stages[episode_id]+=1
        report={}
        if own_role=='annotation':
            known=list(self.flow.receipts.known(episode_id))
            view=NativeEvidenceRootCredit().read_details(self.store,self.scope,known_record_refs=known,details_limit=0,details_offset=0)
            self.root_views.append({'stage':stage,**view})
            if stage==0:
                selection=self.a102.commission(self.store,target_ref=self.target,scope=self.scope,completeness='unknown',
                    task='native_comparison',child_tool_info=[{'name':name,'resources':'local'} for name in (
                        'structure.bind','structure.reference_align','structure.reference_traits')],
                    evidence_refs=[self.reference_source,self.comparison_source,self.trait_definition],
                    question='Measure the supplied reference Y/Z geometry, keeping the sequence-only target separate. Evaluate local reference traits only through actual correspondence; publish missing attribution needs.',
                    context={'mock_task':'reference_only'})
            elif stage==1:
                assert view['credit']==0 and view['axis_components']['A102']==0
                self.before_sequence=deepcopy(view)
                self.native_count_before=self.store.db.execute('SELECT COUNT(*) FROM a102_native_publications').fetchone()[0]
                assert self.native_count_before==1 and len(state['shared_information_context']['needs'])==3
                selection=self.a101.commission(self.store,target_ref=self.target,scope=self.scope,completeness='unknown',
                    child_tool_info=[{'name':'state.query','resources':'local'}],
                    question='Acquire actual native sequence homology so the root can resolve its sibling structural attribution needs.',
                    context={'mock_task':'sequence_search'})
            else:
                assert view['axis_components']['A101']>0 and view['axis_components']['A102']>0
                if stage==2:self.after_sequence=deepcopy(view)
                pending=[need for need in state['shared_information_context']['needs'] if need['publication_ref'] not in self.resolved_needs]
                if pending:
                    need=pending[0]['publication_ref'];self.resolved_needs.add(need)
                    selection={'kind':'tool','tool':'shared.resolve_information_need','arguments':{'need_ref':need,'status':'fulfilled',
                        'evidence_refs':state['child_reports'][-1]['records']}}
                else:selection={'kind':'tool','tool':'shared.list_information','arguments':{'kind':'all','offset':0,'limit':24}}
        else:
            report=initial_report()
            if stage in (1,2):self.reference_bindings[stage-1]=state['last_local_outcome']['result']['binding_ref']
            if stage<2:
                selection={'kind':'tool','tool':'structure.bind','arguments':{
                    'file_source_ref':self.reference_source if stage==0 else self.comparison_source,'target_ref':None,
                    'format':'pdb_3x_text' if stage==0 else 'pdbx_mmcif_text','chain_id':'A',
                    'model_ordinal':0,'block_ordinal':0,'origin':'predicted' if stage==0 else 'experimental',
                    'origin_witness_refs':[self.reference_source if stage==0 else self.comparison_source],
                    'qualifications':['Actual reference subject; not coordinates of the supplied sequence-only target.',
                        *(['Deposited C154G construct.'] if stage==1 else [])]}}
            elif stage==2:
                selection={'kind':'tool','tool':'structure.reference_align','arguments':{'target_ref':self.target,
                    'measured_binding_ref':self.reference_bindings[0],'reference_binding_ref':self.reference_bindings[1],
                    'target_regions':[[0,self.store.subject_length(self.target)]],'sequence_alignment_ref':None,'primary':True}}
            elif stage==3:
                selection={'kind':'tool','tool':'structure.reference_traits','arguments':{'target_ref':self.target,
                    'reference_binding_ref':self.reference_bindings[0],'sequence_alignment_ref':None,
                    'comparison_source_ref':None,'traits':self.probes}}
            else:
                assert state['current_credit']==0
                report.update(structural_summary='native_geometry_retained',scope_status='unresolved',
                    limitations=['unknown_full_length','function_features_unassessed'])
                selection={'kind':'tool','tool':'episode.credit','arguments':{'limit':24,'offset':0}}
        return {'response':{'response_type':'select_action','selection':selection,'report_update':report}}

    async def run(self):
        root=self.flow.build('annotation','root','Attribute reference measurements and local traits to a sequence-only target through specific sibling evidence.',self.scope)
        record=await root.run_async(self.flow.context);await root.build_result(record)
        known=list(self.flow.receipts.known(root.source.episode_id))
        view=NativeEvidenceRootCredit().read_details(self.store,self.scope,known_record_refs=known,details_limit=24,details_offset=0)
        sheets=received_attachments(self.store,known)
        fold=next(row for row in sheets if row['producer_operation']=='structure.reference_align')
        traits=[row for row in sheets if row['producer_operation']=='structure.reference_traits']
        assert fold['score']>0 and len(traits)==2 and all(row['target_feature_ref'] for row in traits)
        assert self.store.db.execute('SELECT COUNT(*) FROM a102_native_publications').fetchone()[0]==self.native_count_before==1
        assert view['credit']==record.controller_state.current_credit==self.after_sequence['credit']
        assert all(self.store.get(row['target_feature_ref'])['subject_ref']==self.target for row in traits)
        assert self.store.count('annotation')==0
        result={'case':'lacy_sequence_only_reference_geometry','decision_mode':'scripted_choices_real_phmmer_USalign_and_automatic_receipt_grading',
            'target_structure_supplied':False,'before_exact_sequence_evidence':self.before_sequence,
            'after_exact_sequence_evidence':self.after_sequence,'final_credit':view,'reference_fold_attachment':fold,
            'local_traits':traits,'native_structural_jobs':1,'native_sequence_jobs':1,
            'additional_structural_jobs_after_link_arrival':0,
            'trait_interpretation':'Engineering local-property probes; no characterized functional site or whole-function assertion.'}
        (self.directory/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
