"""Original actual Store producer setup; no fabricated historical receipt."""
from .controlled_v3_fixtures import Fixture
from ..state import Store
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_controlled_response_storage as storage

def native_case(path,index=0,*,modify=None,**kwargs):
    fixture=Fixture(index,**kwargs)
    if modify:modify(fixture)
    store=Store(path)
    store.create_problem(raw_sequence='MKWAA',molecule='protein')
    sources={}
    for ref in [fixture.main_ref,*[ref for ref in fixture.data if ref!=fixture.main_ref]]:
        data=fixture.data[ref]
        artifact=store.artifact(data)
        sources[ref]=store.put('source',{'provider':'constructed_controlled_fixture','accession':ref,'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':[] if ref==fixture.main_ref else [sources[fixture.main_ref]]},origin='caller')['id']
    def remap(value):
        if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
        if isinstance(value,list):return [remap(v) for v in value]
        return sources.get(value,value) if isinstance(value,str) else value
    args=remap(fixture.args)
    assignment={'source_ref':args['source_ref'],'requested_controlled_response_components':list(storage.COMPONENTS),
        'requested_controlled_response_views':list(storage.VIEWS)}
    context=BindingContext('fixture-run','fixture-child','literature_page',
        (('literature','fixture-parent'),('literature_page','fixture-child')),store.validate_scope(),assignment,{},tuple(sources.values()))
    return store,context,args,fixture
