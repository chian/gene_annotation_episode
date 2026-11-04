"""Synthetic supplied material, actual Store ownership/revisions/forms/export."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.export import export_annotation

READS=b'@a\nACGT\n+\nIIII\n@b\nACGTAC\n+\nIIIIII\n@c\nACGTACGTAC\n+\nIIIIIIIIII\n'


def fixture(store,tmp_path):
    path=tmp_path/'reads.fq';path.write_bytes(READS)
    store.create_problem(path,molecule='dna')
    target,=store.targets()
    from gene_annotation_episode import library_targets as lib
    reads=[store.get(lib.read_ref(target['id'],row['id'])) for row in lib._rows(store,target['id'])]
    full=store.validate_scope()
    choices=[]
    for read in reads:
        choices.append(lib.select(store,target['id'],member_refs=[read['member_ref']]))
    subsets=[{'subject_refs':[target['id']],'read_selection_refs':[choice['id']]} for choice in choices]
    return target,reads,full,subsets,choices


def context_science(store,target):
    artifact=store.artifact('Actual synthetic growth assay on sample S.','text/plain')
    source=store.put('source',{'provider':'test','accession':'S','uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None},origin='external')
    sample=store.put('context',{'context_type':'sample','name':'S','source_ref':source['id'],'attributes':[],'related_refs':[target['id']]},origin='caller')
    h=store.put('hypothesis',{'subject_refs':[sample['id']],'predicate':'growth_capability','value':{'type':'enum','value':'present'},'context_refs':[]},origin='reasoning')
    o=store.put('observation',{'subject_refs':[sample['id']],'source_subject_refs':[sample['id']],'kind':'growth_assay','source_ref':source['id'],'measurements':[],'dependencies':[],'anchor':None},origin='tool')
    return sample,h,o


def assessment_record(h,o,domain,allocation,revision=0):
    row={'hypothesis_ref':h['id'],'observation_ref':o['id'],'extent_basis':'context_allocation','relation':'strengthens','applicability':'direct','condition_refs':[],'assumption_refs':[], 'context_account_scope':domain,'expected_revision':revision}
    if allocation is not None: row['context_scope']=allocation
    return row


def annotation_record(sample,h,a,domain,allocation,revision=0):
    row={'subject_ref':sample['id'],'footprint_kind':'whole_input_context','coherent_sets':[{'interpretations':[{'hypothesis_ref':h['id'],'assessment_refs':[a['id']],'disposition':'supported'}],'context_refs':[]}], 'alternative_refs':[],'resolution':'selected','context_account_scope':domain,'expected_revision':revision}
    if allocation is not None: row['context_scope']=allocation
    return row


def test_semantic_position_set_identity_and_episode_scope_separation(tmp_path):
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,choices=fixture(s,tmp_path)
        union={'subject_refs':full['subject_refs'],'read_selection_refs':[c['id'] for c in choices]}
        selectall=ToolRegistry(s).execute('library.select',{'library_ref':target['id'],'member_refs':[r['member_ref'] for r in reads]})['result']['scope']
        assert s.context_mask_identity(full)==s.context_mask_identity(union)==s.context_mask_identity(selectall)
        assert s.context_mask_measure(union,target['id'])==20
        assert s.context_mask_subset(subsets[0],union)
        assert not s.context_mask_overlap(subsets[0],subsets[1])
        assert s.context_mask_identity({'subject_refs':[]})!=s.context_mask_identity(full)
        with pytest.raises(ContractError):s.validate_scope({'subject_refs':[]})
        with pytest.raises(ContractError):s.validate_scope(union)
        segment=s.coverage(reads[1]['id'])[0]
        split={**subsets[1],'segments':[{**segment,'start':0,'end':3},{**segment,'start':3,'end':6}]}
        assert s.context_mask_identity(split)==s.context_mask_identity(subsets[1])
        # Equal mass is not identity: A[0,4) differs from B[0,4).
        assert s.context_mask_identity(subsets[0])!=s.context_mask_identity({**subsets[1],'segments':[{**segment,'end':4}]})
        sql,params=s.context_mask_target_query(union,target['id'])
        assert sum(r['end']-r['start'] for r in s.db.execute(sql,params))==20
        assert s.db.execute("SELECT count(*) FROM records WHERE record_type='read_subject'").fetchone()[0]==0


def test_current_lineage_full_subset_empty_restored_and_semantic_noop(tmp_path):
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,choices=fixture(s,tmp_path)
        sample,h,o=context_science(s,target)
        a1=s.put('assessment',assessment_record(h,o,full,full),origin='reasoning',scope=full)
        n1=s.put('annotation',annotation_record(sample,h,a1,full,full),origin='reasoning',scope=full)
        alias={'subject_refs':full['subject_refs'],'read_selection_refs':[c['id'] for c in choices]}
        assert s.put('assessment',assessment_record(h,o,alias,alias,1),origin='reasoning',scope=full)==a1
        assert s.put('annotation',annotation_record(sample,h,a1,alias,alias,1),origin='reasoning',scope=full)==n1
        with pytest.raises(ContractError,match='context_allocation_outside_assigned_scope'):
            s.put('assessment',assessment_record(h,o,full,subsets[0],1),origin='reasoning',scope=subsets[0])
        a2=s.put('assessment',assessment_record(h,o,full,subsets[0],1),origin='reasoning',scope=full)
        n2=s.put('annotation',annotation_record(sample,h,a2,full,subsets[0],1),origin='reasoning',scope=full)
        empty={'subject_refs':[]}
        a3=s.put('assessment',assessment_record(h,o,full,empty,2),origin='reasoning',scope=subsets[0])
        n3=s.put('annotation',annotation_record(sample,h,a3,full,empty,2),origin='reasoning',scope=subsets[0])
        # Empty revisions are reportable through immutable domain, not global.
        assert n3 in s.current_annotations(subsets[1])
        assert s.reference_subset([a3['id'],n3['id']],subsets[1])==[a3['id'],n3['id']]
        assert s.count('annotation',subsets[1],current=True)==1
        assert s.query_records('annotation',subsets[1],current_only=True)['records']==[n3]
        assert s.reasoning_view(subsets[1])['annotations']==[n3]
        a4=s.put('assessment',assessment_record(h,o,full,full,3),origin='reasoning',scope=full)
        n4=s.put('annotation',annotation_record(sample,h,a4,full,full,3),origin='reasoning',scope=full)
        assert [a1['revision'],a2['revision'],a3['revision'],a4['revision']]==[1,2,3,4]
        assert s.current_assessments()==[a4] and s.current_annotations()==[n4]
        assert n4['footprint']==[] and o['kind']=='growth_assay' and a4['applicability']=='direct'
        assert a4['context_binding_version']=='fixed_original_position_set_v1'
        assert a4['context_account_sha256']==s.context_mask_identity(full)
        assert a3['context_allocation_sha256']==s.context_mask_identity(empty)
        assert len(s.list('annotation'))==4 and len(s.list('assessment'))==4
        assert s.db.execute("SELECT count(*) FROM current_revisions").fetchone()[0]==2
    with Store(tmp_path/'s') as s:
        assert s.current_annotations()==[n4]
        assert s.get(a1['id'])==a1


def test_context_commit_preserves_independent_rows_and_empty_export(tmp_path):
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,_=fixture(s,tmp_path)
        sample,h,o=context_science(s,target)
        a=s.put('assessment',assessment_record(h,o,full,full),origin='reasoning',scope=full)
        payload={key:[] for key in s.reasoning_schema()['required']}
        payload['assessments']=[{'alias':'bad',**assessment_record(h,o,full,subsets[0],1)},
            {'alias':'own',**assessment_record(h,o,subsets[0],subsets[0])}]
        result=s.commit_reasoning(payload,subsets[0],'mixed')
        assert result['status']=='partial' and result['errors'][0]['code']=='context_allocation_outside_assigned_scope'
        assert result['errors'][0]['current_record_ref']==a['id']
        local=s.get(result['aliases']['own'])
        assert s.current_assessment_subset([a['id'],local['id']])=={a['id']:a,local['id']:local}
        assert result['changed_record_refs']==[local['id']]
        missing=s.put('assessment',assessment_record(h,o,subsets[1],None),origin='reasoning',scope=subsets[1])
        assert 'context_scope' not in missing
        empty=s.put('assessment',assessment_record(h,o,subsets[0],{'subject_refs':[]},1),origin='reasoning',scope=subsets[0])
        ann=s.put('annotation',annotation_record(sample,h,empty,subsets[0],{'subject_refs':[]}),origin='reasoning',scope=subsets[0])
        assert s.current_annotations(subsets[1])==[]
        assert s.reference_subset([ann['id']],subsets[1])==[]
        exported=export_annotation(s,tmp_path/'out.json',scope=subsets[0])
        document=json.loads(Path(exported['json']['path']).read_text())
        assert ann['id'] in document['membership']['current_annotation_refs']
        row=next(r for r in document['records'] if r['id']==ann['id'])
        assert row['context_scope']=={'subject_refs':[]} and row['footprint']==[]
        assert ann['id'] not in document['membership']['source_only_record_refs']
        assert choices_not_required(document)


def choices_not_required(document):
    # Mask reference closure keeps the actual immutable selection rows.
    return any(row['record_type']=='read_selection' for row in document['records'])


def test_context_runtime_signed_revisions_return_actual_parent_facts_without_extra_turns(tmp_path):
    """Scripted reasoning + test-only continuation; no model/provider/native calls."""
    import asyncio
    from test_runtime import ScriptedProvider, FixtureController, obj
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.credit import project_credit
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,_=fixture(s,tmp_path)
        sample,h,o=context_science(s,target)
        schema=obj({'changed':{'type':'array','items':{'type':'string','format':'reference','x-reference-namespace':'annotation'},'x-source':'changed_annotation_refs'},'score':{'type':'number','x-source':'credit'}})
        commission={'selection':{'kind':'child','goal':'Iteratively refine the supplied sample context attribution','scope':full,'purpose':'Receive the actual current allocation revisions and score','schema_json':json.dumps(schema),'initial_report_json':'{}'},'report_update':{}}
        def first(context):
            payload={key:[] for key in s.reasoning_schema()['required']}
            payload['assessments']=[{'alias':'a',**assessment_record(h,o,full,full)}]
            payload['annotation_updates']=[{'alias':'n',**annotation_record(sample,h,{'id':'@a'},full,full)}]
            return {'selection':{'kind':'reason','commit':payload},'report_update':{}}
        def withdraw(context):
            assert context['current_credit']>0
            assert context['current_evidence_vector']['empirical']>0
            payload={key:[] for key in s.reasoning_schema()['required']}
            payload['assessments']=[{'alias':'a',**assessment_record(h,o,full,{'subject_refs':[]},1)}]
            payload['annotation_updates']=[{'alias':'n',**annotation_record(sample,h,{'id':'@a'},full,{'subject_refs':[]},1)}]
            return {'selection':{'kind':'reason','commit':payload},'report_update':{}}
        def parent(context):
            report,=context['child_reports']
            assert report['score']==context['current_credit']==0
            assert set(report['changed'])=={r['id'] for r in s.list('annotation')}
            assert len(report['changed'])==2
            assert s.current_annotations()[0]['context_scope']=={'subject_refs':[]}
            return {'selection':{'kind':'tool','tool':'state.query','arguments':{'kind':'annotation','limit':2,'current_only':True}},'report_update':{}}
        provider=ScriptedProvider([commission,first,withdraw,parent])
        result=asyncio.run(run_workflow(s,ToolRegistry(s),provider=provider,run_dir=tmp_path/'run',controller_factory=lambda path,initial:FixtureController(str(path),initial,2)))
        assert result['completed_actions']==2 and len(provider.contexts)==4
        episodes=list(s.db.execute('SELECT episode_id,path FROM runtime_episodes'))
        child=next(row['episode_id'] for row in episodes if len(json.loads(row['path']))==2)
        child_deltas=[json.loads(row[0])['step']['delta'] for row in s.db.execute('SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',(child,))]
        assert len(child_deltas)==2 and child_deltas[0]>0 and child_deltas[1]<0
        assert sum(child_deltas)==pytest.approx(0)
        assert s.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==4
        assert project_credit(s).credit==0


def test_export_current_context_allocation_uses_mask_not_physical_source_extent(tmp_path):
    """Actual source B stays B; selected A is allocation, not a measured map."""
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,_=fixture(s,tmp_path)
        source_read=reads[1]
        observed=ToolRegistry(s).execute('sequence.inspect',{'subject_ref':source_read['id']})['result']['observation_ref']
        h=s.put('hypothesis',{'subject_refs':[source_read['id']],'predicate':'growth_capability','value':{'type':'enum','value':'unknown'},'context_refs':[]},origin='reasoning')
        a=s.put('assessment',assessment_record(h,{'id':observed},subsets[0],subsets[0]),origin='reasoning',scope=subsets[0])
        assert s.current_assessments(subsets[0])==[a]
        assert not s.scope_covers(s.record_coverage(a),subsets[0])
        output=export_annotation(s,tmp_path/'context-source.json',scope=subsets[0])
        document=json.loads(Path(output['json']['path']).read_text())
        assert a['id'] in document['membership']['current_assessment_refs']
        records={row['id']:row for row in document['records']}
        assert records[a['id']]==a and records[h['id']]==h
        assert records[h['id']]['subject_refs']==[source_read['id']]
        assert records[observed]['subject_refs']==[source_read['id']]
        assert records[a['id']]['context_scope']==subsets[0]


def test_raw_commit_repeated_mask_aliases_normalize_to_existing_lineage_noop(tmp_path):
    with Store(tmp_path/'s') as s:
        target,reads,full,subsets,choices=fixture(s,tmp_path)
        sample,h,o=context_science(s,target)
        a=s.put('assessment',assessment_record(h,o,full,full),origin='reasoning',scope=full)
        n=s.put('annotation',annotation_record(sample,h,a,full,full),origin='reasoning',scope=full)
        repeated={'subject_refs':[target['id'],target['id']], 'read_selection_refs':[choices[2]['id'],choices[0]['id'],choices[1]['id'],choices[0]['id']]}
        payload={key:[] for key in s.reasoning_schema()['required']}
        payload['assessments']=[{'alias':'a',**assessment_record(h,o,repeated,repeated,1)}]
        payload['annotation_updates']=[{'alias':'n',**annotation_record(sample,h,{'id':'@a'},repeated,repeated,1)}]
        result=s.commit_reasoning(payload,full,'semantic-repeated-noop')
        assert result['status']=='completed' and result['errors']==[]
        assert result['aliases']=={'a':a['id'],'n':n['id']}
        assert result['changed_record_refs']==[]
        assert s.current_assessments()==[a] and s.current_annotations()==[n]
        props=s.reasoning_schema()['properties']['assessments']['items']['properties']
        assert 'uniqueItems' not in props['context_account_scope']['properties']['read_selection_refs']
        assert props['assumption_refs']['uniqueItems'] is True
        # Repetition/union is still not an Episode scope contract.
        with pytest.raises(ContractError):s.validate_scope(repeated)
