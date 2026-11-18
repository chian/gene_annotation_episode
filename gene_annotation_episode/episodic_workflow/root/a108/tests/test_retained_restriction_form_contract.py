"""Original pure restriction-form controls over actual private form boundaries.

Only original pure schema tests are selected. No HMMER execution, retained native
fixture dependency, environment opt-in or workflow controller is used here.
"""
from copy import deepcopy
from importlib import import_module
import json

import pytest


@pytest.fixture(autouse=True, params=('a101', 'a105', 'a106', 'a108'))
def private_contract_owner(request, monkeypatch):
    prefix='gene_annotation_episode.episodic_workflow.root.'+request.param
    returns=import_module(prefix+'.library.retained_input_authority.restriction_mapping_returns')
    form_contract=import_module(prefix+'.episode_contract_information')
    for name,value in {'obj':import_module(prefix+'.domain').obj,
        'restriction_mapping_fact_sources':returns.restriction_mapping_fact_sources,
        'requested_restriction_projections':returns.requested_restriction_projections,
        'ContractInformationError':form_contract.ContractInformationError,
        'expand_fact_form':form_contract.expand_fact_form,
        'validate_saved_fact_form':form_contract.validate_saved_fact_form}.items():
        monkeypatch.setitem(globals(),name,value)


SOURCE='restriction_mapping_results'
PARAMETER='x-restriction-selection'
BASE_FIELDS=['selection_policy','sequence_ref','namespace','topology','data_status',
    'coordinate_unit','population_scope']
def selection(*,policy='all_own_completed_results',sequence_ref=None,names=False):
    fields=BASE_FIELDS+(['enzyme_rows.catalog_ordinal','enzyme_rows.name',
        'enzyme_rows.search_state','enzyme_rows.position_meaning'] if names else [])
    return {'version':'restriction_return_selection_v1','policy':policy,
        'sequence_ref':sequence_ref,'fields':fields}


def submitted(chosen=None,*,field='selected'):
    return obj({'status':{'type':'string','enum':['unresolved','qualified']},
        field:{'$ref':'episode-fact:'+SOURCE,PARAMETER:selection() if chosen is None else chosen}})


def expanded(schema,*,facts=None,permitted=('sample_context_evidence',)):
    return expand_fact_form(json.dumps(schema),child_role='sample_context_evidence',
        facts_by_role={'sample_context_evidence':restriction_mapping_fact_sources() if facts is None else facts},
        permitted_child_roles=permitted)


def test_actual_compact_selection_expands_into_existing_explicit_723_contract():
    schema=submitted(selection(names=True))
    original=deepcopy(schema)
    result=expanded(schema)
    view=result['expanded_schema']['properties']['selected']
    requested=requested_restriction_projections(result['expanded_schema'])[SOURCE]
    assert requested['selection']=={'policy':'all_own_completed_results','sequence_ref':None}
    assert set(view['items']['properties'])==set(BASE_FIELDS)|{'enzyme_rows'}
    assert PARAMETER not in view
    assert schema==original
    assert validate_saved_fact_form(child_role='sample_context_evidence',submitted_schema_json=json.dumps(schema),
        expanded_schema=result['expanded_schema'],declaration=result['declaration'])==result['expanded_schema']


@pytest.mark.parametrize('fault',['missing_selector','missing_policy','missing_sequence','extra','wrong_source','nested'])
def test_compact_grammar_never_supplies_selection_defaults(fault):
    schema=submitted()
    node=schema['properties']['selected']
    if fault=='missing_selector':del node[PARAMETER]
    elif fault=='missing_policy':del node[PARAMETER]['policy']
    elif fault=='missing_sequence':del node[PARAMETER]['sequence_ref']
    elif fault=='extra':node['additionalProperties']=False
    elif fault=='wrong_source':node['$ref']='episode-fact:sample_context_evidence_results'
    else:schema['properties']['selected']={'type':'array','items':node}
    with pytest.raises(ContractInformationError):expanded(schema)


@pytest.mark.parametrize('fault',['source','role','base'])
def test_original_frozen_advertisement_remains_required(fault):
    facts=restriction_mapping_fact_sources()
    permitted=('sample_context_evidence',)
    if fault=='source':facts.clear()
    elif fault=='role':permitted=()
    else:facts[SOURCE]['report_schema']['description']='changed original schema'
    with pytest.raises(ContractInformationError) as error:
        expanded(submitted(),facts=facts,permitted=permitted)
    assert error.value.code=={'source':'return_contract_not_available',
        'role':'return_child_role_not_available','base':'selected_fact_base_schema_mismatch'}[fault]


@pytest.mark.parametrize('fault',['text','role','roster','expanded','selection'])
def test_saved_declaration_checks_original_relationships(fault):
    schema=submitted(selection(names=True))
    result=expanded(schema)
    declaration=result['declaration']
    if fault=='text':declaration['submitted_schema_json']+=' '
    elif fault=='role':declaration['child_role']='annotation'
    elif fault=='roster':declaration['fact_references'][0]['field']='forged'
    elif fault=='expanded':result['expanded_schema']['properties']['status']['enum'].append('forged')
    else:
        schema['properties']['selected'][PARAMETER]['fields']=BASE_FIELDS
        # Even a changed declaration carrying its own revised text and all
        # original schema hashes cannot approve a different selected tree.
        declaration['submitted_schema_json']=json.dumps(schema)
    with pytest.raises(ContractInformationError):
        validate_saved_fact_form(child_role='sample_context_evidence',submitted_schema_json=json.dumps(schema),
            expanded_schema=result['expanded_schema'],declaration=declaration)
