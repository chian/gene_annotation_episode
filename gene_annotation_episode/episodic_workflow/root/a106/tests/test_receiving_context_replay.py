"""Unchanged inline identity and controlled saved operation replay; no native work."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from .receiving_context_controls import own, canonical_type, saved_context, AXIS, CASES


def forbidden(*args,**kwargs):
    raise AssertionError('cached controlled operation attempted target acquisition')


def make_provider(store,tmp_path,kind):
    if kind == 'execution':
        return own('execution_progress').ExecutionProgressProvider(store,
            run_id='controlled-receiving-context',directory=tmp_path,resources={},
            api_execution=None,log_window_bytes=8,log_roles=('stdout',))
    jobs = SimpleNamespace(config={'registry_ref':'controlled-registry'},status=forbidden)
    return own('homology_progress').HomologyProgressProvider(store,jobs,
        run_id='controlled-receiving-context',log_window_bytes=8,log_roles=('native_text',))


KINDS = ('execution','homology') if AXIS == 'a101' else ('execution',)




@pytest.mark.parametrize('kind', KINDS)
def test_actual_cached_observe_signature_and_changed_selection_rejection(tmp_path,kind,monkeypatch):
    module = own(kind+'_progress')
    with own('state').Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope = store.validate_scope()
        provider = make_provider(store,tmp_path,kind)
        field_name = 'fields' if kind == 'execution' else 'requested_fields'
        selection = {'operation':'observe','handle':'controlled-handle',field_name:[], 'scope':scope}
        expected_signature = (module.digest({'selection':selection,'provider':provider.as_record()})
            if kind == 'execution' else module.content_digest({**selection,'provider':provider.as_record()}))
        signature,empty = provider._operation('controlled-replay',selection)
        assert signature == expected_signature and empty is None
        payload = {'controlled_cache_fixture':True,'original_fields':[],
                   'qualification':'No scientific observation was acquired by this control.'}
        with store.transaction(): provider._save_operation('controlled-replay',signature,payload)
        if kind == 'execution': monkeypatch.setattr(provider.targets,'read_target',forbidden)
        else: monkeypatch.setattr(provider,'_target',forbidden)
        before = store.db.total_changes
        assert provider.observe('controlled-handle',[],scope,operation_key='controlled-replay') == payload
        assert store.db.total_changes == before
        with pytest.raises(own('domain').ContractError,match=kind+'_progress_operation_identity_conflict'):
            provider.observe('controlled-handle',['execution_status'],scope,operation_key='controlled-replay')
        assert store.db.total_changes == before
    # Reopen the real Store and original provider against unchanged cache data.
    with own('state').Store(tmp_path/'store') as reopened:
        cold = make_provider(reopened,tmp_path,kind)
        if kind == 'execution': monkeypatch.setattr(cold.targets,'read_target',forbidden)
        else: monkeypatch.setattr(cold,'_target',forbidden)
        before = reopened.db.total_changes
        assert cold.observe('controlled-handle',[],scope,operation_key='controlled-replay') == payload
        assert reopened.db.total_changes == before


@pytest.mark.parametrize('which', ('own','canonical'))
def test_execution_native_selection_replay_retains_context_record(tmp_path,monkeypatch,which):
    cls = own('episode_bindings').BindingContext if which == 'own' else canonical_type()
    with own('state').Store(tmp_path/'store') as store:
        context,_ = saved_context(store,cls)
        provider = make_provider(store,tmp_path,'execution')
        scope = store.validate_scope()
        selection = {'operation':'observe','handle':'controlled-handle','fields':[], 'scope':scope,
            'native_operation':'controlled-native-choice','observation_context':context.as_record()}
        signature,old = provider._operation('selected-context',selection)
        assert old is None
        payload = {'controlled_cache_fixture':True,'qualification':'Original saved selection only'}
        with store.transaction(): provider._save_operation('selected-context',signature,payload)
        monkeypatch.setattr(provider.targets,'read_target',forbidden)
        before = store.db.total_changes
        assert provider.observe('controlled-handle',[],scope,operation_key='selected-context',
            native_operation='controlled-native-choice',observation_context=context) == payload
        with pytest.raises(own('domain').ContractError,match='execution_progress_operation_identity_conflict'):
            provider.observe('controlled-handle',[],scope,operation_key='selected-context',
                native_operation='different-native-choice',observation_context=context)
        assert store.db.total_changes == before
