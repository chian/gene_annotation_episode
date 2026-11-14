"""Controlled pre-native private profiles, never reconstructed historical Stores.

The retained source files are exact private validator evidence. Selected source
is either the actual installed owner or an explicitly audited candidate supplied
by the parent test command. All exercised APIs are pure metadata validators.
"""
from copy import deepcopy
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType

import pytest
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_contracts as database_current
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_standard_database_contracts as standard_current
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_program_context as context_current
from .retained_blast_manifest_fixtures import database, standard

FIXTURE = Path(__file__).parent/'fixtures/retained_private_producer_profiles'
sha = lambda value: hashlib.sha256(value).hexdigest()


def _source_set(selected):
    metadata=json.loads((FIXTURE/'profiles.json').read_bytes())
    result={}
    current={'database':database_current,'standard_database':standard_current,'context':context_current}
    stage=os.environ.get('A101_PROFILE_CANDIDATE') if selected else None
    candidate=None
    if stage:
        stage=Path(stage);raw=(stage/'native_library.json').read_bytes();candidate=json.loads(raw)
        audit=json.loads((stage/'candidate_audit.json').read_bytes())
        assert audit['passed'] and audit['manifest_sha256']==sha(raw)
    for name,module in current.items():
        if not selected:
            row=metadata['sources'][name];path=FIXTURE/row['file'];raw=path.read_bytes();assert sha(raw)==row['sha256']
        elif candidate is None:
            path=Path(module.__file__);raw=path.read_bytes()
        else:
            relative=Path(module.__file__).resolve().relative_to(Path.cwd()).as_posix()
            matches=[r for r in candidate['files'] if relative in (r['before_path'],r['path'])]
            if matches:
                row,=matches;path=Path(row['proposed']);raw=path.read_bytes();assert sha(raw)==row['after_sha256']
            else:
                # Unchanged database contracts are authenticated against the
                # audited candidate's preserved-file record, not a fallback guess.
                kept,=[r for r in candidate['preserved_files'] if r['path']==relative]
                path=Path(relative);raw=path.read_bytes();assert sha(raw)==kept['sha256']
        result[name]=(path,raw)
    return metadata,result


def _load_source_modules(monkeypatch, selected):
    metadata,sources=_source_set(selected)
    prefix='_controlled_private_profile_'+('selected' if selected else 'retained')
    for name in (prefix,prefix+'.library'):
        package=ModuleType(name);package.__path__=[];monkeypatch.setitem(sys.modules,name,package)
    context_path,context_raw=sources['context']
    # Actual context source is unchanged; both relative import destinations are
    # exact package scaffolding, with no copied or stubbed scientific function.
    context=ModuleType(prefix+'.blast_program_context');context.__package__=prefix;context.__file__=str(context_path)
    exec(compile(context_raw,str(context_path),'exec'),context.__dict__)
    monkeypatch.setitem(sys.modules,prefix+'.blast_program_context',context)
    monkeypatch.setitem(sys.modules,prefix+'.library.blast_program_context',context)
    # Native06 uses an absolute import. Bind its exact destination to the actual
    # selected context source; do not rewrite the candidate import or its body.
    for name in ('gene_annotation_episode.episodic_workflow.root.a101.blast_program_context',
                 'gene_annotation_episode.episodic_workflow.root.a101.library.blast_program_context'):
        monkeypatch.setitem(sys.modules,name,context)
    loaded={}
    for family in ('database','standard_database'):
        path,raw=sources[family];module=ModuleType(prefix+'.native_blast_'+family+'_contracts')
        module.__package__=prefix;module.__file__=str(path)
        tree=ast.parse(raw)
        # These pure owners have no module-location-dependent scientific logic.
        assert not any(isinstance(n,ast.Name) and n.id in {'__name__','__file__','__package__'} for n in ast.walk(tree))
        exec(compile(raw,str(path),'exec'),module.__dict__);loaded[family]=module
    return metadata,loaded


@pytest.fixture
def owners(monkeypatch):
    metadata,old=_load_source_modules(monkeypatch,False)
    _,selected=_load_source_modules(monkeypatch,True)
    return metadata,old,selected


def _validator(module,family,retained=True,bundle=False):
    middle='standard_blast_database' if family=='standard_database' else 'native_blast_database'
    return getattr(module,'validate_'+('retained_' if retained else '')+middle+('_bundle' if bundle else '_producer_manifest'))


def _manifest(metadata,family,private=True):
    profile=metadata['profiles'][family]
    value=database.manifest_for()
    value['version']='native_blast_'+family+'_producer_manifest_v1'
    value['entry_module']=profile['current_entry' if private else 'original_entry']
    value['package_files']=[dict(relative_path=name,sha256='b'*64,size_bytes=10)
        for name in profile['current_required' if private else 'original_required']]
    return value


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('private',(False,True),ids=('original_global','pre_native_private'))
def test_retained_profiles_are_defensive_and_source_identical(owners,monkeypatch,family,private):
    metadata,old,selected=owners;manifest=_manifest(metadata,family,private);before=deepcopy(manifest)
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old[family],selected[family]):
            result=_validator(module,family)(manifest,module_root='/deploy',python_executable='/runtime/python')
            assert result==before and manifest==before and result is not manifest
            result['python']['size_bytes']=99
            assert manifest['python']['size_bytes']==23


