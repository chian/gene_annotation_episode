"""Authentic Homology descriptor source membership, configuration and old identity.

Source perturbations occur only in copied temporary trees. Passed715 view files
and canonical sources are never changed; real descriptor code/providers execute.
"""
from __future__ import annotations
import ast
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import FunctionType
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
helpers=importlib.import_module(ROOT+'.homology_job_submission.tests.test_homology_original_boundaries')
BASE=Path(__file__).with_name('fixtures')
EXPECTED=json.loads((BASE/'homology_source_identity/expected_members.json').read_text())
CASES=tuple((row['home'],row['class'],row['role']) for row in EXPECTED['homes'])
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def assert_fixed_record_fields(record,expected):
    assert set(record)==set(expected['record_keys'])
    fixed=expected['fixed_record_fields']
    assert {key:record[key] for key in fixed}==fixed
    if expected['home'].startswith('legacy_annotation/'):
        assert fixed['version']=='root_legacy_private_homology_v1'
        assert fixed['commissioning_parent']=='improvement'
        assert fixed['binding_path']==expected['home']
    else:
        assert fixed['version']=='root_private_homology_v1'
        assert 'commissioning_parent' not in record and 'binding_path' not in record


def actual(home,name):
    module=importlib.import_module(ROOT+'.'+home.replace('/','.')+'.binding_identity')
    root=Path(module.__file__).resolve().parents[len(Path(home).parts)]
    cls=getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode'),name)
    jobs=helpers.resource();jobs.directory=Path('/controlled/原始_registry')
    jobs.config={'version':'controlled_registry','registry_ref':'execution_registry_'+'1'*24,'note':'β'}
    binding=helpers.configured(cls,jobs=jobs)
    assert binding.as_record.__func__ is module.as_record
    expected=next(row for row in EXPECTED['homes'] if row['home']==home)
    return module,root,binding,expected


def copied_method(module,root,row,tmp_path):
    tree=(tmp_path/'tree').resolve()
    copied_root=tree/'gene_annotation_episode/episodic_workflow/root'
    for path,digest in row['members'].items():
        raw=(root/path).read_bytes();assert sha(raw)==digest,path
        copied=(copied_root/path).resolve();assert copied.is_relative_to(tree),path
        copied.parent.mkdir(parents=True,exist_ok=True);copied.write_bytes(raw)
    # Same executable code and defining provider objects; only its source-file
    # location points to a copied exact member tree for controlled perturbation.
    globals_=dict(module.as_record.__globals__,__file__=str(copied_root/row['home']/'binding_identity.py'))
    copied=FunctionType(module.as_record.__code__,globals_,module.as_record.__name__,module.as_record.__defaults__,module.as_record.__closure__)
    assert copied.__code__ is module.as_record.__code__
    return copied,copied_root


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('credit',({'version':'controlled_operational','units':['a']},
    {'version':'original_qualification','units':['β','原始']}))
