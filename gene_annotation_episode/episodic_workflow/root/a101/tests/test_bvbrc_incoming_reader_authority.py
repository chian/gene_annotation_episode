"""Finite incoming-reader interfaces; no foreign provider or workflow execution.

These controls exercise original non-applicability, actual schema construction,
base/type identity and context-authentication rejection. They are not evidence
of a complete saved-publication replay or a scientific annotation assessment.
"""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]
CASES=(
    ('phylogeny','BVBRCPhylogenyReturns','phylogeny_fact_sources'),
    ('alignment','BVBRCAlignmentReturns','alignment_fact_sources'),
    ('genome_alignment','BVBRCGenomeAlignmentReturns','genome_alignment_fact_sources'),
    ('comparative_systems','BVBRCComparativeSystemsReturns','comparative_systems_fact_sources'),
    ('fastqutils','BVBRCFastqUtilsReturns','fastqutils_fact_sources'),
    ('application','BVBRCApplicationReturns','application_fact_sources'),
)

def own(name):
    return import_module(PACKAGE+'.'+name)

def reader_module(family):
    return own('library.retained_input_authority.bvbrc_'+family+'_returns')

@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('incoming reader attempted external execution')
    monkeypatch.setattr('socket.create_connection',forbidden)
    monkeypatch.setattr('socket.socket.connect',forbidden)
    monkeypatch.setattr('urllib.request.urlopen',forbidden)
    monkeypatch.setattr('subprocess.run',forbidden)
    monkeypatch.setattr('subprocess.Popen',forbidden)

@pytest.mark.parametrize('family,class_name,schema_name',CASES)
def test_unrequested_descriptive_context_does_not_become_grading_or_admission(tmp_path,family,class_name,schema_name):
    module=reader_module(family)
    with own('state').Store(tmp_path/'state') as store:
        execution=SimpleNamespace(store=store,run_id='incoming-reader-control')
        reader=getattr(module,class_name)(execution)
        assert isinstance(reader,own('episode_return_records').EpisodeReturnRecords)
        assert reader.api is execution and reader.store is store
        # No report source claims this descriptive field. No publication/custody
        # service is supplied, so any accidental scientific reader call fails.
        schema={'type':'object','properties':{'description':{'type':'string'}},'required':['description'],'additionalProperties':False}
        form={'description':'Original contextual metadata remains descriptive.'}
        saved=deepcopy(form);before=store.db.total_changes
        assert reader.received_facts(object(),schema)=={}
        assert reader.validate_received_report(object(),form,schema) is None
        assert reader.record_admission(object(),form,schema,'unexecuted-operation')==[]
        assert form==saved and store.db.total_changes==before

@pytest.mark.parametrize('family,class_name,schema_name',CASES)
def test_original_fact_schema_globals_and_initializers_are_available(family,class_name,schema_name):
    from jsonschema import Draft202012Validator
    module=reader_module(family);factory=getattr(module,schema_name)
    original=factory();assert original and set(original)==set(module.FACT_SOURCES)
    for source,descriptor in original.items():
        assert descriptor['report_schema']['x-source']==source
        Draft202012Validator.check_schema(descriptor['report_schema'])
    changed=factory();source=next(iter(changed));changed[source]['report_schema']['x-source']='altered-descriptive-source'
    assert factory()==original

@pytest.mark.parametrize('family,class_name,schema_name',CASES)
def test_requested_original_reader_rejects_conflicting_run_before_support(tmp_path,family,class_name,schema_name):
    module=reader_module(family)
    with own('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein');scope=store.validate_scope()
        path=(('sequence_homology_evidence','controlled-parent'),)
        context_run='altered-run';ref=own('method_loop.identities').EpisodeRef(context_run,path)
        request={'message':{'scope':scope,'episode_assignment':{}}}
        context=own('episode_bindings').BindingContext(context_run,ref.episode_id,'sequence_homology_evidence',path,scope,{},request)
        execution=SimpleNamespace(store=store,run_id='authentic-run')
        reader=getattr(module,class_name)(execution)
        descriptors=getattr(module,schema_name)();source=next(iter(descriptors))
        schema={'type':'object','properties':{'original_observations':descriptors[source]['report_schema']},'required':['original_observations'],'additionalProperties':False}
        before=store.db.total_changes
        with pytest.raises(ValueError,match='context_conflict'):
            reader.validate_received_report(context,{'original_observations':[]},schema)
        assert store.db.total_changes==before
