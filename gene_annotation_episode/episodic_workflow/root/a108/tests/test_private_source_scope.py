"""Role-specific A108 acquisition and authenticated source boundaries."""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS,HOMES
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError,identity

@pytest.fixture(params=HOMES)
def source_binding(request):
    entries=[{'name':'source.read','input_schema':{'type':'object','properties':{
        'source_ref':{'type':'string'},'representation':{'type':'string'}}}},
        {'name':'public.uniprot.search','input_schema':{'type':'object','properties':{}}},
        {'name':'public.ncbi.search','input_schema':{'type':'object','properties':{'database':{'type':'string'}}}},
        {'name':'foreign.assay.populate','input_schema':{'type':'object','properties':{}}}]
    cls=import_module(AXIS+'.'+request.param+'.episode').LiteratureEpisode
    return cls(SimpleNamespace(tool_catalog=lambda scope:entries))


def test_only_discovery_roles_offer_acquisition_tools(source_binding):
    binding=source_binding;role=binding.roles[0]
    entries={entry['name']:entry for entry in binding.catalog(SimpleNamespace(role=role,scope={}))}
    assert 'source.read' in entries and 'foreign.assay.populate' not in entries
    assert ('public.uniprot.search' in entries)==(role in {'literature','literature_strategy','literature_search'})
    if 'public.ncbi.search' in entries:
        assert entries['public.ncbi.search']['input_schema']['properties']['database']['enum']==[
            'pubmed','protein','nuccore','taxonomy','biosample','bioproject']
    assert {'literature.a108_grading.populate','literature.a108.aggregate'}<=entries.keys()


def test_reading_roles_preserve_original_source_custody(source_binding):
    binding=source_binding;role=binding.roles[0]
    source=identity('source','original');outside=identity('source','outside');artifact=identity('artifact','original')
    page={'version':'page_assignment_v1','source_ref':source,'representation':'original',
        'artifact_ref':artifact,'question_context_refs':[],'prior_delivery_refs':[]}
    if role=='literature_page':assignment=page
    elif role in {'literature_table','literature_ordered','literature_targeted'}:
        window={'source_ref':source,'representation':'original','offset':0,'limit':10}
        assignment={'version':'reading_assignment_v1','page':page,
            'selection':{'spans':[window]} if role=='literature_targeted' else window}
    else:
        version,field={'literature':('literature_assignment_v1','source_refs'),
            'literature_strategy':('strategy_assignment_v1','prior_search_refs'),
            'literature_search':('search_assignment_v1','search_result_refs')}[role]
        assignment={'version':version,'question_context_refs':[],field:[]}
    records={source:{'artifact_ref':artifact,'parent_source_refs':[]},outside:{'artifact_ref':artifact,'parent_source_refs':[]},artifact:{'size':100}}
    binding.services.reference_in_scope=lambda ref,scope,namespace=None:ref in records
    binding.services.read_record=lambda ref:records[ref]
    authorization=SimpleNamespace(authorize_source_access=lambda *args:None)
    binding._a108_grading_repository=lambda:authorization
    binding._a108_aggregation_repository=lambda:authorization
    context=SimpleNamespace(role=role,assignment=assignment,scope={})
    arguments={'source_ref':outside,'representation':'original'}
    if role in {'literature_page','literature_table','literature_ordered','literature_targeted'}:
        with pytest.raises(ContractError,match='literature_reading_outside_assigned_source'):
            binding._tool_arguments(context,'source.read',arguments)
    else:
        assert binding._tool_arguments(context,'source.read',arguments)==arguments
