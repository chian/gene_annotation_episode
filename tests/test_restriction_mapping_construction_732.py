"""Initial reference construction from real typed receipt APIs.

The earlier host-frozen row is namespace-only engineering metadata with no
scientific measurements. These tests do not install a restriction alias or
claim a full nonempty scientific computation.
"""
from copy import deepcopy
import json
import os

import pytest

from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.domain import obj
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import Scenario
from test_restriction_mapping_services_730 import requested, prepared_requested_child, SOURCE


pytestmark=pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,reason='requires bounded529')


def engineering_received_case(tmp_path):
    store=Store(tmp_path/'store')
    case=Scenario(tmp_path,store)
    workflow=case.workflow(ScriptedProvider([]))
    schema=requested(names=True)
    parent,old_child=prepared_requested_child(case,workflow,schema)
    context=workflow.binding_context(old_child.source)
    group={'selection_policy':'all_own_completed_results','sequence_ref':case.scope['subject_refs'][0],
        'namespace':'subject','topology':None,'data_status':'unavailable','coordinate_unit':'nt',
        'population_scope':'full_selected_native_enzyme_population','population':None,
        'enzyme_rows':[{'catalog_ordinal':0,'name':'EcoRI','search_state':'not_started',
            'position_meaning':'unknown'}]}
    form={'status':'qualified','basis':[],'selected':[group]}
    workflow.journal.save('runtime_forms',{'episode_id':old_child.source.episode_id,
        'facts':json.dumps({SOURCE:[group]}),'form':json.dumps(form)})
    contract=TypedReportContract(old_child.request.report_contract.decision,schema,
        workflow.resolver(case.scope,context=context),
        lambda value:workflow.validate_report(value,case.scope,schema=schema,context=context))
    admitted=contract.admit(form,audit_identifiers=(old_child.source.episode_id,old_child.request.goal.goal_id)).as_record()
    workflow.save_attempt(parent.source.episode_id,0,'delivery_engineering732',old_child.source.episode_id,
        contract,form=admitted)
    workflow.receive_form(parent.source,admitted,schema,0)
    return store,case,workflow,parent


def initial_selection(case,name='EcoRI'):
    schema=obj({'enzyme':{'type':'string','format':'identifier','x-reference-namespace':'restriction_enzyme'}})
    selected=case.commission()['selection']
    selected.update(schema_json=json.dumps(schema),initial_report_json=json.dumps({'enzyme':name}))
    return selected


