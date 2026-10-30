"""Exact registered subdocument validation, separate from model-authored fields."""
from copy import deepcopy

import pytest

from gene_annotation_episode.communication import (ReportBoundaryError, form_with_facts, _validate_form_semantics,
    generation_schema, interpretation_schema, validate_closed_schema, validate_form)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_gel_native_contracts import gel_cells_schema

SOURCE = 'literature_gel_component_cells'


def form_schema():
    return obj({'numbers': gel_cells_schema(), 'interpretation': {'type':'string','enum':['unknown','supported']}})


def test_exact_native_contract_is_unchanged_and_facts_remain_host_owned():
    schema = form_schema(); original = deepcopy(schema)
    assert validate_closed_schema(schema)==schema
    assert interpretation_schema(schema)==obj({'interpretation': {'type':'string','enum':['unknown','supported']}})
    assert form_with_facts({'interpretation':'unknown'},schema,{SOURCE:[]})=={'numbers':[],'interpretation':'unknown'}
    assert validate_form({'numbers':[],'interpretation':'unknown'},schema)=={'numbers':[],'interpretation':'unknown'}
    generation_schema(interpretation_schema(schema))
    assert schema==original
    with pytest.raises(ReportBoundaryError,match='Interpretations'):
        form_with_facts({'interpretation':'unknown','numbers':[]},schema,{SOURCE:[]})


@pytest.mark.parametrize('mutation',[
    lambda s:s['properties']['numbers'].update(description='changed native contract'),
    lambda s:s['properties']['numbers']['items']['properties']['sheet_ref'].update(type='number'),
    lambda s:s['properties']['numbers']['$defs'].pop('Science'),
])
def test_registered_native_contract_cannot_be_mutated(mutation):
    schema = form_schema(); mutation(schema)
    with pytest.raises(ReportBoundaryError):validate_closed_schema(schema)


def test_native_contract_cannot_be_nested_and_parent_shape_stays_closed():
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(obj({'nested':obj({'numbers':gel_cells_schema()})}))
    schema = form_schema()
    for payload in ({'numbers':[]},{'numbers':[],'interpretation':'unknown','extra':0},
            {'numbers':{},'interpretation':'unknown'},{'numbers':[{}],'interpretation':'unknown'},
            {'numbers':[],'interpretation':'unrestricted text'}):
        with pytest.raises(ReportBoundaryError):validate_form(payload,schema)


@pytest.mark.parametrize('keyword',['$ref','anyOf','oneOf','allOf'])
def test_semantic_reference_walker_local_resource_fixture(keyword):
    # Closed internal engineering fixture for resource traversal. It is never
    # registered as a controlled response source or accepted as a parent form.
    from jsonschema import Draft202012Validator
    reference = {'type':'string','format':'reference','x-reference-namespace':'source'}
    field = {'$ref':'#/$defs/Target'} if keyword=='$ref' else {keyword:[{'$ref':'#/$defs/Target'}]}
    native = {'type':'array','items':obj({'source':field,'number':{'type':'number'}}),
        '$defs':{'Target':reference}}
    actual = [{'source':'source_test','number':1.25}]
    Draft202012Validator(native).validate(actual)
    seen=[]
    _validate_form_semantics(actual,native,lambda value,namespace: seen.append((value,namespace)) or True,
        path='report.actual_field',resource=native)
    assert seen==[('source_test','source')]
    with pytest.raises(ReportBoundaryError) as error:
        _validate_form_semantics(actual,native,lambda *_:False,path='report.actual_field',resource=native)
    assert error.value.diagnostic=={'category':'report_format','code':'unknown_reference','field':'report.actual_field[0].source'}


def test_semantic_local_resource_conditional_fixture_and_external_ref_rejection():
    native = {'type':'array','items':{'allOf':[obj({'kind':{'enum':['source','other']},
        'value':{'type':'string'}}),{'if':{'properties':{'kind':{'const':'source'}}},
        'then':{'properties':{'value':{'$ref':'#/$defs/Reference'}}}}]},
        '$defs':{'Reference':{'type':'string','format':'reference','x-reference-namespace':'source'}}}
    actual = [{'kind':'source','value':'source_test'}]
    from jsonschema import Draft202012Validator
    Draft202012Validator(native).validate(actual)
    with pytest.raises(ReportBoundaryError,match='unavailable'):
        _validate_form_semantics(actual,native,lambda *_:False,resource=native)
    native['items']['allOf'][1]['then']['properties']['value']={'$ref':'https://invalid.example/remote-schema'}
    with pytest.raises(ReportBoundaryError,match='external'):
        _validate_form_semantics(actual,native,lambda *_:False,resource=native)
    # An external schema cannot be inserted into the actual registered contract.
    original = form_schema(); original['properties']['numbers']['items']={'$ref':'https://invalid.example/remote-schema'}
    with pytest.raises(ReportBoundaryError):validate_closed_schema(original)



def test_actual_gel_semantic_references_inside_local_schema_resource(tmp_path):
    from types import SimpleNamespace
    from literature_gel_worker_fixture_107 import make_case
    from gene_annotation_episode.literature_gel_storage import LiteratureGelRepository
    from gene_annotation_episode.local_return_history import _progress_refs
    store,case=make_case(tmp_path/'state')
    try:
        repo=LiteratureGelRepository(store,'constructed107-communication',evidence_origin='synthetic_fixture')
        context=SimpleNamespace(run_id='constructed107-communication',episode_id='constructed-child',role='literature',
            assignment=case['selection'],scope=case['scope'],received_record_refs=case['source_refs'])
        outcome=repo.populate(context,case['arguments'],'constructed-selected-operation')
        row=next(r for r in outcome['result']['cells'] if r['view']=='comparison')
        payload={'numbers':[row],'interpretation':'unknown'};seen=[]
        validate_form(payload,form_schema(),lambda value,namespace:seen.append((value,namespace)) or True)
        assert (row['sheet_ref'],'source') in seen
        meaning=row['scientific_context']['global']['subject']
        assert (meaning['value_ref'],'reference') in seen
        assert all((ref,'reference') in seen for ref in meaning['witness_refs'])
        assert _progress_refs(payload,{'measurements':{'schema':form_schema()}})==[]
        for target in [meaning['value_ref'],*meaning['witness_refs']]:
            with pytest.raises(ReportBoundaryError) as error:
                validate_form(payload,form_schema(),lambda value,namespace:value!=target)
            assert error.value.diagnostic['code']=='unknown_reference'
            assert 'scientific_context' in error.value.diagnostic['field']
        wrong=deepcopy(payload);wrong['numbers'][0]['cell']['value']=True
        with pytest.raises(ReportBoundaryError):validate_form(wrong,form_schema(),lambda *_:True)
    finally:store.close()
