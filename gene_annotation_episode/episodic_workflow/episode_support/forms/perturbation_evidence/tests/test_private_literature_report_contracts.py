"""Actual communication validator retains source-lead and screening schemas."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence import communication
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms import literature_commission_contracts as contracts

@pytest.mark.parametrize('schema_name',['lead_return_schema','screening_schema'])
def test_registered_original_commission_return_schema_and_rejection(schema_name):
    field=getattr(contracts,schema_name)()
    schema={'type':'object','properties':{'answer':field},'required':['answer'],'additionalProperties':False}
    communication.validate_closed_schema(schema)
    changed=deepcopy(schema);changed['properties']['answer']['items']['properties']['proposed_annotation_ref']={'type':'string'}
    with pytest.raises(communication.ReportBoundaryError):communication.validate_closed_schema(changed)
