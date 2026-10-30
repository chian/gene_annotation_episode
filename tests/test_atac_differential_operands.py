"""Actual Store/Journal receipt checks with authored BAM/software identities.

Opaque bytes are deliberately not parsed or executed. This verifies authority,
not biological data or deployment. Run only with a pinned bounded runner.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.atac_differential_operands import validate_atac_job_inputs
from gene_annotation_episode.native_atac_differential_contracts import (
    REQUIRED_DEPENDENCIES, REQUIRED_MODULES, OPERATION, MODE, requested_job_from_atac)
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


def identity(store, raw):
    artifact = store.artifact(raw)
    row = store.get(artifact)
    return dict(artifact_ref=artifact, sha256=row['sha256'], size_bytes=row['size'], format='bam')


def make_request(store):
    files = [identity(store, b'authored first BAM bytes'), identity(store, b'authored second BAM bytes')]
    return dict(version='atac_differential_request_v1', operation=OPERATION, mode=MODE,
        comparison_key='comparison', reference=dict(reference_id='reference', assembly_accession_version=None,
            source_refs=[], contigs=[dict(chromosome='chrToy', length_bp=12000,
                sequence_accession_version=None, sequence_sha256=None, source_refs=[])], aliases=[]),
        samples=[dict(sample_id='sample'+str(i), input_artifact_refs=[file['artifact_ref']],
            reference_id='reference', biospecimen_id=None, replicate_id=None,
            origin='synthetic_engineering_fixture') for i,file in enumerate(files)],
        conditions=[dict(condition_id='condition'+str(i), label=None, sample_ids=['sample'+str(i)]) for i in range(2)],
        inputs=[dict(input_key='input'+str(i), condition_id='condition'+str(i), sample_id='sample'+str(i),
            reference_id='reference', file=file) for i,file in enumerate(files)],
        callpeak=dict(genome_size_argument='12000', qvalue_cutoff=0.05, keep_duplicates=1,
            nomodel=True, shift_bp=-100, extension_size_bp=200, store_bedgraph=True,
            spmr=False, broad=False, downsample=False),
        bdgdiff=dict(cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0), output_prefix='atac')


def make_assignment(f):
    dependencies=[dict(distribution=name, version='fixture', package_root='/fixture/deps/'+name,
        files=[dict(path='/fixture/deps/'+name+'/fixture', sha256='3'*64, size_bytes=1)])
        for name in sorted(REQUIRED_DEPENDENCIES)]
    driver=dict(python_executable='/fixture/python', python_sha256='1'*64, python_version='fixture',
        module_root='/fixture/source', implementation_files=[dict(module=name,sha256='2'*64)
        for name in sorted(REQUIRED_MODULES)], dependencies=dependencies)
    native=dict(python_executable='/fixture/native/python',python_sha256='4'*64,python_version='fixture',
        macs2_script='/fixture/native/macs2',macs2_sha256='5'*64,macs2_version='2.2.9.1',
        import_roots=['/fixture/native/lib'],files=[dict(path=path,sha256='5'*64,size_bytes=1) for path in
            ['/fixture/native/macs2','/fixture/native/lib/MACS2/callpeak_cmd.py',
             '/fixture/native/lib/MACS2/bdgdiff_cmd.py','/fixture/native/lib/MACS2/IO/Parser.fixture.so',
             '/fixture/native/lib/numpy/__init__.py']])
    job=dict(request=deepcopy(f.request),software=dict(driver_runtime=driver,macs2_runtime=native),
        input_bindings=[dict(input_key=row['input_key'],file=deepcopy(row['file']),path=str(f.store.path/'artifacts'/
            row['file']['sha256'][:2]/row['file']['sha256'])) for row in f.request['inputs']])
    environment={key:'/fixture/runtime' for key in ('PYTHONHOME','TMPDIR','TMP','TEMP','XDG_CACHE_HOME','PIP_CACHE_DIR')}
    environment.update({key:'1' for key in ('PYTHONNOUSERSITE','PYTHONSAFEPATH','PYTHONDONTWRITEBYTECODE',
        'OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')})
    environment['PYTHONPATH']=':'.join([driver['module_root'],*(row['package_root'] for row in dependencies)])
    return dict(requested_job=requested_job_from_atac(job,environment=environment))


def context(f, *, parent=None, role="annotation", index=0, assigned=None, persist=True, scope=None):
    path = (() if parent is None else parent.path) + ((role, "root" if parent is None else "child_" + str(index)),)
    episode_id = EpisodeRef(f.run_id, path).episode_id
    scope = deepcopy(f.scope if scope is None else scope)
    assigned = {} if assigned is None else deepcopy(assigned)
    manifest = f.receipts.bind(episode_id, None if parent is None else parent.episode_id)
    schema = {"type": "object", "properties": {"received": {"type": "boolean",
        "description": "Whether the child observed the assigned supplied input records."}},
        "required": ["received"], "additionalProperties": False}
    contract = None if parent is None else TypedReportContract("Return selected ATAC input facts", schema, lambda *_: True)
    goal = (EpisodeGoal.root(objective="Verify supplied ATAC input authority", result_contract={"role": role})
        if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
            objective="Verify supplied ATAC input authority", result_contract=schema))
    message = {"scope": scope, "episode_assignment": assigned,
        "initial_report": {} if parent is None else {"received": False}, "knowledge_inheritance": manifest}
    request = EpisodeRequest(goal, Record(message), contract).as_record()
    result = BindingContext(f.run_id, episode_id, role, path, scope, assigned, request)
    if persist:
        f.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        if parent is not None:
            selection = {"kind": "episode_child", "role": role, "assignment": assigned,
                "scope": scope, "purpose": contract.decision, "schema_json": canonical(schema)}
            f.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
                "action": canonical(selection), "result": None, "credit": None})
    return result



@pytest.fixture
def f(tmp_path):
    with Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='ACGTACGT',molecule='dna')
        f=SimpleNamespace(store=store,run_id='atac-input471',scope=store.validate_scope())
        f.journal,f.receipts=Journal(store,f.run_id),EpisodeReceipts(store,f.run_id)
        f.root=context(f)
        f.request=make_request(store)
        f.refs=[row['file']['artifact_ref'] for row in f.request['inputs']]
        f.receipts.receive(f.root.episode_id,f.refs,kind='initial')
        yield f


def validate(f, assignment=None, using=None, access=lambda *_:None):
    return validate_atac_job_inputs(f.store,using or f.root,assignment or make_assignment(f),reference_access=access)


def test_raw_received_bams_do_not_require_or_create_source_records(f):
    before=list(f.store.db.iterdump())
    sources=f.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0]
    assert f.store.reference_subset(f.refs,f.scope)==[]
    assert validate(f)==f.refs
    assert list(f.store.db.iterdump())==before
    assert f.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0]==sources


@pytest.mark.parametrize('role',['launch','launch_local','results'])
def test_exact_inherited_input_prefix_for_constructed_resource_child(f,role):
    child=context(f,parent=f.root,role=role,persist=False)
    assert validate(f,using=child)==f.refs
    extra=identity(f.store,b'new later input')
    f.receipts.receive(f.root.episode_id,[extra['artifact_ref']],kind='own_action')
    f.request['inputs'][0]['file']=extra
    f.request['samples'][0]['input_artifact_refs']=[extra['artifact_ref']]
    with pytest.raises(ValueError,match='input_not_received'):
        validate(f,using=child)


@pytest.mark.parametrize('fault',['run','episode','path','scope','request','role'])
def test_original_context_and_role(f,fault):
    if fault=='run': altered=replace(f.root,run_id='other')
    elif fault=='episode': altered=replace(f.root,episode_id='other')
    elif fault=='path': altered=replace(f.root,path=(('annotation','other'),))
    elif fault=='scope': altered=replace(f.root,scope={'subject_refs':[]})
    elif fault=='role':
        altered=replace(f.root)
        object.__setattr__(altered,'role','launch')
    else:
        request=plain(f.root.request);request['message']['extra']=True
        altered=replace(f.root,request=request)
    with pytest.raises(ValueError,match='invalid_context'):
        validate(f,using=altered)


@pytest.mark.parametrize('fault',['unreceived','protected','metadata','path','input_order','argv','condition'])
def test_exact_input_binding_and_received_authority(f,fault):
    assignment=make_assignment(f)
    job=assignment['requested_job']['native_atac_differential']
    if fault=='unreceived':
        f.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?',(f.refs[0],))
    elif fault=='protected':
        with pytest.raises(ValueError,match='protected_reference_denied'):
            validate(f,assignment,access=lambda *_:False)
        return
    elif fault=='metadata':
        f.store.db.execute('UPDATE artifacts SET size=size+1 WHERE id=?',(f.refs[0],))
    elif fault=='path': job['input_bindings'][0]['path']='/other/path'
    elif fault=='input_order': job['input_bindings'].reverse()
    elif fault=='argv': assignment['requested_job']['argv'][-1]='wrong'
    else: job['request']['inputs'][0]['condition_id']='foreign'
    with pytest.raises(ValueError): validate(f,assignment)


def test_explicit_metadata_source_requires_received_source_record(f):
    raw=f.store.artifact(b'metadata')
    source=f.store.put('source',dict(provider='fixture.reference',accession=None,uri=None,artifact_ref=raw,
        text_ref=None,request_ref=None,version=None,retrieved_at=None),origin='caller')
    f.request['reference']['source_refs']=[source['id']]
    with pytest.raises(ValueError,match='input_not_received'): validate(f)
    f.receipts.receive(f.root.episode_id,[source['id']],kind='own_action')
    assert validate(f)==f.refs+[source['id']]
    f.request['reference']['source_refs']=[raw]
    with pytest.raises(ValueError,match='metadata_source_required'): validate(f)


def test_shared_input_bytes_keep_both_selected_occurrences(f):
    f.request['inputs'][1]['file']=deepcopy(f.request['inputs'][0]['file'])
    f.request['samples'][1]['input_artifact_refs']=[f.refs[0]]
    calls=[]
    assert validate(f,access=lambda _,ref,ns:calls.append(ref))==[f.refs[0]]
    assert calls==[f.refs[0],f.refs[0]]


@pytest.mark.parametrize('state',['missing','changed'])
def test_input_authority_does_not_reopen_inputs_or_install_receipts(f,monkeypatch,state):
    assignment=make_assignment(f)
    for row in assignment['requested_job']['native_atac_differential']['input_bindings']:
        path=Path(row['path'])
        path.unlink() if state=='missing' else path.write_bytes(b'changed')
    before=list(f.store.db.iterdump())
    def forbidden(*a,**k): raise AssertionError('Authority opened science or mutated state')
    for name in ('get_artifact','put','artifact'): monkeypatch.setattr(f.store,name,forbidden)
    for name in ('read_bytes','read_text','stat','lstat','open','resolve'): monkeypatch.setattr(Path,name,forbidden)
    for name in ('__init__','bind','receive'): monkeypatch.setattr(EpisodeReceipts,name,forbidden)
    assert validate(f,assignment)==f.refs
    assert list(f.store.db.iterdump())==before


def test_other_jobs_do_not_install_or_query_context(f):
    assert validate_atac_job_inputs(f.store,None,{'requested_job':{}},reference_access=None)==[]
