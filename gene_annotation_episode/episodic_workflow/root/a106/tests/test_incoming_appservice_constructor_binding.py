"""Seven actual incoming construction paths; no complete scientific receipt claim.

Four reader objects use real native result-reader objects and an owned Store.
Three saved-control readers use explicit synthetic, empty-request engineering
controls and actual Journal/context/artifact authentication. The constructor
observer delegates to the real class and replaces no authority method.
"""
import hashlib
import importlib
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a106.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a106.state import Store

PREFIX='gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.'


def selected_module(name):
    return importlib.import_module(PREFIX+name)


def assert_original_document(custody,store,run_id):
    reader=selected_module('appservice_read_contracts')
    assert type(custody) is AppServiceCustody
    assert custody.store is store and custody.run_id==run_id
    assert custody._contract_validator is reader.validate_contract
    assert custody._validate('RequiredApplication','Variation')=='Variation'
    assert custody._validate('RequiredApplication','GenomeAnnotation')=='GenomeAnnotation'
    assert custody._validate('Range',[2,5])==[2,5]


@pytest.mark.parametrize('module_name,class_name,custody_field,native_module,native_class',[
    ('flux_balance_returns','FluxBalanceReturns','declarations','native_flux_balance_results','NativeFluxBalanceResults'),
    ('flux_balance_execution_inputs','FluxBalanceExecutionInputs','custody',None,None),
    ('expression_nmf_returns','ExpressionNMFReturns','declarations','native_expression_nmf_results','NativeExpressionNMFResults'),
    ('fluorescence_returns','FluorescenceReturns','declarations','native_fluorescence_results','NativeFluorescenceResults'),
])
def test_actual_incoming_reader_constructor_binds_original_document(tmp_path,module_name,class_name,custody_field,native_module,native_class):
    with Store(tmp_path/'state') as store:
        owner=SimpleNamespace(store=store,run_id='controlled-incoming-reader',directory=tmp_path/'owned-reader')
        if native_module is not None:
            result_type=getattr(selected_module(native_module),native_class)
            results=result_type(owner)
            setattr(owner,native_module,results)
        reader=getattr(selected_module(module_name),class_name)(owner)
        assert_original_document(getattr(reader,custody_field),store,owner.run_id)
        if native_module is not None:
            assert reader.results is results and type(reader.results) is result_type


@pytest.mark.parametrize('module_name',[
    'flux_balance_request_binding','macs2_peak_request_binding','lumpy_request_binding',
])
def test_actual_saved_control_reader_constructs_original_document_custody(tmp_path,monkeypatch,module_name):
    module=selected_module(module_name)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope();run_id='controlled-saved-input'
        journal=Journal(store,run_id)
        path=(('launch','controlled-reader'),);episode_id=EpisodeRef(run_id,path).episode_id
        assignment={'version':module.LAUNCH_VERSION,'requests':{}}
        request={'goal':{'objective':'Inspect a saved engineering control','scope':scope},
            'message':{'scope':scope,'episode_assignment':assignment},
            'report_contract':{'decision':'Report construction only'}}
        context=BindingContext(run_id,episode_id,'launch',path,scope,assignment,request)
        journal.save('runtime_episodes',{'episode_id':episode_id,'path':canonical(path),
            'request':canonical(request),'initial_credit':0.0,'state':'open'})
        value={'version':module.CONTROL_VERSION,'run_id':run_id,'episode_id':episode_id,
            'context':context.as_record(),'requests':[]}
        raw=canonical(value).encode();reference=store.artifact(raw,'application/json')
        file={'artifact_ref':reference,'sha256':hashlib.sha256(raw).hexdigest(),
            'size_bytes':len(raw),'format':module.CONTROL_VERSION}
        assert module._TABLE in {'runtime_flux_balance_request_bindings','runtime_macs2_peak_request_bindings','runtime_lumpy_request_bindings'}
        with store.transaction():
            store.db.execute(f'CREATE TABLE {module._TABLE} (run_id TEXT NOT NULL, episode_id TEXT NOT NULL, file TEXT NOT NULL, PRIMARY KEY(run_id,episode_id))')
            store.db.execute(f'INSERT INTO {module._TABLE} (run_id,episode_id,file) VALUES (?,?,?)',(run_id,episode_id,canonical(file)))
        observed=[]
        actual_class=module.AppServiceCustody
        assert actual_class is AppServiceCustody
        def observe_constructor(*args,**kwargs):
            actual=actual_class(*args,**kwargs)
            observed.append(actual)
            return actual
        monkeypatch.setattr(module,'AppServiceCustody',observe_constructor)
        result=module.read_request_binding(store,run_id,episode_id)
        assert result=={**plain(value),'file':file}
        assert len(observed)==1
        assert_original_document(observed[0],store,run_id)
        assert store.get_artifact(reference)==raw
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
