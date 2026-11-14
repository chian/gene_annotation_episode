"""Original validator denies protected inputs despite ordinary Store visibility."""
import hashlib
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]


def module(name):return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('family',['atac','chromatin','protein'])
def test_validator_retains_each_original_terminal_guard(family):
    calls=[]
    def denial(*args):calls.append(family);return False
    def ordinary(*args):return None
    owner=SimpleNamespace(store=SimpleNamespace(get=lambda ref:{'record_type':'artifact','id':ref,'revision':1},
        reference_subset=lambda refs,scope:refs,
        get_artifact=lambda ref:pytest.fail('denied input must not read bytes')),
        _atac_reference_access=denial if family=='atac' else ordinary,
        _chromatin_reference_access=denial if family=='chromatin' else ordinary,
        _protein_reference_access=denial if family=='protein' else ordinary)
    with pytest.raises(ValueError):
        module('execution_input_versions').validate_execution_input_versions(owner,
            [{'reference':'artifact_original','version':'1','content_sha256':None}],{},context=object())
    assert calls==[family]


@pytest.mark.parametrize('changed',[False,True])
def test_unprotected_input_keeps_original_byte_identity_check(changed):
    raw=b'original source bytes'
    owner=SimpleNamespace(store=SimpleNamespace(get=lambda ref:{'record_type':'artifact','id':ref,'revision':1},
        reference_subset=lambda refs,scope:refs,get_artifact=lambda ref:raw),
        _atac_reference_access=lambda *args:None,_chromatin_reference_access=lambda *args:None,
        _protein_reference_access=lambda *args:None)
    versions=[{'reference':'artifact_original','version':'1',
               'content_sha256':hashlib.sha256(b'changed' if changed else raw).hexdigest()}]
    if changed:
        with pytest.raises(ValueError,match='execution_input_version_conflict'):
            module('execution_input_versions').validate_execution_input_versions(owner,versions,{},context=object())
    else:
        assert module('execution_input_versions').validate_execution_input_versions(owner,versions,{},context=object()) is None


@pytest.mark.parametrize('product',[False,True])
def test_actual_private_execution_rejects_store_visible_structure_derived_wrapper(tmp_path,monkeypatch,product):
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        source=store.put('source',{'provider':'episode.execution_result','version':'native_protein_structure_bundle_v1',
            'accession':None,'uri':None,'artifact_ref':store.artifact('explicit synthetic protected source marker'),
            'text_ref':None,'request_ref':None,'retrieved_at':None},origin='tool')
        reference=store.put('reference',{'reference_type':'protein','source_ref':source['id'],
            'accession':'synthetic-original','label':'Synthetic protected sequence ancestry',
            'sequence_ref':store.artifact('MAAA','text/plain'),'molecule':'protein','length':4,
            'term_refs':[],'context_refs':[]},origin='tool')
        feature=store.put('feature',{'subject_ref':reference['id'],'kind':'sequence_region',
            'segments':[{'start':0,'end':3}],'strand':'+','context_refs':[]},origin='reasoning')
        target=feature['id']
        if product:
            target=store.put('product',{'parent_refs':[target],'molecule':'protein',
                'sequence_ref':store.artifact('MAA','text/plain'),'derivation':'extraction',
                'context_refs':[],'footprint':[]},origin='tool')['id']
        assert store.reference_subset([target],scope)==[target]
        tools=module('tools').ToolRegistry(store,clients=SimpleNamespace())
        owner=module('execution_job_submission.episode').ExecutionEpisode(None,store=store,
            directory=tmp_path/'run',run_id='protected-input-original',
            resources={'original-api':{'kind':'api','service':'bvbrc_appservice',
                'execution_contract':'bvbrc_appservice_execution_v1',
                'endpoints':{'AppService':'https://unexecuted.invalid/app','Workspace':'https://unexecuted.invalid/workspace'},
                'scientific_adapters':[]}},initial_information={},tool_registry=tools,
            handoff_unit=1,acquired_record_unit=1,log_window_bytes=128,log_roles=('stdout','stderr'))
        monkeypatch.setattr(store,'get_artifact',lambda *args:pytest.fail('derived ancestry denial must precede bytes'))
        with pytest.raises(ValueError):
            owner._versions([{'reference':target,'version':None,'content_sha256':None}],scope,
                context=SimpleNamespace(role='launch',assignment={},scope=scope))
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