@pytest.mark.parametrize('family',('database','standard_database'))
def test_live_producer_does_not_admit_original_global_profile(owners,monkeypatch,family):
    metadata,old,selected=owners;manifest=_manifest(metadata,family,False)
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old[family],selected[family]):
            with pytest.raises(ValueError):
                _validator(module,family,retained=False)(manifest,module_root='/deploy',python_executable='/runtime/python')


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('change',('missing_contract','duplicate_file','runtime_inside_package'))
def test_pre_native_private_profile_rejections_preserve_original_reason(owners,monkeypatch,family,change):
    metadata,old,selected=owners;manifest=_manifest(metadata,family)
    if change=='missing_contract':manifest['package_files']=[r for r in manifest['package_files'] if not r['relative_path'].endswith('_contracts.py')]
    elif change=='duplicate_file':manifest['package_files'].append(deepcopy(manifest['package_files'][0]))
    else:manifest['runtime_files'][0]['path']='/deploy/unowned-runtime'
    before=deepcopy(manifest);errors=[]
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old[family],selected[family]):
            with pytest.raises(ValueError) as caught:
                _validator(module,family)(manifest,module_root='/deploy',python_executable='/runtime/python')
            errors.append((type(caught.value),str(caught.value)))
    assert errors[0]==errors[1] and manifest==before


class _OriginalRetainedFixtureView:
    def __init__(self,module):self.module=module
    def __getattr__(self,name):
        return getattr(self.module,{'validate_standard_blast_database_bundle':'validate_retained_standard_blast_database_bundle'}.get(name,name))


def _bundle(metadata,old,monkeypatch,private):
    with monkeypatch.context() as fixture:
        fixture.setattr(standard,'n',_OriginalRetainedFixtureView(old['standard_database']))
        value=standard.fixture()
    if not private:return value
    value=deepcopy(value);bundle=value['bundle'];verification=bundle['producer_verification'];manifest=verification['manifest']
    profile=metadata['profiles']['standard_database'];manifest['entry_module']=profile['current_entry']
    manifest['package_files']=[dict(relative_path=name,sha256='3'*64,size_bytes=40) for name in profile['current_required']]
    producer_raw=standard.encoded(manifest);digest=standard.sha(producer_raw)
    bundle['plan']['producer_manifest'].update(sha256=digest,size_bytes=len(producer_raw))
    verification['manifest_observed_sha256']=digest
    original_checks=verification['checks'];at=original_checks[0]['checked_at']
    verification['checks']=[deepcopy(original_checks[0]),*[dict(kind='package',path=manifest['module_root']+'/'+r['relative_path'],observed_sha256=r['sha256'],size_bytes=r['size_bytes'],checked_at=at,status='verified') for r in manifest['package_files']]]
    artifact,=[r for r in bundle['artifacts'] if r['artifact_key']=='producer'];artifact.update(sha256=digest,size_bytes=len(producer_raw))
    entry,=[r for r in value['artifact_catalog']['entries'] if r['artifact_key']=='producer'];entry.update(sha256=digest,size_bytes=len(producer_raw))
    value['contents']['artifact-producer']=producer_raw
    value['attempt_identity']['plan_sha256']=standard.sha(standard.encoded(bundle['plan']))
    value['artifact_catalog']['bundle_sha256']=standard.sha(standard.encoded(bundle))
    return value


@pytest.mark.parametrize('private',(False,True),ids=('original_global','pre_native_private'))
def test_complete_retained_standard_bundle_preserves_job_and_attempt(owners,monkeypatch,private):
    metadata,old,selected=owners;value=_bundle(metadata,old,monkeypatch,private)
    bundle=value['bundle'];before=deepcopy(value)
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old['standard_database'],selected['standard_database']):
            actual=_validator(module,'standard_database',bundle=True)(bundle,original_job=value['job'],attempt_identity=value['attempt_identity'])
            assert actual==before['bundle'] and value==before and actual is not bundle


@pytest.mark.parametrize('change',('plan_identity','manifest_observed_hash','original_job'))
def test_private_bundle_custody_rejection_reason_preserved(owners,monkeypatch,change):
    metadata,old,selected=owners;value=_bundle(metadata,old,monkeypatch,True)
    if change=='plan_identity':value['attempt_identity']['plan_sha256']='0'*64
    elif change=='manifest_observed_hash':value['bundle']['producer_verification']['manifest_observed_sha256']='0'*64
    else:value['job']['environment']['EXPLICIT']='altered-independent-job'
    before=deepcopy(value);errors=[]
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old['standard_database'],selected['standard_database']):
            with pytest.raises(ValueError) as caught:
                _validator(module,'standard_database',bundle=True)(value['bundle'],original_job=value['job'],attempt_identity=value['attempt_identity'])
            errors.append((type(caught.value),str(caught.value)))
    assert errors[0]==errors[1] and value==before
