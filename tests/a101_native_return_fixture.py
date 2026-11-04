"""Actual small native searches with fixture decisions for return-boundary tests.

Sequences are real retained UniProt inputs. These tests assess custody and
contracts; scientific choices and continuation horizons are explicit fixtures.
"""
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.a101_investigation import (A101Subtree, initial_report,
    resolve_report, create_a101_workflow)
from gene_annotation_episode.a101_credit import A101SequenceCredit
from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.decision_context import PROTOCOL, apply_state_frame
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs, FileAsset, digest
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.domain import obj
from a101_subtree_fixture import PROGRAM, PUBLICATION, ROLES, action, child, reasoning


REAL = Path(__file__).with_name('fixtures')/'a101/real'
POLICY = LocalJobPolicy(1024**3, 64*1024**2)


def fact_form(**sources):
    return obj({field: {'$ref': 'episode-fact:'+source} for field, source in sources.items()})


class NativeReturnCase:
    def __init__(self, path, store, *, positive=False, return_evidence=True,
                 sequence_file=None, reference_files=None, anonymous_input=False):
        self.path, self.store = path, store
        self.positive, self.return_evidence = positive, return_evidence
        sequence_file = sequence_file or REAL/('characterized_tpi_P0A858.faa' if positive else 'uncharacterized_A0A068B6R9.faa')
        if anonymous_input:
            sequence = ''.join(line.strip() for line in sequence_file.read_text().splitlines()
                if not line.startswith('>'))
            problem = store.create_problem(raw_sequence=sequence, molecule='protein')
        else:
            problem = store.create_problem(sequence_file, molecule='protein')
        target, = problem['subject_refs']
        self.target, self.scope = target, {'subject_refs': [target]}
        database = REAL/'reference_tpi_Q8ZKP7.faa'
        if reference_files is not None:
            database = path/'reference-panel.faa'
            database.write_text(''.join(reference.read_text() for reference in reference_files))
        self.jobs = HomologyJobs.create(path/'jobs', executable=FileAsset(PROGRAM,digest(PROGRAM)),
            reference_database=FileAsset(database,digest(database)),policy=POLICY,max_cpu=1)
        self.homology = HomologyEpisodes(self.jobs,parser_policy=POLICY,
            credit_projector=lambda *a,**k:0,credit_binding={'fixture':'unused_legacy_channel'},
            monitoring_projector=lambda *a,**k:0,monitoring_binding={'fixture':'unused_legacy_channel'})
        self.progress = ScientificFindingProgress(FindingProgressPolicy(1))
        self.states, self.stages = {}, defaultdict(int)
        self.asked, self.information, self.forms = set(), [], {}
        self.presentations=[]
        self.resource_views=defaultdict(list)
        self.presentation=_SessionConnection.__new__(_SessionConnection)
        self.presentation.scientific_prompt_states={}
        self.flow = create_a101_workflow(store,ToolRegistry(store),self,path/'run','a101-native-returns',
            self.controller,project_child_credit=self.progress,
            job_episodes=self.homology,resource_estimator=ResourceToolEstimator(),
            episode_service_factory=self.setup,episode_service_binding={'fixture':'real_native_return_boundary_v1'},
            episode_service_inputs='actual_tool_catalog_v1',annotation_child_roles=ROLES,
            episode_record_receipts=True,initial_known_record_refs=[],decision_protocol=PROTOCOL)
        self.subtree = A101Subtree(path/'run')

    def has_session(self,episode_id,role):
        return episode_id in self.states

    def conversation_key(self,episode_id,role):
        return (episode_id+'-fixture',0) if episode_id in self.states else None

    def setup(self,store,*,run_id,directory,job_episodes,resource_estimator,tool_catalog):
        return bind_assembled_services(store,run_id=run_id,directory=directory,
            job_episodes=job_episodes,resource_estimator=resource_estimator,source_directory=PUBLICATION,
            tool_catalog=tool_catalog,tool_retrieval={'version':'scientific_tool_retrieval_v1','mode':'literal_test_v1'},
            scientific_child_roles=ROLES,handoff_unit=1,acquired_record_unit=1,monitoring_information_unit=1,
            literature_outcome_page_size=8,monitor_outcome_page_size=8,log_window_bytes=128,log_roles=('native_text',),
            scientific_contract_information_profile=CONTRACT_INFORMATION_PROFILE)

    def controller(self,path,initial):
        horizon={'annotation':2,'scientific_process':3,'launch':1,'launch_local':4,'results':2}[path[-1][0]]
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon else 1),
                parameters,{'fixture':'explicit_engineering_horizon'})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    def ask(self,episode,role,source):
        key=(episode,role,source)
        if key in self.asked:return None
        self.asked.add(key)
        return {'response':{'response_type':'request_context','lookup':{
            'view':'composition_information','operation':'episode.return_contract',
            'arguments':{'role':role,'source':source}}}}

    async def complete(self,episode_id,role,instructions,frame,output_schema):
        if frame['kind'] in ('decision_bootstrap','decision_update'):
            self.states[episode_id]=apply_state_frame(self.states.get(episode_id),frame)
        else:
            result=frame['result']
            assert result['status']=='completed',result
            assert result['record_refs']==result['changed_record_refs']==[]
            self.information.append(deepcopy(result))
        state=self.states[episode_id]
        assert state.get('feedback') is None,state.get('feedback')
        path=json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',(episode_id,)).fetchone()[0])
        episode_role=path[-1][0]
        self.resource_views[episode_role].append(deepcopy(state['resource_context']))
        if episode_role=='scientific_process':
            self.presentations.append(self.presentation._presentation(episode_id,role,instructions,frame)[0])
        stage=self.stages[episode_id]
        if episode_role=='scientific_process':
            assert state['contract_information_profile']==CONTRACT_INFORMATION_PROFILE
            for target_role,source in ((('launch','execution_handoff'),) if stage==0 else
                    (('results','committed_record_refs'),('results','job_result_progress')) if stage==1 else ()):
                query=self.ask(episode_id,target_role,source)
                if query is not None:return query
        self.stages[episode_id]+=1
        if episode_role=='annotation':
            if stage==0:
                selected=self.subtree.commission(self.store,target_ref=self.target,scope=self.scope,
                    completeness='unknown',child_tool_info=[{'name':'state.query','resources':'local'}],
                    question='Return actual acquired sequence-search evidence and bounded unknowns.')
                response={'selection':selected,'report_update':{}}
            else:
                self.received=deepcopy(state['child_reports'][-1])
                self.resolved=resolve_report(self.store,self.received,scope=self.scope)
                self.parent_known=set(self.flow.receipts.known(episode_id))
                response=reasoning(self.store,hypotheses=[{'alias':'pending','subject_refs':[self.target],
                    'predicate':'functional_family','value':{'type':'enum','value':'unresolved'},'context_refs':[]}])
        elif episode_role=='scientific_process':
            report=initial_report()
            if stage==0:
                assignment={'version':'resource_launch_assignment_v1','job_request':{'query_ref':self.target,'cpu':1},
                    'immutable_input_versions':[],'constraints':{'cpu':1},'resource_selection':None,
                    'software_knowledge_refs':[],'resource_knowledge_refs':[]}
                response=child('launch',assignment,self.scope,fact_form(handoff='execution_handoff'),'Acquire native handoff.')
            elif stage==1:
                self.forms['launch']=deepcopy(state['child_reports'][-1])
                fields=({'records':'committed_record_refs','coverage':'job_result_progress'} if self.return_evidence
                        else {'job_ref':'job_ref','handoff_state':'job_handoff_state'})
                response=child('results',{'version':'resource_results_assignment_v1','handoff':self.forms['launch']['handoff'],
                    'requested_data_selector':{}},self.scope,fact_form(**fields),'Acquire actual native rows and completeness.')
            else:
                self.forms['results']=deepcopy(state['child_reports'][-1])
                self.owner_known=set(self.flow.receipts.known(episode_id))
                self.credit_before_inspection=state['current_credit']
                assert state['credit_binding']['kind']=='a101_native_sequence_correspondence'
                if self.return_evidence:
                    self.coverage=self.forms['results']['coverage']
                    self.snapshot=self.coverage['snapshot_ref']
                    assert self.snapshot in self.owner_known
                    assert self.snapshot in state['visible_record_refs']
                    if not self.positive:
                        report['family']['status']='unresolved'
                        report['limitations']=['unknown_full_length','no_informative_match','unassessed_alternatives']
                    response=action('episode.credit',{'limit':5,'offset':0},report)
                else:
                    report['limitations']=['partial_acquisition']
                    response=action('state.query',{'refs':[self.target]},report)
        elif episode_role=='launch':
            binding=self.flow.episode_bindings.for_role('launch')
            adapter,=binding.adapters.values()
            assignment=deepcopy(state['assignment'])
            assignment['resource_selection']=adapter._selection(1)
            response=child('launch_local',assignment,self.scope,state['requested_form'],'Establish this selected native job.')
        elif episode_role=='launch_local':
            response=action(('homology.configure','homology.stage','homology.submit','homology.check_handoff')[stage])
        else:
            assert episode_role=='results'
            response=(action('homology.extract',{'offset':0,'limit':20}) if stage==0 else
                action('homology.coverage',{'snapshot_ref':state['last_local_outcome']['result']['snapshot_ref']}))
        if episode_role in ('launch','launch_local','results'):
            assert 'episode.credit' not in {t['name'] for t in state['tools']}
            unsupported=self.flow.credit_read(SimpleNamespace(path=tuple(map(tuple,path)),scope=self.scope),
                {'limit':1,'offset':0})
            assert unsupported['status']=='unavailable'
            assert unsupported['feedback']['code']=='credit_details_not_declared'
        if episode_role=='scientific_process':response['report_update']=report
        return {'response':{'response_type':'select_action',**response}}

    async def release(self,episode_id):pass

    async def run(self):
        root=self.flow.build('annotation','root','Investigate actual supplied sequence.',self.scope)
        record=await root.run_async(self.flow.context)
        await root.build_result(record)
        return record
