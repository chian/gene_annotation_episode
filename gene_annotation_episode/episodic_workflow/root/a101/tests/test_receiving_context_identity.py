"""Nominal sharing plus original immutable values/errors and real custody reads."""
from dataclasses import fields, FrozenInstanceError
from copy import deepcopy
from importlib import import_module
import json
from types import MappingProxyType
import pytest
from .receiving_context_controls import own, canonical_type, operands, saved_context, runtime_shell, CASES


def test_actual_private_alias_is_canonical_class():
    assert own('episode_bindings').BindingContext is canonical_type()
    assert own('episode_return_records').BindingContext is canonical_type()
    assert own('runtime').BindingContext is canonical_type()
    assert own('bvbrc_appservice_custody').BindingContext is canonical_type()


@pytest.mark.parametrize('which', ('own', 'canonical'))
def test_eight_live_fields_seven_saved_fields_and_deep_freezing(which):
    cls = own('episode_bindings').BindingContext if which == 'own' else canonical_type()
    data = operands(); original = deepcopy(data); context = cls(**data)
    assert tuple(f.name for f in fields(cls)) == (
        'run_id','episode_id','role','path','scope','assignment','request','received_record_refs')
    assert tuple(context.as_record()) == ('run_id','episode_id','role','path','scope','assignment','request')
    expected = json.loads(json.dumps({k:v for k,v in original.items() if k != 'received_record_refs'}))
    assert context.as_record() == expected
    assert context.received_record_refs == ('controlled-reference',)
    assert isinstance(context.assignment, MappingProxyType)
    assert isinstance(context.assignment['context_control'], tuple)
    data['assignment']['context_control'][1]['qualified'] = True
    assert context.as_record() == expected
    result = context.as_record(); result['assignment']['context_control'].append('caller-only')
    assert context.as_record() == expected
    with pytest.raises(FrozenInstanceError): context.role = 'changed'
    with pytest.raises(TypeError): context.assignment['new'] = True
    assert cls(**original) == context
    changed = deepcopy(original); changed['received_record_refs'] = ('other-reference',)
    other = cls(**changed)
    assert other != context and other.as_record() == context.as_record()


@pytest.mark.parametrize('field,value,error,message', (
    ('run_id','',ValueError,'nonempty_run_id_required'),
    ('episode_id','',ValueError,'nonempty_episode_id_required'),
    ('role','',ValueError,'nonempty_role_required'),
    ('path',(),ValueError,'binding_context_path_must_match_role'),
    ('path',(('results','wrong-role'),),ValueError,'binding_context_path_must_match_role'),
    ('received_record_refs',[''],ValueError,'received_record_refs_must_be_explicit_references'),
    ('scope',[],TypeError,'scope_must_be_mapping'),
    ('assignment',[],TypeError,'assignment_must_be_mapping'),
    ('request',[],TypeError,'request_must_be_mapping'),
))
@pytest.mark.parametrize('which', ('own','canonical'))
def test_original_invalid_operands(field,value,error,message,which):
    cls = own('episode_bindings').BindingContext if which == 'own' else canonical_type()
    args = operands(); args[field] = value
    with pytest.raises(error, match='^'+message+'$'): cls(**args)


@pytest.mark.parametrize('field', ('scope','assignment','request'))
def test_nonfinite_json_rejected_without_normalization(field):
    args = operands(); args[field] = {'value': float('nan')}
    for cls in (own('episode_bindings').BindingContext, canonical_type()):
        with pytest.raises(ValueError): cls(**args)


def test_cross_constructor_equality_and_received_reference_distinction():
    data = operands()
    assert own('episode_bindings').BindingContext(**data) == canonical_type()(**data)
    changed = deepcopy(data); changed['received_record_refs'] = ('other-reference',)
    assert own('episode_bindings').BindingContext(**data) != canonical_type()(**changed)


