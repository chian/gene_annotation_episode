"""Finite saved projection checks, plus actual host/latest-history boundaries."""
from copy import deepcopy
import hashlib

import pytest
from gene_annotation_episode.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.bvbrc_comparative_systems_fact_contracts import requested_selection
from gene_annotation_episode.bvbrc_comparative_systems_returns import (
    FACT_SOURCES, BVBRCComparativeSystemsReturns, ComparativeSystemsReturnError,
    project_comparative_systems_return_facts, parent_form_schema)
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from test_bvbrc_comparative_systems_bundle import arguments, adapter
from test_bvbrc_comparative_systems_publication import stored
from test_bvbrc_comparative_systems_episode_flow import requested_form, result_selector, forbid_science, declaration


def content(value, source):
    raw = canonical(value).encode()
    sha = hashlib.sha256(raw).hexdigest()
    return {'source_ref': source, 'artifact_field':'artifact_ref','artifact_ref':'artifact_'+sha,
        'sha256':sha,'byte_count':len(raw)}


@pytest.fixture
def retained():
    # These envelopes test the pure saved-value projection only. Host possession
    # is established separately through the real executor, never by these flags.
    args = arguments('families')
    args['requested_form'] = requested_form()
    args['parameters']['producer_evidence_selections'] = []
    args['qualified_producer_evidence'] = ()
    for document in args['parameters']['document_selection']['documents']:
        document['producer_evidence_id'] = None
    selected = result_selector(args['requested_form'])
    selected['adapter']['parameters'] = args['parameters']
    args['bundle']['requested_selector_sha256'] = digest(selected)
    native = adapter.consume_bundle(**args)
    saved,sheet,components = stored(native)
    source = 'source_' + digest(native)[:24]
    body = {'version':RESULT_VERSION,'source_ref':source,'reference':source,'record_refs':[source],
        'assignment':{'selector':selected},'publication_inputs':{'selector':selected,'adapter':selected['adapter'],
            'adapter_implementation_sha256':adapter.implementation_sha256()},'bundle':args['bundle'],
        'publication':{'bundle_content':content(args['bundle'],source),'result_record_refs':[source],'adapter_result':saved}}
    return body,sheet,components


def projected(retained):
    body,sheet,components=retained
    return project_comparative_systems_return_facts(body,requested_sources=FACT_SOURCES,sheet=sheet,components=components)


def test_seven_exact_saved_families_and_closed_identifiers_without_science(retained,monkeypatch):
    expected=projected(retained)
    forbid_science(monkeypatch)
    assert projected(retained)==expected
    body,sheet,components=retained
    schema=parent_form_schema(requested_selection(body['publication_inputs']['selector']['requested_schema']))
    form={name:expected[node['x-source']] for name,node in schema['properties'].items()}
    validate_form(form,schema,lambda ref,namespace=None:BVBRCComparativeSystemsReturns._has_reference(expected,ref,namespace))
    assert len(expected)==7
    assert next(iter(expected.values()))[0]['source_ref']==body['source_ref']
    assert BVBRCComparativeSystemsReturns._has_reference(expected,'PLF_TEST','bvbrc_comparative_systems_identifier')
    assert not BVBRCComparativeSystemsReturns._has_reference(expected,'PGF_TEST','bvbrc_comparative_systems_identifier')
    assert not BVBRCComparativeSystemsReturns._has_reference(expected,'PLF_TEST','bvbrc_comparative_systems_population')


@pytest.mark.parametrize('change',['field','value','source','pin','parameters','form','sheet','calculation','native_diag','generic_diag','entity','failure_context'])
def test_original_selection_and_saved_values_cannot_be_relabelled(retained,change):
    body,sheet,components=deepcopy(retained)
    saved=body['publication']['adapter_result']
    if change=='field': saved['facts']['occurrences']['field_id']='substituted'
    elif change=='value': saved['facts']['occurrences']['values'][0]['value']=999
    elif change=='source': body['source_ref']='source_'+'0'*24
    elif change=='pin': body['publication_inputs']['adapter_implementation_sha256']='not-a-pin'
    elif change=='parameters': body['publication_inputs']['adapter']=deepcopy(body['publication_inputs']['adapter']); body['publication_inputs']['adapter']['parameters']['analysis_id']='substituted'
    elif change=='form': body['publication_inputs']['selector']['requested_schema']['properties']['occurrences']['x-bvbrc-comparative-systems']['expected_cardinality']=2
    elif change=='sheet': sheet['analysis_id']='substituted'
    elif change=='calculation': components['calculations']['components'][0]['ratio']['output']['value']=.5
    elif change=='native_diag': components['diagnostics'].append(deepcopy(components['diagnostics'][0]))
    elif change=='generic_diag': saved['diagnostics'][0]['path']='/not-native/0'
    elif change=='failure_context': components['failure_context']['failure_status']='invalid'
    else: saved['facts']['member']['values'][0]['entity']['family_id']='other'
    with pytest.raises(ValueError): projected((body,sheet,components))


