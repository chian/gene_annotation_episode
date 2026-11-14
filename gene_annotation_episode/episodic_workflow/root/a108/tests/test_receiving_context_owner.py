"""Generic context identity and original A108 custody; synthetic engineering data."""
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108 import episode_bindings
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a108.form_reference_validation import _binding_key
from gene_annotation_episode.episodic_workflow.root.a108.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a108.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a108.state import Store


def context(**changes):
    fields=dict(run_id='controlled-run',episode_id='controlled-episode',role='literature',
        path=(('literature','controlled'),),scope={'subject_refs':[]},
        assignment={'nested':[{'value':'β'}]},request={'message':{}},
        received_record_refs=['ref-a','ref-a','ref-b'])
    fields.update(changes)
    return BindingContext(**fields)


def test_private_registry_uses_the_actual_generic_class_and_equality():
    expected=context()
    actual=episode_bindings.BindingContext(expected.run_id,expected.episode_id,expected.role,
        expected.path,expected.scope,expected.assignment,expected.request,expected.received_record_refs)
    assert episode_bindings.BindingContext is BindingContext
    assert type(actual) is BindingContext and actual==expected


def test_all_eight_values_preserve_seven_field_saved_form_and_detachment():
    source={'nested':[{'value':'β'}]};actual=context(assignment=source)
    source['nested'][0]['value']='changed outside'
    assert actual.assignment['nested'][0]['value']=='β'
    assert actual.received_record_refs==('ref-a','ref-a','ref-b')
    record=actual.as_record()
    assert list(record)==['run_id','episode_id','role','path','scope','assignment','request']
    assert 'received_record_refs' not in record
    record['assignment']['nested'][0]['value']='changed saved copy'
    assert actual.assignment['nested'][0]['value']=='β'
    with pytest.raises(TypeError): actual.assignment['nested'][0]['value']='mutation'


@pytest.mark.parametrize('changes,error,message',[
    ({'run_id':''},ValueError,'nonempty_run_id_required'),
    ({'path':(('annotation','controlled'),)},ValueError,'binding_context_path_must_match_role'),
    ({'received_record_refs':['']},ValueError,'received_record_refs_must_be_explicit_references'),
    ({'assignment':[]},TypeError,'assignment_must_be_mapping'),
])
def test_original_constructor_failures(changes,error,message):
    with pytest.raises(error,match='^'+message+'$'):context(**changes)


def test_actual_cache_key_accepts_root_exact_type_and_keeps_reference_order():
    actual=context();key=_binding_key(actual)
    assert key==json.dumps([actual.as_record(),actual.received_record_refs],sort_keys=True,separators=(',',':'),allow_nan=False)
    assert key!=_binding_key(replace(actual,received_record_refs=('ref-b','ref-a','ref-a')))
    class Child(BindingContext): pass
    subclass=Child(actual.run_id,actual.episode_id,actual.role,actual.path,actual.scope,actual.assignment,actual.request)
    assert _binding_key(subclass)!=_binding_key(subclass)
    duck=SimpleNamespace(**actual.as_record(),received_record_refs=actual.received_record_refs)
    assert _binding_key(duck)!=_binding_key(duck)


def test_actual_native_options_preserve_original_context_without_authenticating_it():
    actual=context()
    result=episode_bindings.native_observation_options('synthetic-operation',actual)
    assert result=={'native_operation':'synthetic-operation','observation_context':actual}
    assert result['observation_context'] is actual
    assert episode_bindings.native_observation_options(None,None)=={}
    for operation,value,code in [
        (None,actual,'progress_observation_context_requires_native_operation'),
        ('',actual,'progress_native_operation_invalid'),
        ('synthetic-operation',object(),'progress_observation_context_required')]:
        with pytest.raises(ContractError,match='^'+code+'$'):
            episode_bindings.native_observation_options(operation,value)


def test_actual_saved_reader_reconstructs_seven_fields_and_keeps_assignment_authority(tmp_path):
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARG',molecule='protein')
        scope=store.validate_scope();path=(('literature','controlled'),);run='context-owner-control'
        episode_id=EpisodeRef(run,path).episode_id
        request={'message':{'scope':scope,'episode_assignment':{'controlled':'original'}}}
        journal=Journal(store,run)
        journal.save('runtime_episodes',{'episode_id':episode_id,'path':json.dumps(path),
            'request':json.dumps(request),'initial_credit':0,'state':'active','completion':None,'archive':None})
        original=dict(store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',(run,episode_id)).fetchone())
        reader=EpisodeReturnRecords(store,run,failure_prefix='controlled_')
        actual=reader.context(episode_id)
        assert type(actual) is BindingContext
        assert actual.received_record_refs==() and actual.request['message']['episode_assignment']['controlled']=='original'
        assert reader.authenticate(actual) is actual
        with pytest.raises(ValueError,match='^controlled_context_conflict$'):
            reader.authenticate(replace(actual,assignment={'controlled':'changed'}))
        changed={'message':{'scope':scope,'episode_assignment':{'controlled':'changed'}}}
        with pytest.raises(ValueError,match='^controlled_original_context_conflict$'):
            reader.authenticate(replace(actual,assignment={'controlled':'changed'},request=changed))
        assert dict(store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',(run,episode_id)).fetchone())==original
