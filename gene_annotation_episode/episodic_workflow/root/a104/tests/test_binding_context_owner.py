"""Original/canonical source epochs; controlled value/type boundaries only."""
from dataclasses import FrozenInstanceError
import os
from types import MappingProxyType
import pytest
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext as RootContext
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext, native_observation_options
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.form_reference_validation import _binding_key

@pytest.fixture
def canonical_epoch():
    phase = os.environ['A104_CONTEXT_SOURCE_EPOCH']
    assert phase in {'original', 'canonical'}
    return phase == 'canonical'

def operands():
    return dict(run_id='r', episode_id='e', role='results', path=(('results', 'selected'),),
        scope={'subjects': ['x']}, assignment={'nested': {'values': [1, True, None]}},
        request={'source': 'request'}, received_record_refs=('second', 'first', 'second'))

def test_all_eight_values_and_original_seven_field_record():
    values = operands(); context = BindingContext(**values)
    assert context.received_record_refs == ('second', 'first', 'second')
    assert set(context.as_record()) == set(values) - {'received_record_refs'}
    assert context.as_record() == RootContext(**values).as_record()
    assert isinstance(context.scope, MappingProxyType) and context.scope['subjects'] == ('x',)
    assert context.assignment['nested']['values'] == (1, True, None)
    values['scope']['subjects'].append('later')
    assert context.scope['subjects'] == ('x',)
    with pytest.raises(FrozenInstanceError): context.role = 'changed'
    with pytest.raises(TypeError): context.assignment['nested']['values'] = ()

def test_nominal_owner_change_is_explicit(canonical_epoch):
    own, root = BindingContext(**operands()), RootContext(**operands())
    assert (BindingContext is RootContext) is canonical_epoch
    assert (own == root) is canonical_epoch
    assert type(own) is BindingContext
    assert own.received_record_refs == root.received_record_refs

@pytest.mark.parametrize('field,value,error,message', [
    ('run_id', '', ValueError, 'nonempty_run_id_required'),
    ('episode_id', '', ValueError, 'nonempty_episode_id_required'),
    ('role', '', ValueError, 'nonempty_role_required'),
    ('path', (('launch', 'selected'),), ValueError, 'binding_context_path_must_match_role'),
    ('received_record_refs', {'bad'}, ValueError, 'received_record_refs_must_be_explicit_references'),
    ('scope', [], TypeError, 'scope_must_be_mapping'),
    ('assignment', None, TypeError, 'assignment_must_be_mapping'),
    ('request', 1, TypeError, 'request_must_be_mapping'),
])
def test_original_constructor_error_identity(field, value, error, message):
    values = operands(); values[field] = value
    for constructor in (BindingContext, RootContext):
        with pytest.raises(error) as observed: constructor(**values)
        assert type(observed.value) is error and str(observed.value) == message

def test_nonfinite_json_remains_rejected():
    values = operands(); values['assignment'] = {'value': float('nan')}
    for constructor in (BindingContext, RootContext):
        with pytest.raises(ValueError): constructor(**values)

def test_native_forwarding_preserves_instance_and_private_error(canonical_epoch):
    own, root = BindingContext(**operands()), RootContext(**operands())
    assert native_observation_options('controlled-native-operation', own)['observation_context'] is own
    if canonical_epoch:
        assert native_observation_options('controlled-native-operation', root)['observation_context'] is root
    else:
        with pytest.raises(ContractError) as observed: native_observation_options('controlled-native-operation', root)
        assert type(observed.value) is ContractError
        assert str(observed.value) == 'progress_observation_context_required'
    with pytest.raises(ContractError) as observed: native_observation_options(None, own)
    assert type(observed.value) is ContractError
    assert str(observed.value) == 'progress_observation_context_requires_native_operation'
    assert native_observation_options(None, None) == {}

def test_exact_cache_key_and_isinstance_remain_distinct(canonical_epoch):
    class Subcontext(BindingContext): pass
    child = Subcontext(**operands())
    assert native_observation_options('controlled-native-operation', child)['observation_context'] is child
    assert _binding_key(child) != _binding_key(child)
    own = BindingContext(**operands()); root = RootContext(**operands())
    assert isinstance(_binding_key(own), str)
    assert isinstance(_binding_key(root), str) is canonical_epoch
    other = BindingContext(**dict(operands(), received_record_refs=('first', 'second')))
    assert own.as_record() == other.as_record()
    assert _binding_key(own) != _binding_key(other)
    assert _binding_key(own) == _binding_key(BindingContext(**operands()))

def test_saved_seven_field_reconstruction_keeps_original_empty_refs():
    context = BindingContext(**operands())
    saved = BindingContext(**context.as_record())
    assert saved.received_record_refs == ()
    assert saved.as_record() == context.as_record()
    assert _binding_key(saved) != _binding_key(context)
