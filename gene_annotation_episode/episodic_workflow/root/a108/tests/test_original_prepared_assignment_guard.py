"""Retained structural wrapper custody is a reader, independent of its producer.

Synthetic original-format journal rows exercise exact source/request/scope and
parent delivery checks. No structural result or native execution is fabricated.
"""
from importlib import import_module
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]

def module(name):return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('changed_request_hash',[False,True])
def test_original_structural_preparation_requires_exact_recorded_parent_custody(tmp_path,changed_request_hash):
    canonical=module('domain').canonical
    digest=module('execution_contracts' if PACKAGE.endswith('.a101') else 'record_identity').digest
    EpisodeRef=import_module('gene_annotation_episode.episodic_workflow.root.method_loop.identities').EpisodeRef  # a108 has no private method_loop; its modules import the shared root package
    BindingContext=module('episode_bindings').BindingContext
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        store.db.execute('CREATE TABLE a102_resource_jobs(run_id TEXT,job_ref TEXT,handoff TEXT,handoff_source_ref TEXT,request TEXT,scope TEXT)')
        store.db.execute('CREATE TABLE a102_handoff_deliveries(run_id TEXT,episode_id TEXT,job_ref TEXT)')
        run='synthetic-prepared-custody'
        parent_path=(('sample_context_evidence','original-parent'),)
        child_path=(*parent_path,('results','child_0'))
        parent_id=EpisodeRef(run,parent_path).episode_id
        selection={'resource_id':'synthetic-resource','kind':'local',
            'allocation':{'cpu':1,'memory_bytes':1024,'scratch_bytes':1024},
            'capability_binding_ref':'synthetic-registry'}
        handoff={'version':'execution_handoff_v1','execution_handle':'synthetic-job',
            'resource_selection':selection,'submitted_input_versions':[],
            'monitoring':{'provider_id':'synthetic-resource','target_handle':'synthetic-job','contract_ref':'original-monitor'},
            'results':{'provider_id':'synthetic-resource','target_handle':'synthetic-job','contract_ref':'original-results'},
            'checked_at':'original-controlled-check','check_record_refs':['synthetic-check'],
            'state':'usable','failure':None}
        selected={'version':'resource_results_assignment_v1','handoff':handoff,'requested_data_selector':{}}
        original_request={'synthetic_original_request':'preserved'}
        native={'version':'a102_structural_results_assignment_v1','job_ref':'synthetic-job',
            'handoff_source_ref':'synthetic-handoff-source','scope_sha256':digest(scope),
            'original_job_request_sha256':digest({'changed':True} if changed_request_hash else original_request)}
        actual={**selected,'adapter_assignment':native}
        request={'message':{'scope':scope,'episode_assignment':actual}}
        child=BindingContext(run,EpisodeRef(run,child_path).episode_id,'results',child_path,scope,actual,request)
        store.db.execute('INSERT INTO a102_resource_jobs VALUES(?,?,?,?,?,?)',
            (run,'synthetic-job',canonical(handoff),'synthetic-handoff-source',canonical(original_request),canonical(scope)))
        store.db.execute('INSERT INTO a102_handoff_deliveries VALUES(?,?,?)',(run,parent_id,'synthetic-job'))
        reader=module('episode_return_records').EpisodeReturnRecords(store,run,failure_prefix='prepared_original_')
        before=store.db.total_changes
        if changed_request_hash:
            with pytest.raises(ValueError,match='commission_assignment_conflict'):
                reader._results_assignment(selected,child)
        else:
            assert reader._results_assignment(selected,child) is None
        assert store.db.total_changes==before
