"""Original prepared-wrapper request hashes retain Unicode and delivery custody.

Synthetic records use the original JSON digest, not any current axis digest.
No foreign producer, worker, policy constructor or scientific assessment runs.
"""
import hashlib
from importlib import import_module
import json
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]

def original_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                     allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize('change',[None,'unicode_hash','missing_parent_delivery'])
def test_prepared_wrapper_preserves_original_unicode_hash_and_parent_delivery(tmp_path,change):
    module=lambda name:import_module(PACKAGE+'.'+name)
    helper=module('library.retained_input_authority.prepared_results')
    identity=module('library.retained_input_authority.prepared_record_identity')
    BindingContext=module('episode_bindings').BindingContext
    EpisodeRef=module('method_loop.identities').EpisodeRef
    original_request={'original_subject':'β-chain','qualifier':'unresolved α/β correspondence'}
    expected=original_digest(original_request)
    alternate=hashlib.sha256(json.dumps(original_request,sort_keys=True,separators=(',',':'),
                                      allow_nan=False,ensure_ascii=False).encode()).hexdigest()
    assert expected!=alternate
    assert identity.digest(original_request)==expected
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        run='synthetic-unicode-preparation'
        parent_path=(('perturbation_evidence','original-parent'),)
        path=(*parent_path,('results','child_0'))
        parent_id=EpisodeRef(run,parent_path).episode_id
        handoff={'original':'controlled handoff retained verbatim'}
        selected={'handoff':handoff}
        native={'version':'a102_structural_results_assignment_v1','job_ref':'original-job',
                'handoff_source_ref':'original-source','scope_sha256':original_digest(scope),
                'original_job_request_sha256':alternate if change=='unicode_hash' else expected}
        actual={**selected,'adapter_assignment':native}
        request={'message':{'scope':scope,'episode_assignment':actual}}
        child=BindingContext(run,EpisodeRef(run,path).episode_id,'results',path,scope,actual,request)
        store.db.execute('CREATE TABLE a102_resource_jobs(run_id TEXT,job_ref TEXT,handoff TEXT,handoff_source_ref TEXT,request TEXT,scope TEXT)')
        store.db.execute('CREATE TABLE a102_handoff_deliveries(run_id TEXT,episode_id TEXT,job_ref TEXT)')
        store.db.execute('INSERT INTO a102_resource_jobs VALUES(?,?,?,?,?,?)',
            (run,'original-job',json.dumps(handoff),'original-source',json.dumps(original_request),json.dumps(scope)))
        if change!='missing_parent_delivery':
            store.db.execute('INSERT INTO a102_handoff_deliveries VALUES(?,?,?)',
                             (run,parent_id,'original-job'))
        before=store.db.total_changes
        assert helper.validate_results_preparation(store,run,selected,actual,child) is (change is None)
        assert store.db.total_changes==before
