"""Controlled message checks using actual axis journal and progress receipt tables.

The SQLite fixture supplies database mechanics only. These checks do not
construct a scientific Store, acquire a job, or prove full-workflow restoration.
"""
from contextlib import contextmanager
from copy import deepcopy
import importlib
import json
import sqlite3
from types import SimpleNamespace

import pytest


class ReceiptDatabase:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row

    @contextmanager
    def transaction(self):
        with self.db:
            yield


class MonitorParentExchangeChecks:
    @pytest.fixture
    def exchange(self, tmp_path):
        module = importlib.import_module(self.parent_module)
        parent = object.__new__(getattr(module, self.parent_type))
        journal_module = importlib.import_module(self.axis_module+'.episode_journal')
        monitoring = importlib.import_module(self.axis_module+'.episode_monitoring')
        domain = importlib.import_module(self.axis_module+'.domain')
        runtime = importlib.import_module(self.axis_module+'.runtime')
        database = ReceiptDatabase(tmp_path/'receipts.sqlite')
        journal = journal_module.Journal(database,'run')
        source = SimpleNamespace(episode_id='parent',path=((self.parent_role,'original'),),scope={})
        provider = monitoring.ProgressProvider(database,object(),run_id='run')
        workflow = SimpleNamespace(store=database,journal=journal,run_id='run',receipts=None,
            progress_provider=provider,specialist=lambda source: parent,binding_context=lambda source: source,
            is_job_source=lambda source:False)
        if self.parent_module.endswith('.root.a106.scientific_process.episode'):
            # A106's scientific parent selects its receiver by the child's bound path.
            child_paths = {'monitor':'scientific_process/execution_progress_assessment',
                'literature':'scientific_process/published_evidence_assessment'}
            workflow.episode_bindings = SimpleNamespace(
                for_child=lambda path,role: SimpleNamespace(binding_path=child_paths[role]))
        value = SimpleNamespace(parent=parent,workflow=workflow,source=source,provider=provider,
            domain=domain,runtime=runtime,WorkflowError=journal_module.WorkflowError)
        try:
            yield value
        finally:
            database.db.close()

    @staticmethod
    def action(value,index,action):
        value.workflow.journal.save('runtime_actions',{'episode_id':'parent','decision_index':index,
            'action':json.dumps(action),'result':None,'credit':None})

    def attempt(self,value,index,*,wrong_parent=False):
        path=((self.parent_role,'another' if wrong_parent else 'original'),('monitor','child_3'))
        value.workflow.journal.save('runtime_episodes',{'episode_id':'child','path':json.dumps(path),
            'request':'{}','initial_credit':0,'state':'yielded','completion':None,'archive':None})
        value.workflow.journal.save('runtime_report_attempts',{'parent_episode_id':'parent',
            'decision_index':index,'delivery_ref':'delivery','child_episode_id':'child',
            'contract':'{}','form':None,'failure':None})

    def test_original_request_fields_and_other_child_assignment(self,exchange):
        assignment={'version':'monitor_assignment_v1','target_handle':'original-target',
            'known_progress_refs':[],'requested_fields':['execution_status'],'permitted_committed_record_types':[]}
        original=deepcopy(assignment)
        prepared=exchange.parent.prepare_child_request(exchange.source,'monitor',assignment)
        assert prepared==original and assignment==original and prepared is not assignment
        assert exchange.parent.prepare_child_request(exchange.source,'literature',assignment) is assignment
        with pytest.raises(exchange.domain.ContractError):
            exchange.parent.prepare_child_request(exchange.source,'monitor',{**assignment,'extra':'invalid'})

    def test_typed_receipt_and_redelivery_preserve_provider_identity(self,exchange):
        value=exchange
        self.action(value,3,{'kind':'episode_child','role':'monitor'})
        self.attempt(value,3)
        self.action(value,7,{'kind':'redeliver_report','delivery_ref':'delivery'})
        self.attempt(value,7)
        reference='progress_'+'a'*24
        value.provider.read_progress=lambda ref,scope:{'progress_ref':ref}
        schema=value.domain.obj({'progress':{'type':'array','items':{'type':'string',
            'format':'reference','x-reference-namespace':'episode_progress'}}})
        form={'progress':[reference]}
        # Save the pre-existing provider result, then deliver through the private
        # parent endpoint with the same operation key. Signature drift must fail.
        key='run:parent:3:typed_form'
        value.provider.receive_form('parent',form,schema,{},key)
        value.provider.receive_form=lambda *args:pytest.fail('private parent receiver not selected')
        assert value.runtime.Workflow._receive_form(value.workflow,value.source,form,schema,3)==[]
        assert value.runtime.Workflow._receive_form(value.workflow,value.source,form,schema,7,redelivery=True)==[]
        assert value.provider.received_progress_refs('parent')==[reference]
        rows=value.workflow.store.db.execute('SELECT operation_key FROM runtime_progress_deliveries ORDER BY operation_key').fetchall()
        assert [r[0] for r in rows]==[key,'run:parent:7:typed_form']
        with pytest.raises(value.runtime.ReportBoundaryError) as rejected:
            value.parent.receive_child_progress_for_role(value.source,'monitor',{'progress':[12]},schema,'invalid',value.provider)
        assert rejected.value.diagnostic['code']=='type'
        assert value.workflow.store.db.execute('SELECT count(*) FROM runtime_progress_deliveries').fetchone()[0]==2

    def test_saved_counterpart_rejects_another_parent(self,exchange):
        value=exchange
        self.action(value,7,{'kind':'redeliver_report','delivery_ref':'delivery'})
        self.attempt(value,7,wrong_parent=True)
        with pytest.raises(value.WorkflowError,match='original_delivery_parent_conflict'):
            value.runtime.Workflow._receive_form(value.workflow,value.source,{},value.domain.obj({}),7,redelivery=True)
        assert value.workflow.store.db.execute('SELECT count(*) FROM runtime_progress_deliveries').fetchone()[0]==0

    def test_other_child_keeps_original_receipt_path(self,exchange):
        value=exchange
        self.action(value,1,{'kind':'episode_child','role':'literature'})
        calls=[]
        value.provider.receive_form=lambda *args:calls.append(args)
        assert value.runtime.Workflow._receive_form(value.workflow,value.source,{},value.domain.obj({}),1)==[]
        assert len(calls)==1