def test_current_real_descriptor_exact_members_and_configuration(home,name,role,credit):
    module,root,binding,expected=actual(home,name)
    provider=importlib.import_module('gene_annotation_episode.execution_contracts')
    assert module.canonical is provider.canonical
    assert (root/'../../execution_contracts.py').resolve()==Path(provider.__file__).resolve()
    binding._role_credit_bindings[role]=deepcopy(credit)
    for path,digest in expected['members'].items():assert sha((root/path).read_bytes())==digest,path
    record=binding.as_record()
    assert_fixed_record_fields(record,expected)
    assert record['binding_id']==role
    assert record['implementation_sha256']==expected['implementation_sha256']
    assert record['registry_directory']==str(binding.jobs.directory)
    assert record['registry_configuration']==binding.jobs.config
    assert record['parser_policy']=={'memory_bytes':1024,'scratch_bytes':2048}
    assert record['credit_binding']==credit and record['statistics'] is None
    record['credit_binding']['units'].append('changed')
    assert binding.binding_for(role)==credit
    declared=ast.parse(Path(module.__file__).read_bytes())
    paths=next(n.value for n in ast.walk(declared) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='paths' for t in n.targets))
    assert ast.literal_eval(paths)==tuple(expected['members'])
    assert expected['new_required_members']==[home+'/internal_summary.py',home+'/yield.py',home+'/waiting.py',
        '../../execution_contracts.py','execution_recording.py','native_events.py']
    assert set(expected['new_required_members'])<=set(expected['members'])
    assert set(expected['substantive_private_sources'])<=set(expected['members'])


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('operand',('own_waiting','shared_serializer','unrelated_owner'))
def test_source_identity_tracks_genuine_operand_changes_only(home,name,role,operand,tmp_path):
    module,root,binding,expected=actual(home,name);method,copied_root=copied_method(module,root,expected,tmp_path)
    before=method(binding);assert before==binding.as_record()
    relative=home+'/waiting.py' if operand=='own_waiting' else '../../execution_contracts.py' if operand=='shared_serializer' else 'unrelated_parent/task.py'
    path=(copied_root/relative).resolve();assert path.is_relative_to(tmp_path/'tree')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((path.read_bytes() if path.exists() else b'')+b'\n# controlled source identity change\n')
    after=method(binding)
    assert (after['implementation_sha256']!=before['implementation_sha256']) is (operand!='unrelated_owner')
    assert {k:v for k,v in after.items() if k!='implementation_sha256'}=={k:v for k,v in before.items() if k!='implementation_sha256'}


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('operand',('internal_summary.py','../../execution_contracts.py','native_events.py'))
def test_missing_required_source_never_claims_current_identity(home,name,role,operand,tmp_path):
    module,root,binding,expected=actual(home,name);method,copied_root=copied_method(module,root,expected,tmp_path)
    path=(copied_root/(operand if operand.startswith('../../') or operand=='native_events.py' else home+'/'+operand)).resolve()
    assert path.is_relative_to(tmp_path/'tree');path.unlink()
    with pytest.raises(FileNotFoundError):method(binding)


def original_serializer():
    nodes=[]
    for name,symbol in (('communication.py.source','plain'),('execution_contracts.py.source','canonical')):
        path=BASE/'original_boundary'/name;raw=path.read_bytes()
        assert sha(raw)==EXPECTED['originals'][name]
        nodes.append(next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==symbol))
    namespace={'Mapping':Mapping,'json':json}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<pinned_original_serializer>','exec'),namespace)
    return namespace['canonical']


def capture(callback):
    try:return ('returned',callback())
    except Exception as error:return ('raised',type(error),str(error))


@pytest.mark.parametrize('value',({'β':('原始',{'Ω':1})},{'none':None,'booleans':[True,False]},
    {'integer':2,'fraction':0.25},{'invalid':float('nan')},{'invalid':float('inf')},
    {'invalid':object()},{1:'integer key','1':'string key'}))
def test_original_unicode_plain_and_invalid_serializer_contract(value):
    module=importlib.import_module('gene_annotation_episode.execution_contracts')
    assert module.plain is importlib.import_module(ROOT+'.communication').plain
    expected=capture(lambda:original_serializer()(value));actual=capture(lambda:module.canonical(value))
    assert actual==expected
    expected_digest=capture(lambda:sha(original_serializer()(value).encode('utf-8')))
    assert capture(lambda:module.digest(value))==expected_digest
    if actual[0]=='returned' and isinstance(value,dict) and 'β' in value:
        assert actual[1]=='{"β":["原始",{"Ω":1}]}' and '\\u' not in actual[1]


@pytest.mark.parametrize('home,name,role',CASES)
def test_historical_family_descriptor_is_not_relabelled_as_current_private_identity(home,name,role):
    module,root,binding,expected=actual(home,name)
    original=helpers.original_class()
    original_file=Path(helpers.__file__).with_name('fixtures')/'original_boundary/homology_episodes.py.source'
    node=next(n for n in ast.parse(original_file.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='_binding')
    namespace={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(original_file),'exec'),namespace)
    original.as_record.__globals__['_binding']=namespace['_binding']
    old=helpers.configured(original,jobs=binding.jobs).as_record();current=binding.as_record()
    assert old['version']=='homology_episode_bindings_v4'
    assert_fixed_record_fields(current,expected)
    assert old['version']!=current['version']
    assert set(old['role_credit_bindings'])=={'job_launch','job_monitor','job_results'}
    for key in ('registry_directory','registry_configuration','parser_policy'):
        assert old[key]==current[key]
    assert 'implementation_sha256' not in old
