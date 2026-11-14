"""Compact restriction forms and original receiver proofs; no native science."""
from copy import deepcopy
import json
import os

import pytest

from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_contract_information import (
    ContractInformationError, expand_fact_form, validate_saved_fact_form,
)
from gene_annotation_episode.restriction_mapping_returns import (
    restriction_mapping_fact_sources, requested_restriction_projections,
    project_restriction_action_return, validate_frozen_restriction_return,
)
from gene_annotation_episode.communication import plain


SOURCE='restriction_mapping_results'
PARAMETER='x-restriction-selection'
BASE_FIELDS=['selection_policy','sequence_ref','namespace','topology','data_status',
    'coordinate_unit','population_scope']
pytestmark=pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,reason='requires bounded529')


def selection(*,policy='all_own_completed_results',sequence_ref=None,names=False):
    fields=BASE_FIELDS+(['enzyme_rows.catalog_ordinal','enzyme_rows.name',
        'enzyme_rows.search_state','enzyme_rows.position_meaning'] if names else [])
    return {'version':'restriction_return_selection_v1','policy':policy,
        'sequence_ref':sequence_ref,'fields':fields}


def submitted(chosen=None,*,field='selected'):
    return obj({'status':{'type':'string','enum':['unresolved','qualified']},
        field:{'$ref':'episode-fact:'+SOURCE,PARAMETER:selection() if chosen is None else chosen}})


def expanded(schema,*,facts=None,permitted=('scientific_process',)):
    return expand_fact_form(json.dumps(schema),child_role='scientific_process',
        facts_by_role={'scientific_process':restriction_mapping_fact_sources() if facts is None else facts},
        permitted_child_roles=permitted)


def test_actual_compact_selection_expands_into_existing_explicit_723_contract():
    schema=submitted(selection(names=True))
    original=deepcopy(schema)
    result=expanded(schema)
    view=result['expanded_schema']['properties']['selected']
    requested=requested_restriction_projections(result['expanded_schema'])[SOURCE]
    assert requested['selection']=={'policy':'all_own_completed_results','sequence_ref':None}
    assert set(view['items']['properties'])==set(BASE_FIELDS)|{'enzyme_rows'}
    assert PARAMETER not in view
    assert schema==original
    assert validate_saved_fact_form(child_role='scientific_process',submitted_schema_json=json.dumps(schema),
        expanded_schema=result['expanded_schema'],declaration=result['declaration'])==result['expanded_schema']


@pytest.mark.parametrize('fault',['missing_selector','missing_policy','missing_sequence','extra','wrong_source','nested'])
def test_compact_grammar_never_supplies_selection_defaults(fault):
    schema=submitted()
    node=schema['properties']['selected']
    if fault=='missing_selector':del node[PARAMETER]
    elif fault=='missing_policy':del node[PARAMETER]['policy']
    elif fault=='missing_sequence':del node[PARAMETER]['sequence_ref']
    elif fault=='extra':node['additionalProperties']=False
    elif fault=='wrong_source':node['$ref']='episode-fact:scientific_process_results'
    else:schema['properties']['selected']={'type':'array','items':node}
    with pytest.raises(ContractInformationError):expanded(schema)


@pytest.mark.parametrize('fault',['source','role','base'])
def test_original_frozen_advertisement_remains_required(fault):
    facts=restriction_mapping_fact_sources()
    permitted=('scientific_process',)
    if fault=='source':facts.clear()
    elif fault=='role':permitted=()
    else:facts[SOURCE]['report_schema']['description']='changed original schema'
    with pytest.raises(ContractInformationError) as error:
        expanded(submitted(),facts=facts,permitted=permitted)
    assert error.value.code=={'source':'return_contract_not_available',
        'role':'return_child_role_not_available','base':'selected_fact_base_schema_mismatch'}[fault]


@pytest.mark.parametrize('fault',['text','role','roster','expanded','selection'])
def test_saved_declaration_checks_original_relationships(fault):
    schema=submitted(selection(names=True))
    result=expanded(schema)
    declaration=result['declaration']
    if fault=='text':declaration['submitted_schema_json']+=' '
    elif fault=='role':declaration['child_role']='annotation'
    elif fault=='roster':declaration['fact_references'][0]['field']='forged'
    elif fault=='expanded':result['expanded_schema']['properties']['status']['enum'].append('forged')
    else:
        schema['properties']['selected'][PARAMETER]['fields']=BASE_FIELDS
        # Even a changed declaration carrying its own revised text and all
        # original schema hashes cannot approve a different selected tree.
        declaration['submitted_schema_json']=json.dumps(schema)
    with pytest.raises(ContractInformationError):
        validate_saved_fact_form(child_role='scientific_process',submitted_schema_json=json.dumps(schema),
            expanded_schema=result['expanded_schema'],declaration=declaration)


