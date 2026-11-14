"""Current monitor descriptors use actual required bytes and original settings.

Fingerprint failure/mutation controls use isolated source copies under pytest's
temporary directory. They never alter the imported implementation or invoke a
native operation, provider, iterator, projector or model.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT_MODULE='gene_annotation_episode.episodic_workflow.root'
HOMES=tuple(prefix+home for prefix in ('','legacy_annotation/','scientific_process/')
    for home in ('execution_monitoring','hpc_coordination/execution_monitoring',
                 'hpc_coordination/hpc_allocation_execution/execution_monitoring'))
ORIGINAL_SHA='118809b224ce84ac5b66d9c481c64b8e7c94ffcd3631e02b3eafad0fcd9b9872'
SHARED=('progress_observations.py','progress_records.py','episode_bindings.py','numerical.py')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def fixture():
    path=Path(__file__).with_name('fixtures')/'monitor_descriptor_sources/expected_members.json'
    value=json.loads(path.read_text())
    assert value['version']=='root_monitor_descriptor_source_members_v1'
    assert {row['home'] for row in value['homes']}==set(HOMES)
    return value


def members(home):
    entry=next(row for row in fixture()['homes'] if row['home']==home)
    names=entry['member_paths']
    assert len(names)==len(set(names))==24
    private=entry['private_files']
    assert len(private)==len(set(private))==20
    assert names==[home+'/'+name for name in sorted(private)]+list(SHARED)
    return names


def bound(home,configured=False):
    module=importlib.import_module(ROOT_MODULE+'.'+home.replace('/','.')+'.binding_identity')
    cls=importlib.import_module(ROOT_MODULE+'.'+home.replace('/','.')+'.episode').MonitorEpisodes
    assert cls.as_record is module.as_record
    assert module.canonical is importlib.import_module(ROOT_MODULE+'.method_loop.durable').canonical
    settings=({'information_unit':3.25,
        'yield_settings':{'kind':'information_accumulation','cutoff':0.375,'uncertainty_alpha':0.125}}
        if configured else {})
    instance=cls(SimpleNamespace(),outcome_page_size=7,**settings)
    return module,instance


def actual_root(module,home):
    root=Path(module.__file__).resolve().parents[len(Path(home).parts)]
    assert root.name=='root' and root.parent.name=='episodic_workflow'
    assert Path(module.__file__).resolve()==root/home/'binding_identity.py'
    return root


def independent_fingerprint(root,home):
    hashes={name:sha((root/name).read_bytes()) for name in members(home)}
    # The descriptor contract is canonical finite JSON of a string->SHA map.
    # Independently encode that map instead of calling its production helper.
    encoded=json.dumps(hashes,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return sha(encoded.encode())


def original_configuration(instance):
    path=Path(__file__).with_name('fixtures')/'original_boundary/episode_monitoring.py.source'
    raw=path.read_bytes();assert sha(raw)==ORIGINAL_SHA
    cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='MonitorEpisodes')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='as_record')
    returned=next(n.value for n in method.body if isinstance(n,ast.Return))
    value=next(value for key,value in zip(returned.keys,returned.values)
        if isinstance(key,ast.Constant) and key.value=='configuration')
    return eval(compile(ast.Expression(body=value),str(path),'eval'),{'self':instance,'deepcopy':deepcopy})


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('configured',(False,True))
def test_actual_descriptor_members_bytes_and_original_configuration(home,configured):
    module,instance=bound(home,configured);root=actual_root(module,home)
    # Exact source tuple and all actual files are checked independently from
    # the dictionary digest; a dropped required file cannot hide behind it.
    tree=ast.parse(Path(module.__file__).read_bytes())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='as_record')
    declaration=next(n for n in function.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='paths' for t in n.targets))
    assert list(ast.literal_eval(declaration.value))==members(home)
    record=instance.as_record()
    assert record=={'version':'root_monitor_private_v1','binding_id':'monitor',
        'implementation_sha256':independent_fingerprint(root,home),
        'configuration':original_configuration(instance)}
    assert record['implementation_sha256']!=ORIGINAL_SHA
    if configured:
        record['configuration']['yield_settings']['cutoff']=999.0
        assert instance.as_record()['configuration']==original_configuration(instance)
        assert instance.yield_settings['cutoff']==0.375


def copied_members(tmp_path,module,home):
    source_root=actual_root(module,home)
    copy_root=tmp_path/'gene_annotation_episode/episodic_workflow/root'
    originals={name:(source_root/name).read_bytes() for name in members(home)}
    for name,raw in originals.items():
        destination=copy_root/name;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(raw)
    return source_root,copy_root,originals


@pytest.mark.parametrize('home',HOMES)
def test_required_private_shared_bytes_change_identity_but_unrelated_bytes_do_not(home,tmp_path,monkeypatch):
    module,instance=bound(home,True)
    source_root,copy_root,originals=copied_members(tmp_path,module,home)
    expected=instance.as_record()
    monkeypatch.setattr(module,'__file__',str(copy_root/home/'binding_identity.py'))
    assert instance.as_record()==expected
    for name in (home+'/task_actions.py','progress_records.py'):
        path=copy_root/name
        path.write_bytes(originals[name]+b'\n# Controlled descriptor byte-change fixture.\n')
        changed=instance.as_record()
        assert changed['implementation_sha256']==independent_fingerprint(copy_root,home)
        assert changed['implementation_sha256']!=expected['implementation_sha256']
        assert changed['configuration']==expected['configuration']
        path.write_bytes(originals[name])
        assert instance.as_record()==expected
    unrelated=copy_root/'unselected_source.py';unrelated.write_text('raise RuntimeError("must never import")\n')
    assert instance.as_record()==expected
    assert all((source_root/name).read_bytes()==raw for name,raw in originals.items())


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('missing',('private','shared'))
def test_missing_required_source_raises_without_old_hash_or_canonical_fallback(home,missing,tmp_path,monkeypatch):
    module,instance=bound(home)
    source_root,copy_root,originals=copied_members(tmp_path,module,home)
    expected=instance.as_record()
    monkeypatch.setattr(module,'__file__',str(copy_root/home/'binding_identity.py'))
    name=home+'/waiting.py' if missing=='private' else 'progress_observations.py'
    path=copy_root/name;path.unlink()
    with pytest.raises(FileNotFoundError) as failure:
        instance.as_record()
    assert Path(failure.value.filename).resolve()==path.resolve()
    path.write_bytes(originals[name]);assert instance.as_record()==expected
    assert all((source_root/name).read_bytes()==raw for name,raw in originals.items())


def test_nine_parent_private_source_identities_are_distinct():
    descriptors={home:bound(home)[1].as_record()['implementation_sha256'] for home in HOMES}
    assert len(set(descriptors.values()))==9
