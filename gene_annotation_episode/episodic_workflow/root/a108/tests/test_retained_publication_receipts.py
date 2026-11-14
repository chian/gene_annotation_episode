"""Real frozen receipts over engineered publication rows; no native production.

These fixtures exercise incoming metadata authority through the actual registry
port. They do not register a scientific execution or validate numerical results.
"""
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]


def module(name):return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('provider,version,operation,origin,public_auxiliary',[
    ('analyze_itc_binding_thermodynamics','ordinary_itc_result_v1','analyze_itc_binding_thermodynamics','tool',True),
    ('liftover_coordinates','ordinary_liftover_result_v1','liftover_coordinates','tool',False),
    ('alphafold',None,'public.alphafold.file','external',False),
])
def test_incoming_publication_uses_original_receipts_even_without_a_producer(
        tmp_path,provider,version,operation,origin,public_auxiliary):
    canonical=module('domain').canonical
    EpisodeRef=import_module('gene_annotation_episode.episodic_workflow.root.method_loop.identities').EpisodeRef  # a108 has no private method_loop; its modules import the shared root package
    BindingContext=module('episode_bindings').BindingContext
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        registry=module('tools').ToolRegistry(store,clients=SimpleNamespace())
        guard=getattr(registry,'retained_molecular_reference_access',None)
        assert callable(guard),'original incoming publication guard missing'
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT,PRIMARY KEY(run_id,episode_id))')
        raw=store.artifact('engineered retained native metadata','application/json')
        control=store.artifact('engineered private request','application/json')
        auxiliary=store.artifact('engineered retained auxiliary','application/json')
        source=store.put('source',{'provider':provider,'accession':None,'uri':None,
            'artifact_ref':raw,'text_ref':None,'request_ref':control,'version':version,
            'retrieved_at':None,'auxiliary_artifact_refs':[auxiliary]},origin=origin)
        key='engineered-publication:'+provider
        op=module('domain').identity('operation',{'key':key,'name':operation})
        result={'status':'completed','operation_ref':op,'record_refs':[source['id']],
                'result':{'source_ref':source['id']},'feedback':None}
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
            (key,op,operation,'{}',canonical(scope),canonical(result)))
        run='original-receiving-run'
        receipts=module('episode_receipts').EpisodeReceipts(store,run)
        parent_path=(('scientific_process','parent'),)
        parent_id=EpisodeRef(run,parent_path).episode_id
        def context(path,parent=None):
            episode=EpisodeRef(run,path).episode_id
            manifest=receipts.bind(episode,parent)
            request={'message':{'scope':scope,'episode_assignment':{},'knowledge_inheritance':manifest}}
            value=BindingContext(run,episode,path[-1][0],path,scope,{},request)
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
                (run,episode,canonical(path),canonical(request)))
            return value
        parent=context(parent_path)
        receipts.receive(parent_id,[source['id']],kind='initial')
        child=context((*parent_path,('literature','child-original')),parent_id)
        assert guard(child,source['id'],'source',initial_record_refs=()) is True
        assert guard(child,raw,'artifact',initial_record_refs=()) is False
        assert guard(child,control,'artifact',initial_record_refs=()) is False
        assert guard(child,auxiliary,'artifact',initial_record_refs=()) is False
        receipts.receive(parent_id,[raw,auxiliary,control],kind='initial')
        # The earlier child's receipt prefix cannot borrow later parent grants.
        assert guard(child,raw,'artifact',initial_record_refs=()) is False
        later=context((*parent_path,('literature','child-later')),parent_id)
        assert guard(later,raw,'artifact',initial_record_refs=()) is True
        assert guard(later,control,'artifact',initial_record_refs=()) is False
        assert guard(later,auxiliary,'artifact',initial_record_refs=()) is public_auxiliary
        assert guard(later,source['id'],'artifact',initial_record_refs=()) is False
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==1
