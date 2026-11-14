"""Four source-qualified metadata profiles, not new historical publications.

Original native6 bundle/plan bytes stay immutable. Private variants are explicit
controlled derivatives; only producer metadata/correlated custody digests change.
No parser, driver, native process, provider, Store or network is executed.
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
from .retained_blast_manifest_fixtures import database, standard

FIXTURE=Path(__file__).parent/'fixtures/remaining30_producer_profiles'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
PROFILES=('original_global','pre_native_private','post_native_private','library_private')
AXIS='gene_annotation_episode.episodic_workflow.root.a101'


def metadata():
    raw=(FIXTURE/'manifest.json').read_bytes();m=json.loads(raw)
    for row in m['assets']:
        assert sha((FIXTURE/row['file']).read_bytes())==row['sha256']
    return m


def selected_sources(m):
    # The source-only overlay is independently audited, not installed or silently
    # treated as historical. The full relocation candidate is accepted separately.
    stage=os.environ.get('A101_REMAINING30_CANDIDATE')
    overlay=os.environ.get('A101_REMAINING30_PROFILE_OVERLAY')
    assert not (stage and overlay)
    if stage or overlay:
        d=Path(stage or overlay);name='remaining30.json' if stage else 'manifest.json'
        raw=(d/name).read_bytes();proposal=json.loads(raw);audit=json.loads((d/'candidate_audit.json').read_bytes())
        assert audit['passed'] and audit['manifest_sha256']==sha(raw)
    result={}
    for family in ('database','standard_database'):
        leaf='native_blast_'+family+'_contracts.py'
        if stage or overlay:
            row,=[r for r in proposal['files'] if Path(r['path']).name==leaf]
            path=Path(row['proposed']) if stage else d/'candidate'/row['path'];raw=path.read_bytes()
            assert sha(raw)==row['after_sha256']
        else:
            root=Path('gene_annotation_episode/episodic_workflow/root/a101')
            choices=[p for p in (root/leaf,root/'library'/leaf) if p.is_file()]
            path,=choices;raw=path.read_bytes()
        result[family]=(str(path),raw)
    return result


def load_owners(monkeypatch,m,selected):
    prefix='_remaining30_profile_'+('selected' if selected else 'captured')
    for package in (prefix,prefix+'.library'):
        module=ModuleType(package);module.__path__=[];monkeypatch.setitem(sys.modules,package,module)
    row=m['source_profiles']['context'];path=FIXTURE/row['file'];raw=path.read_bytes()
    context=ModuleType(prefix+'.blast_program_context');context.__package__=prefix
    exec(compile(raw,str(path),'exec'),context.__dict__)
    for name in (prefix+'.blast_program_context',prefix+'.library.blast_program_context',AXIS+'.library.blast_program_context'):
        monkeypatch.setitem(sys.modules,name,context)
    sources=selected_sources(m) if selected else {f:(str(FIXTURE/m['source_profiles'][f]['file']),(FIXTURE/m['source_profiles'][f]['file']).read_bytes()) for f in ('database','standard_database')}
    result={}
    for family,(path,raw) in sources.items():
        assert not any(isinstance(n,ast.Name) and n.id in {'__file__','__name__','__package__'} for n in ast.walk(ast.parse(raw)))
        module=ModuleType(prefix+'.native_blast_'+family+'_contracts');module.__package__=prefix;module.__file__=path
        exec(compile(raw,path,'exec'),module.__dict__);result[family]=module
    return result


@pytest.fixture
def owners(monkeypatch):
    m=metadata();return m,load_owners(monkeypatch,m,False),load_owners(monkeypatch,m,True)


def validator(module,family,*,retained=True,bundle=False):
    middle='native_blast_database' if family=='database' else 'standard_blast_database'
    return getattr(module,'validate_'+('retained_' if retained else '')+middle+('_bundle' if bundle else '_producer_manifest'))


def declared_manifest(m,family,profile,base=None):
    # Deliberately controlled producer identity; hashes are synthetic metadata,
    # never authenticated source stamps or claimed native deployment evidence.
    result=deepcopy(database.manifest_for() if base is None else base)
    declaration=m['profiles'][family][profile]
    result['version']='native_blast_'+family+'_producer_manifest_v1'
    result['entry_module']=declaration['entry_module']
    result['package_files']=[dict(relative_path=p,sha256='b'*64,size_bytes=10) for p in declaration['required_files']]
    return result


class RetainedFixtureView:
    def __init__(self,owner):self.owner=owner
    def __getattr__(self,name):
        return getattr(self.owner,{'validate_standard_blast_database_bundle':'validate_retained_standard_blast_database_bundle'}.get(name,name))


def original_bundle(m,old,family,monkeypatch):
    if family=='database':
        bundle=json.loads((FIXTURE/'native6_bundle.json').read_bytes())
        plan=json.loads((FIXTURE/'native6_plan.json').read_bytes())
        record=json.loads((FIXTURE/'original_index.json').read_bytes())['native6']
        return dict(bundle=bundle,job=plan['requested_job']['native_blast_database'],attempt_identity=deepcopy(record['attempt_identity']))
    with monkeypatch.context() as guard:
        guard.setattr(standard,'n',RetainedFixtureView(old[family]))
        return standard.fixture()


def controlled_bundle(m,old,family,profile,monkeypatch):
    value=original_bundle(m,old,family,monkeypatch)
    if profile=='original_global':return value
    value=deepcopy(value);bundle=value['bundle'];proof=bundle['producer_verification']
    manifest=declared_manifest(m,family,profile,proof['manifest']);proof['manifest']=manifest
    raw=encoded(manifest);digest=sha(raw);bundle['plan']['producer_manifest'].update(sha256=digest,size_bytes=len(raw))
    proof['manifest_observed_sha256']=digest
    at=proof['checks'][0]['checked_at']
    proof['checks']=[deepcopy(r) for r in proof['checks'] if r['kind']!='package']+[
        dict(kind='package',path=manifest['module_root']+'/'+r['relative_path'],observed_sha256=r['sha256'],size_bytes=r['size_bytes'],checked_at=at,status='verified') for r in manifest['package_files']]
    artifact,=[r for r in bundle['artifacts'] if r['role']=='producer_manifest'];artifact.update(sha256=digest,size_bytes=len(raw))
    value['attempt_identity']['plan_sha256']=sha(encoded(bundle['plan']))
    return value


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('profile',PROFILES)
def test_all_declared_passive_manifest_profiles(owners,monkeypatch,family,profile):
    m,old,new=owners;value=declared_manifest(m,family,profile);before=deepcopy(value)
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        result=validator(new[family],family)(value,module_root=value['module_root'],python_executable=value['python']['path'])
        assert result==before and value==before and result is not value
        if profile!='library_private':
            assert validator(old[family],family)(value,module_root=value['module_root'],python_executable=value['python']['path'])==before


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('profile',PROFILES)
def test_complete_passive_bundle_profiles_preserve_science_and_job(owners,monkeypatch,family,profile):
    m,old,new=owners;value=controlled_bundle(m,old,family,profile,monkeypatch);before=deepcopy(value)
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        result=validator(new[family],family,bundle=True)(value['bundle'],original_job=value['job'],attempt_identity=value['attempt_identity'])
        assert result==before['bundle'] and value==before and result is not value['bundle']
        if profile!='library_private':
            assert validator(old[family],family,bundle=True)(value['bundle'],original_job=value['job'],attempt_identity=value['attempt_identity'])==before['bundle']


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('profile',('pre_native_private','post_native_private','library_private'))
def test_manifest_rejections_keep_complete_original_validation(owners,monkeypatch,family,profile):
    m,old,new=owners;valid=declared_manifest(m,family,profile)
    mutations=(lambda v:v['package_files'].append(deepcopy(v['package_files'][0])),lambda v:v['runtime_files'][0].update(path=v['module_root']+'/inside'),lambda v:v['package_files'][0].update(relative_path='../escape'),lambda v:v.update(entry_module='unrelated.driver'))
    for change in mutations:
        value=deepcopy(valid);change(value);before=deepcopy(value)
        with monkeypatch.context() as guard:
            database.forbid_io(guard)
            with pytest.raises(ValueError):validator(new[family],family)(value,module_root=value['module_root'],python_executable=value['python']['path'])
        assert value==before


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('change',('attempt','job','manifest_hash','contract_missing'))
def test_retained_bundle_custody_is_not_bypassed(owners,monkeypatch,family,change):
    m,old,new=owners;value=controlled_bundle(m,old,family,'post_native_private',monkeypatch)
    if change=='attempt':value['attempt_identity']['plan_sha256']='0'*64
    elif change=='job':value['job']['environment']['EXPLICIT']='changed independent job'
    elif change=='manifest_hash':value['bundle']['producer_verification']['manifest_observed_sha256']='0'*64
    else:value['bundle']['producer_verification']['manifest']['package_files']=[r for r in value['bundle']['producer_verification']['manifest']['package_files'] if not r['relative_path'].endswith('_contracts.py')]
    before=deepcopy(value);messages=[]
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        for module in (old[family],new[family]):
            with pytest.raises(ValueError) as caught:validator(module,family,bundle=True)(value['bundle'],original_job=value['job'],attempt_identity=value['attempt_identity'])
            messages.append(str(caught.value))
    assert messages[0]==messages[1] and value==before


@pytest.mark.parametrize('family',('database','standard_database'))
def test_current_producer_remains_strict_and_permits_extra_package_files(owners,monkeypatch,family):
    m,old,new=owners;value=declared_manifest(m,family,'library_private');value['package_files'].append(dict(relative_path='extra/module.py',sha256='f'*64,size_bytes=1))
    with monkeypatch.context() as guard:
        database.forbid_io(guard)
        assert validator(new[family],family,retained=False)(value,module_root=value['module_root'],python_executable=value['python']['path'])==value
        for profile in PROFILES[:-1]:
            bad=declared_manifest(m,family,profile)
            with pytest.raises(ValueError):validator(new[family],family,retained=False)(bad,module_root=bad['module_root'],python_executable=bad['python']['path'])


def test_required_provenance_keeps_original_native6_bytes_and_profile_relationships():
    m=metadata();index=json.loads((FIXTURE/'original_index.json').read_bytes())['native6']
    assert sha((FIXTURE/'native6_bundle.json').read_bytes())==index['bundle']['sha256']
    assert sha((FIXTURE/'native6_plan.json').read_bytes())==index['plan']['sha256']
    for family,profiles in m['profiles'].items():
        old=set(profiles['post_native_private']['required_files']);new=set(profiles['library_private']['required_files'])
        path='gene_annotation_episode/episodic_workflow/root/a101/native_blast_'+family+'_contracts.py'
        assert old-new=={path} and new-old=={path.rsplit('/',1)[0]+'/library/'+path.rsplit('/',1)[1]}
    assert m['actual_historical_store_claim'] is False
