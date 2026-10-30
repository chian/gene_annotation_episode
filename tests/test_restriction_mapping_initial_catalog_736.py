"""Explicit initial identifiers and original catalog cutoffs, engineering only.

The Workflow, Store, forms, selected commissions and receipts are real. The
publication/job authority seam is an unavailable namespace fixture, with no
scientific measurements, public restriction ToolInfo or native operation.
"""
from copy import deepcopy
import json
import os
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical, identity, obj
from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
from gene_annotation_episode.state import Store
from test_scientific_process_runtime import Scenario
from test_runtime import ScriptedProvider


pytestmark=pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,reason='requires bounded529')
NAMESPACE='restriction_enzyme'


def context_of(workflow,episode):
    return workflow.binding_context(episode.source)


def seeded_case(tmp_path,monkeypatch,*,receipt=True,kind='own_action',source_index=1):
    store=Store(tmp_path/'store')
    case=Scenario(tmp_path,store)
    workflow=case.workflow(ScriptedProvider([]))
    root=workflow.build('annotation','root','Compare supplied enzyme identities',case.scope)
    parent=workflow.selected(root.source,case.commission()['selection'],0).child
    result=SimpleNamespace(store=store,case=case,workflow=workflow,root=root,parent=parent,
        states={},sources={})
    import gene_annotation_episode.restriction_mapping_jobs as jobs
    import gene_annotation_episode.restriction_mapping_publication as publication
    def state(self,key):
        if key not in result.states:raise ValueError('engineering_unbound_operation')
        return deepcopy(result.states[key])
    def published(store,source_ref,*,scope):
        if source_ref not in result.sources:raise ValueError('engineering_unbound_source')
        return deepcopy(result.sources[source_ref])
    monkeypatch.setattr(jobs.RestrictionMappingJobs,'publication_state',state)
    monkeypatch.setattr(publication,'read_published_restriction_result',published)
    store.db.execute('CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT NOT NULL,name TEXT NOT NULL,arguments TEXT NOT NULL,scope TEXT NOT NULL,result TEXT NOT NULL)')
    source=seed_catalog(result,parent,index=1)
    result.source=source
    if receipt:
        workflow.receipts.receive(parent.source.episode_id,[source],kind=kind,source_index=source_index)
    return result


def seed_catalog(result,parent,*,index,names=('EcoRI','BcgI')):
    """Original-operation authority stub, never a native measurement."""
    store,workflow,scope=result.store,result.workflow,result.case.scope
    sequence=scope['subject_refs'][0]
    source=store.put('source',{'provider':'engineering736.namespace_only','accession':parent.source.episode_id+':'+str(index),
        'uri':None,'artifact_ref':store.artifact('ENGINEERING ONLY: no native restriction data'),
        'text_ref':None,'request_ref':None,'version':'engineering','retrieved_at':None},origin='tool')['id']
    input_source=store.get_input(sequence)['source_ref']
    args={'mode':'native','sequence_ref':sequence,'enzyme_names':list(names)}
    key=f'{workflow.run_id}:{parent.source.episode_id}:{index}'
    operation_ref=identity('operation',{'key':key,'name':'find_restriction_sites','arguments':args})
    artifact=store.artifact('ENGINEERING namespace authority seam, no native bytes')
    body={'operation_key':key,'operation_ref':operation_ref,'tool_name':'find_restriction_sites',
        'arguments':args,'scope':scope,'status':'partial','work_mode':'native',
        'input_source_ref':input_source,'prior_result_source_ref':None,
        'files':{'native':{'artifact_ref':artifact},'mapping':None},'failure_code':'reader_unavailable'}
    outcome={'status':'partial','operation_ref':operation_ref,'record_refs':[input_source,source],
        'result':{'source_ref':source,'sequence_ref':sequence,'namespace':'subject',
            'input_source_ref':input_source,'work_mode':'native','native_artifact_ref':artifact,
            'mapping_artifact_ref':None,'data_status':'unavailable','topology':None,'population':None},
        'feedback':None}
    store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
        (key,operation_ref,'find_restriction_sites',canonical(args),canonical(scope),canonical(outcome)))
    workflow.journal.save('runtime_actions',{'episode_id':parent.source.episode_id,'decision_index':index,
        'action':canonical({'kind':'tool','tool':'find_restriction_sites','arguments':args}),
        'result':canonical(outcome),'credit':None})
    result.states[key]={'published_source_ref':source,'published_outcome':deepcopy(outcome)}
    result.sources[source]={'source':{'id':source},'body':body,
        'sequence_binding':{'sequence_ref':sequence,'namespace':'subject','source_ref':input_source},
        'mapping':None,'native':{'catalog':{'enzymes':[{'name':name} for name in names]}},'catalog':None}
    return source


def initial_choice(result,*,name='EcoRI',field='enzyme',namespace=NAMESPACE):
    schema=obj({field:{'type':'string','format':'identifier','x-reference-namespace':namespace}})
    selected=result.case.commission()['selection']
    selected.update(schema_json=json.dumps(schema),initial_report_json=json.dumps({field:name}))
    return selected