def state_rows(store):
    return {table:[dict(row) for row in store.db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
        for table in ('runtime_episodes','runtime_actions','runtime_forms','runtime_observations',
            'runtime_report_attempts','runtime_record_receipts','runtime_receipt_inheritance',
            'runtime_commission_intents')}


def configure_deferred(workflow,case,parent,selected,monkeypatch):
    # Producer-only C1 fixture. No worker reconstruction, dispatch or model
    # capability is claimed by this selected-intent test.
    from scientific_process_worker_fixture import make_binding
    binding=make_binding(workflow.store.path,case.directory,case.descriptors)
    workflow.configure_execution(binding)
    workflow.journal.save('runtime_model_calls',{'episode_id':parent.source.episode_id,'call_index':1,
        'purpose':'decision','request':'{"context":{}}','response':json.dumps({'selection':selected})})
    def forbidden(*args,**kwargs):raise AssertionError('Construction must not dispatch selected work')
    monkeypatch.setattr(workflow.execution_backend,'commission',forbidden)
    monkeypatch.setattr(workflow.execution_backend,'start',forbidden)
    return binding


def test_actual_initial_received_name_uses_saved_context_and_original_commission(tmp_path):
    store,case,workflow,parent=engineering_received_case(tmp_path)
    with store:
        selected=initial_selection(case)
        unit=workflow.selected(parent.source,selected,1)
        child=unit.child
        context=workflow.binding_context(child.source)
        assert json.loads(workflow.journal.row('runtime_episodes',context.episode_id)['request'])['message']['initial_report']=={'enzyme':'EcoRI'}
        assert json.loads(workflow.journal.row('runtime_actions',parent.source.episode_id,1)['action'])==selected
        assert workflow.resolver(case.scope,context=context)('EcoRI','restriction_enzyme') is True
        assert workflow.resolver(case.scope,context=context)('BcgI','restriction_enzyme') is False
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE credit IS NOT NULL').fetchone()[0]==0


@pytest.mark.parametrize('name',['ecori','BcgI','unknown'])
@pytest.mark.parametrize('deferred',[False,True])
def test_unavailable_initial_name_rolls_back_exact_construction_without_observation(tmp_path,monkeypatch,name,deferred):
    store,case,workflow,parent=engineering_received_case(tmp_path)
    with store:
        selected=initial_selection(case,name)
        if deferred:configure_deferred(workflow,case,parent,selected,monkeypatch)
        before=state_rows(store)
        with pytest.raises(ReportBoundaryError) as error:
            workflow.selected(parent.source,selected,1)
        assert error.value.diagnostic['code']=='unknown_reference'
        assert state_rows(store)==before


@pytest.mark.parametrize('deferred',[False,True])
def test_later_semantic_failure_rolls_back_recorded_identity_and_new_prefix(tmp_path,monkeypatch,deferred):
    store,case,workflow,parent=engineering_received_case(tmp_path)
    with store:
        selected=initial_selection(case)
        if deferred:configure_deferred(workflow,case,parent,selected,monkeypatch)
        before=state_rows(store)
        binding=workflow.scientific_process_binding
        original=binding.validate_report
        def reject(context,form,schema):
            original(context,form,schema)
            if form=={'enzyme':'EcoRI'}:
                assert workflow.journal.row('runtime_episodes',context.episode_id) is not None
                assert workflow.journal.row('runtime_actions',parent.source.episode_id,1) is not None
                raise RuntimeError('engineering_semantic_failure_after_proof')
        monkeypatch.setattr(binding,'validate_report',reject)
        with pytest.raises(RuntimeError,match='engineering_semantic_failure_after_proof'):
            workflow.selected(parent.source,selected,1)
        assert state_rows(store)==before


def test_deferred_initial_name_records_original_pending_intent_without_dispatch(tmp_path,monkeypatch):
    from gene_annotation_episode.runtime import DeferredActionUnit
    store,case,workflow,parent=engineering_received_case(tmp_path)
    with store:
        selected=initial_selection(case)
        binding=configure_deferred(workflow,case,parent,selected,monkeypatch)
        unit=workflow.selected(parent.source,selected,1)
        assert isinstance(unit,DeferredActionUnit)
        row=store.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()
        spec=json.loads(row['spec'])
        assert spec['runtime_binding']==binding
        assert spec['child']['request']['message']['initial_report']=={'enzyme':'EcoRI'}
        action=workflow.journal.row('runtime_actions',parent.source.episode_id,1)
        assert json.loads(action['action'])==selected
        assert json.loads(action['result'])['pending_handle']==spec['handle']
        assert action['credit'] is None
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0
        assert not list((case.directory/'episode-execution').glob('commissions/*'))


def test_reconstruction_preserves_original_typed_prefix_after_late_report(tmp_path):
    store,case,workflow,parent=engineering_received_case(tmp_path)
    with store:
        selected=initial_selection(case)
        child=workflow.selected(parent.source,selected,1).child
        context=workflow.binding_context(child.source)
        original_request=workflow.journal.row('runtime_episodes',context.episode_id)['request']
        original_prefix=workflow.receipts.manifest(context.episode_id)
        late=case.commission()['selection']
        schema=requested(names=True)
        late['schema_json']=json.dumps(schema)
        late['initial_report_json']='{"status":"unresolved","basis":[]}'
        late_child=workflow.selected(parent.source,late,2).child
        late_context=workflow.binding_context(late_child.source)
        old=store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id<>?',(late_context.episode_id,)).fetchone()
        facts,form=json.loads(old['facts']),json.loads(old['form'])
        facts[SOURCE][0]['enzyme_rows'][0]['name']='BcgI'
        form['selected'][0]['enzyme_rows'][0]['name']='BcgI'
        workflow.journal.save('runtime_forms',{'episode_id':late_context.episode_id,'facts':json.dumps(facts),'form':json.dumps(form)})
        contract=TypedReportContract(late_child.request.report_contract.decision,schema,
            workflow.resolver(case.scope,context=late_context),
            lambda value:workflow.validate_report(value,case.scope,schema=schema,context=late_context))
        admitted=contract.admit(form,audit_identifiers=(late_child.source.episode_id,late_child.request.goal.goal_id)).as_record()
        workflow.save_attempt(parent.source.episode_id,2,'delivery_engineering732_late',late_child.source.episode_id,contract,form=admitted)
        workflow.receive_form(parent.source,admitted,schema,2)
        assert workflow.resolver(case.scope,context=workflow.binding_context(parent.source))('BcgI','restriction_enzyme') is True
        rebuilt=workflow.selected(parent.source,selected,1).child
        rebuilt_context=workflow.binding_context(rebuilt.source)
        assert workflow.journal.row('runtime_episodes',context.episode_id)['request']==original_request
        assert workflow.receipts.manifest(context.episode_id)==original_prefix
        assert workflow.resolver(case.scope,context=rebuilt_context)('BcgI','restriction_enzyme') is False
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0
