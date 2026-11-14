"""Actual communication validator retains source-lead and screening schemas."""
from copy import deepcopy
from importlib import import_module,util
import pytest
from .test_literature_private_boundaries import PACKAGE

@pytest.mark.parametrize('schema_name',['lead_return_schema','screening_schema'])
def test_registered_original_commission_return_schema_and_rejection(schema_name):
    name=PACKAGE+'.library.literature_commission_contracts'
    if util.find_spec(name) is None:name=PACKAGE+'.literature_task_credit'
    contracts=import_module(name);communication=import_module(PACKAGE+'.communication')
    field=getattr(contracts,schema_name)()
    schema={'type':'object','properties':{'answer':field},'required':['answer'],'additionalProperties':False}
    communication.validate_closed_schema(schema)
    changed=deepcopy(schema);changed['properties']['answer']['items']['properties']['proposed_annotation_ref']={'type':'string'}
    with pytest.raises(communication.ReportBoundaryError):communication.validate_closed_schema(changed)
