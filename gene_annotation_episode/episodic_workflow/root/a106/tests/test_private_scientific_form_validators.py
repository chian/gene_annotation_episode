"""Actual positive/invalid parent form controls for the original A106 validators."""
from copy import deepcopy
from importlib import import_module

import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]
def module(name):return import_module(PACKAGE+'.'+name)

def selected(source,policy):
    if source=='restriction_mapping_results':
        owner=module('library.retained_input_authority.restriction_mapping_returns')
        fields=owner.restriction_mapping_fact_sources()[source]['report_schema']
        validator=owner.requested_restriction_projections
        properties=fields['items']['properties']
        properties['selection_policy']={'type':'string','const':policy}
        if policy=='matching_sequence':properties['sequence_ref']['const']='reference_'+'d'*24
    else:
        owner=module('library.retained_input_authority.alignment_site_returns')
        fields=owner.alignment_site_fact_sources()[source]['report_schema']
        validator=owner.requested_site_projections
        properties=fields['items']['properties']
        properties['selection_policy']={'type':'string','const':policy}
        if policy=='matching_alignment':properties['alignment_ref']['const']='observation_'+'a'*24
    schema={'type':'object','properties':{'selected':fields},'required':['selected'],'additionalProperties':False}
    return schema,validator

CASES=[('reference_site_rows','all_own_completed_results'),('reference_site_rows','matching_alignment'),
    ('blast_hsp_column_rows','all_own_completed_results'),('blast_hsp_column_rows','matching_alignment'),
    ('restriction_mapping_results','all_own_completed_results'),('restriction_mapping_results','matching_sequence')]

@pytest.mark.parametrize('source,policy',CASES)
def test_actual_original_nonempty_selection_and_exact_fields(source,policy):
    schema,validator=selected(source,policy);before=deepcopy(schema)
    result=validator(schema)
    assert list(result)==[source]
    assert result[source]['selection']['policy']==policy
    assert result[source]['fields']==schema['properties']['selected']
    if source=='restriction_mapping_results':
        assert result[source]['selection']['sequence_ref']==('reference_'+'d'*24 if policy=='matching_sequence' else None)
    else:
        assert result[source]['selection']['alignment_refs']==(['observation_'+'a'*24] if policy=='matching_alignment' else None)
    result[source]['fields']['items']['properties'].clear()
    assert schema==before

@pytest.mark.parametrize('source',['reference_site_rows','blast_hsp_column_rows','restriction_mapping_results'])
def test_original_missing_explicit_policy_is_rejected(source):
    schema,validator=selected(source,'all_own_completed_results')
    schema['properties']['selected']['items']['properties']['selection_policy']={'type':'string','enum':['all_own_completed_results']}
    error=module('communication').ReportBoundaryError
    with pytest.raises(error) as caught:validator(schema)
    assert caught.value.diagnostic['code']==('restriction_explicit_selection_required' if source=='restriction_mapping_results' else 'alignment_site_explicit_selection_required')

@pytest.mark.parametrize('source',['reference_site_rows','blast_hsp_column_rows','restriction_mapping_results'])
def test_actual_private_invocation_uses_both_original_validators(source):
    schema,_=selected(source,'all_own_completed_results')
    invocation={'objective':'Validate an explicitly requested saved-result form',
        'purpose':'Return the selected original fields','report_schema':schema,'initial_report':{}}
    owner=module('perturbation_evidence.from_parent').ScientificAssignment
    actual=owner._invocation(invocation,{})
    assert actual['report_schema']==schema and actual['initial_report']=={}
    invalid=deepcopy(invocation)
    invalid['report_schema']['properties']['selected']['items']['properties']['selection_policy']={'type':'string'}
    with pytest.raises(module('communication').ReportBoundaryError):owner._invocation(invalid,{})
