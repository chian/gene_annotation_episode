"""Episode-owned decisions around one durable local job.

Uses the shared method_loop, existing form guard, authenticated model connection,
raw-score estimator and journal. The tree declares capabilities, never stages.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import inspect
import json
from pathlib import Path
import time

from jsonschema import Draft202012Validator
from method_loop import Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from method_loop.archive import JsonArchive

from ..communication import validate_closed_schema, validate_form, interpretation_schema, form_with_facts
from ..numerical import YieldController
from ..providers import ModelConnection, load_config
from ..runtime import (Journal, Record, TypedReportContract, ReleasingContext, FeedbackEpisode,
    ActionLeaf, TimedChildUnit, ActionFailure, WorkflowError, ExecutionContextController, _plain, _json,
    _action_generation_schema, _decode_action_response)
from .service import JobStore, canonical, token, now


def obj(fields):
    return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}


def array(item): return {'type':'array','items':item}

def nullable(schema): return {**schema,'type':[schema['type'],'null']}


REF={'type':'string','format':'reference'}
NUM={'type':'number','minimum':0}
INT={'type':'integer','minimum':0}
HANDOFF=obj({'job_ref':{**REF,'x-reference-namespace':'job'},
    'workload_ref':{**REF,'x-reference-namespace':'workload'},
    'backend':{'type':'string','enum':['local_minimap2_v1']},
    'workspace_ref':{**REF,'x-reference-namespace':'workspace'},
    'status_interface':{'type':'string','enum':['job.status_v1']},
    'progress_interface':{'type':'string','enum':['job.progress_v1']},
    'results_interface':{'type':'string','enum':['job.results_v1']}})
STATUS=obj({'job_ref':{**REF,'x-reference-namespace':'job'},
    'workload_ref':{**REF,'x-reference-namespace':'workload'},
    'state':{'type':'string','enum':['submitted','running','succeeded','failed','lost']},
    **{key:INT for key in ('completed_blocks','total_blocks','completed_reads','total_reads','duration_sample_count')},
    'elapsed_seconds':NUM,'available_blocks':array(INT),
    'mean_completed_block_seconds':nullable(NUM),'estimated_remaining_seconds':nullable(NUM),
    'estimate_meaning':{'type':'string','enum':['native_completed_block_mean_remaining_blocks_excludes_current_block_age']}})
SUMMARY=obj({'extracted_blocks':array(INT),**{key:INT for key in ('input_reads','mapped_reads',
    'reported_alignments','primary_alignments','reverse_alignments','aligned_query_bases')}})
FACTS={'handoff':nullable(HANDOFF),'handoff_receipt':nullable({**REF,'x-reference-namespace':'receipt'}),
    'status':nullable(STATUS),'sample_refs':array({**REF,'x-reference-namespace':'sample'}),'results':SUMMARY}


def example_form(role):
    names={'launch':['handoff','handoff_receipt'],'monitor':['status','sample_refs'],'results':['results']}[role]
    return obj({name:{**FACTS[name],'x-source':name} for name in names})


INSTRUCTIONS='''You own an iterative execution investigation in a method_loop, not a fixed itinerary.
Choose one permitted action from actual outcomes and the goal. Only the numerical controller
ends your Episode; there is no model stop action, turn budget or prescribed sequence.
Parent role: commission a launch child to establish the requested job. You cannot submit it
directly. You can commission monitoring and results-acquisition children, reason over their
requested returned forms, or schedule a future child commission and await that commission.
The same child type is repeatable; never assume a fixed number/order of monitors. Schedule
from returned monitoring evidence and the provided wall-time yield estimate; choose the delay.
Use await_scheduled to let the durable timer execute your exact request. A scheduled commission
is not yet a completed child. Timers do not fabricate observations. Future jobs/parallel launch
are outside this one-workload example. Root integrates results and explicit fixture limitations.
Launch role: investigate environment, stage immutable supplied inputs, configure the native
program, prepare its index, submit and establish a usable monitoring handoff. Tools are choices,
not a forced itinerary. Inspect feedback and repair actual problems. Never change the fixed
workload or resource boundaries. Before successful handoff use handoff.check with the actual
registered job: it exercises the receiver using persisted data. Invalid proposed handoffs return
feedback and preserve the job. The job is detached and may outlive you.
Monitor role: investigate the requested progress/yield information using the supplied admitted
handoff. You are not waiting for the entire job to finish. Unchanged reads add no credit merely
because they were repeated. job.sample returns real time and progress plus an explicitly simple
remaining-time estimate. job.wait_sample may choose an observation interval; it is not a timeout
on the job. Yield governs when this short monitoring investigation ends. Return the parent's form.
Results role: acquire/extract the requested available native result blocks with the provided
handoff, including valid partial results. Inspect availability and extraction feedback, revise
what to request next, and return the requested data to the parent. Do not invent biological
annotation or independently interpret other jobs. Re-extraction of the same block earns no new
credit. Fixed parsers are tools inside your Episode, not a separate parent acquisition route.
All roles: report_update contains exactly the parent's interpretation fields; fact fields are
filled from recorded work through x-source, without another composer. Parent chooses form
fields and meanings. The examples are optional templates, not an instruction to invent fields.
The data are explicitly synthetic. Native mappings demonstrate computation, not biological truth.
'''


@dataclass(frozen=True)
class ScheduledChildUnit(TimedChildUnit):
    commission_ref: str
    due_at: float
    store: JobStore

    async def acquire_async(self, ctx):
        # Replaying an already completed child neither waits again nor fires a
        # second timer. The child's original selections/results reconstruct.
        saved=self.journal.row('runtime_actions',self.parent_episode_id,self.decision_index)
        if saved['result'] is None:
            await asyncio.sleep(max(0,self.due_at-time.time()))
            self.store.db.execute('UPDATE scheduled_commissions SET state="fired",child_episode_id=? WHERE commission_ref=?',
                (self.child.source.episode_id,self.commission_ref)); self.store.db.commit()
        return await super().acquire_async(ctx)


class Source:
    def __init__(self, workflow, path, request, role):
        self.workflow=workflow; self.path=path; self.request=request; self.role=role
        self.episode_id=Episode.identity(workflow.context,workflow.grains[role],path[-1][1],parent_path=path[:-1]).episode_id
        self.index=0; self.feedback=None; self.last_outcome=None
        self.interpret_schema=interpretation_schema(request.report_contract.schema) if request.report_contract else obj({})
        self.report_values=_plain(request.message.as_record()['initial_report'])
        self.visible_reports=[]

    def facts(self):
        store=self.workflow.store; job=store.job(); receipt=None; handoff=None
        if job:
            handoff=store.handoff(job['job_ref'])
            row=store.db.execute('SELECT receipt_ref FROM handoff_receipts WHERE job_ref=? AND handoff=?',
                (job['job_ref'],canonical(handoff))).fetchone()
            if row: receipt=row[0]
        samples=list(store.db.execute('SELECT sample_ref,body FROM job_samples WHERE episode_id=? ORDER BY sampled_at', (self.episode_id,)))
        status=json.loads(samples[-1]['body']) if samples else None
        if status: status={key:status[key] for key in STATUS['properties']}
        return {'handoff':handoff if receipt else None,'handoff_receipt':receipt,
            'status':status,'sample_refs':[r['sample_ref'] for r in samples],'results':store.delivered_summary()}

    async def next(self, view):
        while True:
            index=self.index; self.index+=1
            self.visible_reports=list(view.child_reports)
            schema=self.workflow.schema(self)
            journal=self.workflow.journal
            saved=journal.row('runtime_model_calls',self.episode_id,index)
            if saved and saved['response'] is not None:
                response=json.loads(saved['response'])
            else:
                context=(json.loads(saved['request'])['context'] if saved else view.model_inputs({
                    'role':self.role,'goal':self.request.goal.as_record(),
                    'assignment':self.request.message.as_record(),
                    'workload':self.workflow.store.config(),
                    'own_recorded_facts':self.facts() if self.role!='parent' else {},
                    'own_last_outcome':self.last_outcome,'feedback':self.feedback,
                    'controller':_plain(view.controller_state),
                    'elapsed_time_accounting':journal.elapsed_view(self.episode_id),
                    'available_tools':self.workflow.tools(self.role),
                    'report_fact_schemas':FACTS,'requested_form':self.request.report_contract.schema if self.request.report_contract else None,
                    'current_interpretation_fields':self.report_values,
                    'child_form_examples':{r:example_form(r) for r in ('launch','monitor','results')} if self.role=='parent' else {},
                    'monitoring_yield':self.workflow.monitoring_estimate(self.visible_reports) if self.role=='parent' else None,
                    'pending_commissions':self.workflow.commissions(self.episode_id) if self.role=='parent' else [],
                    'prior_decisions':self.workflow.history(self.episode_id,index)},reports=view.child_reports))
                journal.save('runtime_model_calls',{'episode_id':self.episode_id,'call_index':index,
                    'purpose':'decision','request':_json({'context':context,'schema':schema}),'response':None})
                with journal.measure('runtime_model_calls',self.episode_id,index):
                    response=await self.workflow.provider.complete(self.episode_id,'REASONING',INSTRUCTIONS,context,_action_generation_schema(schema))
                journal.save('runtime_model_calls',{'episode_id':self.episode_id,'call_index':index,
                    'purpose':'decision','request':_json({'context':context,'schema':schema}),'response':_json(response)})
            try:
                response=_decode_action_response(response,schema)
                Draft202012Validator(schema['properties']['selection']).validate(response['selection'])
                unit=self.workflow.selected(self,response['selection'],index)
            except (ValueError,KeyError,TypeError) as error:
                self.feedback={'category':'action_contract','code':type(error).__name__,'detail':str(error)};continue
            try:
                self.report_values=validate_form(response['report_update'],self.interpret_schema,self.workflow.store.resolver)
                self.feedback=None
            except (ValueError,KeyError,TypeError) as error:
                self.feedback={'category':'report_format','detail':getattr(error,'diagnostic',{'code':'invalid_update'})}
            return unit

    async def execute(self, selection, index):
        journal=self.workflow.journal; old=journal.row('runtime_actions',self.episode_id,index)
        if old and json.loads(old['action'])!=selection: raise WorkflowError('selected_work_changed')
        if old and old['result'] is not None:
            result=json.loads(old['result']); credit=old['credit']
        else:
            journal.save('runtime_actions',{'episode_id':self.episode_id,'decision_index':index,
                'action':_json(selection),'result':None,'credit':None})
            with journal.measure('runtime_actions',self.episode_id,index):
                result=await self.workflow.execute(self,selection,index)
            credit=self.workflow.credit(self) if result['status'] in ('completed','partial') else None
            journal.save('runtime_actions',{'episode_id':self.episode_id,'decision_index':index,
                'action':_json(selection),'result':_json(result),'credit':credit})
        self.last_outcome=result
        if result['status'] not in ('completed','partial'):
            raise ActionFailure(result['feedback'])
        return self.workflow.controller_value(self, index, credit)

    async def finish(self, record):
        saved=self.workflow.journal.row('runtime_forms',self.episode_id)
        if self.request.report_contract:
            if saved and saved['form'] is not None: form=json.loads(saved['form'])
            else:
                facts=self.facts()
                form=form_with_facts(self.report_values,self.request.report_contract.schema,facts)
                validate_form(form,self.request.report_contract.schema,self.workflow.store.resolver)
                if self.role=='launch' and facts['handoff'] is not None:
                    # Final communication admission exercises the actual receiving
                    # interface again; the recorded successful probe is not magic.
                    self.workflow.store.check_handoff(facts['handoff'])
                self.workflow.journal.save('runtime_forms',{'episode_id':self.episode_id,'facts':_json(facts),'form':_json(form)})
            await self.workflow.provider.release(self.episode_id)
            return Record({'form':form})
        await self.workflow.provider.release(self.episode_id)
        return Record({'credit':self.workflow.credit(self)})


class JobWorkflow:
    def __init__(self, store, provider, directory, run_id, *, settings=None, controller_factory=None):
        self.store=store;self.provider=provider;self.directory=Path(directory);self.run_id=run_id
        self.journal=Journal(store,run_id);self.archive=JsonArchive(self.directory/'archive')
        self.settings=settings or {'cost':.4,'uncertainty_alpha':.05}
        self.controller_factory=controller_factory
        self.grains={name:Grain(name,'One completed selected action','Recorded contribution and parent-requested form',self.controller)
            for name in ('parent','launch','monitor','results')}
        self.tree=EpisodeTree(self.grains['parent'],{self.grains['parent']:tuple(self.grains[r] for r in ('launch','monitor','results'))})
        self.context=ReleasingContext(tree=self.tree,run_id=run_id)
        self.sources={}

    def controller(self,path):
        eid=Episode.identity(self.context,self.grains[path[-1][0]],path[-1][1],parent_path=path[:-1]).episode_id
        initial=self.journal.row('runtime_episodes',eid)['initial_credit']
        controller = (self.controller_factory(path, initial) if self.controller_factory else
            YieldController(token('epoch',path),initial,self.settings['cost'],
                {k:v for k,v in self.settings.items() if k!='cost'}))
        return ExecutionContextController(controller, self.journal, eid)

    def controller_value(self, source, index, credit):
        """Keep the selected action identity through its actual observation.

        The existing own-action path uses this boundary. The shared wrapper
        records timing only once work has returned; old
        observations retain their original input instead of gaining new times.
        """
        observed = self.store.db.execute('SELECT observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=? AND json_extract(observation,\'$.decision_index\')=?',
            (self.run_id, source.episode_id, index)).fetchone()
        if observed is not None:
            original = json.loads(observed['observation'])['credit']
            if (not isinstance(original, dict) or 'credit' not in original
                    or original.get('estimation_action_index', index) != index):
                raise WorkflowError('recorded controller input does not match its action')
            return Record(original)
        return Record({'credit': credit, 'estimation_action_index': index})

    def credit(self, source):
        store=self.store
        if source.role=='launch':
            return sum([store.setup(k) is not None for k in ('software','inputs','index')]+
                [store.job() is not None,store.db.execute('SELECT 1 FROM handoff_receipts LIMIT 1').fetchone() is not None])/5
        if source.role=='monitor':
            row=store.db.execute('SELECT body FROM job_samples ORDER BY sampled_at DESC LIMIT 1').fetchone()
            if not row: return 0.
            sample=json.loads(row[0]); known=sum([sample['state'] is not None,sample['total_blocks']>0,
                sample['mean_completed_block_seconds'] is not None])/3
            return .5*known+.5*sample['completed_blocks']/max(1,sample['total_blocks'])
        if source.role=='results':
            total=store.setup('inputs')
            return store.delivered_summary()['input_reads']/total['read_count'] if total else 0.
        forms=self.returned_forms(source.episode_id)
        launch=any(any(k.get('x-source')=='handoff_receipt' and form.get(n) is not None for n,k in schema['properties'].items()) for form,schema in forms)
        statuses=[form[n] for form,schema in forms for n,k in schema['properties'].items() if k.get('x-source')=='status' and form.get(n)]
        results=[form[n] for form,schema in forms for n,k in schema['properties'].items() if k.get('x-source')=='results' and form.get(n)]
        coverage=max((r['input_reads']/max(1,store.setup('inputs')['read_count']) for r in results),default=0)
        monitor=max((.5+.5*s['completed_blocks']/max(1,s['total_blocks']) for s in statuses),default=0)
        account=store.db.execute('SELECT 1 FROM parent_accounts WHERE episode_id=? LIMIT 1',(source.episode_id,)).fetchone() is not None
        return .3*launch+.2*monitor+.4*coverage+.1*account

    def returned_forms(self,parent_id):
        rows=store_rows=self.store.db.execute('SELECT a.result,c.request FROM runtime_actions a JOIN runtime_episodes c '
            "ON json_extract(a.result,'$.child_episode_id')=c.episode_id AND a.run_id=c.run_id "
            'WHERE a.run_id=? AND a.episode_id=? AND a.result IS NOT NULL ORDER BY a.decision_index',(self.run_id,parent_id))
        return [(json.loads(r[0])['report'],json.loads(r[1])['report_contract']['measurements']['schema']) for r in rows]

    def history(self,eid,before):
        return [dict(r) for r in self.store.db.execute("SELECT call_index AS decision_index,json_extract(response,'$.selection.kind') AS kind "
            'FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index<? ORDER BY call_index DESC LIMIT 24',(self.run_id,eid,before))]

    def commissions(self,eid):
        return [dict(r) for r in self.store.db.execute('SELECT commission_ref,due_at,state FROM scheduled_commissions WHERE owner_episode_id=? ORDER BY due_at',(eid,))]

    def monitoring_estimate(self,reports):
        samples=[]; returns=0
        for report in reports:
            form=report.as_record();schema=_plain(report.contract.measurements['schema'])
            status=[form[n] for n,k in schema['properties'].items() if k.get('x-source')=='status' and form.get(n)]
            if status: samples.append(status[0]);returns+=1
        rate=None; elapsed=None; gained=None
        if len(samples)>=2:
            elapsed=samples[-1]['elapsed_seconds']-samples[0]['elapsed_seconds']
            gained=samples[-1]['completed_blocks']-samples[0]['completed_blocks']
            if elapsed>0: rate=gained/elapsed
        return {'completed_monitor_returns':returns,'observed_wall_seconds':elapsed,
            'new_completed_blocks':gained,'completed_blocks_per_wall_second':rate,
            'estimated_seconds_per_new_block':1/rate if rate and rate>0 else None,
            'estimate_status':'insufficient_returned_samples' if rate is None else 'observed_rate',
            'meaning':'Simple observed progress/time estimate across returned monitor forms; no calibrated forecast or forced scheduling interval.'}

    def tools(self,role):
        specs={
            'environment.inspect':obj({}), 'execution.configure':obj({'candidate_index':INT,'cpu':{'type':'integer','minimum':1}}),
            'inputs.stage':obj({}), 'index.build':obj({}), 'job.submit':obj({}),
            'handoff.check':obj({'handoff':HANDOFF}),
            'job.sample':obj({}), 'job.wait_sample':obj({'seconds':NUM}),
            'results.available':obj({}), 'results.extract':obj({'block_index':INT})}
        allowed={'parent':[], 'launch':['environment.inspect','execution.configure','inputs.stage','index.build','job.submit','handoff.check'],
            'monitor':['job.sample','job.wait_sample'],'results':['results.available','results.extract']}[role]
        return {key:specs[key] for key in allowed}

    def schema(self,source):
        actions=[obj({'kind':{'type':'string','const':'tool'},'tool':{'type':'string','const':name},'arguments':schema})
            for name,schema in self.tools(source.role).items()]
        if source.role=='parent':
            request=obj({'episode_type':{'type':'string','enum':['launch','monitor','results']},
                'goal':{'type':'string'},'purpose':{'type':'string'},'schema_json':{'type':'string'},
                'initial_report_json':{'type':'string'},'handoff_json':{'type':['string','null']}})
            actions += [obj({'kind':{'type':'string','const':'child'},'request':request}),
                obj({'kind':{'type':'string','const':'schedule'},'delay_seconds':NUM,'request':request}),
                obj({'kind':{'type':'string','const':'await_scheduled'},'commission_ref':{**REF,'x-reference-namespace':'commission'}}),
                obj({'kind':{'type':'string','const':'reason'},'commit':obj({
                    'used_sample_refs':array({**REF,'x-reference-namespace':'sample'}),
                    'used_result_blocks':array(INT),
                    'interpretation':{'type':'string','enum':['execution_unresolved','partial_mapping_available','complete_mapping_summary_available']},
                    'limitations':array({'type':'string','enum':['synthetic_fixture','mapping_is_not_annotation','unmapped_is_not_biological_absence','incomplete_outputs']})})})]
        return obj({'selection':{'anyOf':actions},'report_update':source.interpret_schema})