def test_actual_nested_initial_name_uses_original_parent_catalog_and_cutoff(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        workflow=result.workflow
        selected=initial_choice(result)
        child=workflow.selected(result.parent.source,selected,2).child
        context=context_of(workflow,child)
        resolve=workflow.resolver(result.case.scope,context=context)
        assert resolve('EcoRI',NAMESPACE) is True
        assert resolve('BcgI',NAMESPACE) is False
        assert resolve('ecori',NAMESPACE) is False
        assert plain(context.request)['message']['initial_report']=={'enzyme':'EcoRI'}
        assert result.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0


def saved_rows(result):
    return {table:[dict(row) for row in result.store.db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
        for table in ('runtime_episodes','runtime_actions','runtime_forms','runtime_observations',
            'runtime_report_attempts','runtime_record_receipts','runtime_receipt_inheritance')}


@pytest.mark.parametrize('name',['ecori','EcoRII','unknown'])
def test_unknown_initial_identifier_rolls_back_original_construction(tmp_path,monkeypatch,name):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        before=saved_rows(result)
        with pytest.raises(ReportBoundaryError) as error:
            result.workflow.selected(result.parent.source,initial_choice(result,name=name),2)
        assert error.value.diagnostic['code']=='unknown_reference'
        assert saved_rows(result)==before


@pytest.mark.parametrize('receipt,kind,index',[(False,'own_action',1),
    (True,'initial',1),(True,'decision_input',1),(True,'child_form',1),
    (True,'report_redelivery',1),(True,'own_action',0),(True,'own_action',2)])
def test_initial_name_needs_own_completed_source_receipt(tmp_path,monkeypatch,receipt,kind,index):
    result=seeded_case(tmp_path,monkeypatch,receipt=receipt,kind=kind,source_index=index)
    with result.store:
        before=saved_rows(result)
        with pytest.raises(ReportBoundaryError,match='unavailable'):
            result.workflow.selected(result.parent.source,initial_choice(result),2)
        assert saved_rows(result)==before


@pytest.mark.parametrize('shape',['nested','array'])
def test_typed_initial_names_follow_existing_closed_form_semantics(tmp_path,monkeypatch,shape):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        node={'type':'string','format':'identifier','x-reference-namespace':NAMESPACE}
        payload={'nested':{'chosen':'EcoRI'}} if shape=='nested' else {'chosen':['EcoRI']}
        schema=obj({'nested':obj({'chosen':node})}) if shape=='nested' else obj({'chosen':{'type':'array','items':node}})
        selected=initial_choice(result)
        selected.update(schema_json=json.dumps(schema),initial_report_json=json.dumps(payload))
        child=result.workflow.selected(result.parent.source,selected,2).child
        reader=RestrictionMappingReferences(result.store,result.workflow.run_id)
        assert reader.resolve(context_of(result.workflow,child),'EcoRI',NAMESPACE) is True
        assert reader.resolve(context_of(result.workflow,child),'BcgI',NAMESPACE) is False


@pytest.mark.parametrize('format',['reference','accession'])
def test_existing_semantic_reference_formats_are_preserved(tmp_path,monkeypatch,format):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        selected=initial_choice(result)
        schema=json.loads(selected['schema_json'])
        schema['properties']['enzyme']['format']=format
        selected['schema_json']=json.dumps(schema)
        child=result.workflow.selected(result.parent.source,selected,2).child
        assert result.workflow.resolver(result.case.scope,context=context_of(result.workflow,child))('EcoRI',NAMESPACE) is True


def test_untyped_name_and_field_label_do_not_transfer_catalog_authority(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        selected=initial_choice(result)
        selected['schema_json']=json.dumps(obj({'enzyme':{'type':'string','enum':['EcoRI']}}))
        child=result.workflow.selected(result.parent.source,selected,2).child
        context=context_of(result.workflow,child)
        assert result.workflow.resolver(result.case.scope,context=context)('EcoRI',NAMESPACE) is False
        assert 'restriction_mapping_results' not in result.workflow.facts(child.source)


def test_other_reference_namespace_does_not_create_enzyme_knowledge(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        selected=initial_choice(result,name=result.case.scope['subject_refs'][0],namespace='subject')
        child=result.workflow.selected(result.parent.source,selected,2).child
        assert result.workflow.resolver(result.case.scope,context=context_of(result.workflow,child))('EcoRI',NAMESPACE) is False


def test_initial_name_is_explicit_at_every_generation(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        selected=initial_choice(result)
        child=result.workflow.selected(result.parent.source,selected,2).child
        grandchild=result.workflow.selected(child.source,selected,0).child
        context=context_of(result.workflow,grandchild)
        assert result.workflow.resolver(result.case.scope,context=context)('EcoRI',NAMESPACE) is True
        before=saved_rows(result)
        with pytest.raises(ReportBoundaryError,match='unavailable'):
            result.workflow.selected(child.source,initial_choice(result,name='BcgI'),1)
        assert saved_rows(result)==before
        assert result.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]==0


def test_ancestor_catalog_cannot_skip_uninformed_intermediate_episode(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        intermediate=result.workflow.selected(result.parent.source,result.case.commission()['selection'],2).child
        before=saved_rows(result)
        with pytest.raises(ReportBoundaryError,match='unavailable'):
            result.workflow.selected(intermediate.source,initial_choice(result),0)
        assert saved_rows(result)==before


def test_late_earlier_decision_receipt_cannot_replace_original_frozen_authority(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        workflow=result.workflow
        selected=initial_choice(result)
        child=workflow.selected(result.parent.source,selected,2).child
        context=context_of(workflow,child)
        original=deepcopy(plain(context.request))
        cutoff=original['message']['knowledge_inheritance']['through_receipt_index']
        # Deliberate engineering custody corruption: the old receipt ceases
        # to establish own-action delivery. A newly delivered earlier action
        # may support the current parent but cannot enter the old child prefix.
        result.store.db.execute("UPDATE runtime_record_receipts SET receipt_kind='child_form' WHERE episode_id=? AND record_ref=?",
            (result.parent.source.episode_id,result.source))
        late=seed_catalog(result,result.parent,index=0)
        workflow.receipts.receive(result.parent.source.episode_id,[late],kind='own_action',source_index=0)
        late_index=result.store.db.execute('SELECT receipt_index FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?',
            (result.parent.source.episode_id,late)).fetchone()[0]
        assert late_index>cutoff
        assert workflow.resolver(result.case.scope,context=context)('EcoRI',NAMESPACE) is False
        assert workflow.resolver(result.case.scope,context=context_of(workflow,result.parent))('EcoRI',NAMESPACE) is True
        assert plain(context.request)==original
        assert workflow.receipts.manifest(child.source.episode_id)==original['message']['knowledge_inheritance']


def test_reconstruction_retains_original_request_cutoff_and_no_new_credit(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        workflow=result.workflow
        selected=initial_choice(result)
        child=workflow.selected(result.parent.source,selected,2).child
        original=workflow.journal.row('runtime_episodes',child.source.episode_id)['request']
        late=seed_catalog(result,result.parent,index=3)
        workflow.receipts.receive(result.parent.source.episode_id,[late],kind='own_action',source_index=3)
        before=saved_rows(result)
        rebuilt=workflow.selected(result.parent.source,selected,2).child
        assert workflow.journal.row('runtime_episodes',rebuilt.source.episode_id)['request']==original
        assert saved_rows(result)==before
        assert workflow.resolver(result.case.scope,context=context_of(workflow,rebuilt))('EcoRI',NAMESPACE) is True


@pytest.mark.parametrize('fault',['initial_text','selected_initial','manifest','purpose','scope','role'])
def test_initial_grant_checks_original_commission_and_manifest(tmp_path,monkeypatch,fault):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        workflow=result.workflow
        child=workflow.selected(result.parent.source,initial_choice(result),2).child
        row=workflow.journal.row('runtime_episodes',child.source.episode_id)
        request=json.loads(row['request'])
        action=workflow.journal.row('runtime_actions',result.parent.source.episode_id,2)
        selected=json.loads(action['action'])
        if fault=='initial_text':request['message']['initial_report']['enzyme']='BcgI'
        elif fault=='selected_initial':selected['initial_report_json']='{"enzyme":"BcgI"}'
        elif fault=='manifest':request['message']['knowledge_inheritance']['through_receipt_index']+=100
        elif fault=='purpose':selected['purpose']='Changed selected purpose'
        elif fault=='scope':selected['scope']={'subject_refs':[]}
        else:selected['role']='literature'
        result.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',(json.dumps(request),child.source.episode_id))
        result.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=2',
            (json.dumps(selected),result.parent.source.episode_id))
        reader=RestrictionMappingReferences(result.store,workflow.run_id)
        changed=reader.context(child.source.episode_id)
        name='BcgI' if fault=='initial_text' else 'EcoRI'
        with pytest.raises(ValueError,match='restriction_mapping_reference_'):
            reader.resolve(changed,name,NAMESPACE)


def test_parent_catalog_needs_original_parent_manifest_identity(tmp_path,monkeypatch):
    result=seeded_case(tmp_path,monkeypatch)
    with result.store:
        workflow=result.workflow
        child=workflow.selected(result.parent.source,initial_choice(result),2).child
        row=workflow.journal.row('runtime_episodes',result.parent.source.episode_id)
        request=json.loads(row['request'])
        request['message']['knowledge_inheritance']['through_receipt_index']+=100
        result.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
            (json.dumps(request),result.parent.source.episode_id))
        with pytest.raises(ValueError,match='inheritance_manifest_conflict'):
            RestrictionMappingReferences(result.store,workflow.run_id).resolve(context_of(workflow,child),'EcoRI',NAMESPACE)