def test_empty_requested_sources_do_not_read_or_invent_fields():
    assert project_comparative_systems_return_facts(None,requested_sources=(),sheet=None,components=None)=={}
    with pytest.raises(ComparativeSystemsReturnError):
        project_comparative_systems_return_facts(None,requested_sources=('invented',),sheet=None,components=None)

from test_bvbrc_comparative_systems_episode_flow import driver


def test_latest_partial_keeps_original_named_history_and_authenticates_whole_parameters(driver,monkeypatch):
    import json
    d=driver
    selection=requested_selection(requested_form(False))
    for field in selection['fields']:
        field['availability_requirement']='available_value'
    selected=result_selector(adapter.requested_form_schema(selection))
    selected['requirements'].append({'requirement_id':'requested_pathway_report','role':'pathway_summary',
        'required':True,'declared_format':declaration('comparative_systems_pathways_json_v1'),
        'producer_rule_evidence':None,'exact_object':None})
    d.start(selected=selected)
    d.acquire_manifest()
    original=deepcopy(d.acquire_native())
    assert original['publication']['adapter_result']['status']=='ok'
    assert original['publication']['requested_form_status']=='partial'
    assert d.api._completion(d.context) is None
    assert all(row['status']=='satisfied' for row in original['publication']['adapter_result']['facts'].values())
    assert original['publication_inputs']['selector']==d.selected
    admitted,_,_=d.admit_numeric()
    receipt=d.records.read(original['bundle']['acquisition_receipt_refs'][-1])
    path=d.api.appservice.publications._directory(d.context,receipt['value']['origin']['operation_key'])/'publication_inputs.json'
    retained_bytes=path.read_bytes()
    for key,value in (('analysis_id','substituted-analysis'),('reference_memberships',[{'unbound_reference':True}]),
            ('producer_evidence_selections',[{'unbound_producer_path':True}])):
        altered=json.loads(retained_bytes)
        altered['adapter']['parameters'][key]=value
        altered['selector']['adapter']['parameters'][key]=value
        path.write_text(canonical(altered))
        try:
            with pytest.raises(ValueError): d.api.read_result(original['source_ref'],d.context.scope)
        finally:
            path.write_bytes(retained_bytes)
    d.client.body=b'{"invalid_family_output": true}'
    d.call('download',deepcopy(d.native_args),context=d.context)
    later=d.publication()
    assert later['source_ref']!=original['source_ref']
    assert later['publication_inputs']['selector']==original['publication_inputs']['selector']
    assert later['publication']['requested_form_status'] in {'partial','invalid'}
    assert d.api._completion(d.context) is None
    facts=d.api.comparative_systems_returns.facts(d.context,d.schema)
    assert {row['source_ref'] for rows in facts.values() for row in rows}=={later['source_ref']}
    assert all(row['value']['status']!='satisfied' for rows in facts.values() for row in rows)
    forbidden=forbid_science(monkeypatch)
    monkeypatch.setattr(d.client,'rpc',forbidden)
    monkeypatch.setattr(d.client,'download',forbidden)
    history=d.api.comparative_systems_returns.received_facts(d.parent,d.schema)
    assert {name:history[node['x-source']] for name,node in d.schema['properties'].items()}==admitted
    assert d.api.read_result(original['source_ref'],d.context.scope)==original
    assert d.api.read_result(later['source_ref'],d.context.scope)==later


def test_completed_original_assignment_rejects_another_selected_download(driver,monkeypatch):
    d=driver
    selection=requested_selection(requested_form(False))
    for field in selection['fields']:
        field['availability_requirement']='available_value'
    d.start(form=adapter.requested_form_schema(selection))
    d.acquire_manifest()
    original=d.acquire_native()
    assert original['publication']['requested_form_status']=='satisfied'
    assert d.api._completion(d.context) is not None
    forbidden=forbid_science(monkeypatch)
    monkeypatch.setattr(d.client,'rpc',forbidden)
    monkeypatch.setattr(d.client,'download',forbidden)
    context,key=d.selection('download',deepcopy(d.native_args),context=d.context)
    outcome=d.invoke(context,'download',deepcopy(d.native_args),key)
    assert outcome['status']=='invalid'
    assert outcome['feedback']['code']=='api_assignment_already_completed'
    assert outcome['record_refs']==[]
    assert not (d.api.appservice.publications._directory(context,key)/'intent.json').exists()
    assert d.api.read_result(original['source_ref'],context.scope)==original