def test_compiler_selected_copy_preserves_original_saved_numeric_values():
    from test_restriction_mapping_selection_734 import ALL, _saved_action
    chosen=selection()
    chosen['fields']=ALL
    result=expanded(submitted(chosen))
    action=_saved_action()  # Genuine retained728 file; no Store/native/719 work.
    before=deepcopy(action)
    node=result['expanded_schema']['properties']['selected']
    group=project_restriction_action_return(action,node)
    form={'status':'qualified','selected':[group]}
    validate_frozen_restriction_return(form,result['expanded_schema'],{SOURCE:[group]})
    assert group['population']['complete_empty_enzyme_count']==0
    assert group['enzyme_rows'][0]['recognition_match_count']==1
    assert group['enzyme_rows'][0]['positions'][0]['watson_boundary_0based']==5
    assert group['enzyme_rows'][0]['positions'][0]['crick_boundary_0based']==9
    assert action==before


def configured_case(tmp_path,monkeypatch,*,names=True):
    """Engineering opt-in configuration; actual host contracts, no new prompt.

    Production ScientificProcessEpisodes does not advertise this profile yet.
    This tests its existing generic configured route, without claiming a
    configured-model or newly selectable restriction operation.
    """
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
    from gene_annotation_episode.state import Store
    from test_scientific_process_runtime import Scenario
    from test_runtime import ScriptedProvider
    store=Store(tmp_path/'store')
    case=Scenario(tmp_path,store)
    workflow=case.workflow(ScriptedProvider([]),decision_protocol='decision_exchange_v1')
    monkeypatch.setattr(workflow.scientific_process_binding,'contract_information_profile',
        lambda context: PROFILE if context.role=='annotation' else None,raising=False)
    parent=workflow.build('annotation','root','Inspect explicit restriction return fields',case.scope)
    selected=case.commission()['selection']
    selected.update(schema_json=json.dumps(submitted(selection(names=names))),initial_report_json='{"status":"unresolved"}')
    save_pending(workflow,parent.source,selected,0)
    child=workflow.selected(parent.source,selected,0).child
    return store,case,workflow,parent,child,selected


def save_pending(workflow,source,selected,index):
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
    context={'tools':workflow.catalog(source.scope,source=source),'contract_information_profile':PROFILE}
    schema=workflow.action_schema(source)
    record={'context':context,'schema':schema,'decision_protocol':'decision_exchange_v1',
        'contract_information':workflow.freeze_contract_information(source,context,schema)}
    workflow.validate_contract_information(record)
    workflow.journal.save('runtime_model_calls',{'episode_id':source.episode_id,'call_index':index,
        'purpose':'decision','request':json.dumps(record),'response':json.dumps({'selection':selected})})


def freeze_name(workflow,case,parent,child):
    """Unavailable namespace-only engineering fixture, with no measurements."""
    from gene_annotation_episode.runtime import TypedReportContract
    context=workflow.binding_context(child.source)
    schema=plain(child.request.as_record())['report_contract']['measurements']['schema']
    group={'selection_policy':'all_own_completed_results','sequence_ref':case.scope['subject_refs'][0],
        'namespace':'subject','topology':None,'data_status':'unavailable','coordinate_unit':'nt',
        'population_scope':'full_selected_native_enzyme_population',
        'enzyme_rows':[{'catalog_ordinal':0,'name':'EcoRI','search_state':'not_started','position_meaning':'unknown'}]}
    form={'status':'qualified','selected':[group]}
    workflow.journal.save('runtime_forms',{'episode_id':child.source.episode_id,
        'facts':json.dumps({SOURCE:[group],'interpretations':{'status':'qualified'}}),'form':json.dumps(form)})
    contract=TypedReportContract(child.request.report_contract.decision,schema,
        workflow.resolver(case.scope,context=context),
        lambda value:workflow.validate_report(value,case.scope,schema=schema,context=context))
    report=contract.admit(form,audit_identifiers=(child.source.episode_id,child.request.goal.goal_id)).as_record()
    workflow.save_attempt(parent.source.episode_id,0,'delivery_engineering733',child.source.episode_id,contract,form=report)
    workflow.receive_form(parent.source,report,schema,0)
    return group


