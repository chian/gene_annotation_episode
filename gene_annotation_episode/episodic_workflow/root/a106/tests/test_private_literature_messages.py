"""Named A101/A106 child exchanges with real saved identity and controlled child/receipt ports."""
from importlib import import_module
import json
from types import SimpleNamespace

import pytest
from .test_literature_private_boundaries import PACKAGE as AXIS, HOMES
HOMES = [home.replace('/', '.') for home in HOMES]

EDGES={'literature':{'literature_strategy':'evidence_search_strategy_improvement'},
 'literature_strategy':{'literature_search':'source_relevance_assessment'},
 'literature_search':{'literature_page':'source_evidence_examination'},
 'literature_page':{'literature_table':'table_evidence_extraction','literature_ordered':'source_coverage_improvement','literature_targeted':'passage_evidence_extraction'}}
CASES=[]
for home in HOMES:
    cls=import_module(AXIS+'.'+home+'.episode').LiteratureEpisode
    CASES.extend((home,role,name) for role,name in EDGES.get(cls.roles[0],{}).items())

@pytest.fixture(params=CASES)
def edge(request):
    home,role,name=request.param
    binding=import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace())
    return home,role,name,binding


def outgoing_fixture(edge):
    home,role,name,binding=edge
    parent=SimpleNamespace(role=binding.roles[0],scope={'subject_refs':['target']})
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),scope=parent.scope,episode_id='original-parent')
    selected={'kind':'episode_child','role':role,'scope':{'subject_refs':['target']},
        'goal':'Read actual source conditions','purpose':'Return qualified context',
        'assignment':{'original':'selected-assignment'}}
    calls=[]
    child=SimpleNamespace(required_return_sources=lambda context,role:(),
        prepare_assignment=lambda context,child_role,assignment,scope,key:
            calls.append((context,child_role,assignment,scope,key)) or {'admitted':'original'})
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    workflow=SimpleNamespace(run_id='run-original',store=SimpleNamespace(validate_scope=lambda scope,**kwargs:scope),
        expanded_contract_form=lambda *args:(schema,{'original':'contract-declaration'}),
        episode_bindings=SimpleNamespace(for_child=lambda path,role:child),binding_context=lambda source:parent,
        child_initial_report_input=lambda *args:'{}',specialist=lambda source:binding,
        annotation_child_roles=None,services=SimpleNamespace(capabilities=lambda:()),
        launch_instructions=SimpleNamespace(materialize=lambda selected:None))
    return workflow,source,selected,parent,child,calls,schema



def test_missing_required_typed_result_is_rejected_before_child_admission(edge):
    *_,binding=edge
    workflow,source,selection,parent,child,calls,schema=outgoing_fixture(edge)
    child.required_return_sources=lambda *args:('actual_context_sheets',)
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='child_return_requires_actual_context_sheets'):
        binding.child_request_preparer(selection['role'])(workflow,source,selection,6)
    assert calls==[]