@pytest.mark.parametrize('which', ('own','canonical'))
def test_native_choice_forwards_same_context_without_authenticating_custody(which):
    context = (own('episode_bindings').BindingContext if which == 'own' else canonical_type())(**operands())
    options = own('episode_bindings').native_observation_options
    assert options(None,None) == {}
    result = options('controlled-native-choice',context)
    assert result == {'native_operation':'controlled-native-choice','observation_context':context}
    assert result['observation_context'] is context


@pytest.mark.parametrize('operation,context,error', (
    (None,True,'progress_observation_context_requires_native_operation'),
    ('',None,'progress_native_operation_invalid'),
    (7,None,'progress_native_operation_invalid'),
    ('controlled-native-choice',object(),'progress_observation_context_required'),
))
def test_native_choice_keeps_original_errors(operation,context,error):
    with pytest.raises(own('domain').ContractError, match=error):
        own('episode_bindings').native_observation_options(operation,context)


@pytest.mark.parametrize('which', ('own','canonical'))
def test_runtime_real_identity_and_saved_request_check(tmp_path,which):
    cls = own('episode_bindings').BindingContext if which == 'own' else canonical_type()
    with own('state').Store(tmp_path/'store') as store:
        context,journal = saved_context(store,cls)
        host = runtime_shell(context,journal)
        assert callable(own('runtime').Workflow.resolver(host,dict(context.scope),context=context))
        with pytest.raises(ValueError, match='^report_binding_context_identity_mismatch$'):
            own('runtime').Workflow.resolver(host,{},context=context)
        changed = context.as_record(); changed['request']['message']['unrecorded'] = True
        mismatch = cls(**changed)
        with pytest.raises(ValueError, match='^report_binding_context_original_request_mismatch$'):
            own('runtime').Workflow.resolver(host,dict(context.scope),context=mismatch)


def test_runtime_retains_exact_type_rejection(tmp_path):
    cls = own('episode_bindings').BindingContext
    class Subclass(cls): pass
    with own('state').Store(tmp_path/'store') as store:
        context,journal = saved_context(store,cls)
        host = runtime_shell(context,journal)
        for invalid in (Subclass(**context.as_record()), object()):
            with pytest.raises(TypeError, match='^typed_report_binding_context_required$'):
                own('runtime').Workflow.resolver(host,dict(context.scope),context=invalid)


@pytest.mark.parametrize('which', ('own','canonical'))
def test_appservice_receiving_context_authenticates_original_saved_row_readonly(tmp_path,which):
    cls = own('episode_bindings').BindingContext if which == 'own' else canonical_type()
    with own('state').Store(tmp_path/'store') as store:
        context,journal = saved_context(store,cls)
        reader = own('bvbrc_appservice_custody').AppServiceCustody(store,context.run_id)
        before = store.db.total_changes
        original = tuple(store.db.execute('SELECT path,request FROM runtime_episodes').fetchone())
        assert reader.authenticate(context) is context
        restored = reader.context(context.episode_id)
        assert restored.as_record() == context.as_record()
        assert restored.received_record_refs == ()  # Seven-field saved representation, unchanged.
        changed = context.as_record(); changed['request']['message']['unrecorded'] = 'not-original'
        with pytest.raises(own('bvbrc_appservice_custody').AppServiceCustodyError,
                           match='^bvbrc_appservice_custody_original_context_conflict$'):
            reader.authenticate(cls(**changed))
        assert store.db.total_changes == before
        assert tuple(store.db.execute('SELECT path,request FROM runtime_episodes').fetchone()) == original


@pytest.mark.parametrize('row', [row for row in CASES['aliases'] if row['selector_scope']=='module_callable'], ids=lambda row:row['module'])
def test_each_original_literal_helper_resolves_explicit_alias(row):
    # Import the genuine required helper module; invoke only its original finite
    # module/own function with the literal present in that recorded source.
    helper = import_module(row['module'])
    selector = getattr(helper,row['helper'])
    assert selector.__module__ == row['definition_module']
    selected = selector('episode_bindings')
    assert selected is own('episode_bindings')
    assert selected.BindingContext is canonical_type()