def redelivery(workflow,parent,*,field='redelivered',status=True):
    schema=submitted(selection(names=True),field=field)
    if not status:
        schema['properties']['unrecorded']={'type':'boolean'}
        schema['required'].append('unrecorded')
    selected={'kind':'redeliver_report','delivery_ref':'delivery_engineering733',
        'purpose':'Read the same original requested rows','schema_json':json.dumps(schema)}
    save_pending(workflow,parent.source,selected,1)
    return selected,workflow.selected(parent.source,selected,1)


def test_actual_configured_selection_admission_redelivery_and_reconstruction(tmp_path,monkeypatch):
    from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
    store,case,workflow,parent,child,selected=configured_case(tmp_path,monkeypatch)
    with store:
        declaration=plain(child.request.as_record())['message']['report_contract_declaration']
        assert declaration['submitted_schema_json']==selected['schema_json']
        group=freeze_name(workflow,case,parent,child)
        reader=RestrictionMappingReferences(store,workflow.run_id)
        context=workflow.binding_context(parent.source)
        assert reader._attempt(context,0)=={'EcoRI'}
        original=tuple(store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',(child.source.episode_id,)).fetchone())
        chosen,unit=redelivery(workflow,parent)
        assert unit.report.as_record()['redelivered']==[group]
        assert reader._attempt(context,1)=={'EcoRI'}
        attempt=store.db.execute('SELECT * FROM runtime_report_attempts WHERE decision_index=1').fetchone()
        assert json.loads(attempt['report_contract_declaration'])['submitted_schema_json']==chosen['schema_json']
        assert tuple(store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',(child.source.episode_id,)).fetchone())==original
        request=workflow.journal.row('runtime_episodes',child.source.episode_id)['request']
        rebuilt=workflow.selected(parent.source,selected,0).child
        assert workflow.journal.row('runtime_episodes',rebuilt.source.episode_id)['request']==request
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==1
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE credit IS NOT NULL').fetchone()[0]==0


@pytest.mark.parametrize('fault',['missing','text','hash','fields'])
def test_received_compact_redelivery_rejects_corrupted_saved_proof(tmp_path,monkeypatch,fault):
    from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
    store,case,workflow,parent,child,_=configured_case(tmp_path,monkeypatch)
    with store:
        freeze_name(workflow,case,parent,child)
        redelivery(workflow,parent)
        row=store.db.execute('SELECT report_contract_declaration FROM runtime_report_attempts WHERE decision_index=1').fetchone()
        declaration=json.loads(row[0])
        if fault=='text':declaration['submitted_schema_json']+=' '
        elif fault=='hash':declaration['expanded_schema_sha256']='0'*64
        elif fault=='fields':declaration['fact_references']=[]
        value=None if fault=='missing' else json.dumps(declaration)
        store.db.execute('UPDATE runtime_report_attempts SET report_contract_declaration=? WHERE decision_index=1',(value,))
        with pytest.raises(ValueError,match='restriction_mapping_reference_redelivery_'):
            RestrictionMappingReferences(store,workflow.run_id)._attempt(workflow.binding_context(parent.source),1)


def test_failed_compact_redelivery_retains_actual_declaration_and_frozen_values(tmp_path,monkeypatch):
    store,case,workflow,parent,child,_=configured_case(tmp_path,monkeypatch)
    with store:
        freeze_name(workflow,case,parent,child)
        before=tuple(store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',(child.source.episode_id,)).fetchone())
        selected,unit=redelivery(workflow,parent,status=False)
        assert unit.failure is not None
        row=store.db.execute('SELECT * FROM runtime_report_attempts WHERE decision_index=1').fetchone()
        assert row['form'] is None and row['failure'] is not None
        assert json.loads(row['report_contract_declaration'])['submitted_schema_json']==selected['schema_json']
        assert tuple(store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',(child.source.episode_id,)).fetchone())==before
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==1
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0


@pytest.mark.parametrize('fault',['missing','text'])
def test_original_compact_commission_requires_original_declaration(tmp_path,monkeypatch,fault):
    from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
    store,case,workflow,parent,child,_=configured_case(tmp_path,monkeypatch)
    with store:
        freeze_name(workflow,case,parent,child)
        row=workflow.journal.row('runtime_episodes',child.source.episode_id)
        request=json.loads(row['request'])
        if fault=='missing':del request['message']['report_contract_declaration']
        else:request['message']['report_contract_declaration']['submitted_schema_json']+=' '
        store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
            (json.dumps(request),child.source.episode_id))
        with pytest.raises(ValueError,match='restriction_mapping_reference_original_commission_'):
            RestrictionMappingReferences(store,workflow.run_id)._attempt(workflow.binding_context(parent.source),0)


def test_journal_migration_preserves_old_attempts_and_unknown_proof(tmp_path):
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.state import Store
    with Store(tmp_path/'store') as store:
        store.db.execute('CREATE TABLE runtime_report_attempts (run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,delivery_ref TEXT,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,PRIMARY KEY(run_id,parent_episode_id,decision_index))')
        old=('historic','parent',0,'delivery','child','{"historic":true}','{}',None)
        store.db.execute('INSERT INTO runtime_report_attempts VALUES (?,?,?,?,?,?,?,?)',old)
        Journal(store,'current')
        row=store.db.execute('SELECT * FROM runtime_report_attempts').fetchone()
        assert tuple(row)[:8]==old
        assert row['report_contract_declaration'] is None and row['timing_receipts'] is None
        Journal(store,'current')
        assert tuple(store.db.execute('SELECT * FROM runtime_report_attempts').fetchone())==tuple(row)


@pytest.mark.parametrize('fault',['missing','text'])
def test_attempt_reconstruction_cannot_replace_recorded_declaration(tmp_path,monkeypatch,fault):
    from gene_annotation_episode.runtime import TypedReportContract, WorkflowError
    store,case,workflow,parent,child,_=configured_case(tmp_path,monkeypatch)
    with store:
        freeze_name(workflow,case,parent,child)
        redelivery(workflow,parent)
        row=store.db.execute('SELECT * FROM runtime_report_attempts WHERE decision_index=1').fetchone()
        record=json.loads(row['contract'])
        contract=TypedReportContract(record['decision'],record['measurements']['schema'],lambda *_:True)
        declaration=json.loads(row['report_contract_declaration'])
        args=(parent.source.episode_id,1,row['delivery_ref'],child.source.episode_id,contract)
        workflow.save_attempt(*args,form=json.loads(row['form']),report_contract_declaration=declaration)
        if fault=='text':declaration['submitted_schema_json']+=' '
        else:declaration=None
        with pytest.raises(WorkflowError,match='recorded attempt'):
            workflow.save_attempt(*args,form=json.loads(row['form']),report_contract_declaration=declaration)
        assert dict(store.db.execute('SELECT * FROM runtime_report_attempts WHERE decision_index=1').fetchone())==dict(row)


def test_compact_empty_source_closes_in_actual_shared_method_loop(tmp_path,monkeypatch):
    """Configured engineering presentation and fixture choices, real loop/records."""
    import asyncio
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
    from gene_annotation_episode.state import Store
    from test_scientific_process_runtime import Scenario, action, supplied_molecule_reasoning
    from test_runtime_decision_exchanges import ConversationProvider, select
    with Store(tmp_path/'store') as store:
        case=Scenario(tmp_path,store)
        commission=case.commission()
        commission['selection'].update(schema_json=json.dumps(submitted()),initial_report_json='{"status":"unresolved"}')
        received=[]
        def parent(context):
            received.extend(provider.views[root.source.episode_id]['child_reports'])
            assert received[0]['selected']==[]
            return select(supplied_molecule_reasoning(store,case.scope))
        provider=ConversationProvider([select(commission),
            select(action('fixture.inspect',{'value':2},'unresolved')),
            select(action('process.entry',{'option_id':'P01'},'qualified')),
            select(action('process.entry',{'option_id':'P77'},'qualified')),
            select(action('process.entry',{'option_id':'P01'},'qualified')),parent])
        workflow=case.workflow(provider,decision_protocol='decision_exchange_v1')
        monkeypatch.setattr(workflow.scientific_process_binding,'contract_information_profile',
            lambda context:PROFILE if context.role=='annotation' else None,raising=False)
        root=workflow.build('annotation','root','Read explicit selected restriction facts',case.scope)
        record=asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        row=store.db.execute('SELECT episode_id,request,state FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()
        assert json.loads(row['request'])['message']['report_contract_declaration']['submitted_schema_json']==commission['selection']['schema_json']
        assert json.loads(workflow.journal.row('runtime_forms',row['episode_id'])['facts'])[SOURCE]==[]
        assert len(received)==1
        assert len(case.tools.calls)==1
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==6
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==6
